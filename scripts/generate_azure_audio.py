#!/usr/bin/env python3
"""Stage, resume, audit and publish the approved Xiaoxiao poetry-reading library.

Dry run by default. --generate --prompt-key synthesizes missing tracks only.
--publish requires complete catalog coverage and publishes the manifest last.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

from generate_audio import atomic_json, probe
from narration_recipe import AZURE_RECIPE, input_hash, poetry_ssml, poetry_ssml_chunks
from prepare_narration_trial import (
    ROOT, AzureHTTPError, AzureTransportError, azure_config,
    prompt_azure_config, synthesize_azure_ssml, normalize_audio,
)

STAGE = ROOT / "output/audio-azure-library"
RELEASE_DIR = "assets/audio/xiaoxiao-poetry-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_poems(root=ROOT):
    catalog = json.loads((root / "data/reader/catalog.json").read_text())
    return [json.loads((root / f'data/reader/poems/{p["id"]}.json').read_text())
            for p in catalog["poems"]]


def record(poem, path, duration):
    return {"id": poem["id"], "title": poem["title"], "author": poem["author"],
            "file": f'{RELEASE_DIR}/{poem["id"]}.mp3', "duration": duration,
            "bytes": path.stat().st_size, "sha256": digest(path),
            "ssmlSHA256": hashlib.sha256(poetry_ssml(poem).encode()).hexdigest(),
            "inputSHA256": input_hash(poem, AZURE_RECIPE)}


def valid_record(poem, item, path):
    return (item.get("id") == poem["id"] and item.get("title") == poem["title"]
            and item.get("author") == poem["author"]
            and item.get("file") == f'{RELEASE_DIR}/{poem["id"]}.mp3'
            and item.get("inputSHA256") == input_hash(poem, AZURE_RECIPE)
            and path.is_file() and item.get("bytes") == path.stat().st_size
            and item.get("sha256") == digest(path))


def save_manifest(poems, records, stage):
    sections = {p["id"]: p["section"] for p in json.loads((ROOT / "data/reader/catalog.json").read_text())["poems"]}
    for identity, item in records.items():
        item["section"] = sections.get(identity, "诗词")
    value = {"schemaVersion": 1, "recipe": AZURE_RECIPE, "release": "full",
             "trackOrder": [p["id"] for p in poems],
             "tracks": {p["id"]: records[p["id"]] for p in poems if p["id"] in records}}
    atomic_json(stage / "manifest.json", value)
    return value


def reuse_approved_samples(poems, records, stage):
    samples = ROOT / "output/tts-trial/poetry-reading"
    manifest = samples / "manifest.json"
    candidates = {}
    if manifest.is_file():
        for item in json.loads(manifest.read_text()):
            candidates[item["id"]] = (samples / f'{item["id"]}-xiaoxiao.mp3', item)
    recital = ROOT / "output/tts-trial/recitation"
    if (recital / "manifest.json").is_file():
        for item in json.loads((recital / "manifest.json").read_text()):
            if item["id"] == "e-xiaoxiao-poetry":
                candidates["tang-236-deng-guan-que-lou"] = (recital / "e-xiaoxiao-poetry.mp3", item)
    for poem in poems:
        identity = poem["id"]
        if identity in records or identity not in candidates:
            continue
        path, item = candidates[identity]
        if (item.get("voice") == AZURE_RECIPE["voice"] and item.get("style") == AZURE_RECIPE["style"]
                and item.get("audioSha256") == digest(path)
                and item.get("ssmlSha256") == hashlib.sha256(poetry_ssml(poem).encode()).hexdigest()):
            target = stage / "audio" / f"{identity}.mp3"
            shutil.copy2(path, target)
            records[identity] = record(poem, target, probe(target))
            print(f'复用已认可样音：{poem["title"]}', flush=True)


class RequestPacer:
    """At most 18 request starts per minute, including retries, for Azure F0."""
    def __init__(self, interval=3.5, clock=time.monotonic, sleep=time.sleep):
        self.interval, self.clock, self.sleep = interval, clock, sleep
        self.next_start = 0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            delay = self.next_start - self.clock()
            if delay > 0:
                self.sleep(delay)
            self.next_start = self.clock() + self.interval


def synthesize_with_retry(ssml, target, credentials, pacer, normalize=True):
    for attempt in range(6):
        pacer.wait()
        try:
            return synthesize_azure_ssml(ssml, target, credentials, normalize=normalize)
        except (AzureTransportError, AzureHTTPError) as error:
            transient = isinstance(error, AzureTransportError) or error.status in (408, 429, 500, 502, 503, 504)
            if not transient or attempt == 5:
                raise
            delay = min(60, (15 if isinstance(error, AzureHTTPError) else 2) * 2 ** attempt)
            reason = f'HTTP {error.status}' if isinstance(error, AzureHTTPError) else "传输中断"
            print(f'  {target.stem} {reason}，{delay} 秒后重试（{attempt + 1}/5）。', flush=True)
            time.sleep(delay)


def synthesize_chunked(poem, target, credentials, pacer):
    """Recovery for repeatedly interrupted long transfers; normalize once after joining."""
    from imageio_ffmpeg import get_ffmpeg_exe
    folder = STAGE / 'chunks' / poem['id']
    folder.mkdir(parents=True, exist_ok=True)
    drafts = poetry_ssml_chunks(poem)
    index = folder / 'manifest.json'
    cache = json.loads(index.read_text()) if index.exists() else {}
    records = cache.get('chunks', {}) if cache.get('recipe') == AZURE_RECIPE else {}
    paths = []
    for number, ssml in enumerate(drafts):
        name = f'{number:03d}'
        path = folder / f'{name}.mp3'
        (folder / f'{name}.ssml').write_text(ssml)
        fingerprint = hashlib.sha256(ssml.encode()).hexdigest()
        item = records.get(name, {})
        if not (path.is_file() and item.get('ssmlSHA256') == fingerprint and item.get('sha256') == digest(path)):
            duration = synthesize_with_retry(ssml, path, credentials, pacer, normalize=False)
            records[name] = {'ssmlSHA256': fingerprint, 'sha256': digest(path), 'duration': duration}
            atomic_json(index, {'recipe': AZURE_RECIPE, 'chunks': records})
        paths.append(path)
        print(f'  {poem["title"]} 分段 {number + 1}/{len(drafts)} 已完成', flush=True)
    concat = folder / 'join.ffconcat'
    concat.write_text('ffconcat version 1.0\n' + ''.join(f"file '{path.name}'\n" for path in paths))
    with tempfile.TemporaryDirectory(prefix='.azure-join-', dir=target.parent) as temporary:
        joined, final = Path(temporary) / 'joined.mp3', Path(temporary) / 'final.mp3'
        subprocess.run([get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
                        '-i', str(concat), '-c', 'copy', str(joined)], check=True)
        duration = normalize_audio(joined, final)
        os.replace(final, target)
    return duration


def audit(poems, stage=STAGE, decode=False):
    manifest = json.loads((stage / "manifest.json").read_text())
    expected = {p["id"] for p in poems}
    if (manifest.get("recipe") != AZURE_RECIPE or manifest.get("release") != "full"
            or set(manifest["tracks"]) != expected
            or manifest.get("trackOrder") != [p["id"] for p in poems]):
        raise ValueError("Full audio library is incomplete or uses a different recipe")
    if {p.stem for p in (stage / "audio").glob("*.mp3")} != expected:
        raise ValueError("Staged audio membership differs from catalog")
    total = 0
    for poem in poems:
        path = stage / "audio" / f'{poem["id"]}.mp3'
        item = manifest["tracks"][poem["id"]]
        if not valid_record(poem, item, path):
            raise ValueError(f'Audio hash/input mismatch: {poem["id"]}')
        ssml = stage / "ssml" / f'{poem["id"]}.ssml'
        if ssml.read_text() != poetry_ssml(poem) or digest(ssml) != item["ssmlSHA256"]:
            raise ValueError(f'SSML mismatch: {poem["id"]}')
        if item.get('synthesisMode') == 'couplet-chunks':
            drafts = poetry_ssml_chunks(poem)
            folder = stage / 'chunks' / poem['id']
            cache = json.loads((folder / 'manifest.json').read_text())
            if cache.get('recipe') != AZURE_RECIPE or item.get('chunkCount') != len(drafts):
                raise ValueError(f'Chunk recipe mismatch: {poem["id"]}')
            for number, draft in enumerate(drafts):
                name = f'{number:03d}'
                piece = cache['chunks'][name]
                if ((folder / f'{name}.ssml').read_text() != draft
                        or piece['ssmlSHA256'] != hashlib.sha256(draft.encode()).hexdigest()
                        or piece['sha256'] != digest(folder / f'{name}.mp3')):
                    raise ValueError(f'Chunk input/audio mismatch: {poem["id"]}/{name}')
        duration = probe(path)
        # Catch empty/partial responses as well as the service's 10 minute cutoff.
        characters = sum(len(token[0]) for line in poem["rubyLines"] for token in line)
        if abs(duration - item["duration"]) > 0.05 or not max(3, characters / 10) < duration < 599:
            raise ValueError(f'Unexpected audio duration: {poem["id"]}')
        if decode:
            from imageio_ffmpeg import get_ffmpeg_exe
            subprocess.run([get_ffmpeg_exe(), "-nostdin", "-v", "error", "-xerror", "-i", str(path),
                            "-f", "null", "-"], check=True, stdout=subprocess.DEVNULL)
        total += duration
    return {"tracks": len(expected), "seconds": round(total, 3),
            "bytes": sum(t["bytes"] for t in manifest["tracks"].values()),
            "recipe": AZURE_RECIPE, "allFilesDecoded": decode}


def publish(poems, stage=STAGE, root=ROOT):
    stats = audit(poems, stage, decode=True)
    target = root / RELEASE_DIR
    target.parent.mkdir(parents=True, exist_ok=True)
    # Immutable version directory, then atomic manifest switch. Existing players
    # can finish old files; a failure before the switch leaves the old release live.
    if target.exists():
        if {p.name: digest(p) for p in target.glob("*.mp3")} != {
                p.name: digest(p) for p in (stage / "audio").glob("*.mp3")}:
            raise ValueError("Release directory already contains different audio; use a new recipe version")
    else:
        temporary = Path(tempfile.mkdtemp(prefix=".azure-publish-", dir=target.parent))
        try:
            for source in (stage / "audio").glob("*.mp3"):
                shutil.copy2(source, temporary / source.name)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    previous = root / "data/audio/manifest.json"
    if previous.exists() and not (stage / "previous-manifest.json").exists():
        shutil.copy2(previous, stage / "previous-manifest.json")
    previous.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(previous, json.loads((stage / "manifest.json").read_text()))
    atomic_json(stage / "audit.json", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--generate", action="store_true")
    parser.add_argument("--prompt-key", action="store_true")
    parser.add_argument("--region", default="eastasia")
    parser.add_argument("--reuse-voice-check", action="store_true", help="Reuse a recently verified voice cache for the same resource and region")
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--audit", action="store_true")
    parser.add_argument("--jobs", type=int, choices=(1, 2, 3, 6), default=6)
    parser.add_argument("--chunked", action="store_true", help="Recover missing long tracks with cached couplet chunks; normalize only after joining")
    args = parser.parse_args()
    if args.prompt_key and not args.generate:
        parser.error("--prompt-key requires --generate")
    STAGE.mkdir(parents=True, exist_ok=True)
    with (STAGE / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        poems = load_poems()
        if args.publish or args.audit:
            print(json.dumps(publish(poems) if args.publish else audit(poems, decode=True), ensure_ascii=False))
            return
        for folder in ("audio", "ssml"):
            (STAGE / folder).mkdir(exist_ok=True)
        previous = json.loads((STAGE / "manifest.json").read_text()) if (STAGE / "manifest.json").exists() else {}
        records = {}
        for poem in poems:
            identity = poem["id"]
            draft = poetry_ssml(poem)
            (STAGE / "ssml" / f"{identity}.ssml").write_text(draft)
            item = previous.get("tracks", {}).get(identity, {})
            if previous.get("recipe") == AZURE_RECIPE and valid_record(poem, item, STAGE / "audio" / f"{identity}.mp3"):
                records[identity] = item
        reuse_approved_samples(poems, records, STAGE)
        save_manifest(poems, records, STAGE)
        chars = sum(sum(len(t[0]) for line in p["rubyLines"] for t in line) + len(p["title"]) + len(p["author"]) + 6 for p in poems)
        print(f'整库 {len(poems)} 首，朗读文本约 {chars} 字；已就绪 {len(records)} 首，待生成 {len(poems) - len(records)} 首。', flush=True)
        if not args.generate or len(records) == len(poems):
            return
        credentials = prompt_azure_config(args.region) if args.prompt_key else azure_config()
        from prepare_recitation_variants import verify_voice_styles
        verify_voice_styles(credentials, reuse=args.reuse_voice_check)
        pacer = RequestPacer()
        failures = []
        executor = ThreadPoolExecutor(max_workers=args.jobs)
        renderer = synthesize_chunked if args.chunked else synthesize_with_retry
        futures = {executor.submit(renderer, poem if args.chunked else poetry_ssml(poem),
                                   STAGE / "audio" / f'{poem["id"]}.mp3', credentials, pacer): poem
                   for poem in poems if poem["id"] not in records}
        try:
            for future in as_completed(futures):
                poem = futures[future]
                identity = poem["id"]
                target = STAGE / "audio" / f"{identity}.mp3"
                try:
                    duration = future.result()
                except (AzureTransportError, AzureHTTPError) as error:
                    if isinstance(error, AzureHTTPError) and error.status in (401, 403):
                        raise
                    failures.append({"id": identity, "error": str(error)})
                    atomic_json(STAGE / "failures.json", failures)
                    print(f'暂未完成：{poem["title"]}，已保留进度。', flush=True)
                    continue
                records[identity] = record(poem, target, duration)
                if args.chunked:
                    records[identity]['synthesisMode'] = 'couplet-chunks'
                    records[identity]['chunkCount'] = len(poetry_ssml_chunks(poem))
                save_manifest(poems, records, STAGE)
                print(f'[{len(records)}/{len(poems)}] {poem["title"]} · {duration:.2f}s', flush=True)
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
        atomic_json(STAGE / "failures.json", failures)
        if failures:
            raise ValueError(f'{len(failures)} 首待重试，重新运行同一命令可续做；正式音频尚未替换。')
        print(json.dumps(audit(poems), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, BlockingIOError) as error:
        raise SystemExit(str(error)) from None

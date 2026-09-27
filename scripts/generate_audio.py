#!/usr/bin/env python3
"""Generate resumable offline narration using edge-tts's supported plain-text API.

Install requirements-audio.txt, then run with the same Python.
Only title, author and verse are submitted to the speech service. Displayed
poems are never modified. --ids can generate a small preview before a full run.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECIPE = {"version": 1, "engine": "edge-tts", "engineVersion": "7.2.8",
          "voice": "zh-CN-YunxiNeural", "voiceLabel": "云希 · 男声",
          "rate": "-15%", "pitch": "+0Hz", "loudnessLUFS": -18,
          "bitrate": "64k", "sampleRate": 24000}
# Pronunciation-only aliases: no custom SSML, phoneme markup or display edits.
TITLE_ALIASES = {"tang-224-lu-chai": "鹿寨"}
PREVIEW_IDS = ["tang-224-lu-chai", "tang-232-chun-xiao", "tang-233-ye-si",
               "tang-236-deng-guan-que-lou", "tang-273-feng-qiao-ye-po"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def narration_text(poem):
    lines = [TITLE_ALIASES.get(poem["id"], poem["title"]) + "。",
             "唐代，" + poem["author"] + "。"]
    for tokens in poem["rubyLines"]:
        line = "".join(token[0] for token in tokens).strip()
        if not line:
            continue
        # A sentence stop gives each verse space without unsupported <break> tags.
        if line[-1] not in "。！？!?":
            line = line.rstrip("，,；;、：:") + "。"
        lines.append(line)
    return "\n".join(lines)


def probe(path):
    from mutagen.mp3 import MP3
    stream = MP3(path).info
    duration = stream.length
    if duration <= 1 or stream.sample_rate != 24000 or stream.channels != 1:
        raise ValueError(f"Invalid narration: {path}")
    return round(duration, 3)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


async def generate(args):
    import edge_tts
    from imageio_ffmpeg import get_ffmpeg_exe
    ffmpeg = get_ffmpeg_exe()
    # Fail before contacting the speech service if the local processor is broken.
    check = await asyncio.create_subprocess_exec(ffmpeg, "-version", stdout=asyncio.subprocess.DEVNULL)
    if await check.wait():
        raise RuntimeError("The bundled ffmpeg could not run")
    recipe = dict(RECIPE)
    recipe["voice"] = args.voice
    recipe["voiceLabel"] = "晓晓 · 女声" if args.voice == "zh-CN-XiaoxiaoNeural" else "云希 · 男声"
    catalog = json.loads((ROOT / "data/reader/catalog.json").read_text())["poems"]
    index_path = ROOT / "data/audio/manifest.json"
    output = ROOT / "assets/audio"
    output.mkdir(parents=True, exist_ok=True)
    previous = json.loads(index_path.read_text()) if index_path.exists() else {}
    selection = args.ids if args.ids else ([p["id"] for p in catalog] if args.all else PREVIEW_IDS)
    records = previous.get("tracks", {}) if previous.get("recipe") == recipe else {}
    # Never keep orphaned records when the catalogue changes.
    records = {key: value for key, value in records.items() if key in selection}
    failed = []
    completed = 0
    lock = asyncio.Semaphore(args.jobs)

    def save():
        atomic_json(index_path, {"schemaVersion": 1, "recipe": recipe,
                                "release": "full" if args.all else "preview", "previewIDs": selection,
                                "tracks": dict(sorted(records.items()))})

    async def one(summary):
        nonlocal completed
        async with lock:
            identity = summary["id"]
            poem = json.loads((ROOT / f"data/reader/poems/{identity}.json").read_text())
            spoken = narration_text(poem)
            input_hash = sha(json.dumps({"text": spoken, "recipe": recipe}, sort_keys=True,
                                       ensure_ascii=False).encode())
            target = output / f"{identity}.mp3"
            prior = records.get(identity, {})
            if (prior.get("inputSHA256") == input_hash and target.exists()
                    and prior.get("sha256") == sha(target.read_bytes())):
                completed += 1
                print(f"REUSE {completed}: {poem['title']}", flush=True)
                return
            for attempt in range(4):
                try:
                    with tempfile.TemporaryDirectory(prefix=".tts-", dir=output) as temporary:
                        raw = Path(temporary) / "raw.mp3"
                        processed = Path(temporary) / "narration.mp3"
                        await edge_tts.Communicate(spoken, voice=recipe["voice"],
                                                   rate=recipe["rate"], pitch=recipe["pitch"]).save(str(raw))
                        # Consistent, comfortable playback volume; no music over the verse.
                        process = await asyncio.create_subprocess_exec(
                            ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(raw),
                            "-af", "loudnorm=I=-18:TP=-1.5:LRA=11,apad=pad_dur=0.5",
                            "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
                            str(processed), stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.PIPE)
                        _, stderr = await process.communicate()
                        if process.returncode:
                            raise RuntimeError(stderr.decode())
                        duration = probe(processed)
                        os.replace(processed, target)
                    records[identity] = {"id": identity, "title": poem["title"], "author": poem["author"],
                                         "file": str(target.relative_to(ROOT)), "duration": duration,
                                         "bytes": target.stat().st_size, "sha256": sha(target.read_bytes()),
                                         "inputSHA256": input_hash}
                    completed += 1
                    save()
                    print(f"OK {completed}: {poem['title']} ({duration:.1f}s)", flush=True)
                    return
                except Exception as error:
                    print(f"RETRY {identity} {attempt + 1}: {type(error).__name__}: {error}", flush=True)
                    if attempt < 3:
                        await asyncio.sleep(2 ** (attempt + 1))
            failed.append(identity)

    selected = [p for p in catalog if p["id"] in selection]
    unknown = set(selection) - {p["id"] for p in catalog}
    if unknown:
        raise ValueError(f"Unknown poem IDs: {unknown}")
    await asyncio.gather(*(one(poem) for poem in selected))
    save()
    print(json.dumps({"completed": completed, "totalTracks": len(records), "failed": failed}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--all", action="store_true", help="explicitly generate the full catalogue instead of the five-poem preview")
    parser.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--voice", choices=["zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"], default=RECIPE["voice"])
    options = parser.parse_args()
    asyncio.run(generate(options))

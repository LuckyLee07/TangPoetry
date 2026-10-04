#!/usr/bin/env python3
"""Prepare/resume isolated volume-2 narration; dry run never loads credentials.

Publishing requires all 305 decoded tracks and a current, per-track listening
record in output/audio-azure-volume-2/listening-review.json. Complete each row
only after listening to that exact file: status=approved-after-listening,
reviewedBy, reviewedAt (ISO 8601 with timezone), inputSHA256 and audioSHA256.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import build_volume2_reader as reader_builder
import generate_azure_audio as pipeline
from generate_audio import atomic_json
from narration_recipe import AZURE_RECIPE, input_hash, poetry_ssml
from prepare_narration_trial import AzureHTTPError, AzureTransportError, azure_config, prompt_azure_config
from volume2_narration_release import LISTENING_REVIEW_FILE, approved_listening_row, validate_volume2_manifest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/reader-volume-2/catalog.json'
STAGE = ROOT / 'output/audio-azure-volume-2'
RELEASE = 'assets/volume-2/audio/xiaoxiao-poetry-v1'
MANIFEST = ROOT / 'data/audio-volume-2/manifest.json'
pipeline.STAGE = STAGE
pipeline.RELEASE_DIR = RELEASE


def load():
    """Reject stale reader text/mappings without re-reading the original PNGs."""
    base = ROOT / 'data/expansion/tang-second-volume'
    try:
        report = json.loads((CATALOG.parent / 'build-report.json').read_text())
        inputs = {
            'productionSHA256': base / 'production.json',
            'metadataSHA256': base / 'display-metadata.json',
            'displayGlyphsSHA256': base / 'display-glyphs.json',
            'archivalPoemsSHA256': base / 'poems.json',
        }
        for key, path in inputs.items():
            if report.get(key) != pipeline.digest(path):
                raise ValueError(f'Reader build-report no longer matches {path.name}')
        production = json.loads(inputs['productionSHA256'].read_text())
        source = json.loads(inputs['archivalPoemsSHA256'].read_text())
        assets = json.loads((base / 'delivery-assets.json').read_text())
        expected_catalog, expected_details = reader_builder.reader_entries(production, source, assets)
        catalog = json.loads(CATALOG.read_text())
        if catalog != expected_catalog:
            raise ValueError('Reader catalog differs from the current production/display mapping')
        poems = []
        for entry in catalog['poems']:
            identity = entry['id']
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', identity):
                raise ValueError(f'Invalid narration filename identity: {identity}')
            poem = json.loads((CATALOG.parent / 'poems' / f'{identity}.json').read_text())
            if poem != expected_details[identity]:
                raise ValueError(f'Reader detail differs from the current production/display mapping: {identity}')
            poems.append(poem)
        if len(poems) != 305 or len({p['id'] for p in poems}) != 305:
            raise ValueError('Volume 2 requires all 305 distinct poems')
        return poems
    except (OSError, KeyError, TypeError, AssertionError, ValueError) as error:
        raise ValueError(f'第二卷阅读数据缺失或已过期：{error}。请先运行 python3 scripts/build_volume2_reader.py，再准备音频。') from None


def save(poems, records):
    value = {
        'schemaVersion': 1, 'volume': 'volume-2', 'recipe': AZURE_RECIPE,
        'release': 'full' if len(records) == len(poems) else 'staged',
        'productionSHA256': pipeline.digest(ROOT / 'data/expansion/tang-second-volume/production.json'),
        'catalogSHA256': pipeline.digest(CATALOG),
        'trackOrder': [p['id'] for p in poems],
        'tracks': {p['id']: {**records[p['id']], 'section': p['section']}
                   for p in poems if p['id'] in records},
    }
    atomic_json(STAGE / 'manifest.json', value)
    return value


def read_listening_review():
    path = STAGE / 'listening-review.json'
    if not path.is_file():
        return {'schemaVersion': 1, 'volume': 'volume-2', 'recipe': AZURE_RECIPE, 'tracks': {}}
    review = json.loads(path.read_text())
    if (review.get('schemaVersion') != 1 or review.get('volume') != 'volume-2'
            or review.get('recipe') != AZURE_RECIPE or not isinstance(review.get('tracks'), dict)):
        raise ValueError('第二卷试听记录格式或朗读配方不符，请使用本卷 listening-review.json 重新逐首试听。')
    return review


def prepare_listening_review(poems, records):
    """Prepare pending rows; preserve completed reviews and their exact hashes."""
    review = read_listening_review()
    ids = {p['id'] for p in poems}
    if set(review['tracks']) - ids:
        raise ValueError('第二卷试听记录包含本卷目录以外的曲目。')
    for poem in poems:
        identity = poem['id']
        row = review['tracks'].setdefault(identity, {
            'status': 'pending', 'reviewedBy': '', 'reviewedAt': '', 'notes': '',
        })
        if not isinstance(row, dict):
            raise ValueError(f'第二卷试听记录条目无效：{identity}')
        if row.get('status') == 'pending':
            row['inputSHA256'] = input_hash(poem, AZURE_RECIPE)
            row['audioSHA256'] = records.get(identity, {}).get('sha256')
    atomic_json(STAGE / 'listening-review.json', review)
    return review


def listening_progress(poems, records, review=None):
    review = read_listening_review() if review is None else review
    rows = review['tracks']
    pending = [p['id'] for p in poems if not approved_listening_row(rows.get(p['id']), records.get(p['id']))]
    if set(rows) - {p['id'] for p in poems}:
        raise ValueError('第二卷试听记录包含本卷目录以外的曲目。')
    approved = len(poems) - len(pending)
    status = 'complete' if not pending else 'in-progress' if approved else 'not-started'
    return {'status': status, 'approvedTracks': approved, 'pendingTracks': len(pending), 'pendingIDs': pending}


def require_listening_review(poems, records):
    progress = listening_progress(poems, records)
    if progress['pendingTracks']:
        sample = '、'.join(progress['pendingIDs'][:3])
        raise ValueError(f"第二卷仍有 {progress['pendingTracks']} 首待逐首试听或试听记录已过期（例如 {sample}）。"
                         '请完整试听对应文件后填写 listening-review.json 的 approved-after-listening、'
                         'reviewedBy、带时区的 reviewedAt，并保留匹配的 inputSHA256/audioSHA256，再运行 --publish。')
    return progress


def write_plan(poems, records, review):
    progress = listening_progress(poems, records, review)
    # Inspect names/file presence only. A dry run never reads secret values.
    credentials_present = {'SPEECH_KEY', 'SPEECH_REGION'} <= set(os.environ)
    credentials_present = credentials_present or (ROOT / '.env.azure-speech.local').is_file()
    base = ROOT / 'data/expansion/tang-second-volume'
    plan = {
        'schemaVersion': 1, 'volume': 'volume-2', 'poems': len(poems), 'recipe': AZURE_RECIPE,
        'productionSHA256': pipeline.digest(base / 'production.json'),
        'displayGlyphsSHA256': pipeline.digest(base / 'display-glyphs.json'),
        'catalogSHA256': pipeline.digest(CATALOG),
        'readyTracks': len(records), 'pendingTracks': len(poems) - len(records),
        'sourceCharacters': sum(sum(len(t[0]) for line in p['rubyLines'] for t in line) for p in poems),
        'speechCredentialsConfigured': bool(credentials_present),
        'generationCommand': 'python3 scripts/generate_volume2_audio.py --generate',
        'publishCommand': 'python3 scripts/generate_volume2_audio.py --publish',
        'listeningReviewFile': 'output/audio-azure-volume-2/listening-review.json',
        'listeningReviewStatus': progress['status'],
        'listeningApprovedTracks': progress['approvedTracks'],
        'listeningPendingTracks': progress['pendingTracks'],
        'limits': ['Prepared SSML is not generated audio or listening approval',
                   'Rare characters and polyphonic readings require targeted listening checks',
                   'Credential presence is reported without loading or validating secret values'],
    }
    atomic_json(STAGE / 'plan.json', plan)
    atomic_json(base / 'audio-plan.json', plan)
    return plan


def publish(poems):
    staged = json.loads((STAGE / 'manifest.json').read_text())
    if staged.get('volume') != 'volume-2':
        raise ValueError('第二卷正式音频只能来自本卷 staging manifest。')
    progress = require_listening_review(poems, staged.get('tracks', {}))
    stats = pipeline.audit(poems, stage=STAGE, decode=True)
    stats['listeningApprovedTracks'] = progress['approvedTracks']
    target = ROOT / RELEASE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if ({p.name: pipeline.digest(p) for p in target.glob('*.mp3')}
                != {p.name: pipeline.digest(p) for p in (STAGE / 'audio').glob('*.mp3')}):
            raise ValueError('Existing release differs; choose a fresh version directory')
    else:
        temporary = Path(tempfile.mkdtemp(prefix='.volume2-audio-', dir=target.parent))
        try:
            for path in (STAGE / 'audio').glob('*.mp3'):
                shutil.copy2(path, temporary / path.name)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    permanent_review = ROOT / LISTENING_REVIEW_FILE
    previous_review = permanent_review.read_bytes() if permanent_review.exists() else None
    try:
        atomic_json(permanent_review, read_listening_review())
        release_manifest = {**staged, 'listeningReviewStatus': 'complete',
                            'listeningReviewFile': LISTENING_REVIEW_FILE,
                            'listeningReviewSHA256': pipeline.digest(permanent_review)}
        # Verify copied files and permanent evidence before switching the manifest.
        validate_volume2_manifest(ROOT, json.loads(CATALOG.read_text()),
                                  {p['id']: p for p in poems}, release_manifest)
        atomic_json(MANIFEST, release_manifest)
    except BaseException:
        # The old manifest still binds the old proof until publication succeeds.
        if previous_review is None:
            permanent_review.unlink(missing_ok=True)
        else:
            temporary = permanent_review.with_suffix('.tmp')
            temporary.write_bytes(previous_review)
            os.replace(temporary, permanent_review)
        raise
    atomic_json(STAGE / 'audit.json', stats)
    return stats


def synthesize_curl_ssml(ssml, target, credentials, normalize=True):
    """Use native HTTP/2 without putting the Speech key in arguments or files."""
    import certifi
    key, region = credentials
    if not isinstance(key, str) or not key or any(character.isspace() for character in key):
        raise ValueError('Invalid Speech credential value; no request was sent')
    header = ('Ocp-Apim-Subscription-Key: ' + key).replace('\\', '\\\\').replace('"', '\\"')
    configuration = f'header = "{header}"\n'
    # Config/env generation remains supported, but credentials never enter the
    # curl child environment. Only the private stdin configuration carries them.
    environment = {name: os.environ[name] for name in os.environ if name not in ('SPEECH_KEY', 'SPEECH_REGION')}
    with tempfile.TemporaryDirectory(prefix='.azure-curl-', dir=target.parent) as temporary:
        draft, raw, final = [Path(temporary) / name for name in ('request.ssml', 'raw.mp3', 'normalized.mp3')]
        draft.write_text(ssml, encoding='utf-8')
        command = ['/usr/bin/curl', '-q', '--http2', '--silent', '--show-error', '--config', '-',
                   '--connect-timeout', '30', '--max-time', '120', '--cacert', certifi.where(),
                   '--request', 'POST', '--header', 'Content-Type: application/ssml+xml',
                   '--header', 'X-Microsoft-OutputFormat: audio-24khz-96kbitrate-mono-mp3',
                   '--header', 'User-Agent: TangPoetryVolume2Narration', '--data-binary', f'@{draft}',
                   '--output', str(raw), '--write-out', '%{http_code}',
                   f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1']
        try:
            response = subprocess.run(command, input=configuration.encode('utf-8'), env=environment,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=130)
        except (OSError, subprocess.TimeoutExpired):
            raise AzureTransportError('Azure curl transport failed or timed out (HTTP 0)') from None
        value = response.stdout.decode('ascii', errors='ignore').strip()
        status = int(value) if re.fullmatch(r'[0-9]{3}', value) else 0
        if 400 <= status < 500:
            raise AzureHTTPError(status, f'Azure curl HTTP {status} (exit {response.returncode})')
        if response.returncode != 0 or status != 200:
            raise AzureTransportError(f'Azure curl transport failed (exit {response.returncode}; HTTP {status})')
        if not raw.is_file() or not raw.stat().st_size:
            raise AzureTransportError('Azure curl transport returned no audio (exit 0; HTTP 200)')
        duration = pipeline.normalize_audio(raw, final) if normalize else pipeline.probe(raw)
        os.replace(final if normalize else raw, target)
    return duration


def synthesize_curl_with_retry(ssml, target, credentials, pacer, normalize=True):
    """Apply the existing retry schedule to the isolated second-volume transport."""
    for attempt in range(6):
        pacer.wait()
        try:
            return synthesize_curl_ssml(ssml, target, credentials, normalize=normalize)
        except (AzureTransportError, AzureHTTPError) as error:
            transient = isinstance(error, AzureTransportError) or error.status in (408, 429, 500, 502, 503, 504)
            if not transient or attempt == 5:
                raise
            delay = min(60, (15 if isinstance(error, AzureHTTPError) else 2) * 2 ** attempt)
            reason = f'HTTP {error.status}' if isinstance(error, AzureHTTPError) else 'curl transport'
            print(f'  {target.stem} {reason}，{delay} 秒后重试（{attempt + 1}/5）。', flush=True)
            pipeline.time.sleep(delay)


def synthesize_curl_chunked(poem, target, credentials, pacer):
    """Keep the same couplet cache and one final normalization with curl requests."""
    from imageio_ffmpeg import get_ffmpeg_exe
    folder = STAGE / 'chunks' / poem['id']
    folder.mkdir(parents=True, exist_ok=True)
    drafts = pipeline.poetry_ssml_chunks(poem)
    index = folder / 'manifest.json'
    cache = json.loads(index.read_text()) if index.exists() else {}
    records = cache.get('chunks', {}) if cache.get('recipe') == AZURE_RECIPE else {}
    paths = []
    for number, ssml in enumerate(drafts):
        name, fingerprint = f'{number:03d}', pipeline.hashlib.sha256(ssml.encode()).hexdigest()
        path = folder / f'{name}.mp3'
        (folder / f'{name}.ssml').write_text(ssml)
        item = records.get(name, {})
        if not (path.is_file() and item.get('ssmlSHA256') == fingerprint and item.get('sha256') == pipeline.digest(path)):
            duration = synthesize_curl_with_retry(ssml, path, credentials, pacer, normalize=False)
            records[name] = {'ssmlSHA256': fingerprint, 'sha256': pipeline.digest(path), 'duration': duration}
            atomic_json(index, {'recipe': AZURE_RECIPE, 'chunks': records})
        paths.append(path)
        print(f'  {poem["title"]} 分段 {number + 1}/{len(drafts)} 已完成', flush=True)
    concat = folder / 'join.ffconcat'
    concat.write_text('ffconcat version 1.0\n' + ''.join(f"file '{path.name}'\n" for path in paths))
    with tempfile.TemporaryDirectory(prefix='.azure-join-', dir=target.parent) as temporary:
        joined, final = Path(temporary) / 'joined.mp3', Path(temporary) / 'final.mp3'
        subprocess.run([get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
                        '-i', str(concat), '-c', 'copy', str(joined)], check=True)
        duration = pipeline.normalize_audio(joined, final)
        os.replace(final, target)
    return duration


def generate_tracks(poems, records, credentials, jobs=3, chunked=False, transport='urllib'):
    """Keep only worker-count requests outstanding and retain completed work on failure."""
    pacer = pipeline.RequestPacer()
    if transport == 'curl':
        renderer = synthesize_curl_chunked if chunked else synthesize_curl_with_retry
    else:
        renderer = pipeline.synthesize_chunked if chunked else pipeline.synthesize_with_retry
    remaining = iter(p for p in poems if p['id'] not in records)
    active, failures, fatal = {}, [], None
    executor = ThreadPoolExecutor(max_workers=jobs)

    def submit_next():
        try:
            poem = next(remaining)
        except StopIteration:
            return False
        request = poem if chunked else poetry_ssml(poem)
        future = executor.submit(renderer, request, STAGE / 'audio' / f'{poem["id"]}.mp3', credentials, pacer)
        active[future] = poem
        return True

    def collect(future, poem):
        nonlocal fatal
        try:
            duration = future.result()
            item = pipeline.record(poem, STAGE / 'audio' / f'{poem["id"]}.mp3', duration)
            if chunked:
                item.update(synthesisMode='couplet-chunks', chunkCount=len(pipeline.poetry_ssml_chunks(poem)))
            records[poem['id']] = item
            save(poems, records)
            print(f'[{len(records)}/{len(poems)}] {poem["title"]} · {duration:.2f}s', flush=True)
        except Exception as error:
            failures.append({'id': poem['id'], 'error': str(error)})
            recoverable = (isinstance(error, (AzureHTTPError, AzureTransportError))
                           and not (isinstance(error, AzureHTTPError) and error.status in (401, 403)))
            if not recoverable and fatal is None:
                fatal = error

    try:
        for _ in range(jobs):
            if not submit_next():
                break
        while active:
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            # Inspect the whole completed batch before allowing another request.
            for future in done:
                collect(future, active.pop(future))
            if fatal is not None:
                break
            while len(active) < jobs and submit_next():
                pass
    except BaseException as error:
        if fatal is None:
            fatal = error
    finally:
        for future in active:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        # Already-running requests can finish; keep their successful audio so a
        # resumed run never submits those same inputs again.
        for future, poem in active.items():
            if not future.cancelled():
                collect(future, poem)
    return failures, fatal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--generate', action='store_true')
    mode.add_argument('--publish', action='store_true')
    mode.add_argument('--audit', action='store_true')
    parser.add_argument('--prompt-key', action='store_true', help='read the Speech key without echo or storage')
    parser.add_argument('--region', default='eastasia', help='resource region used with --prompt-key')
    parser.add_argument('--transport', choices=['urllib', 'curl'], default='urllib', help='second-volume HTTP client')
    parser.add_argument('--jobs', type=int, choices=[1, 2, 3, 6], default=3)
    parser.add_argument('--chunked', action='store_true')
    args = parser.parse_args()
    if args.prompt_key and not args.generate:
        parser.error('--prompt-key requires --generate')
    poems = load()
    STAGE.mkdir(parents=True, exist_ok=True)
    with (STAGE / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.publish:
            print(json.dumps(publish(poems), ensure_ascii=False))
            return
        if args.audit:
            print(json.dumps(pipeline.audit(poems, stage=STAGE, decode=True), ensure_ascii=False))
            return
        for folder in ['audio', 'ssml']:
            (STAGE / folder).mkdir(exist_ok=True)
        previous = json.loads((STAGE / 'manifest.json').read_text()) if (STAGE / 'manifest.json').exists() else {}
        records = {}
        for poem in poems:
            identity = poem['id']
            draft = poetry_ssml(poem)
            (STAGE / 'ssml' / f'{identity}.ssml').write_text(draft)
            item = previous.get('tracks', {}).get(identity, {})
            if previous.get('recipe') == AZURE_RECIPE and pipeline.valid_record(poem, item, STAGE / 'audio' / f'{identity}.mp3'):
                records[identity] = item
        save(poems, records)
        review = prepare_listening_review(poems, records)
        plan = write_plan(poems, records, review)
        print(json.dumps(plan, ensure_ascii=False), flush=True)
        if not args.generate or len(records) == len(poems):
            return
        credentials = prompt_azure_config(args.region) if args.prompt_key else azure_config()
        from prepare_recitation_variants import OUT as voice_check_out, verify_voice_styles
        voice_check_out.mkdir(parents=True, exist_ok=True)
        verify_voice_styles(credentials, reuse=(voice_check_out / 'voice-support.json').is_file())
        failures, fatal = generate_tracks(poems, records, credentials, jobs=args.jobs, chunked=args.chunked,
                                          transport=args.transport)
        atomic_json(STAGE / 'failures.json', failures)
        review = prepare_listening_review(poems, records)
        write_plan(poems, records, review)
        if fatal is not None:
            raise fatal
        if failures:
            raise ValueError(f'{len(failures)} tracks require retry; no released manifest changed')
        print(json.dumps(pipeline.audit(poems, stage=STAGE), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, BlockingIOError) as error:
        raise SystemExit(str(error)) from None

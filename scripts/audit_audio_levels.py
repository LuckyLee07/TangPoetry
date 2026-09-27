#!/usr/bin/env python3
"""Measure every staged MP3 without altering it; reuse only exact file hashes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import re
import subprocess
import time

from generate_audio import atomic_json
from generate_azure_audio import STAGE


def measure(item):
    from imageio_ffmpeg import get_ffmpeg_exe
    path = STAGE / "audio" / f'{item["id"]}.mp3'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item['sha256']:
        raise ValueError(f'File changed: {item["id"]}')
    result = subprocess.run([get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-v', 'info', '-xerror',
                             '-i', str(path), '-af', 'loudnorm=I=-18:TP=-1.5:LRA=11:print_format=json',
                             '-f', 'null', '-'], capture_output=True, text=True, check=True)
    matches = re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if len(matches) != 1:
        raise ValueError(f'No loudness measurement: {item["id"]}')
    values = json.loads(matches[0])
    loudness, peak = float(values['input_i']), float(values['input_tp'])
    if not math.isfinite(loudness) or not -22 <= loudness <= -16 or not math.isfinite(peak) or peak > -1:
        raise ValueError(f'Unexpected loudness/peak: {item["id"]} ({loudness}, {peak})')
    return {"id": item['id'], "sha256": digest, "duration": item['duration'],
            "integratedLUFS": loudness, "truePeakDBTP": peak,
            "loudnessRangeLU": float(values['input_lra']), "decoded": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true', help='Continue checking new files until the staged catalog is complete')
    args = parser.parse_args()
    target = STAGE / 'levels.json'
    checks = json.loads(target.read_text()).get('tracks', {}) if target.exists() else {}
    while True:
        manifest = json.loads((STAGE / 'manifest.json').read_text())
        current = manifest['tracks']
        checks = {identity: entry for identity, entry in checks.items()
                  if identity in current and entry['sha256'] == current[identity]['sha256']}
        pending = [item for identity, item in current.items() if identity not in checks]
        with ThreadPoolExecutor(max_workers=2) as pool:
            for entry in pool.map(measure, pending):
                checks[entry['id']] = entry
        result = {"tracks": checks, "checked": len(checks), "expected": len(manifest['trackOrder']),
                  "loudnessRangeLUFS": [min(c['integratedLUFS'] for c in checks.values()), max(c['integratedLUFS'] for c in checks.values())] if checks else [],
                  "highestTruePeakDBTP": max((c['truePeakDBTP'] for c in checks.values()), default=None)}
        atomic_json(target, result)
        if pending:
            print(f'解码/响度检查：{len(checks)}/{result["expected"]}', flush=True)
        if len(checks) == result['expected'] or not args.watch:
            print(json.dumps({key: value for key, value in result.items() if key != 'tracks'}, ensure_ascii=False), flush=True)
            return
        time.sleep(8)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build an offline volume-2 audition folder and ZIP after all 305 MP3s pass audit.

Run with the same Python environment as generate_volume2_audio.py:
    python3 scripts/package_volume2_audio.py --check-only
    python3 scripts/package_volume2_audio.py

No credentials or network are used. Generation is verified separately from
human listening approval; this tool never modifies or approves listening records.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/audio-azure-volume-2'
DEFAULT_OUTPUT = STAGE / 'volume2-audio-audition'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_coverage(catalog, manifest):
    """Reject incomplete staging without any decoder or optional dependencies."""
    if not isinstance(catalog, dict) or not isinstance(manifest, dict):
        raise ValueError('目录与音轨清单必须是JSON对象。')
    entries = catalog.get('poems')
    if not isinstance(entries, list) or catalog.get('volume') != 'volume-2':
        raise ValueError('第二卷目录格式不符。')
    identities = [p['id'] for p in entries]
    if len(identities) != 305 or len(set(identities)) != 305:
        raise ValueError('离线试听包需要第二卷完整的305首目录。')
    tracks = manifest.get('tracks')
    count = len(tracks) if isinstance(tracks, dict) else 0
    if (manifest.get('schemaVersion') != 1 or manifest.get('volume') != 'volume-2'
            or manifest.get('release') != 'full'
            or not isinstance(tracks, dict) or set(tracks) != set(identities)
            or manifest.get('trackOrder') != identities):
        raise ValueError(f'音轨尚未生成完整（{count}/305）；不创建离线包。')
    return identities


@contextmanager
def generation_lock():
    """Hold the generator's existing lock, without writing a lock file."""
    with (STAGE / '.run.lock').open('rb') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('第二卷音频生成或发布仍在运行，请完成后再打包。') from None
        yield


def verified_inputs():
    catalog_path = ROOT / 'data/reader-volume-2/catalog.json'
    manifest_path = STAGE / 'manifest.json'
    catalog = json.loads(catalog_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    validate_coverage(catalog, manifest)
    if manifest.get('catalogSHA256') != digest(catalog_path):
        raise ValueError('音轨清单与当前第二卷目录哈希不符。')
    production_path = ROOT / 'data/expansion/tang-second-volume/production.json'
    if manifest.get('productionSHA256') != digest(production_path):
        raise ValueError('音轨清单与当前第二卷制作资料哈希不符。')
    # Existing load/audit functions verify current text, SSML, recipe, input/file
    # hashes, durations and every decoded MP3. Neither function loads credentials.
    import generate_volume2_audio as audio
    poems = audio.load()
    stats = audio.pipeline.audit(poems, stage=STAGE, decode=True)
    if stats.get('tracks') != 305 or not stats.get('allFilesDecoded'):
        raise ValueError('305首完整音频解码校验尚未通过。')
    return catalog, {poem['id']: poem for poem in poems}, manifest, stats


def render_html(catalog, details, manifest):
    """Embed data, styles and the same manual audition UI; no fetch on file://."""
    embedded = {
        'catalog': catalog,
        'details': details,
        'manifest': manifest,
        'audioFiles': {poem['id']: f"audio/{poem['id']}.mp3" for poem in catalog['poems']},
    }
    # A poem may contain HTML-like text. Keep all data inert in its JSON element.
    payload = json.dumps(embedded, ensure_ascii=False, separators=(',', ':'))
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    styles = (ROOT / 'styles.css').read_text() + '\n' + (ROOT / 'tools/volume2-audio.css').read_text()
    script = (ROOT / 'tools/volume2-audio.js').read_text()
    html = (ROOT / 'tools/volume2-audio.html').read_text()
    expected = [
        '  <link rel="stylesheet" href="../styles.css">\n',
        '  <link rel="stylesheet" href="./volume2-audio.css">\n',
        '  <script type="module" src="./volume2-audio.js"></script>',
        '<a href="../index.html?volume=2">图文阅读</a>',
    ]
    if not all(html.count(value) == 1 for value in expected):
        raise ValueError('试听页模板已改变，请更新离线打包模板。')
    html = html.replace(expected[0], '').replace(expected[1], '')
    html = html.replace(expected[2], f'<style>\n{styles}\n</style>\n'
                        f'<script id="auditionData" type="application/json">{payload}</script>\n'
                        f'<script type="module">\n{script}\n</script>')
    return html.replace(expected[3], '<a href="./README.txt">使用说明</a>')


def write_bundle(destination, catalog, details, manifest, stats):
    """Copy verified files to a new folder, then archive that folder."""
    validate_coverage(catalog, manifest)
    if stats.get('tracks') != 305 or not stats.get('allFilesDecoded') or set(details) != set(manifest['tracks']):
        raise ValueError('只有305首完整正文与解码校验通过的音轨可以打包。')
    destination = Path(destination).resolve()
    archive = destination.parent / f'{destination.name}.zip'
    if destination.exists() or archive.exists():
        raise ValueError(f'输出目录或ZIP已存在，不覆盖已有试听包：{destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        'schemaVersion': 1,
        'volume': 'volume-2',
        'purpose': 'local-audition',
        'generationComplete': True,
        'tracks': 305,
        'audioBytes': stats['bytes'],
        'seconds': stats['seconds'],
        'allFilesDecoded': True,
        # Null means this packaging tool does not certify human listening approval.
        'listeningApproved': None,
        'catalogSHA256': manifest['catalogSHA256'],
        'productionSHA256': manifest['productionSHA256'],
    }
    instructions = """第二卷 · 本地朗读听校包

先完整解压 ZIP，保留 index.html、audio、data 的相对位置。
双击 index.html，即可通过 file:// 搜索诗题、作者或诗句，并对照正文试听。
点击播放器手动播放；拖动进度条定位；可调整速度和上一首、下一首。
切换诗篇不会自动开始播放。不要直接在 ZIP 预览中打开 HTML。

此包包含305首已经生成、校验文件哈希并完成解码检查的 MP3。
generationComplete=true 只表示完整生成与机器校验通过。
listeningApproved=null 表示打包工具不评审或证明人工听审批准。
页面和脚本均不修改或自动批准 listening-review.json。

这是一份本地听校包，不会发布音频，也不会启用正式 App 的第二卷朗读。
人工听校后，仍须在原工作目录逐首填写真实的 listening-review.json 记录，
保留该次 inputSHA256、audioSHA256，按现有 generate_volume2_audio.py
--publish 与客户端构建流程发布和启用。

data/catalog.json 与 data/manifest.json 保留打包时的原始资料；
index.html 内嵌目录和正文，播放器只读取本包 audio/{id}.mp3。
清单中的 assets 发布路径不会用于离线试听。
"""
    with tempfile.TemporaryDirectory(prefix='.volume2-audition-', dir=destination.parent) as folder:
        temporary = Path(folder)
        bundle = temporary / destination.name
        (bundle / 'audio').mkdir(parents=True)
        (bundle / 'data').mkdir()
        for poem in catalog['poems']:
            identity = poem['id']
            source = STAGE / 'audio' / f'{identity}.mp3'
            target = bundle / 'audio' / source.name
            shutil.copy2(source, target)
            if target.stat().st_size != manifest['tracks'][identity]['bytes'] or digest(target) != manifest['tracks'][identity]['sha256']:
                raise ValueError(f'复制后的音轨校验失败：{identity}')
        shutil.copy2(ROOT / 'data/reader-volume-2/catalog.json', bundle / 'data/catalog.json')
        shutil.copy2(STAGE / 'manifest.json', bundle / 'data/manifest.json')
        (bundle / 'index.html').write_text(render_html(catalog, details, manifest))
        (bundle / 'README.txt').write_text(instructions)
        (bundle / 'bundle-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temporary_zip = temporary / 'bundle.zip'
        with zipfile.ZipFile(temporary_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    zipped.write(path, path.relative_to(temporary))
        os.replace(bundle, destination)
        os.replace(temporary_zip, archive)
    return {**report, 'directory': str(destination), 'zip': str(archive), 'zipBytes': archive.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='只校验305首，不创建试听包')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='新试听目录，旁边同时生成同名ZIP')
    args = parser.parse_args()
    # Reject 0/partial coverage before checking any audio/decode dependencies.
    catalog = json.loads((ROOT / 'data/reader-volume-2/catalog.json').read_text())
    manifest = json.loads((STAGE / 'manifest.json').read_text())
    validate_coverage(catalog, manifest)
    with generation_lock():
        catalog, details, manifest, stats = verified_inputs()
        if args.check_only:
            result = {**stats, 'generationComplete': True, 'listeningApproved': None}
        else:
            result = write_bundle(args.output, catalog, details, manifest, stats)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f'第二卷离线试听包未生成：{error}') from None

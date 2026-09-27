#!/usr/bin/env python3
"""Extend the selected Xiaoxiao E rendition to four poems, without publishing."""
import argparse
import hashlib
import html
import json
import time

from prepare_narration_trial import (
    ROOT, AzureTransportError, azure_config, prompt_azure_config, synthesize_azure_ssml,
)
from prepare_recitation_variants import VARIANTS, recitation_ssml, verse_lines, verify_voice_styles

OUT = ROOT / "output/tts-trial/poetry-reading"
VOICE_PLAN = next(variant for variant in VARIANTS if variant["id"] == "e-xiaoxiao-poetry")
SAMPLES = [
    {"id": "tang-224-lu-chai", "genre": "五言绝句", "note": "听幽静的氛围与句尾留白。"},
    {"id": "tang-273-feng-qiao-ye-po", "genre": "七言绝句", "note": "听七言句的连贯性与夜泊的情绪。"},
    {"id": "tang-091-wang-yue-huai-yuan", "genre": "五言律诗", "note": "听八句之间的衔接与情绪递进。"},
    {"id": "tang-186-deng-gao", "genre": "七言律诗", "note": "听长句的气息与整首的沉郁感。"},
]


def load_poems():
    return [json.loads((ROOT / f'data/reader/poems/{sample["id"]}.json').read_text()) for sample in SAMPLES]


def write_page(poems):
    cards = []
    for index, (sample, poem) in enumerate(zip(SAMPLES, poems), 1):
        filename = f'{poem["id"]}-xiaoxiao.mp3'
        player = (f'<audio controls preload="metadata" aria-label="试听：{html.escape(poem["title"])}" '
                  f'src="{filename}"></audio><a class="download" href="{filename}" download>下载音频</a>'
                  if (OUT / filename).is_file() else '<p>正在准备</p>')
        cards.append(f'''<article><p class="category">{index:02d} / {sample['genre']}</p>
<h2>{html.escape(poem['title'])}</h2><p>唐 · {html.escape(poem['author'])}</p>
<div class="poem">{'<br>'.join(html.escape(line) for line in verse_lines(poem))}</div>
<p class="hint">{sample['note']}</p>{player}</article>''')
    reference = (OUT.parent / "recitation/e-xiaoxiao-poetry.mp3").is_file()
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>晓晓 · 诗歌朗读试听</title>
<style>*{box-sizing:border-box}body{max-width:1080px;margin:0 auto;padding:36px 24px 60px;background:#f5f0e5;color:#352f27;font:16px/1.7 system-ui}
a{color:#755038}h1{font:34px/1.4 serif;margin:20px 0 12px}h2{font:29px/1.4 serif;margin:0 0 8px}p{color:#756b60;margin:0 0 14px}
.intro{max-width:740px}.samples{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px 40px;margin-top:28px}
article{border-top:1px solid #d9d0c0;padding:24px 0;display:flex;flex-direction:column;align-items:flex-start}.category{font-size:13px;letter-spacing:.12em;color:#806449}
.poem{font:23px/1.85 serif;letter-spacing:.06em;margin:8px 0 22px}.hint{font-size:14px;margin-top:auto}audio{display:block;width:100%;margin:10px 0 14px}.download{font-size:14px}
details{max-width:650px;border:1px solid #d9d0c0;border-radius:10px;padding:12px 16px;margin-top:22px}summary{cursor:pointer}footer{color:#756b60;font-size:14px;margin-top:20px}
@media(max-width:700px){body{padding:24px 18px 40px}.samples{grid-template-columns:1fr;gap:0}h1{font-size:28px}.poem{font-size:22px}}
</style></head><body><a href="../recitation/">← 登鹳雀楼五版对比</a>
<h1>晓晓 · 诗歌朗读试听</h1><p class="intro">沿用你选中的 E 版。这次听四首不同体裁的诗，比较短诗与律诗的节奏、停连和情绪。保持同一套朗读参数，无配乐。</p>'''
    if reference:
        page += '''<details><summary>回听已选版本：《登鹳雀楼》</summary>
<audio controls preload="metadata" aria-label="回听：登鹳雀楼 E 版" src="../recitation/e-xiaoxiao-poetry.mp3"></audio></details>'''
    page += '<div class="samples">' + ''.join(cards) + '</div>'
    release_path = ROOT / "data/audio/manifest.json"
    release = json.loads(release_path.read_text()) if release_path.exists() else {}
    if release.get("release") == "full" and release.get("recipe", {}).get("style") == "poetry-reading":
        page += '<footer>这版朗读已用于全库 320 首。<a href="../../../?v=0.6.1">打开完整诗库，轻点「听诗」体验</a>。</footer>'
    else:
        page += '<footer>可以直接反馈哪首最合适、哪一句需要调整。这里只是试听样例，App 中的正式音频尚未替换。</footer>'
    page += '''
<script>document.addEventListener('play',event=>{if(event.target.tagName==='AUDIO'){
document.querySelectorAll('audio').forEach(audio=>{if(audio!==event.target)audio.pause()})}},true)</script></body></html>'''
    (OUT / "index.html").write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--prompt-key", action="store_true")
    parser.add_argument("--region", default="eastasia")
    parser.add_argument("--only", choices=[sample["id"] for sample in SAMPLES])
    args = parser.parse_args()
    if args.prompt_key and not args.generate:
        parser.error("--prompt-key 必须与 --generate 一起使用")
    OUT.mkdir(parents=True, exist_ok=True)
    poems = load_poems()
    drafts = {poem["id"]: recitation_ssml(poem, VOICE_PLAN) for poem in poems}
    for identity, ssml in drafts.items():
        (OUT / f"{identity}-xiaoxiao.ssml").write_text(ssml)
    write_page(poems)
    if args.generate:
        credentials = prompt_azure_config(args.region) if args.prompt_key else azure_config()
        cache_path = OUT.parent / "recitation/voice-support.json"
        if not cache_path.is_file():
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            verify_voice_styles(credentials)
        supported = json.loads(cache_path.read_text())
        if VOICE_PLAN["style"] not in supported.get(VOICE_PLAN["voice"], {}).get("StyleList", []):
            raise ValueError("晓晓诗歌朗读风格尚未通过验证。")
        manifest_path = OUT / "manifest.json"
        previous = json.loads(manifest_path.read_text()) if manifest_path.is_file() else []
        records = {item["id"]: item for item in previous}
        for sample, poem in zip(SAMPLES, poems):
            if args.only and sample["id"] != args.only:
                continue
            ssml = drafts[poem["id"]]
            target = OUT / f'{poem["id"]}-xiaoxiao.mp3'
            for attempt in range(2):
                try:
                    duration = synthesize_azure_ssml(ssml, target, credentials)
                    break
                except AzureTransportError:
                    if attempt:
                        raise
                    print(f'{poem["title"]} 传输中断，重试一次。', flush=True)
                    time.sleep(2)
            records[poem["id"]] = {**sample, "title": poem["title"], "author": poem["author"],
                                   "voice": VOICE_PLAN["voice"], "style": VOICE_PLAN["style"],
                                   "styledegree": VOICE_PLAN["degree"], "rate": "-6%", "pairPauseMs": 500,
                                   "duration": round(duration, 3),
                                   "audioSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                   "ssmlSha256": hashlib.sha256(ssml.encode()).hexdigest()}
            ordered = [records[item["id"]] for item in SAMPLES if item["id"] in records]
            manifest_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n")
            write_page(poems)
            print(f'{poem["title"]} / {sample["genre"]}: {duration:.2f}s', flush=True)
    print(f"Samples: {OUT / 'index.html'}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None

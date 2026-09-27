#!/usr/bin/env python3
"""Create four Deng Guan Que Lou recitations, retaining the first Azure sample.

Default: write SSML and the local comparison page only.
--generate --prompt-key: verify supported styles and synthesize four samples.
"""
import argparse
import hashlib
import html
from http.client import HTTPException
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from prepare_narration_trial import (
    ROOT, TITLE_ALIASES, azure_config, couplets, prompt_azure_config, synthesize_azure_ssml,
)
from narration_recipe import poetry_ssml

OUT = ROOT / "output/tts-trial/recitation"
POEM_ID = "tang-236-deng-guan-que-lou"
NS = {"s": "http://www.w3.org/2001/10/synthesis", "m": "https://www.w3.org/2001/mstts"}
VARIANTS = [
    {"id": "b-yunze-phrasing", "letter": "B", "name": "云泽 · 逐句精调", "voice": "zh-CN-YunzeNeural",
     "style": "documentary-narration", "degree": "1.2", "shaped": True,
     "description": "逐句调整快慢与音高，在「千里」「更上」处加重，联间留出停顿。"},
    {"id": "c-yunze-intensity", "letter": "C", "name": "云泽 · 情绪加强", "voice": "zh-CN-YunzeNeural",
     "style": "documentary-narration", "degree": "1.85", "shaped": True,
     "description": "沿用 B 的节奏，只提高旁白风格强度，比较情绪参数的实际差别。"},
    {"id": "d-yunjian-phrasing", "letter": "D", "name": "云健 · 男声对照", "voice": "zh-CN-YunjianNeural",
     "style": "documentary-narration", "degree": "1.2", "shaped": True,
     "description": "沿用 B 的朗读编排，换成云健男声，比较声音本身是否更合适。"},
    {"id": "e-xiaoxiao-poetry", "letter": "E", "name": "晓晓 · 诗歌朗读", "voice": "zh-CN-XiaoxiaoNeural",
     "style": "poetry-reading", "degree": "1.3", "shaped": False,
     "description": "女声诗歌朗读风格，轻微放慢，主要由该风格处理句内韵律。"},
]
LINE_SETTINGS = [
    {"rate": "-12%", "pitch": "-2%", "volume": "+0%", "pause": 240},
    {"rate": "-3%", "pitch": "+1%", "volume": "+4%", "pause": 600},
    {"rate": "-10%", "pitch": "+3%", "volume": "+8%", "pause": 330},
    {"rate": "-15%", "pitch": "-1%", "volume": "+8%", "pause": 0},
]


def verse_lines(poem):
    return ["".join(token[0] for token in line).strip() for line in poem["rubyLines"]]


def recitation_ssml(poem, variant):
    if variant["id"] == "e-xiaoxiao-poetry":
        return poetry_ssml(poem)
    lines = verse_lines(poem)
    if variant["shaped"]:
        if len(lines) != 4 or poem["id"] != POEM_ID:
            raise ValueError("逐句精调编排仅适用于《登鹳雀楼》的四句正文。")
        fragments = []
        for index, (line, setting) in enumerate(zip(lines, LINE_SETTINGS)):
            text = html.escape(line)
            if index == 2:
                text = text.replace("千里", '<prosody rate="-10%" volume="+6%">千里</prosody>')
            elif index == 3:
                text = text.replace("更上", '<prosody rate="-8%" volume="+8%">更上</prosody>')
            fragments.append(
                f'<s><prosody rate="{setting["rate"]}" pitch="{setting["pitch"]}" '
                f'volume="{setting["volume"]}">{text}</prosody></s>')
            if setting["pause"]:
                fragments.append(f'<break time="{setting["pause"]}ms"/>')
        body = "\n".join(fragments)
    else:
        body = '<prosody rate="-6%">' + '<break time="500ms"/>'.join(
            f'<s>{html.escape(pair)}</s>' for pair in couplets(poem)) + '</prosody>'
    ssml = f'''<speak version="1.0" xmlns="{NS['s']}" xmlns:mstts="{NS['m']}" xml:lang="zh-CN">
  <voice name="{variant['voice']}">
    <prosody rate="-5%"><s>{html.escape(TITLE_ALIASES.get(poem['id'], poem['title']))}。</s><break time="350ms"/>
      <s>唐代，{html.escape(poem['author'])}。</s></prosody>
    <break time="800ms"/>
    <mstts:express-as style="{variant['style']}" styledegree="{variant['degree']}">
      {body}
    </mstts:express-as>
    <break time="800ms"/>
  </voice>
</speak>
'''
    element = ET.fromstring(ssml).find(".//m:express-as", NS)
    spoken = "".join("".join(element.itertext()).split())
    if spoken != "".join(lines):
        raise ValueError("朗读稿与原诗不一致，已停止。")
    return ssml


def verify_voice_styles(credentials, reuse=False):
    import certifi
    key, region = credentials
    request = Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
                      headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "TangPoetryRecitationTrial"})
    if reuse:
        # Explicit retry option, for the same resource/region in this trial.
        voices = json.loads((OUT / "voice-support.json").read_text())
    else:
        try:
            with urlopen(request, context=ssl.create_default_context(cafile=certifi.where()), timeout=30) as response:
                voices = {voice["ShortName"]: voice for voice in json.load(response)}
        except HTTPError as error:
            raise RuntimeError(f"Azure 音色查询 HTTP {error.code}，未开始合成。") from None
        except (URLError, TimeoutError, HTTPException):
            raise RuntimeError("Azure 音色查询传输失败，未开始合成。") from None
    selected = {}
    for variant in VARIANTS:
        voice = voices.get(variant["voice"], {})
        if variant["style"] not in voice.get("StyleList", []):
            raise ValueError(f'{variant["name"]} 的所需风格未获服务端支持，未开始合成。')
        selected[variant["voice"]] = {name: voice.get(name) for name in ("ShortName", "Gender", "StyleList", "Status")}
    (OUT / "voice-support.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n")
    print("已复用本轮通过的音色检查。" if reuse else "Azure 已确认云泽、云健及晓晓支持本轮风格。", flush=True)


def write_page(poem):
    baseline = {"letter": "A", "name": "云泽 · 上一版", "description": "保留你刚才听过的版本，作为参照。"}
    cards = []
    for variant in [baseline, *VARIANTS]:
        filename = f'{variant["id"]}.mp3' if "id" in variant else f"../{POEM_ID}-azure.mp3"
        path = OUT / filename
        player = (f'<audio controls preload="metadata" aria-label="试听 {variant["letter"]}：{variant["name"]}" '
                  f'src="{filename}"></audio><a class="download" href="{filename}" download>下载音频</a>'
                  if path.is_file() else '<p class="pending">正在准备</p>')
        cards.append(f'''<article><span class="letter">{variant['letter']}</span><div class="content">
<h2>{variant['name']}</h2><p>{variant['description']}</p>{player}</div></article>''')
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>登鹳雀楼 · 五版朗诵对比</title>
<style>*{box-sizing:border-box}body{max-width:880px;margin:0 auto;padding:40px 24px 64px;background:#f5f0e5;color:#352f27;font:16px/1.7 system-ui}
a{color:#755038}h1{font:34px/1.4 serif;margin:20px 0 12px}h2{font-size:19px;margin:0 0 8px}p{margin:0 0 16px;color:#756b60}
.intro{max-width:660px}.poem{font:23px/1.9 serif;letter-spacing:.08em;margin:24px 0 32px;padding-left:20px;border-left:2px solid #c7b292}
article{display:flex;gap:20px;padding:24px 0;border-top:1px solid #d9d0c0}.letter{font:30px/1.4 serif;color:#806449;min-width:30px}.content{flex:1;min-width:0}
audio{display:block;width:100%;margin:12px 0}.download{font-size:14px}.pending{font-size:14px}footer{font-size:14px;color:#756b60;margin-top:32px}
@media(max-width:520px){body{padding:24px 18px 40px}h1{font-size:28px}.poem{font-size:20px}article{gap:12px}}
</style></head><body><a href="../">← 三首朗读对照</a><h1>登鹳雀楼 · 五版朗诵对比</h1>
<p class="intro">先听 A，再比较 B、C 的节奏和情绪；D 换男声，E 换诗歌朗读风格。各版采用相同的音量处理，无配乐。</p>'''
    page += '<div class="poem">' + '<br>'.join(html.escape(line) for line in verse_lines(poem)) + '</div>'
    page += "".join(cards)
    if (OUT.parent / "poetry-reading/index.html").is_file():
        page += '<p><a href="../poetry-reading/">继续试听：晓晓诗歌朗读 · 四种体裁 →</a></p>'
    page += '''<footer>这轮只比较《登鹳雀楼》。喜欢的版本可以用编号反馈，也可以告诉我哪一句过平、过重或停顿过长。</footer>
<script>document.addEventListener('play',event=>{if(event.target.tagName==='AUDIO'){
document.querySelectorAll('audio').forEach(audio=>{if(audio!==event.target)audio.pause()})}},true)</script></body></html>'''
    (OUT / "index.html").write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--prompt-key", action="store_true")
    parser.add_argument("--region", default="eastasia")
    parser.add_argument("--only", choices=[variant["id"] for variant in VARIANTS], help="synthesize one selected variant")
    parser.add_argument("--reuse-voice-check", action="store_true", help="reuse this trial's voice-support.json when retrying the same resource/region")
    args = parser.parse_args()
    if args.prompt_key and not args.generate:
        parser.error("--prompt-key 必须与 --generate 一起使用")
    OUT.mkdir(parents=True, exist_ok=True)
    poem = json.loads((ROOT / f"data/reader/poems/{POEM_ID}.json").read_text())
    drafts = {variant["id"]: recitation_ssml(poem, variant) for variant in VARIANTS}
    for identity, ssml in drafts.items():
        (OUT / f"{identity}.ssml").write_text(ssml)
    write_page(poem)
    if args.generate:
        credentials = prompt_azure_config(args.region) if args.prompt_key else azure_config()
        verify_voice_styles(credentials, reuse=args.reuse_voice_check)
        manifest_path = OUT / "manifest.json"
        previous = json.loads(manifest_path.read_text()) if manifest_path.is_file() else []
        manifest = {item["id"]: item for item in previous}
        for variant in VARIANTS:
            if args.only and variant["id"] != args.only:
                continue
            target = OUT / f'{variant["id"]}.mp3'
            ssml = drafts[variant["id"]]
            duration = synthesize_azure_ssml(ssml, target, credentials)
            manifest[variant["id"]] = {**variant, "duration": round(duration, 3),
                                      "audioSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                      "ssmlSha256": hashlib.sha256(ssml.encode()).hexdigest()}
            ordered = [manifest[item["id"]] for item in VARIANTS if item["id"] in manifest]
            manifest_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n")
            write_page(poem)
            print(f'{variant["letter"]} {variant["name"]}: {duration:.2f}s', flush=True)
    print(f"Comparison: {OUT / 'index.html'}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None

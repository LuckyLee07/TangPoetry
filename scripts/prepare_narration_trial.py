#!/usr/bin/env python3
"""Prepare three narration comparisons without changing the app's audio library.

The default writes Azure SSML drafts and the comparison page locally.
--generate-edge submits only these three poems to Edge TTS.
Azure synthesis is separate and awaits a configured Speech resource.
"""
import argparse
import asyncio
import getpass
import html
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import warnings
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from generate_audio import TITLE_ALIASES, probe

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/tts-trial"
TRIALS = [
    {"id": "tang-236-deng-guan-que-lou", "rate": "-5%",
     "style": "documentary-narration", "degree": "1.2", "pause": 650,
     "direction": "云泽纪录片旁白风格，整体语速略放慢"},
    {"id": "tang-273-feng-qiao-ye-po", "rate": "-10%",
     "style": "sad", "degree": "0.8", "pause": 850,
     "direction": "云泽悲伤风格，语速较慢"},
    {"id": "tang-224-lu-chai", "rate": "-8%",
     "style": "calm", "degree": "0.8", "pause": 800,
     "direction": "云泽平静风格，联间停顿较长"},
]
EDGE_VOICE = "zh-CN-YunxiNeural"
AZURE_VOICE = "zh-CN-YunzeNeural"


class AzureTransportError(RuntimeError):
    """A transient connection/read failure; partial audio is never committed."""


class AzureHTTPError(RuntimeError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def couplets(poem):
    lines = ["".join(token[0] for token in line).strip() for line in poem["rubyLines"]]
    return ["".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]


def edge_text(poem):
    title = TITLE_ALIASES.get(poem["id"], poem["title"])
    return f"{title}。\n唐代，{poem['author']}。\n\n" + "\n\n".join(couplets(poem))


def azure_ssml(poem, plan):
    title = html.escape(TITLE_ALIASES.get(poem["id"], poem["title"]))
    body = f'<break time="{plan["pause"]}ms"/>'.join(
        f"<s>{html.escape(pair)}</s>" for pair in couplets(poem))
    result = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
 xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
  <voice name="{AZURE_VOICE}">
    <prosody rate="-5%"><s>{title}。</s><break time="350ms"/>
      <s>唐代，{html.escape(poem['author'])}。</s></prosody>
    <break time="800ms"/>
    <mstts:express-as style="{plan['style']}" styledegree="{plan['degree']}">
      <prosody rate="{plan['rate']}">{body}</prosody>
    </mstts:express-as>
    <break time="800ms"/>
  </voice>
</speak>
'''
    ElementTree.fromstring(result)
    return result


def normalize_audio(raw, target):
    from imageio_ffmpeg import get_ffmpeg_exe
    subprocess.run([get_ffmpeg_exe(), "-nostdin", "-v", "error", "-y", "-i", str(raw),
                    "-af", "loudnorm=I=-18:TP=-1.5:LRA=11,apad=pad_dur=0.5",
                    "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
                    str(target)], check=True)
    return probe(target)


async def generate_edge(poem, plan):
    import edge_tts
    target = OUT / f"{poem['id']}-edge.mp3"
    # Never touch assets/audio or the release manifest.
    with tempfile.TemporaryDirectory(prefix=".edge-", dir=OUT) as temporary:
        raw = Path(temporary) / "raw.mp3"
        normalized = Path(temporary) / "normalized.mp3"
        await edge_tts.Communicate(edge_text(poem), voice=EDGE_VOICE,
                                   rate=plan["rate"], pitch="+0Hz").save(str(raw))
        duration = normalize_audio(raw, normalized)
        os.replace(normalized, target)
    print(f"Edge sample ready: {poem['title']} ({duration:.2f}s)", flush=True)


def azure_config():
    values = {}
    path = ROOT / ".env.azure-speech.local"
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if separator and name.strip() in ("SPEECH_KEY", "SPEECH_REGION"):
                values[name.strip()] = value.strip().strip("\"'")
    key = os.environ.get("SPEECH_KEY") or values.get("SPEECH_KEY", "")
    region = os.environ.get("SPEECH_REGION") or values.get("SPEECH_REGION", "")
    if not key or not region:
        raise ValueError("先创建 Azure Speech 资源，再在 .env.azure-speech.local 填写 SPEECH_KEY 与 SPEECH_REGION。")
    if not re.fullmatch(r"[a-z][a-z0-9]{1,40}", region):
        raise ValueError("SPEECH_REGION 应为资源区域代码，例如 eastasia，不是完整网址或中文地区名。")
    return key, region


def prompt_azure_config(region):
    if not re.fullmatch(r"[a-z][a-z0-9]{1,40}", region):
        raise ValueError("区域应为 eastasia 等区域代码。")
    if not sys.stdin.isatty():
        raise ValueError("隐藏密钥输入需要在本机交互式终端运行。")
    # Refuse getpass's echoing fallback; credentials must never enter logs.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("Azure Speech 密钥（输入隐藏，粘贴后回车）：").strip()
        except (getpass.GetPassWarning, EOFError):
            raise ValueError("无法安全读取密钥，已取消合成。") from None
    if not key or any(character.isspace() for character in key):
        raise ValueError("密钥为空或包含空白字符，未发送请求。")
    return key, region


def synthesize_azure_ssml(ssml, target, credentials, *, normalize=True):
    import certifi
    key, region = credentials
    request = Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"), method="POST",
        headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                 "User-Agent": "TangPoetryNarrationTrial"})
    try:
        # The bundled macOS Python may not have a configured default CA path.
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=120, context=context) as response:
            audio = response.read()
    except HTTPError as error:
        # Keep credentials and response bodies out of logs.
        reasons = {400: "请检查音色、风格及朗读稿", 401: "请检查密钥与资源区域是否匹配",
                   403: "请检查资源权限或网络访问限制", 429: "已达到请求限制，请稍后重试"}
        raise AzureHTTPError(error.code, f"Azure HTTP {error.code}：{reasons.get(error.code, '服务暂不可用，请稍后重试')}") from None
    except (URLError, TimeoutError, ConnectionError, ssl.SSLError):
        raise AzureTransportError("Azure 连接失败，请检查网络及资源区域。") from None
    except HTTPException:
        raise AzureTransportError("Azure 音频传输中断，未保存不完整的文件；请重试当前版本。") from None
    with tempfile.TemporaryDirectory(prefix=".azure-", dir=target.parent) as temporary:
        raw = Path(temporary) / "raw.mp3"
        normalized = Path(temporary) / "normalized.mp3"
        raw.write_bytes(audio)
        duration = normalize_audio(raw, normalized) if normalize else probe(raw)
        os.replace(normalized if normalize else raw, target)
    return duration


def generate_azure(poem, plan, credentials):
    duration = synthesize_azure_ssml(azure_ssml(poem, plan), OUT / f"{poem['id']}-azure.mp3", credentials)
    print(f"Azure sample ready: {poem['title']} ({duration:.2f}s)", flush=True)


def write_comparison(poems):
    sections = []
    for poem, plan in zip(poems, TRIALS):
        identity = poem["id"]
        edge = (f'<audio controls preload="none" src="{identity}-edge.mp3"></audio>'
                if (OUT / f"{identity}-edge.mp3").is_file() else "尚未生成")
        azure = (f'<audio controls preload="none" src="{identity}-azure.mp3"></audio>'
                 if (OUT / f"{identity}-azure.mp3").is_file() else "<p>等待 Azure Speech 资源配置；尚未合成</p>")
        sections.append(f'''<section><h2>{html.escape(poem['title'])}</h2>
<p>{html.escape(plan['direction'])}</p><div class="samples">
<div><h3>现有版 · 云希</h3><p>语速 −15%，每行独立句读</p>
<audio controls preload="none" src="../../assets/audio/{identity}.mp3"></audio></div>
<div><h3>节奏调整版 · 云希</h3><p>语速 {plan['rate']}，上下句连读，保留原标点</p>{edge}</div>
<div><h3>情绪对照版 · 云泽</h3>{azure}
<a href="{identity}-azure.ssml" download>下载朗诵稿</a></div></div></section>''')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>三首朗读对照</title>
<style>body{max-width:1050px;margin:40px auto;padding:0 24px;background:#f5f0e5;color:#352f27;
font:16px/1.7 system-ui}h1{font:32px serif}h2{font:26px serif}h3{font-size:16px}p{color:#70685d}
section{border-top:1px solid #d9d0c0;padding:20px 0}.samples{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px}
audio{width:100%}a{color:#7a4b2b}</style><h1>三首朗读对照</h1>
<p>先比较人声与节奏。各版采用相同的音量处理，无配乐。正式 App 仍保留原五首试听。</p>'''
    if (OUT / "recitation/index.html").is_file():
        page += '<p><a href="recitation/">新增：登鹳雀楼 · 五版朗诵对比 →</a></p>'
    if (OUT / "poetry-reading/index.html").is_file():
        page += '<p><a href="poetry-reading/">晓晓诗歌朗读 · 四种体裁试听 →</a></p>'
    page += "".join(sections)
    page += '''<script>document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')
document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true)</script></html>'''
    (OUT / "index.html").write_text(page)


async def main(generate, azure=False, prompt_key=False, region="eastasia"):
    credentials = (prompt_azure_config(region) if prompt_key else azure_config()) if azure else None
    OUT.mkdir(parents=True, exist_ok=True)
    poems = [json.loads((ROOT / f"data/reader/poems/{p['id']}.json").read_text()) for p in TRIALS]
    for poem, plan in zip(poems, TRIALS):
        (OUT / f"{poem['id']}-edge.txt").write_text(edge_text(poem) + "\n")
        (OUT / f"{poem['id']}-azure.ssml").write_text(azure_ssml(poem, plan))
    write_comparison(poems)
    if generate:
        for poem, plan in zip(poems, TRIALS):
            await generate_edge(poem, plan)
            write_comparison(poems)
    if azure:
        for poem, plan in zip(poems, TRIALS):
            generate_azure(poem, plan, credentials)
            write_comparison(poems)
    print(f"Comparison: {OUT / 'index.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-edge", action="store_true")
    parser.add_argument("--generate-azure", action="store_true", help="synthesize only the three Azure trial poems")
    parser.add_argument("--prompt-key", action="store_true", help="read the Azure key without echo or storage")
    parser.add_argument("--region", default="eastasia", help="resource region for --prompt-key (default: eastasia)")
    args = parser.parse_args()
    if args.prompt_key and not args.generate_azure:
        parser.error("--prompt-key 必须与 --generate-azure 一起使用")
    try:
        asyncio.run(main(args.generate_edge, args.generate_azure, args.prompt_key, args.region))
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")

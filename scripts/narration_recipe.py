"""Stable, credential-free narration recipe shared by generation and packaging."""
import hashlib
import copy
import html
import json
from xml.etree import ElementTree as ET

AZURE_RECIPE = {
    "version": 1, "engine": "azure-speech", "voice": "zh-CN-XiaoxiaoNeural",
    "voiceLabel": "晓晓 · 诗歌朗读", "style": "poetry-reading", "styledegree": "1.3",
    "rate": "-6%", "introRate": "-5%", "pairPauseMs": 500,
    "introPauseMs": 800, "endingPauseMs": 800, "titlePauseMs": 350,
    "loudnessLUFS": -18, "truePeakDB": -1.5, "loudnessRange": 11,
    "endingPadSeconds": 0.5, "bitrate": "64k", "sampleRate": 24000,
}
NS = {"s": "http://www.w3.org/2001/10/synthesis", "m": "https://www.w3.org/2001/mstts"}
TITLE_ALIASES = {"tang-224-lu-chai": "鹿寨"}


def poetry_ssml(poem):
    lines = ["".join(token[0] for token in line).strip() for line in poem["rubyLines"]]
    if not lines or not all(lines):
        raise ValueError(f"Empty verse in {poem['id']}")
    dynasty = poem.get('dynasty', '唐')
    era = '唐代' if dynasty == '唐' else dynasty
    pairs = ["".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    body = '<prosody rate="-6%">' + '<break time="500ms"/>'.join(
        f'<s>{html.escape(pair)}</s>' for pair in pairs) + '</prosody>'
    result = f'''<speak version="1.0" xmlns="{NS['s']}" xmlns:mstts="{NS['m']}" xml:lang="zh-CN">
  <voice name="zh-CN-XiaoxiaoNeural">
    <prosody rate="-5%"><s>{html.escape(TITLE_ALIASES.get(poem['id'], poem['title']))}。</s><break time="350ms"/>
      <s>{html.escape(era)}，{html.escape(poem['author'])}。</s></prosody>
    <break time="800ms"/>
    <mstts:express-as style="poetry-reading" styledegree="1.3">
      {body}
    </mstts:express-as>
    <break time="800ms"/>
  </voice>
</speak>
'''
    element = ET.fromstring(result).find(".//m:express-as", NS)
    if "".join("".join(element.itertext()).split()) != "".join(lines):
        raise ValueError(f"Narration body differs from poem: {poem['id']}")
    return result


def poetry_ssml_chunks(poem, couplets_per_chunk=4):
    """Split long transfers at existing couplet pauses, keeping every spoken word."""
    if couplets_per_chunk < 1:
        raise ValueError("A chunk must contain at least one couplet")
    ET.register_namespace("", NS['s'])
    ET.register_namespace("mstts", NS['m'])
    original = ET.fromstring(poetry_ssml(poem))
    sentences = original.find('.//m:express-as/s:prosody', NS).findall('s:s', NS)
    chunks = []
    for start in range(0, len(sentences), couplets_per_chunk):
        root = copy.deepcopy(original)
        voice = root.find('s:voice', NS)
        body = voice.find('m:express-as/s:prosody', NS)
        for child in list(body):
            body.remove(child)
        end = min(start + couplets_per_chunk, len(sentences))
        for index in range(start, end):
            body.append(copy.deepcopy(sentences[index]))
            if index < len(sentences) - 1:
                ET.SubElement(body, f'{{{NS["s"]}}}break', {'time': '500ms'})
        if start:
            # Title/author prosody and the following introduction pause.
            voice.remove(voice.find('s:prosody', NS))
            voice.remove(voice.find('s:break', NS))
        if end < len(sentences):
            voice.remove(list(voice)[-1])  # The final 800ms belongs only to the last chunk.
        chunks.append(ET.tostring(root, encoding='unicode'))
    spoken = ''.join(''.join(ET.fromstring(chunk).itertext()) for chunk in chunks)
    if ''.join(spoken.split()) != ''.join(''.join(original.itertext()).split()):
        raise ValueError("Chunking changed the spoken text")
    return chunks


def input_hash(poem, recipe):
    if recipe.get("engine") == "azure-speech":
        if recipe != AZURE_RECIPE:
            raise ValueError("Unknown Azure recipe; regenerate with the supported recipe")
        payload = {"ssml": poetry_ssml(poem), "recipe": recipe}
    elif recipe.get("engine") == "edge-tts":
        try:
            from .generate_audio import narration_text
        except ImportError:
            from generate_audio import narration_text
        payload = {"text": narration_text(poem), "recipe": recipe}
    else:
        raise ValueError("Unknown narration engine")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_release(root):
    """Check released audio references and inputs without optional audio packages."""
    catalog = json.loads((root / "data/reader/catalog.json").read_text())["poems"]
    manifest = json.loads((root / "data/audio/manifest.json").read_text())
    ids = {p["id"] for p in catalog}
    expected = set(manifest.get("previewIDs", [])) if manifest.get("release") == "preview" else ids
    if not expected or set(manifest["tracks"]) != expected or not expected <= ids:
        raise ValueError("Narration catalog coverage is incomplete")
    if manifest.get("release") == "full" and manifest.get("trackOrder") != [p["id"] for p in catalog]:
        raise ValueError("Narration order differs from the poetry catalog")
    for summary in catalog:
        identity = summary["id"]
        if identity not in expected:
            continue
        track = manifest["tracks"][identity]
        poem = json.loads((root / f"data/reader/poems/{identity}.json").read_text())
        prefix = "assets/audio/xiaoxiao-poetry-v1" if manifest["recipe"]["engine"] == "azure-speech" else "assets/audio"
        if (track.get("id") != identity or track.get("title") != poem["title"]
                or track.get("author") != poem["author"] or track.get("file") != f"{prefix}/{identity}.mp3"
                or track.get("inputSHA256") != input_hash(poem, manifest["recipe"])):
            raise ValueError(f"Narration source/recipe mismatch: {identity}")
        if manifest["recipe"]["engine"] == "azure-speech" and track.get("section") != summary["section"]:
            raise ValueError(f"Narration genre mismatch: {identity}")
        path = root / track["file"]
        if path.stat().st_size != track["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != track["sha256"]:
            raise ValueError(f"Narration file integrity failure: {identity}")
    return len(expected)

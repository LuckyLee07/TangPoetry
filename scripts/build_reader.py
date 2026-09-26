#!/usr/bin/env python3
"""Build compact shared web/iOS data without modifying the archival content sources."""
import json
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/reader"
SECTION_ORDER = ["五言绝句", "七言绝句", "五言律诗", "七言律诗", "五言古诗", "七言古诗", "乐府"]
FALLBACKS = {
    "思乡": "jing-ye-si", "山水": "lu-zhai", "春日": "chun-xiao",
    "送别": "song-yuan-er", "冬雪": "jiang-xue"
}


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def theme_for(poem):
    tags = " ".join(poem.get("tags", []))
    title = poem["title"]
    for theme, words in [("送别", ["送", "别"]), ("边塞", ["塞", "从军", "凉州"]),
                         ("思乡", ["思乡", "怀乡"]), ("春日", ["春"]),
                         ("怀古", ["怀古", "咏史"]), ("田园", ["田园"]), ("咏物", ["咏物"])]:
        if any(word in title + tags for word in words):
            return theme
    return "山水"


def optimized(image, width, suffix):
    """Lossy delivery copies; keep original artwork untouched."""
    target = ROOT / "assets/optimized" / f"{Path(image).stem}-{suffix}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / image
    if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(["cwebp", "-quiet", "-q", "83", "-resize", str(width), "0", str(source), "-o", str(target)], check=True)
    return target.relative_to(ROOT).as_posix()


def ruby_lines(poem, editorial):
    flat = [list(pair) for line in poem["rubyLines"] for pair in line]
    if editorial.get("pinyin"):
        chars = [pair for pair in flat if re.fullmatch(r"[\u3400-\u9fff]", pair[0])]
        assert len(chars) == len(editorial["pinyin"]), f"Pinyin count: {poem['id']}"
        for pair, pinyin in zip(chars, editorial["pinyin"]):
            pair[1] = pinyin
    # Split the complete poem at punctuation, never truncate long poems.
    lines, current = [], []
    for pair in flat:
        current.append(pair)
        if pair[0] in "，。！？；：":
            lines.append(current)
            current = []
    if current:
        lines.append(current)
    return lines


def commentary_entries():
    entries = {}
    for path in sorted((ROOT / "data/commentary").glob("*.json")):
        batch = json.loads(path.read_text())["poems"]
        assert not entries.keys() & batch.keys(), f"Duplicate commentary: {path}"
        entries.update(batch)
    return entries


def note_key(text):
    return re.sub(r"[\W_]+", "", re.sub(r"^[：:\s]*\d+[.．、]\s*", "", text))


def reading_notes(poem, commentary, corrections=()):
    """Rejoin source HTML line wraps; separate meanings, glosses and textual variants."""
    grouped = []
    for raw in poem.get("notes", []):
        text = raw["text"].strip().lstrip("：:")
        if not text:
            continue
        for correction in poem.get("corrections", []):
            if correction.get("original") == "□":
                text = text.replace("□", correction["replacement"])
        if (raw["source"] == "chiuinan" and grouped
                and grouped[-1]["source"] == raw["source"]
                and not re.match(r"^\d+[.．、]", text)):
            grouped[-1]["text"] += text
        else:
            grouped.append({"text": text, "source": raw["source"]})

    variants = [dict(note) for note in poem.get("variants", [])]
    annotations = []
    applied = set()
    for note in grouped:
        note["text"] = re.sub(r"^\d+[.．、]\s*", "", note["text"])
        for index, correction in enumerate(corrections):
            if note["source"] == correction["source"] and note["text"] == correction["original"]:
                note["text"] = correction["replacement"]
                applied.add(index)
        # This imported note combines a variant with a definition in one sentence.
        if re.fullmatch(r'挂帆席--一作\s*[“"]洞庭去[”"]，\s*扬帆驶船。', note["text"]):
            annotations.append({"text": "挂帆席：扬帆驶船。", "source": note["source"]})
            note["text"] = "挂帆席，一作“洞庭去”。"
        if re.search(r"一作|又作|另作|本作|应作|应以.+为正", note["text"]):
            variants.append(note)
        else:
            annotations.append(note)
    assert len(applied) == len(corrections), f"Stale reading-note correction: {poem.get('id')}"

    # Original editorial glosses can replace the same headword's imported definition.
    # The complete source notes remain unchanged in data/final for traceability.
    glossary = commentary.get("glossary", [])
    terms = {note_key(item["term"]) for item in glossary}
    annotations = [note for note in annotations
                   if note_key(re.split(r"[：:]", note["text"], maxsplit=1)[0]) not in terms]
    annotations = [{"text": f"{item['term']}：{item['text']}", "source": "编辑释义"}
                   for item in glossary] + annotations

    def unique(notes):
        result, seen = [], set()
        for note in notes:
            key = note_key(note["text"])
            if key and key not in seen:
                seen.add(key)
                result.append(note)
        return result

    return unique(annotations), unique(variants)


def build():
    source = read("data/final/tang_poems_final.json")
    editorial = read("data/editorial.json")["poems"]
    commentary = commentary_entries()
    note_corrections = read("data/note-corrections.json")["poems"]
    assert commentary.keys() == {p["id"] for p in source["poems"]}, "Commentary must cover the entire edition"
    visuals = read("data/visuals.json")
    art_plan_path = ROOT / "data/illustrations/plan.json"
    art_plan = read("data/illustrations/plan.json")["poems"] if art_plan_path.exists() else {}
    icon_frames = read("data/illustrations/library-icons.json")["poems"]
    assert icon_frames.keys() == {p["id"] for p in source["poems"]}, "Directory artwork must cover the edition"
    catalog, missing, details = [], [], []
    for poem in source["poems"]:
        edit = editorial.get(poem["id"], {})
        explanation = commentary[poem["id"]]
        assert explanation["summary"].strip() and explanation["interpretation"], poem["id"]
        theme = edit.get("theme", theme_for(poem))
        candidate = edit.get("image") or art_plan.get(poem["id"], {}).get("image") or visuals.get(poem["id"], {}).get("image", "")
        dedicated = bool(candidate and (ROOT / candidate).is_file())
        if candidate and not dedicated:
            missing.append({"id": poem["id"], "image": candidate})
        image = candidate if dedicated else f"assets/illustrations-portrait/{FALLBACKS.get(theme, 'lu-zhai')}.png"
        icon = icon_frames[poem["id"]]
        assert icon["source"] == image, f"Directory artwork needs reframing: {poem['id']}"
        assert icon["sourceSHA256"] == hashlib.sha256((ROOT / image).read_bytes()).hexdigest(), f"Directory source changed: {poem['id']}"
        assert 0 < icon["side"] <= 1 and 0 <= icon["x"] <= 1 - icon["side"] + 0.00001, poem["id"]
        assert 0 <= icon["y"] <= icon["aspect"] - icon["side"], poem["id"]
        title = edit.get("displayTitle", poem["title"])
        aliases = list(dict.fromkeys([poem["title"], *poem.get("aliases", [])]))
        item = {
            "id": poem["id"], "order": poem["order"], "title": title, "aliases": aliases,
            "author": poem["author"], "section": poem["section"], "theme": theme,
            "featured": bool(edit.get("featured") and dedicated), "dedicatedArt": dedicated,
            "image": optimized(image, 940, "page"), "thumbnail": optimized(image, 240, "thumb"),
            "thumbnailFrame": {key: icon[key] for key in ("x", "y", "side", "aspect")},
            "searchText": " ".join([title, *aliases, poem["titleTraditional"], poem["author"], poem["authorTraditional"],
                                    poem["section"], theme, *poem.get("tags", []), poem["text"], poem["textTraditional"]])
        }
        for key in ("artworkMode", "artworkFocusY", "textStart"):
            if key in edit:
                item[key] = edit[key]
        catalog.append(item)
        annotations, variants = reading_notes(poem, explanation, note_corrections.get(poem["id"], []))
        detail = {
            "id": poem["id"], "title": title, "author": poem["author"],
            "rubyLines": ruby_lines(poem, edit), "noteTitle": edit.get("noteTitle", "诗意"),
            "note": explanation["summary"], "interpretation": explanation["interpretation"],
            "annotations": annotations, "variants": variants, "preface": poem.get("preface", []),
            "notes": [note["text"] for note in annotations],
            "contentStatus": explanation["reviewStatus"],
            "sourceTitle": poem["title"], "layout": edit.get("layout", "center-low")
        }
        details.append(detail)
        write(OUT / "poems" / f"{poem['id']}.json", detail)
    section_rank = {section: rank for rank, section in enumerate(SECTION_ORDER)}
    unknown_sections = {poem["section"] for poem in catalog} - section_rank.keys()
    assert not unknown_sections, f"Unclassified sections: {sorted(unknown_sections)}"
    catalog.sort(key=lambda poem: (section_rank[poem["section"]], poem["order"]))
    write(OUT / "catalog.json", {"schemaVersion": 1, "sections": SECTION_ORDER, "poems": catalog})
    write(OUT / "build-report.json", {
        "poems": len(catalog), "featured": sum(p["featured"] for p in catalog),
        "sections": [{"section": section, "poems": sum(p["section"] == section for p in catalog)}
                     for section in SECTION_ORDER],
        "dedicatedArt": sum(p["dedicatedArt"] for p in catalog),
        "artRemaining": sum(not p["dedicatedArt"] for p in catalog),
        "notesMissing": sum(not p["note"].strip() for p in details),
        "interpretationsMissing": sum(not p["interpretation"] for p in details),
        "sourceNotesMissing": sum(not p["notes"] for p in source["poems"]),
        "poemsWithPreface": sum(bool(p["preface"]) for p in details),
        "poemsWithVariants": sum(bool(p["variants"]) for p in details),
        "unavailablePlannedArt": missing, "missingSourceOrders": source["stats"]["missingCtextOrders"]
    })
    print(f"Built {len(catalog)} poems, {sum(p['featured'] for p in catalog)} featured, {sum(p['dedicatedArt'] for p in catalog)} dedicated illustrations; {len(missing)} planned assets use fallback.")


if __name__ == "__main__":
    build()

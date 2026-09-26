#!/usr/bin/env python3
"""Build compact shared web/iOS data without modifying the archival content sources."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/reader"
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


def build():
    source = read("data/final/tang_poems_final.json")
    editorial = read("data/editorial.json")["poems"]
    visuals = read("data/visuals.json")
    catalog, missing = [], []
    for poem in source["poems"]:
        edit = editorial.get(poem["id"], {})
        theme = edit.get("theme", theme_for(poem))
        candidate = edit.get("image") or visuals.get(poem["id"], {}).get("image", "")
        dedicated = bool(candidate and (ROOT / candidate).is_file())
        if candidate and not dedicated:
            missing.append({"id": poem["id"], "image": candidate})
        image = candidate if dedicated else f"assets/illustrations-portrait/{FALLBACKS.get(theme, 'lu-zhai')}.png"
        title = edit.get("displayTitle", poem["title"])
        aliases = list(dict.fromkeys([poem["title"], *poem.get("aliases", [])]))
        item = {
            "id": poem["id"], "order": poem["order"], "title": title, "aliases": aliases,
            "author": poem["author"], "section": poem["section"], "theme": theme,
            "featured": bool(edit.get("featured") and dedicated), "dedicatedArt": dedicated,
            "image": optimized(image, 940, "page"), "thumbnail": optimized(image, 240, "thumb"),
            "searchText": " ".join([title, *aliases, poem["titleTraditional"], poem["author"], poem["authorTraditional"],
                                    poem["section"], theme, *poem.get("tags", []), poem["text"], poem["textTraditional"]])
        }
        catalog.append(item)
        notes = list(dict.fromkeys(n["text"] for n in poem.get("notes", []) if n.get("text")))
        detail = {
            "id": poem["id"], "title": title, "author": poem["author"],
            "rubyLines": ruby_lines(poem, edit), "noteTitle": edit.get("noteTitle", "字词小注"),
            "note": edit.get("note", "；".join(notes[:2])), "notes": notes,
            "contentStatus": edit.get("contentStatus", "source-import"),
            "sourceTitle": poem["title"], "layout": edit.get("layout", "center-low")
        }
        write(OUT / "poems" / f"{poem['id']}.json", detail)
    write(OUT / "catalog.json", {"schemaVersion": 1, "poems": catalog})
    write(OUT / "build-report.json", {
        "poems": len(catalog), "featured": sum(p["featured"] for p in catalog),
        "notesMissing": sum(not p["notes"] for p in source["poems"]),
        "unavailablePlannedArt": missing, "missingSourceOrders": source["stats"]["missingCtextOrders"]
    })
    print(f"Built {len(catalog)} poems, {sum(p['featured'] for p in catalog)} featured; {len(missing)} planned assets use fallback.")


if __name__ == "__main__":
    build()

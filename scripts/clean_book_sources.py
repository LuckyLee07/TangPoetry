#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_sources"
OUT_DIR = ROOT / "data" / "sources"
LOCAL_SOURCE = ROOT / "唐诗三百首.json"

CHIUINAN_URL = "https://chiuinan.github.io/game/game/cin/poem300.htm"
CTEXT_URL = "https://ctext.org/wiki.pl?if=en&chapter=820428"

GENRES_TRADITIONAL = (
    "五言古詩",
    "七言古詩",
    "五言絕句",
    "七言絕句",
    "五言律詩",
    "七言律詩",
    "樂府",
)

SECTION_NORMALIZATION = {
    "五言古詩": "五言古诗",
    "七言古詩": "七言古诗",
    "五言絕句": "五言绝句",
    "七言絕句": "七言绝句",
    "五言律詩": "五言律诗",
    "七言律詩": "七言律诗",
    "樂府": "乐府",
}

t2s = OpenCC("t2s")
s2t = OpenCC("s2t")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_key(text: str) -> str:
    text = t2s.convert(text or "")
    return re.sub(r"[\s　·．。！？；：，、,.!?;:'\"“”‘’《》〈〉（）()\[\]【】-]+", "", text)


def clean_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_cn_lines(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.findall(r"[^。！？；]+[。！？；]?", text)
    return [part.strip() for part in parts if part.strip()]


def normalize_notes(lines: list[str]) -> list[str]:
    notes: list[str] = []
    for line in lines:
        item = clean_text(line)
        if not item:
            continue
        item = re.sub(r"^〔註〕", "", item).strip()
        notes.append(item)
    return notes


def load_local_poems() -> list[dict[str, Any]]:
    return json.loads(LOCAL_SOURCE.read_text(encoding="utf-8"))


def known_authors_traditional(local_poems: list[dict[str, Any]]) -> list[str]:
    authors = {s2t.convert(poem.get("author", "")) for poem in local_poems if poem.get("author")}
    authors.update(
        {
            "杜秋娘",
            "邱為",
            "唐玄宗",
            "劉脊虛",
            "僧皎然",
            "李頻",
            "顧況",
            "佚名",
            "無名氏",
        }
    )
    return sorted(authors, key=len, reverse=True)


def split_ctext_heading(rest: str, authors: list[str]) -> tuple[str, str]:
    for author in authors:
        if rest.startswith(author):
            return author, rest[len(author) :].strip()
    return "", rest.strip()


def parse_chiuinan() -> list[dict[str, Any]]:
    html = (RAW_DIR / "chiuinan.html").read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")
    if not pre:
        raise RuntimeError("chiuinan.html does not contain a <pre> block")

    lines = pre.get_text("\n").splitlines()
    poems: list[dict[str, Any]] = []
    section = ""
    i = 0
    order = 0
    header_re = re.compile(r"^\s*(.+?)\s+--\s+唐．(.+?)\s*$")

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("§"):
            candidate = stripped.lstrip("§").strip()
            section = candidate if candidate in GENRES_TRADITIONAL else ""
            i += 1
            continue

        match = header_re.match(lines[i])
        if not match or not section:
            i += 1
            continue

        title_traditional = clean_text(match.group(1))
        author_traditional = clean_text(match.group(2))

        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines) or set(lines[i].strip()) != {"="}:
            continue
        i += 1

        poem_lines: list[str] = []
        while i < len(lines):
            value = lines[i].strip()
            if value and set(value) == {"="}:
                i += 1
                break
            if value:
                poem_lines.append(value)
            i += 1

        note_lines: list[str] = []
        while i < len(lines):
            value = lines[i]
            stripped = value.strip()
            if stripped.startswith("§") or header_re.match(value):
                break
            if stripped:
                note_lines.append(stripped)
            i += 1

        order += 1
        poems.append(
            {
                "source": "chiuinan",
                "sourceUrl": CHIUINAN_URL,
                "bookOrder": order,
                "sectionTraditional": section,
                "sectionSimplified": SECTION_NORMALIZATION[section],
                "titleTraditional": title_traditional,
                "titleSimplified": t2s.convert(title_traditional),
                "authorTraditional": author_traditional,
                "authorSimplified": t2s.convert(author_traditional),
                "linesTraditional": poem_lines,
                "linesSimplified": [t2s.convert(line) for line in poem_lines],
                "textTraditional": "".join(poem_lines),
                "textSimplified": t2s.convert("".join(poem_lines)),
                "notesTraditional": normalize_notes(note_lines),
                "notesSimplified": [t2s.convert(note) for note in normalize_notes(note_lines)],
                "matchKey": compact_key(author_traditional + title_traditional),
            }
        )

    return poems


@dataclass
class CTextPoem:
    source: str
    sourceUrl: str
    bookOrder: int
    sequence: int
    sectionTraditional: str
    sectionSimplified: str
    titleTraditional: str
    titleSimplified: str
    authorTraditional: str
    authorSimplified: str
    linesTraditional: list[str]
    linesSimplified: list[str]
    textTraditional: str
    textSimplified: str
    englishHeadingRaw: str
    englishTranslationRaw: str
    englishTranslationClean: str
    englishTranslationSegments: list[str]
    matchKey: str


def clean_ctext_translation(text: str) -> tuple[str, list[str]]:
    text = clean_text(text)
    replacements = [
        ("。。。。", ".... "),
        ("，", ", "),
        ("；", "; "),
        ("。", ". "),
        ("？", "? "),
        ("！", "! "),
        ("：", ": "),
        ("『", "'"),
        ("』", "'"),
        ("“", '"'),
        ("”", '"'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip()
    segments = [seg.strip() for seg in re.split(r"(?<=[.!?;])\s+", text) if seg.strip()]
    return text, segments


def parse_ctext(local_poems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    authors = known_authors_traditional(local_poems)
    html = (RAW_DIR / "ctext.html").read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    values: list[str] = []
    for row in soup.select("tr.result"):
        cells = row.find_all("td", class_="ctext")
        if len(cells) >= 2:
            values.append(clean_text(cells[-1].get_text("", strip=True)))

    header_re = re.compile(rf"^(\d{{3}})({'|'.join(GENRES_TRADITIONAL)})(.+)$")
    poems: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    order = 0

    def finish() -> None:
        nonlocal current
        if not current:
            return
        english_clean, segments = clean_ctext_translation(current.get("englishTranslationRaw", ""))
        current["englishTranslationClean"] = english_clean
        current["englishTranslationSegments"] = segments
        current["textTraditional"] = "".join(current["linesTraditional"])
        current["textSimplified"] = t2s.convert(current["textTraditional"])
        current["linesSimplified"] = [t2s.convert(line) for line in current["linesTraditional"]]
        current["matchKey"] = compact_key(current["authorTraditional"] + current["titleTraditional"])
        poems.append(current)
        current = None

    for value in values:
        if not value or set(value) == {"-"}:
            continue
        match = header_re.match(value)
        if match:
            finish()
            sequence = int(match.group(1))
            section = match.group(2)
            author, title = split_ctext_heading(match.group(3), authors)
            order += 1
            current = {
                "source": "ctext",
                "sourceUrl": CTEXT_URL,
                "bookOrder": order,
                "sequence": sequence,
                "sectionTraditional": section,
                "sectionSimplified": SECTION_NORMALIZATION[section],
                "titleTraditional": title,
                "titleSimplified": t2s.convert(title),
                "authorTraditional": author,
                "authorSimplified": t2s.convert(author),
                "linesTraditional": [],
                "linesSimplified": [],
                "textTraditional": "",
                "textSimplified": "",
                "englishHeadingRaw": "",
                "englishTranslationRaw": "",
                "englishTranslationClean": "",
                "englishTranslationSegments": [],
                "matchKey": "",
            }
            continue

        if not current:
            continue
        if re.search(r"[\u4e00-\u9fff]", value):
            current["linesTraditional"].extend(split_cn_lines(value))
        elif not current["englishHeadingRaw"]:
            current["englishHeadingRaw"] = value
        else:
            if current["englishTranslationRaw"]:
                current["englishTranslationRaw"] += " "
            current["englishTranslationRaw"] += value

    finish()
    return poems


def build_match_report(
    local_poems: list[dict[str, Any]],
    chiuinan: list[dict[str, Any]],
    ctext: list[dict[str, Any]],
) -> dict[str, Any]:
    local_by_key: dict[str, list[dict[str, Any]]] = {}
    local_by_text: dict[str, list[dict[str, Any]]] = {}
    for index, poem in enumerate(local_poems, start=1):
        key = compact_key(s2t.convert(poem.get("author", "")) + s2t.convert(poem.get("title", "")))
        item = {
            "sourceIndex": index,
            "title": poem.get("title", ""),
            "author": poem.get("author", ""),
        }
        local_by_key.setdefault(key, []).append(
            item
        )
        text_key = compact_key("".join(poem.get("paragraphs", [])))
        if text_key:
            local_by_text.setdefault(text_key, []).append(item)

    def match_local(poem: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        title_matches = local_by_key.get(poem["matchKey"])
        if title_matches:
            return "authorTitle", title_matches

        text_key = compact_key(poem.get("textTraditional", ""))
        text_matches = local_by_text.get(text_key)
        if text_matches:
            return "textExact", text_matches

        if len(text_key) >= 24:
            prefix = text_key[:24]
            for local_text_key, candidates in local_by_text.items():
                if len(local_text_key) >= 24 and local_text_key[:24] == prefix:
                    return "textPrefix24", candidates

        return "", []

    def summarize(source_poems: list[dict[str, Any]], name: str) -> dict[str, Any]:
        matched = []
        unmatched = []
        methods: dict[str, int] = {}
        duplicate_source_keys: dict[str, int] = {}
        for poem in source_poems:
            key = poem["matchKey"]
            duplicate_source_keys[key] = duplicate_source_keys.get(key, 0) + 1
            match_method, target = match_local(poem)
            item = {
                "bookOrder": poem["bookOrder"],
                "sequence": poem.get("sequence"),
                "section": poem["sectionSimplified"],
                "titleTraditional": poem["titleTraditional"],
                "titleSimplified": poem["titleSimplified"],
                "authorTraditional": poem["authorTraditional"],
                "authorSimplified": poem["authorSimplified"],
                "matchKey": key,
            }
            if target:
                methods[match_method] = methods.get(match_method, 0) + 1
                matched.append({**item, "matchMethod": match_method, "localMatches": target})
            else:
                unmatched.append(item)

        return {
            "source": name,
            "total": len(source_poems),
            "matchedLocal": len(matched),
            "unmatchedLocal": len(unmatched),
            "matchMethods": methods,
            "duplicateSourceKeys": [
                {"matchKey": key, "count": count}
                for key, count in sorted(duplicate_source_keys.items())
                if count > 1
            ],
            "unmatchedSamples": unmatched[:40],
        }

    return {
        "generatedAt": now_iso(),
        "localSource": str(LOCAL_SOURCE.relative_to(ROOT)),
        "localPoemCount": len(local_poems),
        "sources": [summarize(chiuinan, "chiuinan"), summarize(ctext, "ctext")],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    local_poems = load_local_poems()
    chiuinan = parse_chiuinan()
    ctext = parse_ctext(local_poems)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "chiuinan_clean.json", chiuinan)
    write_json(OUT_DIR / "ctext_clean.json", ctext)
    write_json(OUT_DIR / "source_match_report.json", build_match_report(local_poems, chiuinan, ctext))

    book_order = [
        {
            "bookOrder": poem["bookOrder"],
            "sequence": poem.get("sequence"),
            "section": poem["sectionSimplified"],
            "titleTraditional": poem["titleTraditional"],
            "titleSimplified": poem["titleSimplified"],
            "authorTraditional": poem["authorTraditional"],
            "authorSimplified": poem["authorSimplified"],
            "matchKey": poem["matchKey"],
        }
        for poem in ctext
    ]
    write_json(OUT_DIR / "ctext_book_order.json", book_order)

    print(f"chiuinan poems: {len(chiuinan)}")
    print(f"ctext poems: {len(ctext)}")
    print(f"outputs: {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

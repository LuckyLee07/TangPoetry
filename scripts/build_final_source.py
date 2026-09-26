#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

from build_poems import best_order_match, compact_key, load_order_sources, slugify, text_similarity


ROOT = Path(__file__).resolve().parents[1]
BASE_SOURCE = ROOT / "唐诗三百首.json"
CTEXT_SOURCE = ROOT / "data" / "sources" / "ctext_clean.json"
CHIUINAN_SOURCE = ROOT / "data" / "sources" / "chiuinan_clean.json"
NEW_DEDUP_SOURCE = ROOT / "data" / "sources" / "tang300_new_dedup.json"
OUT = ROOT / "data" / "final" / "tang_poems_final.json"
REPORT_OUT = ROOT / "data" / "final" / "tang_poems_final_report.json"

t2s = OpenCC("t2s")
s2t = OpenCC("s2t")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def chinese_text(lines: list[str] | None) -> str:
    return "".join(lines or [])


def normalize_tags(tags: list[str]) -> list[str]:
    blocked = {"唐诗三百首", "隋・唐・五代"}
    normalized: list[str] = []
    for tag in tags or []:
        tag = t2s.convert(str(tag).strip())
        if not tag or tag in blocked:
            continue
        if tag not in normalized:
            normalized.append(tag)
    return normalized


def split_display_lines(paragraphs: list[str], limit: int = 4) -> list[str]:
    lines: list[str] = []
    for paragraph in paragraphs:
        for line in re.findall(r"[^，。！？；]+[，。！？；]?", paragraph):
            if line.strip():
                lines.append(line.strip())
    return lines[:limit]


def line_to_pinyin(line: str) -> list[list[str]]:
    chars = [char for char in line if re.match(r"[\u4e00-\u9fff]", char)]
    pinyin = lazy_pinyin("".join(chars), style=Style.TONE)
    index = 0
    result = []
    for char in line:
        if re.match(r"[\u4e00-\u9fff]", char):
            result.append([char, pinyin[index] if index < len(pinyin) else ""])
            index += 1
        else:
            result.append([char, ""])
    return result


def best_text_match(source: dict[str, Any], candidates: list[dict[str, Any]], threshold: float) -> dict[str, Any] | None:
    source_text = chinese_text(source.get("paragraphs"))
    best_score = 0.0
    best_candidate = None
    for candidate in candidates:
        candidate_text = candidate.get("textSimplified") or candidate.get("textTraditional")
        if not candidate_text:
            candidate_text = chinese_text(candidate.get("paragraphs") or candidate.get("linesSimplified"))
        score = text_similarity(source_text, candidate_text)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    if best_candidate and best_score >= threshold:
        best_candidate = dict(best_candidate)
        best_candidate["_matchScore"] = round(best_score, 4)
        return best_candidate
    return None


def source_aliases(*titles: str) -> list[str]:
    aliases: list[str] = []
    for title in titles:
        title = t2s.convert(title or "").strip()
        if title and title not in aliases:
            aliases.append(title)
    return aliases


def build_poem(
    base: dict[str, Any],
    source_index: int,
    order_sources: list[tuple[str, list[dict[str, Any]]]],
    ctext_by_order: dict[int, dict[str, Any]],
    chiuinan: list[dict[str, Any]],
    new_dedup: list[dict[str, Any]],
) -> dict[str, Any]:
    order_info = best_order_match(base, order_sources)
    ctext = ctext_by_order.get(order_info["bookOrder"])
    chiuinan_match = best_text_match(base, chiuinan, 0.86)
    new_match = best_text_match(base, new_dedup, 0.86)

    canonical_title = order_info["externalTitle"] or t2s.convert(base["title"])
    canonical_author = order_info["externalAuthor"] or t2s.convert(base["author"])
    canonical_lines = ctext["linesSimplified"] if ctext else base["paragraphs"]
    canonical_lines_traditional = ctext["linesTraditional"] if ctext else [s2t.convert(line) for line in base["paragraphs"]]

    notes = []
    for note in base.get("notes") or []:
        notes.append({"source": "唐诗三百首.json", "text": note})
    if chiuinan_match:
        for note in chiuinan_match.get("notesSimplified", []):
            notes.append({"source": "chiuinan", "text": note})

    tags = [order_info["bookSection"]]
    if new_match:
        tags.extend(normalize_tags(new_match.get("tags", [])))
    normalized_tags = []
    for tag in tags:
        if tag and tag not in normalized_tags:
            normalized_tags.append(tag)

    display_lines = split_display_lines(canonical_lines)
    ruby_lines = [line_to_pinyin(line) for line in canonical_lines]
    poem_id = f"tang-{order_info['bookOrder']:03d}-{slugify(canonical_title)}"

    return {
        "id": poem_id,
        "order": order_info["bookOrder"],
        "section": order_info["bookSection"],
        "title": canonical_title,
        "titleTraditional": ctext["titleTraditional"] if ctext else s2t.convert(canonical_title),
        "author": canonical_author,
        "authorTraditional": ctext["authorTraditional"] if ctext else s2t.convert(canonical_author),
        "dynasty": base.get("dynasty", "唐代"),
        "aliases": source_aliases(base.get("title", ""), ctext.get("titleSimplified", "") if ctext else ""),
        "lines": canonical_lines,
        "linesTraditional": canonical_lines_traditional,
        "text": chinese_text(canonical_lines),
        "textTraditional": chinese_text(canonical_lines_traditional),
        "displayLines": display_lines,
        "displayRubyLines": ruby_lines[: len(display_lines)],
        "rubyLines": ruby_lines,
        "notes": notes,
        "tags": normalized_tags,
        "english": {
            "headingRaw": ctext.get("englishHeadingRaw", "") if ctext else "",
            "translationRaw": ctext.get("englishTranslationRaw", "") if ctext else "",
            "translationClean": ctext.get("englishTranslationClean", "") if ctext else "",
            "segments": ctext.get("englishTranslationSegments", []) if ctext else [],
            "quality": "raw-spacing-lost" if ctext and ctext.get("englishTranslationRaw") else "missing",
        },
        "sourceRefs": {
            "base": {
                "file": "唐诗三百首.json",
                "index": source_index,
                "title": base.get("title", ""),
                "author": base.get("author", ""),
            },
            "order": {
                "source": order_info["orderSource"],
                "confidence": order_info["orderConfidence"],
                "score": order_info["orderScore"],
            },
            "ctext": {
                "matched": bool(ctext),
                "order": ctext.get("bookOrder") if ctext else None,
                "url": ctext.get("sourceUrl", "") if ctext else "",
            },
            "chiuinan": {
                "matched": bool(chiuinan_match),
                "order": chiuinan_match.get("bookOrder") if chiuinan_match else None,
                "score": chiuinan_match.get("_matchScore") if chiuinan_match else None,
                "url": chiuinan_match.get("sourceUrl", "") if chiuinan_match else "",
            },
            "tang300New": {
                "matched": bool(new_match),
                "id": new_match.get("id") if new_match else None,
                "score": new_match.get("_matchScore") if new_match else None,
            },
        },
    }


def build() -> None:
    base_poems = read_json(BASE_SOURCE, [])
    ctext_poems = read_json(CTEXT_SOURCE, [])
    chiuinan_poems = read_json(CHIUINAN_SOURCE, [])
    new_dedup_poems = read_json(NEW_DEDUP_SOURCE, [])

    order_sources = load_order_sources()
    ctext_by_order = {poem["bookOrder"]: poem for poem in ctext_poems}

    poems = [
        build_poem(base, index, order_sources, ctext_by_order, chiuinan_poems, new_dedup_poems)
        for index, base in enumerate(base_poems, start=1)
    ]
    poems.sort(key=lambda poem: poem["order"])

    # Visual briefs are editorial work, not disposable build output.
    visuals = read_json(ROOT / "data" / "visuals.json", {})
    for poem in poems:
        if poem["id"] in visuals:
            poem["visual"] = visuals[poem["id"]]

    missing_orders = [order for order in range(1, 321) if order not in {poem["order"] for poem in poems}]
    payload = {
        "schemaVersion": "1.0.0",
        "generatedAt": now_iso(),
        "name": "唐诗三百首最终内容源",
        "sourcePolicy": {
            "baseContent": "唐诗三百首.json",
            "orderAndCanonicalTitle": "data/sources/ctext_clean.json",
            "traditionalTextAndEnglish": "data/sources/ctext_clean.json",
            "notesFallback": ["唐诗三百首.json", "data/sources/chiuinan_clean.json"],
            "tagsSupplement": "data/sources/tang300_new_dedup.json",
        },
        "stats": {
            "poemCount": len(poems),
            "ctextMatched": sum(1 for poem in poems if poem["sourceRefs"]["ctext"]["matched"]),
            "chiuinanMatched": sum(1 for poem in poems if poem["sourceRefs"]["chiuinan"]["matched"]),
            "tang300NewMatched": sum(1 for poem in poems if poem["sourceRefs"]["tang300New"]["matched"]),
            "poemsWithNotes": sum(1 for poem in poems if poem["notes"]),
            "poemsWithTags": sum(1 for poem in poems if poem["tags"]),
            "missingCtextOrders": missing_orders,
        },
        "poems": poems,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "generatedAt": payload["generatedAt"],
        "output": str(OUT.relative_to(ROOT)),
        "stats": payload["stats"],
        "firstPoems": [
            {
                "order": poem["order"],
                "title": poem["title"],
                "author": poem["author"],
                "section": poem["section"],
                "aliases": poem["aliases"],
            }
            for poem in poems[:12]
        ],
        "poemsWithoutNotes": [
            {"order": poem["order"], "title": poem["title"], "author": poem["author"]}
            for poem in poems
            if not poem["notes"]
        ],
    }
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(poems)} poems to {OUT.relative_to(ROOT)}")
    print(f"Wrote report to {REPORT_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()

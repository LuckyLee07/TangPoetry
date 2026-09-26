#!/usr/bin/env python3
"""Validate deliverable references, complete text, and curated pronunciation alignment."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION_ORDER = ["五言绝句", "七言绝句", "五言律诗", "七言律诗", "五言古诗", "七言古诗", "乐府"]
catalog_data = json.loads((ROOT / "data/reader/catalog.json").read_text())
catalog = catalog_data["poems"]
source = {p["id"]: p for p in json.loads((ROOT / "data/final/tang_poems_final.json").read_text())["poems"]}
editorial = json.loads((ROOT / "data/editorial.json").read_text())["poems"]
assert len(catalog) == len(source) == 320
assert {p["order"] for p in catalog} == set(range(1, 321)), "The chosen edition must have all 320 source orders"
assert {p["id"] for p in catalog} == source.keys(), "Source poem identities must be preserved"
assert catalog_data["sections"] == SECTION_ORDER, "Unexpected genre sequence"
assert list(dict.fromkeys(p["section"] for p in catalog)) == SECTION_ORDER, "Genres must form ordered groups"
section_ranks = [SECTION_ORDER.index(p["section"]) for p in catalog]
assert section_ranks == sorted(section_ranks), "Genres must be contiguous and ordered"
for section in SECTION_ORDER:
    orders = [p["order"] for p in catalog if p["section"] == section]
    assert orders == sorted(orders), f"Source order changed within {section}"
assert all(p["dedicatedArt"] for p in catalog), "Every poem must have its own illustration"
assert len({p["image"] for p in catalog}) == 320
assert len({p["thumbnail"] for p in catalog}) == 320
for poem in catalog:
    original = source[poem["id"]]
    edit = editorial.get(poem["id"], {})
    for key in ("artworkMode", "artworkFocusY", "textStart"):
        assert (key in poem) == (key in edit), f"Unexpected layout metadata: {poem['id']} {key}"
        if key in edit:
            assert poem[key] == edit[key], f"Layout metadata mismatch: {poem['id']} {key}"
    if "artworkMode" in poem:
        assert poem["artworkMode"] == "window", f"Unknown artwork mode: {poem['id']}"
    if "artworkFocusY" in poem:
        assert poem.get("artworkMode") == "window", f"Artwork focus requires a window: {poem['id']}"
        assert type(poem["artworkFocusY"]) in (int, float) and 0 <= poem["artworkFocusY"] <= 1, poem["id"]
    if "textStart" in poem:
        assert type(poem["textStart"]) in (int, float) and 0 < poem["textStart"] < 1, poem["id"]
    assert poem["order"] == original["order"], f"Source order identity changed: {poem['id']}"
    assert poem["section"] == original["section"], f"Source genre changed: {poem['id']}"
    for key in ("image", "thumbnail"):
        assert (ROOT / poem[key]).is_file(), (poem["id"], key)
    detail = json.loads((ROOT / "data/reader/poems" / f"{poem['id']}.json").read_text())
    actual = "".join(pair[0] for line in detail["rubyLines"] for pair in line)
    assert actual == "".join(source[poem["id"]]["lines"]), poem["id"]
    assert "□" not in actual and "又作" not in actual, f"Editorial markers in poetry: {poem['id']}"
    assert detail["note"].strip() and detail["interpretation"], f"Missing meaning: {poem['id']}"
    assert all(text.strip() for text in detail["interpretation"]), poem["id"]
    assert detail["note"] not in detail["notes"], f"Summary duplicated as a word note: {poem['id']}"
    assert detail["notes"] == [note["text"] for note in detail["annotations"]]
    assert len(detail["notes"]) == len(set(detail["notes"])), f"Repeated notes: {poem['id']}"
    assert all("□" not in note for note in detail["notes"]), f"Unresolved placeholder in notes: {poem['id']}"
    assert detail["preface"] == original.get("preface", []), f"Missing preface: {poem['id']}"
    assert all(variant in detail["variants"] for variant in original.get("variants", [])), f"Missing variant: {poem['id']}"
    if poem["featured"]:
        assert poem["dedicatedArt"] and detail["note"]
        assert detail["contentStatus"] == "editorial-draft"
    assert detail["id"] == poem["id"]
catalog_bytes = (ROOT / "data/reader/catalog.json").stat().st_size
assert catalog_bytes < 600_000, catalog_bytes
print(f"Validated {len(catalog)} poems in {len(SECTION_ORDER)} ordered genres, {sum(p['featured'] for p in catalog)} featured; catalog {catalog_bytes:,} bytes; source identities, all active images, and full text are preserved.")

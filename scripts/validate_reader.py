#!/usr/bin/env python3
"""Validate deliverable references, complete text, and curated pronunciation alignment."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / "data/reader/catalog.json").read_text())["poems"]
source = {p["id"]: p for p in json.loads((ROOT / "data/final/tang_poems_final.json").read_text())["poems"]}
assert len(catalog) == len(source) == 317
assert len({p["id"] for p in catalog}) == 317
assert all(p["dedicatedArt"] for p in catalog), "Every poem must have its own illustration"
assert len({p["image"] for p in catalog}) == 317
assert len({p["thumbnail"] for p in catalog}) == 317
assert [p["order"] for p in catalog] == sorted(p["order"] for p in catalog)
for poem in catalog:
    for key in ("image", "thumbnail"):
        assert (ROOT / poem[key]).is_file(), (poem["id"], key)
    detail = json.loads((ROOT / "data/reader/poems" / f"{poem['id']}.json").read_text())
    actual = "".join(pair[0] for line in detail["rubyLines"] for pair in line)
    assert actual == "".join(source[poem["id"]]["lines"]), poem["id"]
    if poem["featured"]:
        assert poem["dedicatedArt"] and detail["note"]
        assert detail["contentStatus"] == "editorial-draft"
    assert detail["id"] == poem["id"]
catalog_bytes = (ROOT / "data/reader/catalog.json").stat().st_size
assert catalog_bytes < 600_000, catalog_bytes
print(f"Validated {len(catalog)} poems, {sum(p['featured'] for p in catalog)} featured; catalog {catalog_bytes:,} bytes; all active images exist and full text is preserved.")

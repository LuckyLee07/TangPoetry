#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "final" / "tang_poems_final.json"
OUT_DIR = ROOT / "data" / "final" / "poems"
INDEX_OUT = OUT_DIR / "index.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def poem_filename(poem: dict) -> str:
    return f"{poem['order']:03d}-{poem['id']}.json"


def build() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    poems = data.get("poems", [])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entries = []
    generated_at = now_iso()
    for poem in poems:
        filename = poem_filename(poem)
        relative_path = f"poems/{filename}"
        payload = {
            "schemaVersion": data.get("schemaVersion", "1.0.0"),
            "generatedAt": generated_at,
            "sourceFile": "data/final/tang_poems_final.json",
            "poem": poem,
        }
        write_json(OUT_DIR / filename, payload)
        entries.append(
            {
                "id": poem["id"],
                "order": poem["order"],
                "section": poem["section"],
                "title": poem["title"],
                "author": poem["author"],
                "path": relative_path,
            }
        )

    index_payload = {
        "schemaVersion": data.get("schemaVersion", "1.0.0"),
        "generatedAt": generated_at,
        "sourceFile": "data/final/tang_poems_final.json",
        "poemCount": len(entries),
        "poems": entries,
    }
    write_json(INDEX_OUT, index_payload)

    print(f"Wrote {len(entries)} poem files to {OUT_DIR.relative_to(ROOT)}")
    print(f"Wrote index to {INDEX_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()

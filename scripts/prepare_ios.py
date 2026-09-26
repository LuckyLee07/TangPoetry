#!/usr/bin/env python3
"""Package the same reader content for an entirely offline iPhone app."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Avoid reserved bundle-directory names such as Resources at an iOS app's root.
OUT = ROOT / "ios/Content"


def build():
    data = json.loads((ROOT / "data/reader/catalog.json").read_text())
    (OUT / "Art").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "data/reader/poems", OUT / "poems", dirs_exist_ok=True)
    converted = {}
    for poem in data["poems"]:
        for field in ("image", "thumbnail"):
            source = poem[field]
            name = Path(source).stem + ".jpg"
            target = OUT / "Art" / name
            if source not in converted:
                if not target.exists() or target.stat().st_mtime < (ROOT / source).stat().st_mtime:
                    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85", str(ROOT / source), "--out", str(target)], check=True, stdout=subprocess.DEVNULL)
                converted[source] = "Art/" + name
            poem[field] = converted[source]
    (OUT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"Prepared iOS: {len(data['poems'])} poems, {len(converted)} image variants.")


if __name__ == "__main__":
    build()

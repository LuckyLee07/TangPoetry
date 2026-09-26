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

    def convert(source):
        if source not in converted:
            target = OUT / "Art" / (Path(source).stem + ".jpg")
            if not target.exists() or target.stat().st_mtime < (ROOT / source).stat().st_mtime:
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85", str(ROOT / source), "--out", str(target)], check=True, stdout=subprocess.DEVNULL)
            converted[source] = "Art/" + target.name
        return converted[source]

    for poem in data["poems"]:
        for field in ("image", "thumbnail"):
            poem[field] = convert(poem[field])
    # The cover intentionally keeps its full-scene painting even when that poem's
    # reading-page illustration has been replaced by an image with more whitespace.
    convert("assets/optimized/song-yuan-er-page.webp")
    (OUT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"Prepared iOS: {len(data['poems'])} poems, {len(converted)} image resources including the cover.")


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""Validate packaged offline art membership and every shipped AppIcon dimension."""
import argparse
import json
import struct
from pathlib import Path
from prepare_ios import ROOT, OUT, validate_snapshot


def audit():
    stats = validate_snapshot(OUT)
    icon_root = ROOT / "ios/Assets.xcassets/AppIcon.appiconset"
    icons = json.loads((icon_root / "Contents.json").read_text())["images"]
    files = set()
    marketing = False
    for slot in icons:
        size = int(slot["size"].split("x")[0]) * int(slot["scale"].rstrip("x"))
        path = icon_root / slot["filename"]
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not PNG: {path.name}")
        width, height, depth, color = struct.unpack(">IIBB", data[16:26])
        if (width, height, depth, color) != (size, size, 8, 2):
            raise ValueError(f"Icon must be opaque RGB at its exact size: {path.name}")
        if slot["idiom"] == "ios-marketing" and size == 1024:
            marketing = True
        files.add(path.name)
    if not marketing:
        raise ValueError("Missing opaque 1024px marketing icon")
    return {"status": "passed", **stats, "unreferencedArt": 0,
            "appIcon": {"slots": len(icons), "files": len(files), "marketingPixels": 1024, "opaque": True}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))

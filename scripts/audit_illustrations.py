#!/usr/bin/env python3
"""Audit the individual artwork plan and its visual-review receipts."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(require_complete=False):
    plan = json.loads((ROOT / "data/illustrations/plan.json").read_text())["poems"]
    reviewed = {}
    for path in sorted((ROOT / "data/illustrations").glob("receipts-*.json")):
        data = json.loads(path.read_text())
        entries = data if isinstance(data, list) else data.get("completed", data.get("receipts", []))
        for entry in entries:
            if entry.get("status") in ("complete", "accepted"):
                reviewed[entry["id"]] = path.relative_to(ROOT).as_posix()
    assets, pending, hashes = [], [], set()
    for poem_id, item in plan.items():
        path = ROOT / item["image"]
        if not path.is_file():
            pending.append(poem_id)
            continue
        raw = path.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Not PNG: {path}"
        width, height = struct.unpack(">II", raw[16:24])
        assert height > width >= 640, f"Invalid portrait size: {path}"
        digest = hashlib.sha256(raw).hexdigest()
        assert digest not in hashes, f"Duplicate artwork: {path}"
        assert poem_id in reviewed, f"Missing visual review: {poem_id}"
        hashes.add(digest)
        assets.append({"id": poem_id, "image": item["image"], "width": width,
                       "height": height, "bytes": len(raw), "sha256": digest,
                       "receipt": reviewed[poem_id]})
    report = {"planned": len(plan), "complete": len(assets), "remaining": len(pending),
              "method": "built-in imagegen; one generation per poem",
              "assets": assets, "pending": pending}
    (ROOT / "data/illustrations/audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Illustrations: {len(assets)}/{len(plan)} inspected, distinct portraits; {len(pending)} remaining.")
    if require_complete:
        assert not pending, f"{len(pending)} illustrations remain"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    audit(parser.parse_args().require_complete)

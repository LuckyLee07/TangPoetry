#!/usr/bin/env python3
"""Build a complete offline iOS snapshot without publishing partially built content.

Image conversions use source/output hashes, not mtimes. An unchanged JPEG is
reused byte-for-byte. A new snapshot contains exactly the referenced resources,
so superseded artwork cannot remain in the app bundle indefinitely.
"""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ios/Content"
COVER = "assets/optimized/song-yuan-er-page.webp"
RECIPE = {"format": "jpeg", "quality": 85, "version": 1}
MANIFEST = "build-manifest.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert_jpeg(source, target):
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions",
                    str(RECIPE["quality"]), str(source), "--out", str(target)],
                   check=True, stdout=subprocess.DEVNULL)


def image_sources(catalog):
    return sorted({p[field] for p in catalog["poems"] for field in ("image", "thumbnail")} | {COVER})


def validate_snapshot(out):
    """Check manifest, catalog references and exact generated file membership."""
    catalog = json.loads((out / "catalog.json").read_text())
    manifest = json.loads((out / MANIFEST).read_text())
    images = {record["target"] for record in manifest["images"].values()}
    references = {p[field] for p in catalog["poems"] for field in ("image", "thumbnail")}
    references.add(manifest["cover"])
    if references != images:
        raise ValueError("Image manifest and catalog references disagree")
    poems = {f"poems/{p['id']}.json" for p in catalog["poems"]}
    expected = images | poems | {"catalog.json", MANIFEST}
    actual = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}
    if expected != actual:
        raise ValueError(f"Generated resource mismatch: missing={expected-actual}, stale={actual-expected}")
    for record in manifest["images"].values():
        target = out / record["target"]
        if digest(target) != record["outputSHA256"] or target.stat().st_size != record["bytes"]:
            raise ValueError(f"Image integrity failure: {target.name}")
    for path in poems:
        if json.loads((out / path).read_text())["id"] != Path(path).stem:
            raise ValueError(f"Poem identity mismatch: {path}")
    return {"poems": len(poems), "images": len(images),
            "imageBytes": sum((out / path).stat().st_size for path in images),
            "contentBytes": sum(p.stat().st_size for p in out.rglob("*") if p.is_file())}


def build(root=ROOT, out=None, converter=convert_jpeg):
    out = out or root / "ios/Content"
    out.parent.mkdir(parents=True, exist_ok=True)
    # The persistent lock file lives outside Content and is never bundled.
    with (out.parent / ".content-build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = out.parent / ".Content.previous"
        # Recover a process interrupted between the two final directory renames.
        if previous.exists() and not out.exists():
            os.replace(previous, out)
        elif previous.exists():
            shutil.rmtree(previous)
        old = {}
        if (out / MANIFEST).exists():
            old = json.loads((out / MANIFEST).read_text())
        catalog = json.loads((root / "data/reader/catalog.json").read_text())
        stage = Path(tempfile.mkdtemp(prefix=".Content-stage-", dir=out.parent))
        converted = 0
        reused = 0
        try:
            (stage / "Art").mkdir()
            (stage / "poems").mkdir()
            records = {}
            targets = set()
            for source in image_sources(catalog):
                target = "Art/" + Path(source).stem + ".jpg"
                if target in targets:
                    raise ValueError(f"Image basename collision: {target}")
                targets.add(target)
                source_hash = digest(root / source)
                prior = old.get("images", {}).get(source, {})
                existing = out / target
                if (old.get("recipe") == RECIPE and prior.get("sourceSHA256") == source_hash
                        and prior.get("target") == target and existing.exists()
                        and prior.get("outputSHA256") == digest(existing)):
                    # Reuse validated bytes; never mutate the old snapshot.
                    shutil.copy2(existing, stage / target)
                    reused += 1
                else:
                    converter(root / source, stage / target)
                    converted += 1
                if not (stage / target).is_file() or (stage / target).stat().st_size == 0:
                    raise ValueError(f"Converter produced no image: {source}")
                records[source] = {"target": target, "sourceSHA256": source_hash,
                                   "outputSHA256": digest(stage / target),
                                   "bytes": (stage / target).stat().st_size}
            for poem in catalog["poems"]:
                for field in ("image", "thumbnail"):
                    poem[field] = records[poem[field]]["target"]
                detail = root / "data/reader/poems" / f"{poem['id']}.json"
                shutil.copy2(detail, stage / "poems" / detail.name)
            (stage / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")))
            manifest = {"schemaVersion": 1, "recipe": RECIPE,
                        "cover": records[COVER]["target"], "images": records}
            (stage / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            stats = validate_snapshot(stage)
            # Nothing above this point changes the installed snapshot. Roll back a
            # failed final rename; an interrupted process is recovered next run.
            if out.exists():
                os.replace(out, previous)
            try:
                os.replace(stage, out)
            except BaseException:
                if previous.exists():
                    os.replace(previous, out)
                raise
            if previous.exists():
                shutil.rmtree(previous)
            return {**stats, "converted": converted, "reused": reused}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the packaged snapshot without rebuilding")
    args = parser.parse_args()
    print(json.dumps(validate_snapshot(OUT) if args.check else build(), ensure_ascii=False))

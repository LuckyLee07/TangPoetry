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
try:
    from scripts.narration_recipe import input_hash
except ModuleNotFoundError:
    from narration_recipe import input_hash

try:
    from scripts.volume2_narration_release import validate_volume2_release
except ModuleNotFoundError:
    from volume2_narration_release import validate_volume2_release

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ios/Content"
COVER = "assets/optimized/song-yuan-er-page.webp"
COVER_LAYERS = ("background.png", "willow-matte.png")
RECIPE = {"format": "jpeg", "quality": 85, "version": 1}
MANIFEST = "build-manifest.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert_jpeg(source, target):
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions",
                    str(RECIPE["quality"]), str(source), "--out", str(target)],
                   check=True, stdout=subprocess.DEVNULL)


def image_sources(catalog, cover=COVER):
    return sorted({p[field] for p in catalog["poems"] for field in ("image", "thumbnail")} | {cover})


def validate_audio_coverage(narration, catalog):
    catalog_ids = {p["id"] for p in catalog["poems"]}
    track_ids = set(narration["tracks"])
    expected = set(narration.get("previewIDs", [])) if narration.get("release") == "preview" else catalog_ids
    if not expected or track_ids != expected or not track_ids <= catalog_ids:
        raise ValueError("Complete the narration selection before packaging iOS content")


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
    layers = manifest.get("coverLayers", {})
    if layers and set(layers) != set(COVER_LAYERS):
        raise ValueError("Incomplete cover layers")
    for name, record in layers.items():
        target = out / record["target"]
        if (record["target"] != f"Cover/{name}" or digest(target) != record["sha256"]
                or target.stat().st_size != record["bytes"]):
            raise ValueError(f"Cover layer integrity failure: {name}")
        expected.add(record["target"])
    audio = manifest.get("audio", {})
    if audio:
        narration = json.loads((out / "Audio/manifest.json").read_text())
        validate_audio_coverage(narration, catalog)
        if set(audio) != set(narration["tracks"]):
            raise ValueError("Audio manifest identities disagree")
        expected |= {record["target"] for record in audio.values()} | {"Audio/manifest.json"}
        for identity, record in audio.items():
            track = narration["tracks"][identity]
            target = out / record["target"]
            if (track["file"] != record["target"] or track["id"] != identity
                    or digest(target) != record["sha256"] or target.stat().st_size != record["bytes"]):
                raise ValueError(f"Audio integrity failure: {identity}")
    if catalog.get("narrationAvailable") and len(audio) != len(poems):
        raise ValueError("Incomplete packaged narration cannot be marked available")
    volume_stats = []
    for identity, record in manifest.get("volumes", {}).items():
        if identity != "2" or record["path"] != "Volumes/2":
            raise ValueError("Unknown nested volume")
        nested = out / record["path"]
        if digest(nested / "catalog.json") != record["catalogSHA256"] or digest(nested / MANIFEST) != record["manifestSHA256"]:
            raise ValueError("Nested volume metadata changed")
        volume_stats.append(validate_snapshot(nested))
        expected |= {str(path.relative_to(out)) for path in nested.rglob("*") if path.is_file()}
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
    return {"poems": len(poems) + sum(stats["poems"] for stats in volume_stats),
            "primaryPoems": len(poems), "volumes": 1 + len(volume_stats),
            "images": len(images) + sum(stats["images"] for stats in volume_stats),
            "audioTracks": len(audio) + sum(stats["audioTracks"] for stats in volume_stats),
            "audioBytes": sum(record["bytes"] for record in audio.values()) + sum(stats["audioBytes"] for stats in volume_stats),
            "imageBytes": sum((out / path).stat().st_size for path in images) + sum(stats["imageBytes"] for stats in volume_stats),
            "contentBytes": sum(p.stat().st_size for p in out.rglob("*") if p.is_file())}


def build(root=ROOT, out=None, converter=convert_jpeg, volume=1, include_volume_2=False):
    if volume not in (1, 2) or (volume == 2 and include_volume_2):
        raise ValueError("Select one volume, or include volume 2 with the first volume")
    out = out or root / ("ios/Content" if volume == 1 else "ios/Volume2Content")
    if volume == 2 and out.resolve() == (root / "ios/Content").resolve():
        raise ValueError("Stage volume 2 separately to preserve the first volume")
    second_out = root / "ios/Volume2Content"
    if include_volume_2 and out.resolve() == second_out.resolve():
        raise ValueError("Choose a combined output separate from the second-volume stage")
    second_stats = build(root, second_out, converter, volume=2) if include_volume_2 else None
    reader_root = root / ("data/reader" if volume == 1 else "data/reader-volume-2")
    out.parent.mkdir(parents=True, exist_ok=True)
    # The persistent lock file lives outside Content and is never bundled.
    with (out.parent / (".content-build.lock" if out.name == "Content" else f".{out.name}-build.lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = out.parent / f".{out.name}.previous"
        # Recover a process interrupted between the two final directory renames.
        if previous.exists() and not out.exists():
            os.replace(previous, out)
        elif previous.exists():
            shutil.rmtree(previous)
        old = {}
        if (out / MANIFEST).exists():
            old = json.loads((out / MANIFEST).read_text())
        catalog = json.loads((reader_root / "catalog.json").read_text())
        second_release = None
        second_manifest_sha = None
        if volume == 2:
            second_details = {p["id"]: json.loads((reader_root / "poems" / f'{p["id"]}.json').read_text())
                              for p in catalog["poems"]}
            second_release = validate_volume2_release(root, catalog, second_details)
            if (type(catalog.get("narrationAvailable")) is not bool
                    or catalog["narrationAvailable"] != second_release["available"]):
                raise ValueError("Second-volume narration availability is stale; rebuild reader with "
                                 "python3 scripts/build_volume2_reader.py before packaging")
            if second_release["available"]:
                second_manifest_sha = digest(root / "data/audio-volume-2/manifest.json")
        cover_poem = next((p for p in catalog["poems"] if p["id"] == catalog.get("coverPoemID")), catalog["poems"][0])
        cover = COVER if volume == 1 else cover_poem["image"]
        stage = Path(tempfile.mkdtemp(prefix=".Content-stage-", dir=out.parent))
        converted = 0
        reused = 0
        try:
            (stage / "Art").mkdir()
            (stage / "poems").mkdir()
            records = {}
            targets = set()
            for source in image_sources(catalog, cover):
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
                detail = reader_root / "poems" / f"{poem['id']}.json"
                shutil.copy2(detail, stage / "poems" / detail.name)
            manifest = {"schemaVersion": 1, "recipe": RECIPE,
                        "cover": records[cover]["target"], "images": records, "volume": volume}
            # Preserve the matte's exact colors; JPEG edges would compromise keying.
            layer_sources = [root / "assets/cover-layers" / name for name in COVER_LAYERS]
            if volume == 1 and any(path.exists() for path in layer_sources):
                if not all(path.is_file() for path in layer_sources):
                    raise ValueError("Incomplete cover layers")
                (stage / "Cover").mkdir()
                manifest["coverLayers"] = {}
                for source in layer_sources:
                    target = f"Cover/{source.name}"
                    shutil.copy2(source, stage / target)
                    manifest["coverLayers"][source.name] = {"target": target,
                        "sha256": digest(source), "bytes": source.stat().st_size}
            audio_source = root / ("data/audio/manifest.json" if volume == 1 else "data/audio-volume-2/manifest.json")
            if catalog.get("narrationAvailable") and not audio_source.exists():
                raise ValueError("Complete the narration before marking it available")
            catalog["narrationAvailable"] = False
            package_audio = audio_source.exists() if volume == 1 else second_release["available"]
            if package_audio:
                if volume == 2:
                    validate_volume2_release(root, catalog, second_details)
                    audio_payload = audio_source.read_bytes()
                    if hashlib.sha256(audio_payload).hexdigest() != second_manifest_sha:
                        raise ValueError("Second-volume release changed during packaging; rebuild reader and retry")
                    narration = json.loads(audio_payload)
                else:
                    narration = json.loads(audio_source.read_text())
                validate_audio_coverage(narration, catalog)
                (stage / "Audio").mkdir()
                audio_records = {}
                for identity, track in narration["tracks"].items():
                    if "inputSHA256" in track:
                        detail = json.loads((reader_root / "poems" / f"{identity}.json").read_text())
                        if input_hash(detail, narration["recipe"]) != track["inputSHA256"]:
                            raise ValueError(f"Regenerate narration after poem or voice changes: {identity}")
                    source = root / track["file"]
                    if digest(source) != track["sha256"] or source.stat().st_size != track["bytes"]:
                        raise ValueError(f"Narration changed or incomplete: {identity}")
                    target = f"Audio/{identity}.mp3"
                    shutil.copy2(source, stage / target)
                    track["file"] = target
                    audio_records[identity] = {"target": target, "sha256": track["sha256"], "bytes": track["bytes"]}
                manifest["audio"] = audio_records
                catalog["narrationAvailable"] = set(narration["tracks"]) == {p["id"] for p in catalog["poems"]}
                (stage / "Audio/manifest.json").write_text(json.dumps(narration, ensure_ascii=False, separators=(",", ":")))
            (stage / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")))
            if include_volume_2:
                nested = stage / "Volumes/2"
                shutil.copytree(second_out, nested)
                manifest["volumes"] = {"2": {"path": "Volumes/2",
                    "catalogSHA256": digest(nested / "catalog.json"), "manifestSHA256": digest(nested / MANIFEST)}}
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
            return {**stats, "converted": converted + (second_stats["converted"] if second_stats else 0),
                    "reused": reused + (second_stats["reused"] if second_stats else 0)}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the packaged snapshot without rebuilding")
    parser.add_argument("--volume", type=int, choices=(1, 2), default=1, help="stage volume 2 separately; default remains the first volume")
    parser.add_argument("--include-volume-2", action="store_true", help="bundle the optional second volume alongside the first")
    parser.add_argument("--out", type=Path, help="write a review snapshot to a separate directory")
    args = parser.parse_args()
    out = args.out or ROOT / ("ios/Content" if args.volume == 1 else "ios/Volume2Content")
    print(json.dumps(validate_snapshot(out) if args.check else build(out=out, volume=args.volume, include_volume_2=args.include_volume_2), ensure_ascii=False))

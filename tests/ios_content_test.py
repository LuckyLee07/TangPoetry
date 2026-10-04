"""Release packaging invariants, using tiny fixtures instead of the real image set."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from scripts.narration_recipe import AZURE_RECIPE, poetry_ssml
from scripts.volume2_narration_release import RELEASE_DIR, LISTENING_REVIEW_FILE

SPEC = importlib.util.spec_from_file_location("prepare_ios", Path(__file__).resolve().parents[1] / "scripts/prepare_ios.py")
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


class IOSContentTests(unittest.TestCase):
    def audio_fixture(self, root):
        audio = root / "assets/audio/one.mp3"
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b"MP3 fixture")
        record = {"id": "one", "file": "assets/audio/one.mp3", "duration": 12,
                  "sha256": packaging.digest(audio), "bytes": audio.stat().st_size}
        manifest = root / "data/audio/manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"tracks": {"one": record}}))
        return audio, manifest

    def fixture(self, root):
        (root / "data/reader/poems").mkdir(parents=True)
        images = ["assets/one-page.webp", "assets/one-thumb.webp", packaging.COVER]
        for image in images:
            path = root / image
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image.encode())
        (root / "data/reader/catalog.json").write_text(json.dumps({"poems": [
            {"id": "one", "image": images[0], "thumbnail": images[1]}]}))
        (root / "data/reader/poems/one.json").write_text('{"id":"one"}')

    @staticmethod
    def converter(source, target):
        target.write_bytes(b"JPEG fixture:" + source.read_bytes())

    def second_fixture(self, root):
        reader = root / "data/reader-volume-2"
        (reader / "poems").mkdir(parents=True)
        images = ["assets/volume-2/two-page.webp", "assets/volume-2/two-thumb.webp"]
        for image in images:
            path = root / image
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image.encode())
        (reader / "catalog.json").write_text(json.dumps({"poems": [
            {"id": "two", "image": images[0], "thumbnail": images[1]}],
            "coverPoemID": "two", "narrationAvailable": False}))
        (reader / "poems/two.json").write_text('{"id":"two"}')

    def test_second_volume_stages_separately_without_first_artwork_or_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.audio_fixture(root)
            self.second_fixture(root)
            packaging.build(root, converter=self.converter)
            first = root / "ios/Content"
            before = {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()}
            result = packaging.build(root, converter=self.converter, volume=2)
            self.assertEqual(result["poems"], 1)
            self.assertEqual(result["images"], 2)
            self.assertEqual(result["audioTracks"], 0)
            self.assertEqual(before, {str(p.relative_to(first)): p.read_bytes() for p in first.rglob("*") if p.is_file()})
            second = root / "ios/Volume2Content"
            self.assertFalse(json.loads((second / "catalog.json").read_text())["narrationAvailable"])
            with self.assertRaisesRegex(ValueError, "preserve the first volume"):
                packaging.build(root, out=first, converter=self.converter, volume=2)

    def test_optional_combined_bundle_validates_both_and_keeps_primary_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.second_fixture(root)
            result = packaging.build(root, converter=self.converter, include_volume_2=True)
            self.assertEqual(result["poems"], 2)
            self.assertEqual(result["primaryPoems"], 1)
            self.assertEqual(result["volumes"], 2)
            out = root / "ios/Content"
            self.assertEqual(json.loads((out / "catalog.json").read_text())["poems"][0]["id"], "one")
            self.assertEqual(json.loads((out / "Volumes/2/catalog.json").read_text())["poems"][0]["id"], "two")
            self.assertEqual(packaging.validate_snapshot(out)["poems"], 2)
            (out / "Volumes/2/Art/two-page.jpg").write_bytes(b"damaged")
            with self.assertRaisesRegex(ValueError, "Image integrity"):
                packaging.validate_snapshot(out)

    def test_failed_second_volume_cannot_replace_existing_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.second_fixture(root)
            packaging.build(root, converter=self.converter, include_volume_2=True)
            out = root / "ios/Content"
            before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            (root / "assets/volume-2/two-page.webp").unlink()
            with self.assertRaises(FileNotFoundError):
                packaging.build(root, converter=self.converter, include_volume_2=True)
            self.assertEqual(before, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()})

    def test_second_volume_cannot_claim_audio_before_manifest_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.second_fixture(root)
            catalog_path = root / "data/reader-volume-2/catalog.json"
            catalog = json.loads(catalog_path.read_text())
            catalog["narrationAvailable"] = True
            catalog_path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, "build_volume2_reader.py before packaging"):
                packaging.build(root, converter=self.converter, volume=2)

    def test_cover_layers_keep_exact_bytes_and_reject_partial_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            layers = root / "assets/cover-layers"
            layers.mkdir()
            for name in packaging.COVER_LAYERS:
                (layers / name).write_bytes(b"PNG matte fixture:" + name.encode())
            packaging.build(root, converter=self.converter)
            out = root / "ios/Content"
            for name in packaging.COVER_LAYERS:
                self.assertEqual((out / "Cover" / name).read_bytes(), (layers / name).read_bytes())
            before = (out / packaging.MANIFEST).read_bytes()
            (layers / "willow-matte.png").unlink()
            with self.assertRaisesRegex(ValueError, "Incomplete cover layers"):
                packaging.build(root, converter=self.converter)
            self.assertEqual((out / packaging.MANIFEST).read_bytes(), before)
            (out / "Cover/background.png").write_bytes(b"broken")
            with self.assertRaisesRegex(ValueError, "Cover layer integrity"):
                packaging.validate_snapshot(out)

    def test_rebuild_is_incremental_reproducible_and_removes_stale_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            first = packaging.build(root, converter=self.converter)
            out = root / "ios/Content"
            snapshot = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            (out / "Art/obsolete.jpg").write_bytes(b"old art")
            (out / "poems/obsolete.json").write_text('{}')
            second = packaging.build(root, converter=self.converter)
            self.assertEqual(first["converted"], 3)
            self.assertEqual(second["converted"], 0)
            self.assertEqual(second["reused"], 3)
            self.assertEqual(snapshot, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()})

    def test_conversion_failure_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            packaging.build(root, converter=self.converter)
            out = root / "ios/Content"
            before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            (root / "assets/one-page.webp").write_bytes(b"new")
            def broken(source, target):
                target.write_bytes(b"partial")
                raise RuntimeError("conversion interrupted")
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                packaging.build(root, converter=broken)
            self.assertEqual(before, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()})
            self.assertFalse(list(out.parent.glob(".Content-stage-*")))

    def test_source_hash_change_rebuilds_even_when_mtime_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            packaging.build(root, converter=self.converter)
            source = root / "assets/one-page.webp"
            stat = source.stat()
            source.write_bytes(b"new pixels")
            import os
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            result = packaging.build(root, converter=self.converter)
            self.assertEqual(result["converted"], 1)
            self.assertEqual(result["reused"], 2)

    def test_audio_is_remapped_and_integrity_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.audio_fixture(root)
            result = packaging.build(root, converter=self.converter)
            self.assertEqual(result["audioTracks"], 1)
            out = root / "ios/Content"
            narration = json.loads((out / "Audio/manifest.json").read_text())
            self.assertEqual(narration["tracks"]["one"]["file"], "Audio/one.mp3")
            (out / "Audio/one.mp3").write_bytes(b"truncated")
            with self.assertRaisesRegex(ValueError, "Audio integrity"):
                packaging.validate_snapshot(out)

    def test_incomplete_audio_cannot_replace_a_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            audio, manifest = self.audio_fixture(root)
            packaging.build(root, converter=self.converter)
            out = root / "ios/Content"
            before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            manifest.write_text('{"tracks":{}}')
            with self.assertRaisesRegex(ValueError, "Complete the narration"):
                packaging.build(root, converter=self.converter)
            self.assertEqual(before, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()})


    def full_second_audio_fixture(self, root, available=True):
        self.second_fixture(root)
        reader = root / "data/reader-volume-2"
        initial = json.loads((reader / "catalog.json").read_text())
        poems, tracks, approvals = [], {}, {}
        for order in range(1, 306):
            identity = f"second-{order:03d}"
            detail = {"id": identity, "title": f"诗{order}", "author": "测试作者", "dynasty": "唐",
                      "section": "五言绝句", "rubyLines": [[["山", ""], ["。", ""]]]}
            (reader / "poems" / f"{identity}.json").write_text(json.dumps(detail))
            poems.append({"id": identity, "order": order, "section": "五言绝句",
                          "image": initial["poems"][0]["image"], "thumbnail": initial["poems"][0]["thumbnail"]})
            path = root / RELEASE_DIR / f"{identity}.mp3"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("non-audio-fixture:" + identity).encode())
            tracks[identity] = {"id": identity, "title": detail["title"], "author": detail["author"],
                "section": detail["section"], "file": str(path.relative_to(root)), "duration": 12,
                "bytes": path.stat().st_size, "sha256": packaging.digest(path),
                "inputSHA256": packaging.input_hash(detail, AZURE_RECIPE),
                "ssmlSHA256": hashlib.sha256(poetry_ssml(detail).encode()).hexdigest()}
            approvals[identity] = {"status": "approved-after-listening", "reviewedBy": "isolated-test-fixture",
                "reviewedAt": "2026-10-04T18:00:00+08:00", "inputSHA256": tracks[identity]["inputSHA256"],
                "audioSHA256": tracks[identity]["sha256"]}
        catalog = {"schemaVersion": 1, "volume": "volume-2", "poems": poems,
                   "coverPoemID": poems[0]["id"], "narrationAvailable": available}
        (reader / "catalog.json").write_text(json.dumps(catalog))
        production = root / "data/expansion/tang-second-volume/production.json"
        production.parent.mkdir(parents=True)
        production.write_text('{"fixture":true}')
        proof = root / LISTENING_REVIEW_FILE
        proof.parent.mkdir(parents=True)
        proof.write_text(json.dumps({"schemaVersion": 1, "volume": "volume-2", "recipe": AZURE_RECIPE, "tracks": approvals}))
        manifest = {"schemaVersion": 1, "volume": "volume-2", "release": "full", "recipe": AZURE_RECIPE,
            "tracks": tracks, "trackOrder": [p["id"] for p in poems], "productionSHA256": packaging.digest(production),
            "listeningReviewStatus": "complete", "listeningReviewFile": LISTENING_REVIEW_FILE,
            "listeningReviewSHA256": packaging.digest(proof)}
        path = root / "data/audio-volume-2/manifest.json"
        path.write_text(json.dumps(manifest))
        return path, proof

    def test_second_volume_complete_release_requires_rebuilt_availability_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.full_second_audio_fixture(root, available=False)
            with self.assertRaisesRegex(ValueError, "build_volume2_reader.py before packaging"):
                packaging.build(root, converter=self.converter, volume=2)
            catalog_path = root / "data/reader-volume-2/catalog.json"
            catalog = json.loads(catalog_path.read_text())
            catalog["narrationAvailable"] = True
            catalog_path.write_text(json.dumps(catalog))
            result = packaging.build(root, converter=self.converter, volume=2)
            self.assertEqual(result["audioTracks"], 305)
            self.assertTrue(json.loads((root / "ios/Volume2Content/catalog.json").read_text())["narrationAvailable"])

    def test_second_volume_missing_permanent_proof_is_rejected_before_conversion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, proof = self.full_second_audio_fixture(root)
            proof.unlink()
            def unexpected(*args):
                self.fail("Artwork conversion occurred before release validation")
            with self.assertRaisesRegex(ValueError, "release rejected"):
                packaging.build(root, converter=unexpected, volume=2)
            self.assertFalse((root / "ios/Volume2Content").exists())

    def test_second_volume_invalid_permanent_approval_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest_path, proof = self.full_second_audio_fixture(root)
            packaging.build(root, converter=self.converter, volume=2)
            out = root / "ios/Volume2Content"
            before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            review = json.loads(proof.read_text())
            review["tracks"]["second-001"]["status"] = "pending"
            proof.write_text(json.dumps(review))
            manifest = json.loads(manifest_path.read_text())
            manifest["listeningReviewSHA256"] = packaging.digest(proof)
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "listening approval.*invalid or stale"):
                packaging.build(root, converter=self.converter, volume=2)
            self.assertEqual(before, {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()})

    def test_second_volume_preview_is_rejected_but_first_preview_still_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            second_manifest, _ = self.full_second_audio_fixture(root)
            value = json.loads(second_manifest.read_text())
            value.update(release="preview", previewIDs=["second-001"])
            value["tracks"] = {"second-001": value["tracks"]["second-001"]}
            second_manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "full volume-2 release"):
                packaging.build(root, converter=self.converter, volume=2)
            self.fixture(root)
            _, first_manifest = self.audio_fixture(root)
            catalog_path = root / "data/reader/catalog.json"
            catalog = json.loads(catalog_path.read_text())
            catalog["poems"].append({**catalog["poems"][0], "id": "two"})
            catalog_path.write_text(json.dumps(catalog))
            (root / "data/reader/poems/two.json").write_text('{"id":"two"}')
            value = json.loads(first_manifest.read_text())
            value.update(release="preview", previewIDs=["one"])
            first_manifest.write_text(json.dumps(value))
            result = packaging.build(root, converter=self.converter)
            self.assertEqual(result["audioTracks"], 1)
            self.assertFalse(json.loads((root / "ios/Content/catalog.json").read_text())["narrationAvailable"])



if __name__ == "__main__":
    unittest.main()

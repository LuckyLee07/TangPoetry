"""Release packaging invariants, using tiny fixtures instead of the real image set."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("prepare_ios", Path(__file__).resolve().parents[1] / "scripts/prepare_ios.py")
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


class IOSContentTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

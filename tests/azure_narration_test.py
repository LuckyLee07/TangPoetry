import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_azure_audio as library
from narration_recipe import AZURE_RECIPE, NS, input_hash, poetry_ssml, poetry_ssml_chunks
from prepare_narration_trial import AzureHTTPError, AzureTransportError


class AzureNarrationTests(unittest.TestCase):
    def poem(self):
        return {"id": "tang-224-lu-chai", "title": "鹿柴", "author": "王维",
                "rubyLines": [[["山", "shān"], ["，", ""]], [["水", "shuǐ"], ["。", ""]], [["末", "mò"]]],
                "note": "不要朗读的注释"}

    def test_odd_final_line_and_punctuation_survive_without_reading_notes_or_pinyin(self):
        poem = self.poem()
        before = copy.deepcopy(poem)
        xml = ET.fromstring(poetry_ssml(poem))
        body = xml.find('.//m:express-as', NS)
        self.assertEqual(''.join(''.join(body.itertext()).split()), '山，水。末')
        self.assertEqual(len(body.findall('.//s:s', NS)), 2)
        text = ''.join(xml.itertext())
        self.assertIn('鹿寨', text)
        self.assertNotIn('不要朗读', text)
        self.assertNotIn('shān', text)
        self.assertEqual(poem, before)

    def test_all_catalog_poems_keep_full_body_including_longest_poem(self):
        poems = library.load_poems()
        self.assertEqual(len(poems), 320)
        for poem in poems:
            xml = ET.fromstring(poetry_ssml(poem))
            body = xml.find('.//m:express-as', NS)
            expected = ''.join(t[0] for line in poem['rubyLines'] for t in line)
            self.assertEqual(''.join(''.join(body.itertext()).split()), expected, poem['id'])

    def test_editing_poetry_invalidates_audio_but_commentary_does_not(self):
        poem = self.poem()
        original = input_hash(poem, AZURE_RECIPE)
        poem['note'] = '新注释'
        self.assertEqual(input_hash(poem, AZURE_RECIPE), original)
        poem['rubyLines'][-1][0][0] = '改'
        self.assertNotEqual(input_hash(poem, AZURE_RECIPE), original)

    def test_long_recovery_chunks_preserve_all_text_with_one_intro_and_original_pauses(self):
        poem = next(p for p in library.load_poems() if p['title'] == '兵车行')
        chunks = [ET.fromstring(s) for s in poetry_ssml_chunks(poem)]
        original = ET.fromstring(poetry_ssml(poem))
        self.assertGreater(len(chunks), 1)
        self.assertEqual(''.join(''.join(''.join(c.itertext()) for c in chunks).split()),
                         ''.join(''.join(original.itertext()).split()))
        self.assertEqual(sum(len(c.findall('s:voice/s:prosody', NS)) for c in chunks), 1)
        self.assertEqual(sum(len(c.findall('.//s:break', NS)) for c in chunks), len(original.findall('.//s:break', NS)))

    def test_pacer_counts_retries_and_does_not_burst_after_idle(self):
        clock = [100.0]
        pacer = library.RequestPacer(clock=lambda: clock[0], sleep=lambda duration: clock.__setitem__(0, clock[0] + duration))
        pacer.wait()
        pacer.wait()
        self.assertEqual(clock[0], 103.5)
        clock[0] = 200
        pacer.wait()
        pacer.wait()
        self.assertEqual(clock[0], 203.5)

    def test_transient_failure_retries_but_invalid_credentials_stop_immediately(self):
        pacer = library.RequestPacer(interval=0)
        with patch.object(library, 'synthesize_azure_ssml', side_effect=[AzureTransportError('interrupted'), 12]) as call, patch.object(library.time, 'sleep'):
            self.assertEqual(library.synthesize_with_retry('<speak/>', Path('one.mp3'), ('test', 'eastasia'), pacer), 12)
            self.assertEqual(call.call_count, 2)
        with patch.object(library, 'synthesize_azure_ssml', side_effect=AzureHTTPError(401, 'unauthorized')) as call:
            with self.assertRaises(AzureHTTPError):
                library.synthesize_with_retry('<speak/>', Path('one.mp3'), ('test', 'eastasia'), pacer)
            self.assertEqual(call.call_count, 1)

    def test_incomplete_stage_cannot_replace_live_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage = root / 'stage'
            stage.mkdir()
            (stage / 'manifest.json').write_text(json.dumps({'tracks': {}, 'recipe': AZURE_RECIPE, 'release': 'full'}))
            live = root / 'data/audio/manifest.json'
            live.parent.mkdir(parents=True)
            live.write_text('previous release')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                library.publish([self.poem()], stage, root)
            self.assertEqual(live.read_text(), 'previous release')
            self.assertFalse((root / library.RELEASE_DIR).exists())

    def test_manifest_switch_failure_keeps_old_release_and_can_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage = root / 'stage'
            (stage / 'audio').mkdir(parents=True)
            (stage / 'audio/one.mp3').write_bytes(b'validated audio fixture')
            (stage / 'manifest.json').write_text('{"tracks":{"one":{}}}')
            live = root / 'data/audio/manifest.json'
            live.parent.mkdir(parents=True)
            live.write_text('{"previous":true}')
            with patch.object(library, 'audit', return_value={'tracks': 1}), patch.object(library, 'atomic_json', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    library.publish([], stage, root)
            self.assertEqual(live.read_text(), '{"previous":true}')
            with patch.object(library, 'audit', return_value={'tracks': 1}):
                library.publish([], stage, root)
            self.assertIn('one', json.loads(live.read_text())['tracks'])


if __name__ == '__main__':
    unittest.main()

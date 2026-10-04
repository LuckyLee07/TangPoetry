"""Volume-2 production and reader regressions; no real outputs or artwork writes."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_volume2_production as production_builder
import build_volume2_reader as reader_builder


class Volume2ReaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / 'data/expansion/tang-second-volume'
        cls.source = production_builder.read(base / 'poems.json')
        cls.corrections = production_builder.read(base / 'text-corrections.json')
        cls.metadata = production_builder.read(base / 'display-metadata.json')
        cls.glyphs = production_builder.read(base / 'display-glyphs.json')
        cls.commentary = {
            path.name: production_builder.read(path)
            for path in sorted((base / 'commentary').glob('*.json'))
        }

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def fixture(self, root):
        base = root / 'data/expansion/tang-second-volume'
        for name, value in (
            ('poems.json', self.source),
            ('text-corrections.json', self.corrections),
            ('display-metadata.json', self.metadata),
            ('display-glyphs.json', self.glyphs),
        ):
            self.write_json(base / name, value)
        for name, value in self.commentary.items():
            self.write_json(base / 'commentary' / name, value)
        # Receipts intentionally absent: this exercises content assembly without artwork I/O.
        return base

    def assemble_fixture(self, root, base, save=True, check_existing=False):
        with mock.patch.object(production_builder, 'ROOT', root), \
                mock.patch.object(production_builder, 'BASE', base):
            return production_builder.assemble(save=save, check_existing=check_existing)

    def reader_fixture(self, root, base):
        self.assemble_fixture(root, base)
        production = production_builder.read(base / 'production.json')
        assets = {'poems': {
            poem['id']: {
                'page': {'file': f"fixture-art/{poem['id']}-page.webp"},
                'thumbnail': {'file': f"fixture-art/{poem['id']}-thumb.webp"},
            }
            for poem in production['poems']
        }}
        return production, copy.deepcopy(self.source), assets

    def adapt(self, base, production, source, assets):
        with mock.patch.object(reader_builder, 'ROOT', base.parents[2]), \
                mock.patch.object(reader_builder, 'BASE', base), \
                mock.patch.object(reader_builder, 'prepare_assets') as prepare_assets:
            result = reader_builder.reader_entries(production, source, assets)
            prepare_assets.assert_not_called()
            return result

    def test_all_305_ids_survive_assembly_and_reader_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            production, source, assets = self.reader_fixture(root, base)
            inputs = copy.deepcopy((production, source, assets))
            catalog, details = self.adapt(base, production, source, assets)

            original = {poem['id']: poem['order'] for poem in self.source['poems']}
            self.assertEqual(len(original), 305)
            self.assertEqual({poem['id']: poem['order'] for poem in production['poems']}, original)
            self.assertEqual({poem['id']: poem['order'] for poem in catalog['poems']}, original)
            self.assertEqual(set(details), set(original))
            self.assertEqual(len(catalog['poems']), 305)
            self.assertEqual(catalog['coverPoemID'], self.source['poems'][0]['id'])
            self.assertEqual(sum(poem['featured'] for poem in catalog['poems']), 20)
            self.assertFalse(catalog['narrationAvailable'])
            self.assertEqual((production, source, assets), inputs)

    def test_exactly_11_evidenced_corrections_are_separate_from_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            archived_bytes = (base / 'poems.json').read_bytes()
            audit = self.assemble_fixture(root, base)
            production = production_builder.read(base / 'production.json')
            original = {poem['id']: poem for poem in self.source['poems']}
            fixes = {fix['id']: fix for fix in self.corrections['corrections']}
            self.assertEqual(len(fixes), 11)
            self.assertEqual({fix['order'] for fix in fixes.values()},
                             {2, 30, 89, 108, 114, 126, 194, 208, 226, 235, 280})
            self.assertEqual(audit['textCorrectionCount'], 11)
            changed = {poem['id'] for poem in production['poems']
                       if poem['text'] != original[poem['id']]['text']}
            self.assertEqual(changed, set(fixes))
            for poem in production['poems']:
                with self.subTest(order=poem['order']):
                    if poem['id'] in fixes:
                        fix = fixes[poem['id']]
                        self.assertEqual(poem['sourceText'], original[poem['id']]['text'])
                        self.assertEqual(poem['sourceText'], fix['sourceText'])
                        self.assertEqual(poem['text'], fix['proposedText'])
                        self.assertEqual(poem['paragraphs'], poem['text'].splitlines())
                        self.assertEqual(''.join(poem['sentences']), poem['text'].replace('\n', ''))
                        self.assertTrue(poem['textCorrection']['verificationRefs'])
                    else:
                        self.assertEqual(poem['text'], original[poem['id']]['text'])
                        self.assertNotIn('textCorrection', poem)
                        self.assertNotIn('sourceText', poem)
            self.assertEqual((base / 'poems.json').read_bytes(), archived_bytes)

    def test_real_rare_glyphs_display_without_changing_archival_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            production, source, assets = self.reader_fixture(root, base)
            catalog, details = self.adapt(base, production, source, assets)
            by_order = {poem['order']: poem for poem in production['poems']}
            catalog_by_id = {poem['id']: poem for poem in catalog['poems']}

            poem = by_order[28]
            detail = details[poem['id']]
            ruby = ''.join(character for line in detail['rubyLines'] for character, _ in line)
            self.assertIn('贫寠有苍卒', ruby)
            self.assertIn('贫寠有苍卒', detail['readingText'])
            self.assertIn('贫𪧘有苍卒', detail['text'])
            self.assertEqual(detail['sourceText'], poem['text'])
            self.assertEqual(detail['displayGlyphs']['𪧘'], '寠')

            poem = by_order[183]
            detail = details[poem['id']]
            self.assertIn('郑礒', detail['title'])
            self.assertIn('郑𥐟', detail['sourceTitle'])
            self.assertEqual(detail['sourceTitle'], poem['title'])
            self.assertEqual(detail['displaySourceTitle'], poem['title'].replace('𥐟', '礒'))
            self.assertEqual(detail['text'], poem['text'])
            self.assertEqual(detail['sourceText'], poem['text'])
            self.assertIn(poem['title'], catalog_by_id[poem['id']]['aliases'])
            self.assertIn('郑𥐟', catalog_by_id[poem['id']]['searchText'])
            self.assertEqual(detail['displayGlyphs']['𥐟'], '礒')

    def test_each_glyph_maps_in_title_and_ruby_but_preserves_source_and_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            production, source, assets = self.reader_fixture(root, base)
            for character, display in [('𪧘', '寠'), ('𥐟', '礒')]:
                with self.subTest(character=character):
                    fixture = copy.deepcopy(production)
                    poem = fixture['poems'][0]
                    poem.update(title=character + '原题', displayTitle=character + '显示题',
                                sourceTitle=character + '旧题', aliases=[character + '别名'],
                                text=character + '，𫶇。', sourceText=character + '归档正文',
                                sentences=[character + '，', '𫶇。'])
                    before = copy.deepcopy(poem)
                    catalog, details = self.adapt(base, fixture, source, assets)
                    entry = next(entry for entry in catalog['poems'] if entry['id'] == poem['id'])
                    detail = details[poem['id']]
                    self.assertEqual(detail['title'], display + '显示题')
                    self.assertEqual(detail['rubyLines'],
                                     [[[display, ''], ['，', '']], [['𫶇', ''], ['。', '']]])
                    self.assertEqual(detail['readingText'], display + '，𫶇。')
                    self.assertEqual(detail['text'], before['text'])
                    self.assertEqual(detail['sourceText'], before['sourceText'])
                    self.assertEqual(detail['sourceTitle'], before['title'])
                    self.assertEqual(detail['displaySourceTitle'], display + '原题')
                    self.assertEqual(detail['originalEditionTitle'], before['sourceTitle'])
                    self.assertTrue(set([before['title'], before['sourceTitle'], *before['aliases']])
                                    <= set(entry['aliases']))
                    self.assertEqual(poem, before)

    def test_reader_rejects_missing_or_replaced_archival_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            production, source, assets = self.reader_fixture(root, base)
            for invalid in ('missing', 'replaced'):
                with self.subTest(invalid=invalid):
                    archival = copy.deepcopy(source)
                    if invalid == 'missing':
                        archival['poems'].pop()
                    else:
                        archival['poems'][-1]['id'] = 'unknown-archive-id'
                    with self.assertRaisesRegex(AssertionError, 'Archival and production IDs differ'):
                        self.adapt(base, production, archival, assets)

    def test_reader_rejects_unknown_metadata_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            production, source, assets = self.reader_fixture(root, base)
            production['poems'][0]['catalogSection'] = '未知门类'
            with self.assertRaisesRegex(AssertionError, 'Unclassified'):
                self.adapt(base, production, source, assets)

    def test_production_rejects_correction_source_mismatch_without_saving(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            corrections = copy.deepcopy(self.corrections)
            fix = corrections['corrections'][0]
            fix['sourceText'] += '不属于归档正文'
            self.write_json(base / 'text-corrections.json', corrections)
            with mock.patch.object(production_builder, 'write') as write:
                with self.assertRaisesRegex(AssertionError, fix['id']):
                    self.assemble_fixture(root, base, save=False)
                write.assert_not_called()
            self.assertFalse((base / 'production.json').exists())

    def test_production_check_cli_accepts_current_outputs_and_rejects_each_stale_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            self.assemble_fixture(root, base)
            script = root / 'scripts/build_volume2_production.py'
            script.parent.mkdir()
            script.write_bytes((ROOT / 'scripts/build_volume2_production.py').read_bytes())
            args = [sys.executable, str(script), '--check']
            result = subprocess.run(args, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['textCorrectionCount'], 11)
            names = ('production.json', 'production-audit.json', 'editorial-notes.json')
            current = {name: (base / name).read_bytes() for name in names}
            for name, message in (
                ('production.json', 'Production output stale'),
                ('production-audit.json', 'Production audit stale'),
                ('editorial-notes.json', 'Editorial notes output stale'),
            ):
                with self.subTest(output=name):
                    for output, content in current.items():
                        (base / output).write_bytes(content)
                    value = production_builder.read(base / name)
                    if name == 'production.json':
                        value['poems'][0]['text'] += '过期正文'
                    elif name == 'production-audit.json':
                        value['poemCount'] -= 1
                    else:
                        value['notes'][0]['notes'].append('过期笔记')
                    self.write_json(base / name, value)
                    before = {path.relative_to(base): path.read_bytes()
                              for path in base.rglob('*') if path.is_file()}
                    result = subprocess.run(args, cwd=root, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
                    after = {path.relative_to(base): path.read_bytes()
                             for path in base.rglob('*') if path.is_file()}
                    self.assertEqual(after, before, '--check must reject stale output without rewriting it')


if __name__ == '__main__':
    unittest.main()

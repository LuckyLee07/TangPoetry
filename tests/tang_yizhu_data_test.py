"""Integrity checks for the research dataset; no network or app mutations."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_tang_yizhu as builder

DATA = ROOT / 'data/expansion/tang-yizhu'


def read(name):
    return json.loads((DATA / name).read_text())


class TextProcessingTests(unittest.TestCase):
    def test_supplied_character_is_kept_and_footnote_separated(self):
        lines, notes = builder.separate_annotations(['[欸]乃一聲山水綠。[二]'])
        self.assertEqual(lines, ['欸乃一聲山水綠。'])
        self.assertEqual([n['kind'] for n in notes], ['supplied-reading', 'footnote-marker'])

    def test_multiline_nested_note_does_not_leak_into_verse(self):
        lines, notes = builder.separate_annotations(['山水綠。（校記：', '（一作碧）見某集。', '）岩上無心雲相逐。'])
        self.assertEqual(lines, ['山水綠。', '岩上無心雲相逐。'])
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['endParagraphIndex'], 2)

    def test_unclosed_annotation_is_reported(self):
        _, notes = builder.separate_annotations(['明月。（缺末尾'])
        self.assertEqual(notes[0]['kind'], 'unclosed-parenthetical-note')

    def test_parenthetical_cycle_number_is_retained(self):
        _, group, position, _ = builder.title_parts('獨坐敬亭山（其二）')
        self.assertEqual((group, position), ('独坐敬亭山', 2))


class DatasetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = read('poems.json')
        cls.poems = cls.dataset['poems']
        cls.by_id = {p['id']: p for p in cls.poems}
        cls.source = read('sources/selected-qts.json')['records']
        cls.raw = {p['raw']['id']: p['raw'] for p in cls.source}
        cls.existing_path = ROOT / 'data/final/tang_poems_final.json'
        cls.existing = json.loads(cls.existing_path.read_text())['poems']
        cls.existing_ids = {p['id'] for p in cls.existing}

    def test_counts_ids_and_text_hashes(self):
        self.assertEqual(len(self.by_id), len(self.poems))
        self.assertEqual([p['order'] for p in self.poems], list(range(1, len(self.poems)+1)))
        self.assertEqual(self.dataset['stats']['recordCount'], len(self.poems))
        for p in self.poems:
            with self.subTest(poem=p['id']):
                self.assertTrue(p['title'] and p['author'] and p['paragraphs'])
                self.assertEqual(p['text'], '\n'.join(p['paragraphs']))
                self.assertEqual(p['textSha256'], hashlib.sha256(p['text'].encode()).hexdigest())
                self.assertTrue(all(builder.key(line) for line in p['paragraphs']))
                counts = [len(builder.HAN.findall(s)) for s in p['sentences']]
                self.assertEqual(counts, p['form']['characterCounts'])
                self.assertEqual(sum(counts), p['form']['characterCount'])
                self.assertEqual(len(counts), p['form']['sentenceCount'])

    def test_every_base_record_is_preserved_once(self):
        ids = [i for p in self.poems for i in p['sourceRecordIds']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(self.raw))
        for p in self.poems:
            if not p['sourceRecordIds']:
                continue
            raw = self.raw[p['sourceRecordIds'][0]]
            lines, notes = builder.separate_annotations(raw['paragraphs'])
            self.assertEqual(p['paragraphs'], [builder.simplified(line) for line in lines])
            self.assertEqual(p['paragraphsTraditional'], lines)
            self.assertEqual(p['sourceAnnotations'], notes)
            self.assertEqual(p['sourceTitle'], raw['title'])
            witnessed_ids = {r.get('recordId') for r in p['sourceRefs']}
            witnessed_ids.update(w['sourceRef'].get('recordId') for w in p['witnesses'])
            self.assertTrue(set(p['sourceRecordIds']).issubset(witnessed_ids))

    def test_sources_and_honest_book_scope(self):
        self.assertFalse(self.dataset['bookCatalogComplete'])
        self.assertFalse(self.dataset['publicationReady'])
        chapters = set()
        for p in self.poems:
            self.assertTrue(p['sourceRefs'])
            for ref in p['sourceRefs'] + [w['sourceRef'] for w in p['witnesses']]:
                self.assertTrue(ref['url'].startswith('https://'))
                self.assertEqual(ref['accessedOn'], '2026-09-28')
            if p['selection']['bookMembership'] == 'confirmed':
                chapters.add(p['selection']['bookChapterId'])
                self.assertTrue(any(w['sourceRef']['sourceId'] == 'tangshi-xieying-public-preview' for w in p['witnesses']))
        self.assertEqual(chapters, {7, 25, 49, 50})
        self.assertEqual(self.dataset['stats']['bookConfirmedCount'], 4)

    def test_app_deduplication_and_status_partition(self):
        self.assertEqual(self.dataset['existingLibrary']['sha256'], hashlib.sha256(self.existing_path.read_bytes()).hexdigest())
        eligible = read('new-candidates.json')['poemIds']
        self.assertEqual(set(eligible), {p['id'] for p in self.poems if p['collectionStatus'] == 'new-candidate'})
        status = Counter(p['collectionStatus'] for p in self.poems)
        self.assertEqual(sum(status.values()), len(self.poems))
        for key, label in [('newCandidateCount', 'new-candidate'), ('alreadyInAppCount', 'already-in-app'), ('reviewBeforeInclusionCount', 'review-before-inclusion')]:
            self.assertEqual(self.dataset['stats'][key], status[label])
        for p in self.poems:
            matches = p['existingLibraryMatches']
            self.assertEqual(bool(matches), p['collectionStatus'] == 'already-in-app')
            self.assertTrue(all(m['id'] in self.existing_ids for m in matches))
            if any(not m['authorAgrees'] for m in matches):
                self.assertIn('existing-library-author-differs', p['review']['issues'])

    def test_author_and_group_indexes_have_no_orphans(self):
        authors = read('authors.json')['authors']
        self.assertEqual(len(authors), self.dataset['stats']['authorCount'])
        ids = [i for a in authors for i in a['poemIds']]
        self.assertEqual(set(ids), set(self.by_id))
        self.assertEqual(len(ids), len(self.by_id))
        for a in authors:
            self.assertEqual(a['poemCount'], len(a['poemIds']))
            self.assertTrue(all(self.by_id[i]['author'] == a['name'] for i in a['poemIds']))
        groups = read('groups.json')['groups']
        self.assertEqual(len(groups), self.dataset['stats']['groupCount'])
        grouped = []
        for group in groups:
            items = [self.by_id[i] for i in group['poemIds']]
            self.assertEqual(group['collectedPositions'], [p['group']['position'] for p in items])
            self.assertTrue(all(p['author'] == group['author'] and p['group']['title'] == group['title'] for p in items))
            grouped.extend(group['poemIds'])
        self.assertEqual(set(grouped), {p['id'] for p in self.poems if p['group']})

    def test_request_resolution_is_traceable(self):
        requests = read('selection-report.json')['requests']
        pending = [r for r in requests if r['finalStatus'] == 'unresolved']
        self.assertEqual({r['request'] for r in pending}, {'王维|画', '元稹|自遣'})
        for r in requests:
            self.assertEqual(bool(r['resolvedPoemIds']), r['finalStatus'] == 'resolved')
            self.assertTrue(set(r['resolvedPoemIds']).issubset(self.by_id))
            self.assertTrue(all(r['request'] in self.by_id[i]['selection']['requests'] for i in r['resolvedPoemIds']))

    def test_content_regressions(self):
        qin = next(p for p in self.poems if p['author'] == '韦庄' and p['title'] == '秦妇吟')
        self.assertEqual((qin['form']['sentenceCount'], qin['form']['characterCount']), (238, 1666))
        self.assertNotIn('刘修业', qin['text'])
        fisher = next(p for p in self.poems if p['author'] == '柳宗元' and p['title'] == '渔翁')
        self.assertIn('欸乃一声山水绿', fisher['text'])
        eagle = next(p for p in self.poems if p['author'] == '杜甫' and p['title'] == '画鹰')
        self.assertEqual(eagle['collectionStatus'], 'review-before-inclusion')
        self.assertIn('source-editorial-markers', eagle['review']['issues'])
        for p in self.poems:
            for w in p['witnesses']:
                if w.get('numberingStatus') == 'differs-from-base-cycle':
                    self.assertNotIn(w['title'], p['aliases'])


if __name__ == '__main__':
    unittest.main()

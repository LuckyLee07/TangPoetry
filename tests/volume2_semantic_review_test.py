import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_volume2_semantic_review as checker
import build_volume2_semantic_report as report_builder


class SemanticReviewTest(unittest.TestCase):
    def setUp(self):
        self.audit = checker.read(checker.BASE / 'semantic-review-audit.json')
        self.baseline = checker.read_at_commit(self.audit['reviewedCommit'], 'data/expansion/tang-second-volume/production.json')
        self.completed = checker.read_at_commit(self.audit['semanticReviewResultCommit'], 'data/expansion/tang-second-volume/production.json')
        self.archival = (checker.BASE / 'poems.json').read_bytes()
        self.batches = {relative: checker.read(checker.ROOT / relative)
                        for relative in self.audit['reviewFiles']}

    def fixture(self, root, live=None):
        base = root / 'data/expansion/tang-second-volume'
        base.mkdir(parents=True)
        (base / 'semantic-review-audit.json').write_text(json.dumps(self.audit, ensure_ascii=False))
        (base / 'production.json').write_text(json.dumps(live or self.completed, ensure_ascii=False))
        (base / 'poems.json').write_bytes(self.archival)
        for relative, batch in self.batches.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(batch, ensure_ascii=False))
        return base

    def git_show(self, args, cwd):
        ref = args[2]
        if ref == self.audit['reviewedCommit'] + ':data/expansion/tang-second-volume/production.json':
            return json.dumps(self.baseline, ensure_ascii=False).encode()
        if ref == self.audit['semanticReviewResultCommit'] + ':data/expansion/tang-second-volume/production.json':
            return json.dumps(self.completed, ensure_ascii=False).encode()
        if ref == self.audit['reviewedCommit'] + ':data/expansion/tang-second-volume/poems.json':
            return self.archival
        raise AssertionError('Unexpected Git lookup: ' + ref)

    def run_check(self, root, base, current=False):
        with mock.patch.object(checker, 'ROOT', root), mock.patch.object(checker, 'BASE', base), \
                mock.patch.object(checker.subprocess, 'check_output', side_effect=self.git_show):
            return checker.check(current=current)

    def test_check_rejects_non_list_and_invalid_alignment_notes(self):
        # A nonempty string passed the old all(str) check and became one bullet per character.
        for invalid in ['a whole sentence', [], [''], ['  '], [4], {'note': 'sentence'}]:
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                base = self.fixture(root)
                relative = self.audit['reviewFiles'][0]
                batch = copy.deepcopy(self.batches[relative])
                batch['reviews'][0]['alignmentNotes'] = invalid
                (root / relative).write_text(json.dumps(batch, ensure_ascii=False))
                with self.assertRaisesRegex(AssertionError, 'alignmentNotes|Invalid alignment note'):
                    self.run_check(root, base)
                with self.assertRaisesRegex(AssertionError, 'alignmentNotes|Invalid alignment note'):
                    report_builder.render_poem(batch['reviews'][0], self.audit['resolutions'][0])

    def test_later_text_metadata_and_editorial_notes_do_not_rewrite_history(self):
        live = copy.deepcopy(self.completed)
        poem = live['poems'][0]
        poem['text'] += '（后续校订示例）'
        poem['displayTitle'] = '新展示题名'
        poem['form']['proposedGenre'] = '后续体裁校订'
        poem['commentary']['reviewNotes'].append('后续正文校订说明')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root, live)
            result = self.run_check(root, base, current=True)
            self.assertTrue(result['allRevisionsMatchReviewedResult'])
            self.assertTrue(result['currentArchivalUnchanged'])
            self.assertTrue(result['liveComparison']['evolvedSinceReview'])
            self.assertEqual(result['liveComparison']['textChangedPoemCount'], 1)
            self.assertEqual(result['liveComparison']['metadataChangedPoemCount'], 1)
            self.assertEqual(result['liveComparison']['readerFieldsChangedPoemCount'], 0)
            self.assertEqual((result['revisedReaderPoemCount'], result['notesOnlyPoemCount']), (29, 1))

    def test_current_option_detects_reader_changes_without_invalidating_history(self):
        live = copy.deepcopy(self.completed)
        live['poems'][0]['commentary']['summary'] += '（尚未纳入本轮复核）'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root, live)
            result = self.run_check(root, base)
            self.assertEqual(result['liveComparison']['readerFieldsChangedPoemCount'], 1)
            with self.assertRaisesRegex(AssertionError, 'Current reader fields differ'):
                self.run_check(root, base, current=True)

    def test_tampered_completed_result_is_rejected(self):
        self.completed['poems'][0]['commentary']['summary'] += '（被改写的历史结果）'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self.fixture(root)
            with self.assertRaisesRegex(AssertionError, 'Completed review result mismatch'):
                self.run_check(root, base)

    def test_report_is_deterministic_and_keeps_decisions_and_sources(self):
        records = [record for batch in self.batches.values() for record in batch['reviews']]
        rendered = report_builder.render_report(self.audit, records)
        self.assertEqual(rendered, report_builder.render_report(self.audit, list(reversed(records))))
        self.assertEqual(rendered, (checker.BASE / 'SEMANTIC_REVIEW.md').read_text())
        self.assertEqual(len(re.findall(r'^### \d{3} ', rendered, flags=re.M)), 305)
        first = records[0]
        self.assertIn('- ' + first['alignmentNotes'][0] + '\n', rendered)
        self.assertNotIn('- 四\n- 段\n', rendered)
        for record in records:
            for ref in record['verificationRefs']:
                self.assertIn('](' + ref + ')', rendered)
        for resolution in self.audit['resolutions']:
            for decision in resolution['issueDecisions']:
                self.assertIn('- 根代理采用结论：' + decision['reason'] + '\n', rendered)
        self.assertEqual(self.audit['stats']['baselineAssessmentCounts'], {
            'consistent': 275, 'revise': 22, 'interpretive-uncertainty': 8})


if __name__ == '__main__':
    unittest.main()

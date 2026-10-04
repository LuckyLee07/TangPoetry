#!/usr/bin/env python3
"""Check review coverage and revision provenance, not literary correctness."""
import argparse
from collections import Counter
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/expansion/tang-second-volume'
READER_FIELDS = ('summary', 'interpretation', 'glossary')


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_alignment_notes(record):
    notes = record['alignmentNotes']
    pid = record['id']
    assert isinstance(notes, list) and notes, f'alignmentNotes must be a nonempty list: {pid}'
    assert all(isinstance(n, str) and n.strip() for n in notes), f'Invalid alignment note: {pid}'


def read_at_commit(commit, relative):
    return json.loads(subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=ROOT))


def compare_live_review(completed, live):
    text_changed = []
    metadata_changed = []
    commentary_changed = []
    reader_fields_changed = []
    text_fields = {'text', 'paragraphs', 'sentences', 'commentary'}
    for pid, previous in completed.items():
        current = live[pid]
        if previous['text'] != current['text']:
            text_changed.append(pid)
        if any(previous.get(k) != current.get(k) for k in (set(previous) | set(current)) - text_fields):
            metadata_changed.append(pid)
        if previous['commentary'] != current['commentary']:
            commentary_changed.append(pid)
        if any(previous['commentary'][k] != current['commentary'][k] for k in READER_FIELDS):
            reader_fields_changed.append(pid)
    return {
        'evolvedSinceReview': any(completed[pid] != live[pid] for pid in completed),
        'textChangedPoemCount': len(text_changed),
        'metadataChangedPoemCount': len(metadata_changed),
        'commentaryChangedPoemCount': len(commentary_changed),
        'readerFieldsChangedPoemCount': len(reader_fields_changed),
        'readerFieldsChangedPoemIds': reader_fields_changed,
    }


def check(current=False):
    audit = read(BASE / 'semantic-review-audit.json')
    baseline = read_at_commit(audit['reviewedCommit'], 'data/expansion/tang-second-volume/production.json')
    assert len(baseline['poems']) == 305
    before = {p['id']: p for p in baseline['poems']}
    production = read(BASE / 'production.json')
    assert len(production['poems']) == 305
    live = {p['id']: p for p in production['poems']}
    # This audit records the completed review. Later editorial work must not rewrite its conclusions.
    completed = read_at_commit(audit['semanticReviewResultCommit'], 'data/expansion/tang-second-volume/production.json')
    after = {p['id']: p for p in completed['poems']}
    assert len(before) == len(after) == len(live) == 305 and set(before) == set(after) == set(live)
    assert audit['publicationReady'] is False and completed['publicationReady'] is False and production['publicationReady'] is False
    for pid, poem in live.items():
        assert (poem['order'], poem['author'], poem['image']) == (after[pid]['order'], after[pid]['author'], after[pid]['image']), f'Unexpected identity or image change: {pid}'
    archival_raw = subprocess.check_output(
        ['git', 'show', audit['reviewedCommit'] + ':data/expansion/tang-second-volume/poems.json'],
        cwd=ROOT,
    )
    assert hashlib.sha256((BASE / 'poems.json').read_bytes()).hexdigest() == audit['archivalPoemsSha256']
    assert audit['archivalPoemsSha256'] == hashlib.sha256(archival_raw).hexdigest()

    records = {}
    for relative in audit['reviewFiles']:
        batch = read(ROOT / relative)
        assert batch['reviewedCommit'] == audit['reviewedCommit']
        for r in batch['reviews']:
            pid = r['id']
            assert pid not in records, f'Duplicate review: {pid}'
            b = before[pid]
            assert (r['order'], r['title'], r['author']) == (b['order'], b['title'], b['author'])
            assert isinstance(r['poemMeaning'], str) and r['poemMeaning'].strip()
            validate_alignment_notes(r)
            assert r['assessment'] in ('consistent', 'revise', 'interpretive-uncertainty')
            assert r['reviewedTextSha256'] == hashlib.sha256(b['text'].encode('utf-8')).hexdigest()
            assert r['reviewedCommentarySha256'] == digest(b['commentary'])
            records[pid] = r
    assert set(records) == set(before), 'Full 305-poem review coverage required'
    resolutions = {r['id']: r for r in audit['resolutions']}
    assert len(audit['resolutions']) == 305 and set(resolutions) == set(before)
    revised = clarified = 0
    for pid, r in resolutions.items():
        b, a = before[pid], after[pid]
        assert a['text'] == b['text'], f'Text changed during semantic review: {pid}'
        assert (a['order'], a['title'], a['author'], a['image']) == (b['order'], b['title'], b['author'], b['image'])
        assert r['finalCommentarySha256'] == digest(a['commentary']), f'Completed review result mismatch: {pid}'
        actual = {k for k in set(b['commentary']) | set(a['commentary'])
                  if (k in b['commentary']) != (k in a['commentary'])
                  or b['commentary'].get(k) != a['commentary'].get(k)}
        issues = records[pid]['issues']
        for issue in issues:
            assert issue['severity'] in ('major', 'moderate', 'minor')
            assert issue['field'].strip() and issue['problem'].strip() and issue['proposed'].strip()
            assert 'original' in issue and isinstance(issue['verificationRefs'], list)
        assert len(r['issueDecisions']) == len(issues), f'Unresolved issue: {pid}'
        for index, decision in enumerate(r['issueDecisions']):
            assert decision['issueIndex'] == index
            assert decision['action'] in ('revised', 'clarified', 'retain-with-evidence') and decision['reason'].strip()
            if decision['action'] != 'retain-with-evidence':
                assert decision['targetFields'] and set(decision['targetFields']) <= actual
            if decision['action'] == 'revised':
                assert set(decision['targetFields']) & {'summary', 'interpretation', 'glossary'}
            elif decision['action'] == 'clarified':
                assert set(decision['targetFields']) & {'reviewNotes', 'basis'}
        for change in r['changes']:
            field = change['field']
            assert change['before'] == b['commentary'].get(field)
            assert change['after'] == a['commentary'].get(field)
        # All actual field changes, including reference additions, must be logged.
        assert actual == {c['field'] for c in r['changes']}, f'Unlogged edit: {pid}'
        if any(b['commentary'][k] != a['commentary'][k] for k in READER_FIELDS):
            revised += 1
        elif b['commentary']['reviewNotes'] != a['commentary']['reviewNotes']:
            clarified += 1
    assert audit['stats']['baselineAssessmentCounts'] == dict(Counter(r['assessment'] for r in records.values()))
    assert audit['stats']['reviewerIssueCount'] == sum(len(r['issues']) for r in records.values())
    assert audit['stats']['reviewedPoemCount'] == 305
    assert audit['stats']['revisedReaderPoemCount'] == revised
    assert audit['stats']['notesOnlyPoemCount'] == clarified
    live_comparison = compare_live_review(after, live)
    if current:
        assert not live_comparison['readerFieldsChangedPoemIds'], 'Current reader fields differ from the completed semantic review: ' + ', '.join(live_comparison['readerFieldsChangedPoemIds'])
    return {'reviewedPoemCount': 305, 'revisedReaderPoemCount': revised,
            'notesOnlyPoemCount': clarified, 'allRevisionsMatchReviewedResult': True,
            'semanticReviewResultCommit': audit['semanticReviewResultCommit'],
            'currentArchivalUnchanged': True, 'liveComparison': live_comparison,
            'publicationReady': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', action='store_true', help='Also require current summary, interpretation and glossary to match the completed review; later text and metadata revisions are reported separately.')
    args = parser.parse_args()
    print(json.dumps(check(current=args.current), ensure_ascii=False))

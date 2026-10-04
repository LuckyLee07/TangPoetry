#!/usr/bin/env python3
"""Check review coverage and revision provenance, not literary correctness."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/expansion/tang-second-volume'


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check():
    audit = read(BASE / 'semantic-review-audit.json')
    baseline_raw = subprocess.check_output(
        ['git', 'show', audit['reviewedCommit'] + ':data/expansion/tang-second-volume/production.json'],
        cwd=ROOT,
    )
    baseline = json.loads(baseline_raw)
    assert len(baseline['poems']) == 305
    before = {p['id']: p for p in baseline['poems']}
    production = read(BASE / 'production.json')
    assert len(production['poems']) == 305
    after = {p['id']: p for p in production['poems']}
    assert len(before) == len(after) == 305 and set(before) == set(after)
    assert audit['publicationReady'] is False and production['publicationReady'] is False
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
            assert r['poemMeaning'].strip() and r['alignmentNotes']
            assert all(isinstance(n, str) and n.strip() for n in r['alignmentNotes'])
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
        assert r['finalCommentarySha256'] == digest(a['commentary']), f'Review result stale: {pid}'
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
        reader_fields = ('summary', 'interpretation', 'glossary')
        if any(b['commentary'][k] != a['commentary'][k] for k in reader_fields):
            revised += 1
        elif b['commentary']['reviewNotes'] != a['commentary']['reviewNotes']:
            clarified += 1
    assert audit['stats']['reviewedPoemCount'] == 305
    assert audit['stats']['revisedReaderPoemCount'] == revised
    assert audit['stats']['notesOnlyPoemCount'] == clarified
    return {'reviewedPoemCount': 305, 'revisedReaderPoemCount': revised,
            'notesOnlyPoemCount': clarified, 'allRevisionsMatchProduction': True,
            'archivalTextUnchanged': True, 'publicationReady': False}


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False))

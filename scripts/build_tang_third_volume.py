#!/usr/bin/env python3
"""Build the independent third-volume research selection; never modify app data."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path

from build_tang_yizhu import key, read, sentences, shape, make_record, source_ref

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/expansion/tang-third-volume'
CORPUS = ROOT / 'data/expansion/tang-yizhu/poems.json'
APP = ROOT / 'data/final/tang_poems_final.json'
XIEYING = ROOT / 'data/expansion/tang-yizhu/xieying/matched-poems.json'
DATE = '2026-09-28'
THRESHOLD = .70
ADDITIONAL = OUT / 'sources/additional-qts.json'


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fingerprint(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write(name, value):
    target = OUT / name
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    target.write_text(text)


def load_corpus():
    corpus = {p['id']: p for p in read(CORPUS)['poems']}
    extra = read(ADDITIONAL)
    for item in extra['records']:
        raw = item['raw']
        ref = source_ref('chinese-poetry-qts', item['file'], recordId=raw['id'],
                         recordIndex=item['index'], repositoryCommit=extra['repositoryCommit'])
        record = make_record(raw, [ref])
        record['textSha256'] = sha(record['text'])
        if record['id'] in corpus:
            raise ValueError(f'Additional source already exists in corpus: {record["id"]}')
        corpus[record['id']] = record
    return corpus


def readings(poem):
    """Compare every available text witness, regardless of title/author spelling."""
    values = [poem['text']]
    if 'sourceReading' in poem:
        values.append(poem['sourceReading']['text'])
    values.extend('\n'.join(w['paragraphs']) for w in poem.get('witnesses', []) if w.get('paragraphs'))
    return list(dict.fromkeys(key(t) for t in values if key(t)))


def duplicate_candidates(left, right, same_collection=False):
    ldata = [(p, [(t, Counter(t)) for t in readings(p)]) for p in left]
    rdata = ldata if same_collection else [(p, [(t, Counter(t)) for t in readings(p)]) for p in right]
    found = []
    for i, (a, av) in enumerate(ldata):
        for j, (b, bv) in enumerate(rdata):
            if same_collection and j <= i:
                continue
            shared_ids = sorted(set(a.get('sourceRecordIds', [])) & set(b.get('sourceRecordIds', [])))
            best = 0
            for at, ac in av:
                for bt, bc in bv:
                    if at == bt:
                        best = 1
                    elif 2 * min(len(at), len(bt)) / (len(at) + len(bt)) >= THRESHOLD:
                        bound = 2 * sum((ac & bc).values()) / (len(at) + len(bt))
                        if bound >= THRESHOLD:
                            best = max(best, SequenceMatcher(None, at, bt, autojunk=False).ratio())
            if best >= THRESHOLD or shared_ids or a['id'] == b['id']:
                found.append({'leftId': a['id'], 'leftTitle': a['title'], 'leftAuthor': a['author'],
                              'rightId': b['id'], 'rightTitle': b['title'], 'rightAuthor': b['author'],
                              'similarity': round(best, 6), 'sharedSourceRecordIds': shared_ids,
                              'requiresHumanReview': best < 1})
    return found


def main():
    manifest = read(OUT / 'selection.json')
    revision = read(OUT / 'sources/popularity-revision.json')
    entries = manifest['entries']
    if not entries or len({e['id'] for e in entries}) != len(entries):
        raise ValueError('Selection must contain distinct poem IDs; never pad to a quota')
    corpus = load_corpus()
    edits = {e['poemId']: e for e in read(OUT / 'sources/editions.json')['records']}
    notes = {}
    for n in read(OUT / 'sources/editorial-notes.json')['records']:
        notes.setdefault(n['poemId'], []).append(n)
    poems = []
    for index, entry in enumerate(entries, 1):
        original = corpus[entry['id']]
        if entry['author'] != original['author']:
            raise ValueError(f"Unexpected author change: {entry['id']}")
        p = deepcopy(original)
        # Preserve the complete source reading and provenance before any chosen reading is applied.
        p['sourceReading'] = {k: deepcopy(original[k]) for k in ('title', 'sourceTitle', 'text', 'paragraphs',
                              'paragraphsTraditional', 'textSha256', 'traditionalTextOrigin')}
        p['title'] = entry['title']
        p['order'] = index
        p['selectionOrder'] = entry['selectionOrder']
        p['editorialDecisions'] = []
        if edit := edits.get(p['id']):
            if edit.get('paragraphs'):
                p['paragraphs'] = edit['paragraphs'][:]
            for replacement in edit.get('replace', []):
                old, new = replacement['old'], replacement['new']
                if '\n'.join(p['paragraphs']).count(old) != 1:
                    raise ValueError(f'Reading correction no longer applicable: {p["id"]}')
                p['paragraphs'] = [x.replace(old, new) for x in p['paragraphs']]
            if edit.get('title'):
                p['title'] = edit['title']
            p['editorialDecisions'].append(edit)
            p['sourceRefs'].append({'sourceId': 'third-volume-reading-check', 'url': edit['sourceUrl'],
                                    'accessedOn': edit['accessedOn'], 'scope': edit['kind']})
        p['text'] = '\n'.join(p['paragraphs'])
        p['sentences'] = sentences(p['paragraphs'])
        p['form'] = shape(p['paragraphs'], p['title'], p['sourceTitle'])
        p['textSha256'] = sha(p['text'])
        p['normalizedTextSha256'] = sha(key(p['text']))
        if p['text'] != original['text']:
            # An unverified machine-converted traditional edition would conceal the chosen differences.
            p['paragraphsTraditional'] = None
            p['traditionalTextOrigin'] = 'not-prepared-for-corrected-reading; original-in-sourceReading'
        p['aliases'] = list(dict.fromkeys([*original.get('aliases', []), original['title'], entry['title'], p['title']]))
        p['titleTraditional'] = None
        p['titleTraditionalOrigin'] = 'not-prepared-for-third-volume-display-title'
        p['selection'] = {'basis': 'familiar-poems-first-editorial-curation',
                          'reason': entry['reason'], 'retainedFrom': entry['retainedFrom'],
                          'bookMembership': {'shijingQianshuo': 'not-verified', 'maoTangshixuan': 'not-verified'},
                          'upstreamCandidateSelection': original['selection']}
        p['editorialNotes'] = notes.get(p['id'], [])
        p['authorDisplay'] = next((n['authorDisplay'] for n in p['editorialNotes'] if 'authorDisplay' in n), p['author'])
        p['review'] = {'status': 'selection-complete-texts-collected-needs-edition-proofreading',
                       'publicationReady': False, 'upstreamIssues': original['review']['issues'],
                       'issues': [n['code'] for n in p['editorialNotes']],
                       'limits': ['not-line-by-line-checked-against-print-edition', 'composition-date-unverified']}
        p['collectionStatus'] = 'third-volume-selected-not-imported'
        # No illustrations, audio, translations or modern commentary are copied.
        poems.append(p)

    app = read(APP)['poems']
    xieying_doc = read(XIEYING)
    xe = [p for e in xieying_doc['entries'] for p in e.get('poems', [])]
    print('Checking all text witnesses against both baseline volumes...', flush=True)
    overlap = duplicate_candidates(poems, app + xe)
    internal = duplicate_candidates(poems, poems, same_collection=True)
    # Only exact normalized matches are merged for the release-plan arithmetic.
    baseline_unique = len({key(p['text']) for p in app + xe})
    cross = [{'appId': a['id'], 'appTitle': a['title'], 'xieyingId': b['id'], 'xieyingTitle': b['title'],
              'author': a['author']} for a in app for b in xe if key(a['text']) == key(b['text'])]
    inherited_issues = [{'id': p['id'], 'title': p['title'], 'author': p['author'],
                         'issues': p['review']['upstreamIssues']} for p in poems if p['review']['upstreamIssues']]
    special = [{'id': p['id'], 'title': p['title'], 'author': p['author'], 'notes': p['editorialNotes']}
               for p in poems if p['editorialNotes']]
    retained = Counter(p['selection']['retainedFrom'] for p in poems)
    if retained != Counter({'reader-selection-80': 80, 'earlier-recommendations-13': 13, 'expanded-to-300': len(poems)-93}):
        raise ValueError('Original 93 recommendations were not fully retained')
    retained_snapshot = read(OUT / 'sources/retained-93.json')['entries']
    expected_retained = {(e['id'], e['retainedFrom']) for e in retained_snapshot}
    actual_retained = {(p['id'], p['selection']['retainedFrom']) for p in poems
                       if p['selection']['retainedFrom'] != 'expanded-to-300'}
    if actual_retained != expected_retained:
        raise ValueError('The original 93 identities changed; do not silently replace them')
    # Fail closed if source/baseline changes cause an overlap; no silent dropping or substitution.
    if overlap or internal:
        raise ValueError(json.dumps({'baselineCandidates': overlap, 'internalCandidates': internal}, ensure_ascii=False))
    stats = {'poems': len(poems), 'retainedRecommendations': 93, 'newSelections': len(poems)-93,
             'sourceAuthorLabels': len({p['author'] for p in poems}),
             'byProposedGenre': dict(Counter(p['form']['proposedGenre'] for p in poems)),
             'bySourceAuthor': dict(sorted(Counter(p['author'] for p in poems).items(), key=lambda x: (-x[1], x[0]))),
             'editionDecisions': sum(bool(p['editorialDecisions']) for p in poems),
             'longPoemsOver24Sentences': sum(p['form']['sentenceCount'] > 24 for p in poems)}
    inputs = [CORPUS, APP, XIEYING, OUT/'selection.json', OUT/'sources/editions.json',
              OUT/'sources/editorial-notes.json', OUT/'sources/methodology.json',
              OUT/'sources/retained-93.json', ADDITIONAL, OUT/'sources/popularity-revision.json',
              OUT/'sources/selection-before-popularity-review.json']
    audit = {'schemaVersion': 1, 'checkedOn': DATE, 'inputs': [fingerprint(p) for p in inputs],
             'deduplication': {'normalization': 'build_tang_yizhu.key: punctuation removed, simplified + explicit glyph folding',
                              'allAvailableTextWitnessesCompared': True, 'authorsNotUsedAsFilter': True,
                              'similarityCandidateThreshold': THRESHOLD, 'algorithm': 'difflib.SequenceMatcher(autojunk=False); character-multiset upper bound prefilter',
                              'scope': 'current 320 app records + 305 Xieying provisional selected records; not all historical anthologies',
                              'baselineCandidates': overlap, 'internalCandidates': internal,
                              'sharedSourceRecordIdsChecked': True},
             'baseline': {'appPoems': len(app), 'xieyingPoems': len(xe), 'crossVolumeExactMatches': cross,
                          'uniquePoems': baseline_unique,
                          'xieyingUserConfirmedPoems': sum(len(e.get('poems', [])) for e in xieying_doc['entries'] if e['status']=='user-confirmed-selection')},
             'releasePlan': {'volume1': len(app), 'volume2Gross': len(xe), 'volume2NetNew': baseline_unique-len(app),
                             'volume3NetNew': len(poems), 'uniqueTotal': baseline_unique+len(poems),
                             'status': 'planned; volume2 and volume3 not imported'},
             'inheritedReviewFlags': inherited_issues, 'editorialReviewNotes': special,
             'stats': stats, 'selectionPolicy': manifest['selectionPolicy'],
             'revisionRef': 'sources/popularity-revision.json', 'publicationReady': False}
    document = {'schemaVersion': 1, 'name': manifest['name'], 'selectedOn': DATE,
                'publicationReady': False, 'importIntoApp': False,
                'status': 'familiar-poems-first-editorial-draft', 'stats': stats,
                'catalogGrouping': 'author', 'selectionPolicy': manifest['selectionPolicy'],
                'sourcePolicy': 'Public-domain verse + linked provenance; all inclusion reasons are original editorial notes. No modern book annotations copied.',
                'methodologyRef': 'sources/methodology.json', 'auditRef': 'audit.json', 'poems': poems}
    write('poems.json', document)
    write('audit.json', audit)

    catalog = [f'# 唐诗画笺·第三卷：{len(poems)} 首选目', '',
               f'保留此前 93 首，其余 {len(poems)-93} 首；按单首计数。仅整理数据，尚未导入 App。', '',
               '以广为传诵、值得熟读为优先标准，不设主题或作者配额。目录按作者归组，不表示诗人或作品排名。', '',
               f'本轮替换 {revision["replacementCount"]} 首；{len(poems)} 是目前候选数量，并非宣称每首均已测量大众知名度，也不是必须凑足的整数。', '',
               '每首的作者署名、首联、收录理由如下；题名可跳转到完整诗文。正文来源与校订记录见全文和 JSON。', '',
               '[说明与统计](README.md) · [全文](POEMS.md) · [本轮替换](REVISION.md) · [结构化数据](poems.json) · [校订与待核](REVIEW.md)', '']
    full = ['# 唐诗画笺·第三卷：完整诗文', '',
            f'收录 {len(poems)} 首，组诗按单首展开，长诗不节选。正文为编辑工作稿，尚未逐字对校印本。', '',
            '展示标题与底本原题分别保存；异体字和不影响身份的版本差异一般沿底本。', '',
            '个别校订见每首“文本处理”；繁体原始读法与完整见证信息见 poems.json 的 sourceReading / witnesses。', '',
            '[目录](CATALOG.md) · [编辑说明](README.md) · [待核清单](REVIEW.md)', '']
    for author in dict.fromkeys(p['author'] for p in poems):
        members = [p for p in poems if p['author'] == author]
        catalog += [f'## {members[0]["authorDisplay"]}（{len(members)} 首）', '',
                    '| 编号 | 题名 | 首联 | 收录理由 |', '| --- | --- | --- | --- |']
        for p in poems:
            if p['author'] != author:
                continue
            opening = ''.join(p['sentences'][:2])
            catalog.append(f'| {p["order"]:03} | [《{p["title"]}》](POEMS.md#{p["id"]}) | {opening} | {p["selection"]["reason"]} |')
        catalog.append('')
    for p in poems:
        full += [f'<a id="{p["id"]}"></a>', '', f'## {p["order"]:03}　{p["title"]}', '',
                 p['authorDisplay'], '', '  \n'.join(p['paragraphs']), '',
                 f'**收录理由：** {p["selection"]["reason"]}', '',
                 f'**来源：** [底本文本]({p["sourceRefs"][0]["url"]})；原题《{p["sourceReading"]["title"]}》；记录 `{p["id"]}`。']
        for e in p['editorialDecisions']:
            full += ['', f'**文本处理：** {e["note"]} [对照来源]({e["sourceUrl"]})']
        for n in p['editorialNotes']:
            full += ['', '**待核说明：** ' + n['note'] + (f' [依据]({n["sourceUrl"]})' if n.get('sourceUrl') else '')]
        if p['review']['upstreamIssues']:
            full += ['', '**底本检查标记：** ' + '、'.join(p['review']['upstreamIssues']) + '（含杂言句式提示，不等于已判定诗文有误）。']
        full.append('')
    write('CATALOG.md', '\n'.join(catalog).rstrip()+'\n')
    write('POEMS.md', '\n'.join(full).rstrip()+'\n')
    changes = ['# 本轮选目调整', '', '依据用户意见：以脍炙人口为优先，不设主题或作者配额。', '',
               f'本轮替换 {revision["replacementCount"]} 首，当前 {len(poems)} 首；此前 93 首推荐全部保留。', '',
               '以下替换是编辑取舍，不表示被替换作品质量较低，也不是经过统计的传播热度排名。', '',
               '| 原篇目 | 本轮补入 | 收录考虑 |', '| --- | --- | --- |']
    for change in revision['replacements']:
        previous, replacement = change['previous'], change['replacement']
        changes.append(f'| {previous["author"]}《{previous["title"]}》 | '
                       f'{replacement["author"]}[《{replacement["title"]}》](POEMS.md#{replacement["id"]}) | '
                       f'{replacement["reason"]} |')
    changes += ['', '原选目保存在 [历史快照](sources/selection-before-popularity-review.json)，被替换诗文仍保留在上游研究库。', '',
                '历史快照里的主题字段仅用于追溯旧稿，不参与当前选目。 [当前目录](CATALOG.md)', '']
    write('REVISION.md', '\n'.join(changes))
    review = ['# 校订与待核说明', '', '选目已完成；文本是可追溯的整理稿，尚未形成出版定本。', '',
              f'## 已明确处理的 {stats["editionDecisions"]} 项', '', '| 作者 / 篇目 | 处理与依据 |', '| --- | --- |']
    for p in poems:
        for e in p['editorialDecisions']:
            review.append(f'| {p["author"]}《{p["title"]}》 | {e["note"]} [来源]({e["sourceUrl"]}) |')
    review += ['', '校订仅作用于第三卷输出，上游候选库和前两卷均未改写。原文和原始哈希留在 `sourceReading`。', '',
               '## 需要继续定本的具体项目', '', '| 作者 / 篇目 | 说明 |', '| --- | --- |']
    for p in poems:
        for n in p['editorialNotes']:
            review.append(f'| {p["author"]}《{p["title"]}》 | {n["note"]}'+(f' [依据]({n["sourceUrl"]})' if n.get('sourceUrl') else '')+' |')
    review += ['', '## 自动检查继承的标记', '',
               '杂言乐府天然可能长短句并存；`mixed-length-verse-review` 是检查入口，不能据此判作残诗。', '',
               '| 作者 / 篇目 | 标记 |', '| --- | --- |']
    for row in inherited_issues:
        review.append(f'| {row["author"]}《{row["title"]}》 | {"、".join(row["issues"])} |')
    review += ['', '## 发布前的文本工作', '',
               '- 选择统一的可靠校注本，对 300 首逐句校读；有争议处保留异文、出处和决定。',
               '- 核对组诗篇次与异题；本次按来源中的单首身份计数，没有把整组算作一首。',
               '- 对跨唐五代作者核单篇系年，检查来源署名与通行作者名的对应。',
               '- 体裁目前是句式初分与底本乐府门类，未逐首验平仄和用韵。',
               '- 个别罕见字、古字、长诗引号和来源标点尚需整理，尤其《秦妇吟》；未据猜测改字。',
               '- 现代译文、词注、创作背景、拼音和朗读尚未新增；不把收录理由冒充校注或参考书原评。', '',
               '本清单不妨碍选目审阅，但 `publicationReady` 在完成审校前保持 `false`。', '']
    write('REVIEW.md', '\n'.join(review))
    print(json.dumps({'poems':len(poems),'grouping':'author','authors':stats['sourceAuthorLabels'],
                      'releasePlan':audit['releasePlan'],'dedupCandidates':len(overlap)+len(internal)},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

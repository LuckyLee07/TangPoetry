#!/usr/bin/env python3
"""Export the App's second-volume research selection without rewriting the book catalogue."""
from copy import deepcopy
import json
from pathlib import Path
import hashlib
from build_tang_yizhu import key, sentences
from build_tang_third_volume import duplicate_candidates

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/expansion/tang-second-volume'
CATALOG = ROOT/'data/expansion/tang-yizhu/xieying/matched-poems.json'
APP = ROOT/'data/final/tang_poems_final.json'
CORPUS = ROOT/'data/expansion/tang-yizhu/poems.json'

def read(path): return json.loads(path.read_text())
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def write(name,obj): (OUT/name).write_text(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def main():
    policy=read(OUT/'selection-policy.json'); remove=policy['replace']; add=policy['supplement']
    app=read(APP)['poems']; source=read(CATALOG); poems=[]; excluded=[]
    for entry in source['entries']:
        for p in entry.get('poems',[]):
            if p['id']==remove['poemId']:
                assert entry['id']==remove['catalogEntryId']
                existing=next(a for a in app if a['id']==remove['firstVolumePoemId'])
                assert key(p['text'])==key(existing['text'])
                excluded.append({'id':p['id'],'title':p['title'],'author':p['author'],'catalogEntryId':entry['id'],
                                 'firstVolumePoemId':existing['id'],'reason':remove['reason']})
                continue
            p=deepcopy(p)
            p['collectionOrigin']={'kind':'xieying-catalog-selection','catalogEntryId':entry['id'],
                                   'catalogTitle':entry['title'],'catalogStatus':entry['status'],
                                   'sourceSection':entry['section']}
            poems.append(p)
    assert len(excluded)==1, 'Expected exactly the approved overlap; do not silently remove other poems'
    p=deepcopy(next(p for p in read(CORPUS)['poems'] if p['id']==add['poemId']))
    assert p['author']==add['author']
    p['sourceReading']={k:deepcopy(p[k]) for k in ['title','text','paragraphs','paragraphsTraditional','traditionalTextOrigin','textSha256']}
    edit=add['edition'];assert p['text'].count(edit['old'])==1
    p['paragraphs']=[s.replace(edit['old'],edit['new']) for s in p['paragraphs']]
    p['paragraphsTraditional']=[s.replace(edit['oldTraditional'],edit['newTraditional']) for s in p['paragraphsTraditional']]
    p['traditionalTextOrigin']='source-with-documented-variant-selection; original-in-sourceReading'
    p['text']='\n'.join(p['paragraphs']);p['sentences']=sentences(p['paragraphs']);p['textSha256']=sha(p['text'])
    p['form'].update(proposedGenre=add['proposedGenre'],status='editorial-genre-selection',
                     metricalShape='八句七言；不据句数推定律诗',
                     basis='本篇按七言古诗收录；原候选按八句七言推测为律诗的标签不沿用，未声称完成平仄校验')
    p['editorialDecisions']=[edit]
    p['sourceRefs'].append({'sourceId':'second-volume-edition-check','url':edit['url'],'accessedOn':edit['accessedOn']})
    p['selection']={'basis':'editorial-supplement','reason':add['reason'],'bookMembership':add['bookMembership']}
    p['collectionOrigin']={'kind':'editorial-supplement','section':add['section'],'replacesPoemId':remove['poemId'],
                           'note':'App 第二卷补选；不冒充《唐诗撷英》原书篇目。'}
    p['review'].update(publicationReady=False,status='selected-needs-print-edition-proofreading')
    poems.append(p)
    for i,p in enumerate(poems,1):
        p['order']=i;p['collectionStatus']='second-volume-selected-not-imported'
    overlap=duplicate_candidates(poems,app);internal=duplicate_candidates(poems,poems,same_collection=True)
    assert not overlap and not internal, (overlap,internal)
    assert len(poems)==len({p['id'] for p in poems})==305
    stats={'sourceCatalogPoems':sum(len(e.get('poems',[])) for e in source['entries']),
           'retainedSourcePoems':len(poems)-1,'excludedOverlaps':len(excluded),'editorialSupplements':1,
           'poems':len(poems),'netNewAgainstVolume1':len(poems)}
    write('poems.json',{'schemaVersion':1,'name':'唐诗画笺·第二卷：撷英与补选','preparedOn':'2026-09-28',
                        'importIntoApp':False,'publicationReady':False,'stats':stats,'excludedFromAppSelection':excluded,
                        'sourceCatalogRef':'../tang-yizhu/xieying/matched-poems.json','policyRef':'selection-policy.json','poems':poems})
    write('audit.json',{'checkedOn':'2026-09-28','stats':stats,'baselineCandidates':overlap,'internalCandidates':internal,
                       'inputs':[{'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
                                 for f in [CATALOG,APP,CORPUS,OUT/'selection-policy.json']]})
    rows=['# App 第二卷选目：305 首','',
          '304 首保留原目录对应，1 首为独立补选；排除与第一卷重复的《子夜吴歌·冬歌》。原书目档案保持完整。暂未导入 App。','',
          '[整理说明](README.md) · [结构化完整诗文](poems.json)','',
          '| 编号 | 作者 | 诗题 | 起句 | 选目来源 |','| --- | --- | --- | --- | --- |']
    for p in poems:
        origin='独立补选' if p['collectionOrigin']['kind']=='editorial-supplement' else p['collectionOrigin']['catalogEntryId']
        rows.append(f"| {p['order']} | {p['author']} | {p['title']} | {''.join(p['sentences'][:2])} | {origin} |")
    write('CATALOG.md','\n'.join(rows)+'\n')
    print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':main()

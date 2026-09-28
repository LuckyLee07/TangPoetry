#!/usr/bin/env python3
"""Assemble second-volume editorial drafts without changing source poems or the App."""
import argparse, copy, hashlib, json, re, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/expansion/tang-second-volume'
def read(p): return json.loads(p.read_text())
def write(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def assemble(require_complete=False, save=True):
    source = read(BASE/'poems.json'); poems = source['poems']
    assert len(poems) == 305 and len({p['id'] for p in poems}) == 305
    commentary = {}; files = {}
    for path in sorted((BASE/'commentary').glob('*.json')):
        for pid, item in read(path)['poems'].items():
            assert pid not in commentary, f'Duplicate commentary: {pid}'
            commentary[pid] = item; files[pid] = str(path.relative_to(ROOT))
    assert set(commentary) == {p['id'] for p in poems}, 'Commentary coverage differs'
    corrections_path = BASE/'text-corrections.json'
    corrections = {}
    if corrections_path.exists():
        for fix in read(corrections_path)['corrections']:
            assert fix['id'] not in corrections and fix['status']=='accepted-for-editorial-draft'
            assert fix['reason'] and fix['verificationRefs'] and fix['sourceText'] != fix['proposedText']
            corrections[fix['id']] = fix
    assert set(corrections) <= set(commentary), 'Unknown correction IDs'
    receipts = {}; hashes = {}; image_bytes = 0; errors = []
    for path in sorted((BASE/'illustrations/receipts').glob('*.json')):
        r = read(path); pid = r['id']; asset = ROOT/r['image']
        assert pid not in receipts, f'Duplicate art receipt: {pid}'
        try:
            b = asset.read_bytes(); size = struct.unpack('>II', b[16:24])
            assert b[:8] == b'\x89PNG\r\n\x1a\n' and size == (r['width'], r['height']) and size[1]>size[0]
            digest = hashlib.sha256(b).hexdigest()
            assert digest == r['sha256'], 'Hash mismatch'
            assert digest not in hashes, 'Image reused for multiple poems'
            assert r['status']=='accepted' and r['visualReview'] and r['prompt']
            hashes[digest] = pid; image_bytes += len(b)
        except (OSError, AssertionError, struct.error) as exc:
            errors.append(f"{r['order']}: {exc}")
        receipts[pid] = r
    assert not (set(receipts)-set(commentary)), 'Unknown image IDs'
    output = []; notes = []; paragraphs = glossary_count = 0
    for p in poems:
        pid=p['id']; c=copy.deepcopy(commentary[pid]); r=receipts.get(pid)
        assert isinstance(c.get('summary'),str) and c['summary'].strip(), pid
        assert isinstance(c.get('interpretation'),list) and all(isinstance(x,str) and x.strip() for x in c['interpretation']) and c['interpretation'], pid
        assert isinstance(c.get('glossary'),list) and all(x.get('term') and x.get('text') for x in c['glossary']), pid
        assert isinstance(c.get('reviewNotes'),list) and c['reviewStatus']=='editorial-draft', pid
        assert c.get('artDirection') and c['basis'].get('sourceRefs'), pid
        for key in ('title','author','order'):
            if key in c: assert c[key]==p[key], (pid,key)
        if c.get('sourceTextSha256'):
            assert c['sourceTextSha256']==hashlib.sha256(p['text'].encode()).hexdigest(), pid
        if r: assert (r['order'],r['title'],r['author'])==(p['order'],p['title'],p['author']),pid
        entry={key:p[key] for key in ('id','order','title','author','dynasty','paragraphs','sentences','text','form','sourceRefs','collectionOrigin')}
        if pid in corrections:
            fix = corrections[pid]
            assert fix['order']==p['order'] and fix['sourceText']==p['text'], pid
            entry['sourceText'] = p['text']
            entry['text'] = fix['proposedText']
            entry['paragraphs'] = fix['proposedText'].splitlines()
            entry['sentences'] = [s.strip() for line in entry['paragraphs'] for s in re.findall(r'[^，。！？；、\n]+[，。！？；、]?', line) if s.strip()]
            entry['form'] = copy.deepcopy(p['form'])
            counts = [sum('\u3400'<=ch<='\u9fff' or '\U00020000'<=ch<='\U000323af' for ch in line) for line in entry['sentences']]
            entry['form'].update(sentenceCount=len(counts), characterCounts=counts, characterCount=sum(counts), uniformLineLength=counts[0] if len(set(counts))==1 else None)
            for key, value in fix.get('commentaryOverrides',{}).items():
                assert key in ('summary','interpretation','glossary'), key
                c[key] = value
            assert isinstance(c['summary'],str) and c['summary'].strip(), pid
            assert isinstance(c['interpretation'],list) and c['interpretation'] and all(isinstance(x,str) and x.strip() for x in c['interpretation']), pid
            assert isinstance(c['glossary'],list) and all(isinstance(x,dict) and x.get('term') and x.get('text') for x in c['glossary']), pid
            c['reviewNotes'] = ['制作稿已校订：'+fix['reason']+' 原始 poems.json 保留原貌，本次仅用于独立编辑预览，尚非纸书终校。'] + ['初稿记录（归档底本）：'+note for note in c['reviewNotes']]
            c['basis']['verificationRefs'] = list(dict.fromkeys(c['basis'].get('verificationRefs',[])+fix['verificationRefs']))
            entry['textCorrection'] = {'status':fix['status'],'reason':fix['reason'],'verificationRefs':fix['verificationRefs'],'record':'data/expansion/tang-second-volume/text-corrections.json'}
        paragraphs += len(c['interpretation']); glossary_count += len(c['glossary'])
        entry.update(commentary=c,commentaryFile=files[pid],image=r['image'] if r else None,illustrationReceipt=f"data/expansion/tang-second-volume/illustrations/receipts/{p['order']:03d}.json" if r else None)
        output.append(entry)
        if c['reviewNotes']:
            notes.append({'id':pid,'order':p['order'],'title':p['title'],'author':p['author'],'notes':c['reviewNotes'],'verificationRefs':c['basis'].get('verificationRefs',[])})
    pending=[p['order'] for p in poems if p['id'] not in receipts]
    audit={'schemaVersion':1,'scope':'第二卷内容制作；不改写原底本、不导入第一卷 App', 'poemCount':len(poems),'commentaryCount':len(commentary),'interpretationParagraphCount':paragraphs,'glossaryEntryCount':glossary_count,'illustrationCount':len(receipts),'illustrationBytes':image_bytes,'pendingIllustrationOrders':pending,'editorialNotePoemCount':len(notes),'textCorrectionCount':len(corrections),'assetErrors':errors,'allAssetsPresent':not pending and not errors,'publicationReady':False,'checks':['稳定 ID 一一对应','全部诗意、解读、词注字段及来源非空检查','所记录原文哈希检查','校订前原文精确匹配与证据字段检查','PNG 尺寸、SHA-256 与重复文件检查'],'limits':['结构检查不能代替学术终审','插画为逐张 AI 助手视觉复核，尚未整库真人审阅','校勘笔记含异文、释义边界及疑似缺字缺句，不等于全部是错误']}
    assert not errors, errors
    if require_complete: assert not pending, f'Missing illustrations: {pending}'
    if save:
        write(BASE/'production.json',{'schemaVersion':1,'name':'唐诗画笺·第二卷制作稿','importIntoApp':False,'publicationReady':False,'stats':audit,'poems':output})
        write(BASE/'production-audit.json',audit)
        write(BASE/'editorial-notes.json',{'schemaVersion':1,'status':'editorial-draft','notes':notes})
        md=['# 第二卷校勘与释义笔记','','自动汇总自逐首编辑稿。包含版本差异、解释边界和待核问题；不是勘误清单，也不代表原书已经核对。原始 `poems.json` 保留原貌。','']
        for n in notes:
            md += [f"## {n['order']:03d} {n['title']} · {n['author']}",'']+[f'- {s}' for s in n['notes']]+['']
            md += [f'- [核对来源 {i+1}]({url})' for i,url in enumerate(n['verificationRefs'])]+['']
        (BASE/'EDITORIAL_NOTES.md').write_text('\n'.join(md).rstrip()+'\n')
    return audit
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--require-complete',action='store_true'); ap.add_argument('--check',action='store_true'); a=ap.parse_args()
    print(json.dumps(assemble(a.require_complete,not a.check),ensure_ascii=False))

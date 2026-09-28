#!/usr/bin/env python3
"""Save one visually reviewed built-in imagegen result; never synthesize images here."""
import hashlib, json, shutil, struct, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/expansion/tang-second-volume'
def main():
    record = json.loads(sys.argv[1])
    poems = json.loads((BASE / 'poems.json').read_text())['poems']
    poem = next(p for p in poems if p['order'] == record['order'])
    source = Path(record['source'])
    data = source.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG output')
    width, height = struct.unpack('>II', data[16:24])
    if height <= width:
        raise ValueError('Poem page must be portrait')
    if not record.get('prompt') or not record.get('visualReview'):
        raise ValueError('Final prompt and actual visual review are required')
    name = f"{poem['order']:03d}-{poem['id']}.png"
    dest = ROOT / 'assets/volume-2/poem-art' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.read_bytes() != data:
        raise ValueError('Do not overwrite an existing accepted asset; version separately')
    if not dest.exists():
        shutil.copy2(source, dest)
    result = {'schemaVersion':1,'id':poem['id'],'order':poem['order'],'title':poem['title'],
              'author':poem['author'],'method':'built-in image_gen','prompt':record['prompt'],
              'source':str(source),'image':str(dest.relative_to(ROOT)),
              'sha256':hashlib.sha256(data).hexdigest(),'width':width,'height':height,
              'status':'accepted','visualReview':record['visualReview'],
              'reviewKind':'assistant-visual-review','acceptedAt':datetime.now(timezone.utc).isoformat()}
    out = BASE / 'illustrations/receipts' / f"{poem['order']:03d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'order':poem['order'],'title':poem['title'],'image':result['image'],'size':[width,height]},ensure_ascii=False))
if __name__ == '__main__':
    main()

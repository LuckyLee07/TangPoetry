#!/usr/bin/env python3
"""Render the completed semantic review without changing its editorial conclusions."""
import argparse
import json
from pathlib import Path

from check_volume2_semantic_review import BASE, ROOT, check, read, validate_alignment_notes


REPORT_PREAMBLE = """# 第二卷诗意与注解逐首复核

复核日期：2026-10-04。范围：第二卷305首实际制作稿的正文、短诗意、展开解读和必要词注。基线提交：`2921d5e`。

305首均有具体的原诗意旨概述和句意对应记录，随后对问题逐一复核。基线结果为275首意旨相符、22首建议修订、8首有解释分歧；最终调整29首读者可见的释义，另为1首只补充解释笔记。22与8是初审分类，29与1是最终字段改动数量，两组数字不可相加。

初审提出33处问题或解释边界；根代理另补《橡媪叹》摘要的冬粮数量关系、《秋兴八首·其七》摘要的石鲸与织女静动区别。并非35处均为确定错误：有据的异文和可通的古注仍保留。

本报告及采用记录保存本轮已完成的语义复核，结果固定于提交 `{semanticReviewResultCommit}`。后续正文校订、展示题名或体裁调整另记，不因此改写本轮305首的原始判断，也不表示新稿已经再次逐首语义复核。

## 修订重点

| 诗篇 | 对照发现 | 落实结果 |
| --- | --- | --- |
| 自京赴奉先县咏怀五百字 | “忍为尘埃没”的反问被写成接受埋没的假设 | 恢复不甘沉沦、仍守济民志愿的语气 |
| 咏田家 | “不照…只照…”被译成“不只…更…” | 恢复对权贵宴席的否定与对逃亡农家的关照 |
| 吟韩冬郎·其一 | 把本诗的冷灰残烛认作韩冬郎原作所写 | 还原为回忆饯别席，不杜撰其原作内容 |
| 调张籍 | 织女关系含混，“经营”泛写眼前筹划 | 说明神游想象及诗歌构思，保留相关古注分歧 |
| 橡媪叹 | 一天拾满一筐被压缩成一天凑齐冬粮；借贷主语含混 | 区分拾取与晒蒸，把官粮放私债、归还本金取利写清 |
| 节妇吟 | 表层还珠故事与题名中的政治寄托未连起来 | 在简短诗意和词注补明婉拒李师道招揽 |
| 秋兴八首·其七 | 菰米如沉云的比喻被写成真实云影沉水 | 恢复菰米黑密如云；摘要区分织女静与石鲸动 |
| 夜 | 牛斗误写牵牛、北斗；步蟾字义过定 | 牛宿、斗宿与北斗分清；并列步蟾／步檐读法 |
| 西塞山泊渔家 | 作客诗人被扩成整日路过的众多旅人 | 恢复诗人泊舟羡望的视角 |
| 南园十三首·其五 | “若个”的反问被缩成何时有所作为 | 恢复哪一个书生凭笔墨封侯的激问 |
| 题桃花夫人庙 | 提到两位女子却未解释末联反衬 | 说明原诗的节义比较，区分古代评价与现代立场 |
| 古离别 | 酒半酣误写成酒喝到一半 | 改为酒意半酣，与展开解读一致 |

## 保留的解释空间

本轮八首需特别保留解释空间：030《长安古意》、043《省试湘灵鼓瑟》、138《幽州夜饮》、147《登裴秀才迪小台》、178《陪诸贵公子丈八沟携妓纳凉晚际遇雨二首·其一》、208《送宫人入道归山》、209《和侯大夫秋原山观征人回》、211《再授连州至衡阳酬柳柳州赠别》。下文分别记录争点和证据。

“萧相”有萧望之通行说及萧何古注；“能忘迟暮心”有暂忘与反问难忘两说；省略主语、词性及遥想关系不强行写成写实事实。已经归档的“秋未／秋禾”“世贤／避贤”“岸雨／片雨”等既有异文记录继续保留，这八首并不是整卷仅有的版本差异。

## 记录与检查

- 逐首原始审阅：`semantic-review/001-105.json`、`106-205.json`（本轮仅106–130）、`131-205.json`、`206-305.json`。
- 根代理补查和再判：`semantic-review/root-findings.json`。
- 完整采用记录、每个字段的前后稿和最终制作稿哈希：[semantic-review-audit.json](semantic-review-audit.json)。
- 运行 `python3 scripts/build_volume2_semantic_report.py` 重建本报告；`--check` 只检查生成结果是否一致。
- 运行 `python3 scripts/check_volume2_semantic_review.py`，验证305首覆盖、基线哈希、每项决策与已完成复核提交的实际修改一致，当前归档正文未变；当前制作稿与历史结果的差异另行报告。`--current` 额外要求当前短诗意、展开解读与词注仍与历史结果一致，允许有证据的正文及元数据后续校订。此脚本检查记录完整性，不代替文学判断。
- 六首既有正文校订的释义覆盖层已经同步更新，防止重建时覆盖回旧稿。新复核笔记与归档底本笔记分别标识。

本轮由AI助手实际逐首阅读完成，不是纸书或古籍影印本的逐页终校。保留 `editorial-draft` 和 `publicationReady=false`；没有以结构校验或哈希一致宣称学术上完全无误。

## 逐首意旨与对应记录

"""
ASSESSMENTS = {
    'consistent': '原稿与正文意旨相符。',
    'revise': '已修订明确误读或表述偏差。',
    'interpretive-uncertainty': '有解释分歧，已收紧措辞或补明依据。',
}


def render_poem(record, resolution):
    validate_alignment_notes(record)
    lines = [
        f"### {record['order']:03d} {record['title']} · {record['author']}",
        '', f"核验结论：{ASSESSMENTS[record['assessment']]}",
        '', f"原诗意旨：{record['poemMeaning']}", '',
    ]
    lines.extend('- ' + note for note in record['alignmentNotes'])
    lines.append('')
    assert len(record['issues']) == len(resolution['issueDecisions'])
    for index, issue in enumerate(record['issues']):
        decision = resolution['issueDecisions'][index]
        assert decision['issueIndex'] == index
        severity = {'major': '主要误读', 'moderate': '实质偏差或解释边界', 'minor': '细节精度'}[issue['severity']]
        lines.extend([
            f"- 问题（{severity}；`{issue['field']}`）：{issue['problem']}",
            f"- 初审建议：{issue['proposed']}",
            f"- 根代理采用结论：{decision['reason']}",
        ])
        if record['assessment'] == 'interpretive-uncertainty':
            lines.append('- 裁决：保留有据的解释空间，已限定主文或补充笔记，不将可通的另一解判为错误。')
        lines.append('')
    if resolution['changes']:
        fields = '、'.join(f"`{change['field']}`" for change in resolution['changes'])
        lines.extend([f'实际更新字段：{fields}。完整前后文本见审计JSON。', ''])
    lines.extend(f'- [核对来源 {index}](%s)' % ref
                 for index, ref in enumerate(record['verificationRefs'], 1))
    return '\n'.join(lines).rstrip() + '\n\n'


def render_report(audit, records):
    resolutions = {r['id']: r for r in audit['resolutions']}
    assert len(records) == len(resolutions) == 305
    assert {r['id'] for r in records} == set(resolutions)
    assert {r['order'] for r in records} == set(range(1, 306))
    preamble = REPORT_PREAMBLE.replace('{semanticReviewResultCommit}', audit['semanticReviewResultCommit'])
    return (preamble + ''.join(render_poem(record, resolutions[record['id']])
                               for record in sorted(records, key=lambda r: r['order']))).rstrip() + '\n'


def build_report():
    audit = read(BASE / 'semantic-review-audit.json')
    records = [record for relative in audit['reviewFiles']
               for record in read(ROOT / relative)['reviews']]
    return render_report(audit, records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify that the saved report matches the deterministic rendering without writing.')
    args = parser.parse_args()
    check()
    report = build_report()
    path = BASE / 'SEMANTIC_REVIEW.md'
    if args.check:
        assert path.read_text(encoding='utf-8') == report, 'Semantic review report requires regeneration'
    else:
        path.write_text(report, encoding='utf-8')
    print(json.dumps({'report': str(path.relative_to(ROOT)), 'reviewedPoemCount': 305,
                      'mode': 'check' if args.check else 'write'}, ensure_ascii=False))

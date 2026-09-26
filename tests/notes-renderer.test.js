import test from 'node:test';
import assert from 'node:assert/strict';
import { notesMarkup } from '../reader-renderer.js';

test('expanded notes separate the meaning, glossary, variants and preface without repeating the preview', () => {
  const html = notesMarkup({
    note: '页上的简短诗意', interpretation: ['第一联的意思。', '第二联的意思。'],
    annotations: [{ text: '西陆：秋天。', source: 'chiuinan' }],
    variants: [{ text: '客思深，一作客思侵。', source: '归档源' }],
    preface: ['序文上段，', '序文下段。']
  });
  assert(!html.includes('页上的简短诗意'));
  for (const title of ['诗意', '字词解释', '异文', '题序']) assert(html.includes(`<h3>${title}</h3>`));
  assert.equal(html.match(/西陆：秋天/g).length, 1);
  assert(html.includes('序文上段，序文下段。'));
});

test('empty note sections are omitted and imported text stays inert', () => {
  const html = notesMarkup({ interpretation: ['<script>不可执行</script>'], annotations: [], variants: [], preface: [] });
  assert(html.includes('&lt;script&gt;不可执行&lt;/script&gt;'));
  assert(!html.includes('字词解释') && !html.includes('异文') && !html.includes('题序'));
});

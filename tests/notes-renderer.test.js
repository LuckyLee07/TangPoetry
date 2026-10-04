import test from 'node:test';
import assert from 'node:assert/strict';
import { notesMarkup, poemMarkup } from '../reader-renderer.js';

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

test('a matching display source title omits the original-title section', () => {
  const html = notesMarkup({
    title: '盩厔县郑礒宅送钱大',
    sourceTitle: '盩厔县郑𥐟宅送钱大',
    displaySourceTitle: '盩厔县郑礒宅送钱大'
  });
  assert(!html.includes('<h3>原题</h3>'));
  assert(!html.includes('𥐟'));
});

test('a distinct display source title renders its readable name glyph', () => {
  const html = notesMarkup({
    title: '送友人',
    sourceTitle: '盩厔县郑𥐟宅送钱大',
    displaySourceTitle: '盩厔县郑礒宅送钱大'
  });
  assert(html.includes('<h3>原题</h3><p>盩厔县郑礒宅送钱大</p>'));
  assert(!html.includes('𥐟'));
});

test('first-volume notes still fall back to sourceTitle without the new display field', () => {
  const html = notesMarkup({ title: '登金陵凤凰台', sourceTitle: '登凤凰台' });
  assert(html.includes('<h3>原题</h3><p>登凤凰台</p>'));
  assert(!notesMarkup({ title: '登凤凰台', sourceTitle: '登凤凰台' }).includes('<h3>原题</h3>'));
});

test("poem bylines retain Weng Hong's Five Dynasties and early Song label", () => {
  const html = poemMarkup({
    id: 'weng-hong', title: '春残', author: '翁宏', dynasty: '五代宋初',
    section: '五言律诗', genre: '五言律诗', image: 'fixture.webp'
  }, { dynasty: '唐', rubyLines: [[['又', ''], ['是', ''], ['春', ''], ['残', ''], ['也', ''], ['，', '']]] });
  assert(html.includes('<p class="poem-author">五代宋初 · 翁宏</p>'));
  assert(!html.includes('<p class="poem-author">唐 · 翁宏</p>'));
});

test('poem ribbons show regulated-verse genre independently of their catalogue section', () => {
  const html = poemMarkup({
    id: 'qian-qi', title: '省试湘灵鼓瑟', author: '钱起', dynasty: '唐',
    section: '五言律诗', genre: '五言排律', image: 'fixture.webp'
  }, { rubyLines: [[['善', ''], ['鼓', ''], ['云', ''], ['和', ''], ['瑟', ''], ['，', '']]] });
  assert(html.includes('<div class="book-ribbon">五言排律</div>'));
  assert(!html.includes('<div class="book-ribbon">五言律诗</div>'));
});

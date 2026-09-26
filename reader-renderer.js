import { readingLayout } from './reader-core.js?v=0.5.0';

export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

export function verses(lines) {
  return lines.map(line => {
    const text = line.map(([character]) => character).join('');
    const characters = [...text];
    const lastCharacter = characters.findLastIndex(character => !/\p{Punctuation}/u.test(character));
    const cells = [];
    for (const [index, character] of characters.entries()) {
      if (index > lastCharacter && cells.length) cells.at(-1).marks += character;
      else cells.push({ character, marks: '' });
    }
    const endSpace = Math.max(1, [...(cells.at(-1)?.marks || '')].length);
    return `<div class="verse-line" role="group" style="--end-space:${endSpace}em" aria-label="${escapeHTML(text)}">${cells.map(cell => `<span class="verse-cell" aria-hidden="true">${escapeHTML(cell.character)}${cell.marks ? `<span class="verse-punctuation">${escapeHTML(cell.marks)}</span>` : ''}</span>`).join('')}</div>`;
  }).join('');
}
export function layoutReadingPage(element, detail, options) {
  if (!detail || !element.querySelector('.poem-body')) return;
  const layout = readingLayout(detail, options);
  element.dataset.layout = layout.kind;
  for (const [name, value] of Object.entries({ 'poem-top': layout.baseTop, 'poem-bottom': layout.bottom, 'poem-size': layout.fontSize, 'title-size': layout.titleSize, 'note-gap': layout.noteGap })) {
    element.style.setProperty(`--${name}`, `${value}px`);
  }
  element.style.setProperty('--verse-leading', layout.lineHeight);
  // Account for actual fonts, title wrapping and browser scrollbar width after the estimate.
  const body = element.querySelector('.poem-body');
  const text = element.querySelector('.poem-text');
  let size = layout.fontSize;
  // Keep the existing type size while the poem moves and the note gains breathing room.
  while (layout.fitWhole && size > layout.minimumFont && text.scrollHeight > body.clientHeight - layout.textRise - 21) {
    size = Math.max(layout.minimumFont, size - 0.5);
    element.style.setProperty('--poem-size', `${size}px`);
  }
  if (!layout.hasVisibleNotes) {
    // Measure after fitting so wrapped titles and large text keep their scrolling room.
    const noNoteShift = Math.max(0, Math.min(60, (body.clientHeight - text.scrollHeight - 21) / 2));
    element.style.setProperty('--poem-top', `${layout.baseTop + noNoteShift}px`);
  }
}

export function poemMarkup(poem, detail) {
  return `<figure class="scene" aria-hidden="true"><img src="./${escapeHTML(poem.image)}" alt="" decoding="async" /></figure>
    <div class="book-ribbon">${escapeHTML(poem.section)}</div>
    <div class="poem-body" tabindex="0" aria-label="${escapeHTML(poem.title)}全文"><div class="poem-text"><h2 class="poem-title">${escapeHTML(poem.title)}</h2><p class="poem-author">唐 · ${escapeHTML(poem.author)}</p><div class="poem-lines">${verses(detail.rubyLines)}</div></div>
    ${detail.note?.trim() ? `<section class="note"><h3>${escapeHTML(detail.noteTitle)}</h3><p>${escapeHTML(detail.note)}</p><button class="note-more" data-notes="${poem.id}" aria-label="查看${escapeHTML(poem.title)}的完整诗意和注释">展开</button></section>` : ''}</div>`;
}

export function notesMarkup(poem) {
  const paragraphs = items => items.map(text => `<p>${escapeHTML(text)}</p>`).join('');
  const section = (title, content) => content ? `<section class="notes-section"><h3>${title}</h3>${content}</section>` : '';
  const entries = items => items.map(item => `<p>${escapeHTML(item.text)}</p>`).join('');
  const sourceName = source => ({ ctext: '中国哲学书电子化计划', chiuinan: '唐诗选本附注', '唐诗三百首.json': '基础选本' }[source] || source);
  const variants = (poem.variants || []).map(item => `<p>${escapeHTML(item.text)}<small class="note-source">来源：${escapeHTML(sourceName(item.source))}</small></p>`).join('');
  return section('诗意', paragraphs(poem.interpretation || []))
    + section('字词解释', entries(poem.annotations || []))
    + section('异文', variants ? `<p class="note-source">以下为选本原有校记，保留不同说法。</p>${variants}` : '')
    + section('题序', paragraphs(poem.preface?.length ? [poem.preface.join('')] : []))
    + section('原题', paragraphs(poem.sourceTitle && poem.sourceTitle !== poem.title ? [poem.sourceTitle] : []));
}

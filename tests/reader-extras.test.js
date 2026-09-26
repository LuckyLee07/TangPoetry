import test from 'node:test';
import assert from 'node:assert/strict';
import { dailyPoem, wrapCardText } from '../reader-extras.js';

test('daily poem is stable within a local calendar day and independent of catalog ordering', () => {
  const poems = Array.from({ length: 320 }, (_, order) => ({ id: `p${order}`, order }));
  const morning = new Date(2026, 8, 26, 0, 1), evening = new Date(2026, 8, 26, 23, 59);
  assert.equal(dailyPoem(poems, morning).id, dailyPoem([...poems].reverse(), evening).id);
  assert.notEqual(dailyPoem(poems, morning).id, dailyPoem(poems, new Date(2026, 8, 27)).id);
  assert.equal(dailyPoem([], morning), null);
  const seen = new Set(Array.from({ length: 320 }, (_, d) => dailyPoem(poems, new Date(2026, 0, d + 1)).id));
  assert.equal(seen.size, 320);
});

test('share wrapping preserves all text and keeps closing punctuation with a character', () => {
  const value = '独在异乡为异客，每逢佳节倍思亲。';
  const lines = wrapCardText(value, text => [...text].length * 10, 70);
  assert.equal(lines.join(''), value);
  assert(lines.every(line => [...line].length <= 7));
  assert(lines.every(line => !/^[，。]/.test(line)));
});

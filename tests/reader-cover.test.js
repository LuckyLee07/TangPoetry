import test from 'node:test';
import assert from 'node:assert/strict';
import { CoverMotionClock, coverCrop, coverRainDrop } from '../reader-cover.js';

test('drizzle stays faint and short, with streaks aligned to actual falling velocity', () => {
  for (let index = 0; index < 48; index++) {
    const drop = coverRainDrop(index, 10, 390, 844);
    assert.ok(drop.alpha >= 0 && drop.alpha <= 0.30);
    assert.ok(drop.dy > 3 && drop.dy < 9);
    const next = coverRainDrop(index, 10.001, 390, 844);
    if (Math.abs(next.y - drop.y) < 1) {
      assert.ok(Math.abs((next.x - drop.x) / (next.y - drop.y) - drop.dx / drop.dy) < 1e-6);
    }
    assert.equal(coverRainDrop(index, 0, 390, 844).alpha, 0);
  }
});

test('cover phase freezes while paused and resumes without counting time in a sheet or background', () => {
  const clock = new CoverMotionClock();
  assert.equal(clock.value(100), 0);
  clock.setRunning(true, 100);
  assert.equal(clock.value(105), 5);
  clock.setRunning(false, 105);
  assert.equal(clock.value(10000), 5);
  clock.setRunning(true, 10000);
  assert.equal(clock.value(10000), 5);
  clock.setRunning(true, 10001);
  assert.equal(clock.value(10002), 7, 'repeated lifecycle signals do not restart the phase');
  clock.setRunning(false, 10002);
  clock.setRunning(false, 10004);
  assert.equal(clock.value(10005), 7);
});

test('moving cover preserves the still poster aspect-fill crop on wide and tall viewports', () => {
  const [x, y, w, h] = coverCrop(940, 1671, 390, 844);
  assert(w < 1); assert.equal(h, 1); assert.equal(y, 0);
  assert.equal(x, (1 - w) / 2);
  const wide = coverCrop(940, 1671, 430, 600);
  assert.equal(wide[0], 0); assert.equal(wide[2], 1);
  assert.equal(wide[1], (1 - wide[3]) * 0.3);
  for (const value of [...coverCrop(940, 1671, 390, 844), ...wide]) assert(value >= 0 && value <= 1);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { createReadingIdle, createNarrationAutoplay } from '../reader-controls.js';

function clock() {
  let time = 0, nextID = 0;
  const timers = new Map();
  return {
    schedule(fn, delay) { const id = ++nextID; timers.set(id, { at: time + delay, fn }); return id; },
    unschedule(id) { timers.delete(id); },
    async advance(ms) {
      time += ms;
      for (const [id, timer] of timers) if (timer.at <= time) { timers.delete(id); await timer.fn(); }
    }
  };
}

test('reading idle resets on interaction, suspends for sheets/touch/accessibility, and rechecks eligibility', async () => {
  const timer = clock();
  let visible = true, suspended = false, hides = 0;
  const idle = createReadingIdle({ ...timer, hide: () => { visible = false; hides++; }, canHide: () => visible && !suspended });
  idle.activity();
  await timer.advance(5000);
  idle.activity();
  await timer.advance(5000);
  assert(visible);
  suspended = true;
  await timer.advance(1000);
  assert(visible, 'a newly opened sheet prevents an already scheduled hide');
  idle.activity();
  await timer.advance(20000);
  assert(visible);
  suspended = false;
  idle.activity();
  await timer.advance(6000);
  assert.equal(hides, 1);
  idle.activity(); // Page turns and compact playback are activity, not explicit reveals.
  await timer.advance(6000);
  assert.equal(visible, false);
  assert.equal(hides, 1);
  visible = true;
  idle.activity();
  idle.cancel();
  await timer.advance(10000);
  assert(visible, 'backgrounding cancels a pending hide');
});

test('one listen tap starts audio after the presentation delay and never restarts playing audio', async () => {
  const timer = clock();
  const audio = { paused: true, plays: 0, async play() { this.paused = false; this.plays++; }, pause() { this.paused = true; } };
  const auto = createNarrationAutoplay(audio, { ...timer, canPlay: () => true, blocked: assert.fail });
  auto.start();
  await timer.advance(349);
  assert.equal(audio.plays, 0);
  await timer.advance(1);
  assert.equal(audio.plays, 1);
  auto.start();
  await timer.advance(350);
  assert.equal(audio.plays, 1);
});

test('dismissal, poem changes, manual transport and browser policy cannot leave stray autoplay', async () => {
  const timer = clock();
  let current = true, errors = 0;
  const audio = { paused: true, plays: 0, async play() { this.plays++; throw Object.assign(new Error(), { name: 'NotAllowedError' }); }, pause() {} };
  const auto = createNarrationAutoplay(audio, { ...timer, canPlay: () => current, blocked: () => errors++ });
  auto.start(); auto.cancel();
  await timer.advance(1000);
  assert.equal(audio.plays, 0);
  auto.start(); current = false;
  await timer.advance(1000);
  assert.equal(audio.plays, 0);
  current = true; auto.start(); auto.manualTransport();
  await timer.advance(1000);
  assert.equal(audio.plays, 0);
  auto.start(); await timer.advance(350);
  assert.equal(errors, 1, 'autoplay rejection is handled rather than reported as playing');
});

test('closing while a media play promise is pending aborts that start, without stopping established playback', async () => {
  const timer = clock();
  let resolve, pauses = 0;
  const audio = { paused: true, play: () => new Promise(done => { resolve = done; }), pause: () => pauses++ };
  const auto = createNarrationAutoplay(audio, { ...timer, canPlay: () => true, blocked: assert.fail });
  auto.start();
  const tick = timer.advance(350);
  auto.cancel();
  assert.equal(pauses, 1);
  resolve(); await tick;
  audio.paused = false;
  auto.start(); auto.cancel();
  assert.equal(pauses, 1);
});

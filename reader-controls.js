/** One deadline at a time; modal/held-pointer/keyboard states suspend idle hiding. */
export function createReadingIdle({ hide, canHide, delay = 6000, schedule = setTimeout, unschedule = clearTimeout }) {
  let timer;
  const cancel = () => { unschedule(timer); timer = undefined; };
  const activity = () => {
    cancel();
    if (!canHide()) return;
    timer = schedule(() => { timer = undefined; if (canHide()) hide(); }, delay);
  };
  return { activity, cancel };
}

/** Cancel even a pending media play promise when its originating sheet is dismissed. */
export function createNarrationAutoplay(audio, { canPlay, blocked, delay = 350, schedule = setTimeout, unschedule = clearTimeout }) {
  let timer, pendingStart = false, revision = 0;
  function cancel() {
    revision++;
    unschedule(timer);
    timer = undefined;
    if (pendingStart) { pendingStart = false; audio.pause(); }
  }
  function start() {
    cancel();
    if (!audio.paused) return;
    const current = revision;
    timer = schedule(async () => {
      timer = undefined;
      if (!canPlay()) return;
      pendingStart = true;
      try {
        await audio.play();
      } catch (error) {
        if (revision === current && canPlay() && error.name !== 'AbortError') blocked(error);
      } finally {
        if (revision === current) pendingStart = false;
      }
    }, delay);
  }
  // Native audio controls take precedence over an unstarted timer.
  function manualTransport() { unschedule(timer); timer = undefined; }
  return { start, cancel, manualTransport };
}

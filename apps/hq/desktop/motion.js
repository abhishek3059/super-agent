// Pure motion math for the overlay, shared by overlay.js and the self-test. No DOM, no Electron.
(function (root) {
  const SIZE = 72;
  const GAP = { x: 26, y: 22 };
  const MARGIN = 8;
  const FLIP = 40; // hysteresis: the side changes only this far past the edge, so it never flickers

  /** Where the companion should sit: beside the cursor, on the side with room, inside the screen. */
  function targetFor(cursor, area, side, mode) {
    const max = { x: area.width - SIZE - MARGIN, y: area.height - SIZE - MARGIN };
    if (mode === 'park') return { point: max, side };
    const next = { ...side };
    const room = { x: area.width - MARGIN - cursor.x - GAP.x - SIZE, y: area.height - MARGIN - cursor.y - GAP.y - SIZE };
    if (room.x < 0) next.left = true;
    else if (room.x > FLIP) next.left = false;
    if (room.y < 0) next.up = true;
    else if (room.y > FLIP) next.up = false;
    const x = next.left ? cursor.x - GAP.x - SIZE : cursor.x + GAP.x;
    const y = next.up ? cursor.y - GAP.y - SIZE : cursor.y + GAP.y;
    const clamp = (v, hi) => Math.min(Math.max(v, MARGIN), hi);
    return { point: { x: clamp(x, max.x), y: clamp(y, max.y) }, side: next };
  }

  /** One step of a critically damped spring (no overshoot), stable for any dt. */
  function springStep(pos, vel, target, dt, omega = 16) {
    const out = { pos: {}, vel: {} };
    const e = Math.exp(-omega * dt);
    for (const k of ['x', 'y']) {
      const d = pos[k] - target[k];
      const c = vel[k] + omega * d;
      out.pos[k] = target[k] + (d + c * dt) * e;
      out.vel[k] = (c - omega * (d + c * dt)) * e;
    }
    return out;
  }

  /** Voice energy that rises fast and falls slowly, so the face pulses with speech instead of jittering. */
  const smoothLevel = (current, sample) => current + (sample - current) * (sample > current ? 0.5 : 0.12);

  const api = { SIZE, targetFor, springStep, smoothLevel };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Motion = api;
})(this);

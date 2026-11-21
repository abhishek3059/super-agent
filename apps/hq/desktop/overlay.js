const { targetFor, springStep, smoothLevel } = window.Motion;
const buddy = document.querySelector('.buddy');
const art = buddy.querySelector('.companion__art');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');

let area = { width: innerWidth, height: innerHeight };
let cursor = { x: area.width / 2, y: area.height / 2 };
let mode = 'follow';
let side = { left: false, up: false };
let pos = null;
let vel = { x: 0, y: 0 };
let sample = 0;
let level = 0;
let last = performance.now();

window.overlay.on((channel, value) => {
  if (channel === 'cursor') cursor = value;
  else if (channel === 'area') { area = value; pos = null; }
  else if (channel === 'mode') { mode = value; buddy.hidden = mode === 'hidden'; }
  else if (channel === 'connection') buddy.dataset.connection = value;
  else if (channel === 'companion') {
    buddy.dataset.status = value.status;
    art.dataset.look = value.skin;
    sample = value.level;
  }
});

function frame(now) {
  const dt = Math.min((now - last) / 1000, 0.1);
  last = now;
  const next = targetFor(cursor, area, side, mode);
  side = next.side;
  if (!pos || reduced.matches) { pos = next.point; vel = { x: 0, y: 0 }; }
  else ({ pos, vel } = springStep(pos, vel, next.point, dt));
  buddy.style.transform = `translate3d(${pos.x.toFixed(1)}px, ${pos.y.toFixed(1)}px, 0)`;
  level = reduced.matches ? 0 : smoothLevel(level, sample);
  buddy.style.setProperty('--level', level.toFixed(3));
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

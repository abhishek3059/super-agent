const { SIZE, targetFor, springStep, smoothLevel } = window.Motion;
const { fibonacciSphere, frame: sphereFrame } = window.Sphere;
const buddy = document.querySelector('.buddy');
const art = buddy.querySelector('.companion__art');
const canvas = buddy.querySelector('.companion__sphere');
const ctx = canvas.getContext('2d');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
const points = fibonacciSphere();

let area = { width: innerWidth, height: innerHeight };
let cursor = { x: area.width / 2, y: area.height / 2 };
let mode = 'follow';
let side = { left: false, up: false };
let pos = null;
let vel = { x: 0, y: 0 };
let sample = 0;
let level = 0;
let accent = '';
let last = performance.now();

function resize() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(SIZE * dpr);
  canvas.height = Math.round(SIZE * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
resize();

window.overlay.on((channel, value) => {
  if (channel === 'cursor') cursor = value;
  else if (channel === 'area') { area = value; pos = null; resize(); }
  else if (channel === 'mode') { mode = value; buddy.hidden = mode === 'hidden'; }
  else if (channel === 'connection') buddy.dataset.connection = value;
  else if (channel === 'companion') {
    buddy.dataset.status = value.status;
    art.dataset.look = value.skin;
    accent = '';
    sample = value.level;
  }
});

/** 520 points, the back half dimmed, the front half bright. */
function drawSphere(now, at) {
  ctx.clearRect(0, 0, SIZE, SIZE);
  if (!accent) accent = getComputedStyle(art).getPropertyValue('--companion-accent').trim() || '#39d0ff';
  const still = reduced.matches;
  const t = still ? 0 : now / 1000;
  const status = buddy.dataset.status || 'idle';
  const spin = status === 'thinking' ? 1.1 : status === 'speaking' ? 0.5 : 0.18;
  const gazeX = still ? 0 : Math.max(-0.9, Math.min(0.9, (cursor.x - at.x - SIZE / 2) / 180));
  const gazeY = still ? 0 : Math.max(-0.7, Math.min(0.7, -(cursor.y - at.y - SIZE / 2) / 180));
  const pts = sphereFrame(points, {
    yaw: gazeX + t * spin, pitch: gazeY, t,
    level: still ? 0 : level, radius: SIZE * 0.36, cx: SIZE / 2, cy: SIZE / 2,
  });
  ctx.fillStyle = accent;
  for (const p of pts) {
    ctx.globalAlpha = 0.12 + 0.88 * Math.pow((p.z + 1) / 2, 1.6);
    ctx.beginPath();
    ctx.arc(p.x, p.y, 1.05, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

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
  if (mode !== 'hidden') drawSphere(now, pos);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

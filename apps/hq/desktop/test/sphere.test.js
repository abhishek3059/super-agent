const test = require('node:test');
const assert = require('node:assert/strict');
const { COUNT, fibonacciSphere, rotate, wave, frame } = require('../sphere.js');

const close = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} != ${b}`);

test('the sphere has 520 points, each on the unit sphere', () => {
  const points = fibonacciSphere();
  assert.equal(points.length, COUNT);
  for (const p of points) close(Math.hypot(p.x, p.y, p.z), 1);
});

test('the spiral is deterministic and starts at the north pole', () => {
  const a = fibonacciSphere();
  const b = fibonacciSphere();
  assert.deepEqual(a[0], b[0]);
  close(a[0].y, 1 - 1 / COUNT);
  close(a[COUNT - 1].y, -1 + 1 / COUNT);
});

test('rotation keeps a unit vector a unit vector', () => {
  const r = rotate(fibonacciSphere()[7], 1.3, -0.4);
  close(Math.hypot(r.x, r.y, r.z), 1);
});

test('the ripple stays between -1 and 1', () => {
  for (const p of fibonacciSphere()) for (const t of [0, 0.7, 2.1, 9.5]) {
    const w = wave(p, t);
    assert.ok(w >= -1 && w <= 1);
  }
});

test('a silent frame is a plain projection at the given radius', () => {
  const p = fibonacciSphere()[0];
  const [out] = frame([p], { radius: 30, cx: 36, cy: 36 });
  close(out.x, 36 + p.x * 30);
  close(out.y, 36 + p.y * 30);
  close(out.z, p.z);
});

test('voice energy moves the surface outward and inward', () => {
  const points = fibonacciSphere();
  const quiet = frame(points, { radius: 30, cx: 36, cy: 36, t: 0, level: 0 });
  const loud = frame(points, { radius: 30, cx: 36, cy: 36, t: 0, level: 1 });
  const moved = loud.some((p, i) => Math.hypot(p.x - quiet[i].x, p.y - quiet[i].y) > 0.01);
  assert.ok(moved);
  assert.ok(loud.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y)));
});

test('zero radius collapses the sphere to its centre', () => {
  const out = frame(fibonacciSphere(8), { radius: 0, cx: 10, cy: 20, level: 1, t: 3 });
  assert.ok(out.every((p) => p.x === 10 && p.y === 20));
});

const assert = require('node:assert/strict');
const { test } = require('node:test');
const { SIZE, targetFor, springStep, smoothLevel } = require('../motion.js');

const area = { width: 1440, height: 900 };
const right = { left: false, up: false };

test('sits beside the cursor and stays on screen at every edge', () => {
  assert.deepEqual(targetFor({ x: 400, y: 300 }, area, right, 'follow').point, { x: 426, y: 322 });
  for (const cursor of [{ x: 0, y: 0 }, { x: 1440, y: 900 }, { x: 1440, y: 0 }, { x: 0, y: 900 }, { x: -50, y: 2000 }]) {
    const { point } = targetFor(cursor, area, right, 'follow');
    assert.ok(point.x >= 8 && point.x + SIZE <= area.width - 8, JSON.stringify(cursor));
    assert.ok(point.y >= 8 && point.y + SIZE <= area.height - 8, JSON.stringify(cursor));
  }
});

test('flips away from an edge and does not flip back until well clear of it', () => {
  const flipped = targetFor({ x: 1400, y: 300 }, area, right, 'follow').side;
  assert.equal(flipped.left, true);
  assert.equal(targetFor({ x: 1330, y: 300 }, area, flipped, 'follow').side.left, true, 'hysteresis holds near the edge');
  assert.equal(targetFor({ x: 600, y: 300 }, area, flipped, 'follow').side.left, false);
});

test('park goes to the corner whatever the cursor does', () => {
  assert.deepEqual(targetFor({ x: 10, y: 10 }, area, right, 'park').point, { x: 1440 - SIZE - 8, y: 900 - SIZE - 8 });
});

test('the spring settles on the target without overshoot, even with a long frame', () => {
  let s = { pos: { x: 0, y: 0 }, vel: { x: 0, y: 0 } };
  let max = 0;
  for (let i = 0; i < 120; i++) { s = springStep(s.pos, s.vel, { x: 100, y: 50 }, i === 5 ? 0.5 : 1 / 60); max = Math.max(max, s.pos.x); }
  assert.ok(max <= 100 + 1e-9, `overshoot ${max}`);
  assert.ok(Math.abs(s.pos.x - 100) < 0.01 && Math.abs(s.pos.y - 50) < 0.01);
});

test('voice energy rises faster than it falls', () => {
  assert.ok(smoothLevel(0, 1) > 1 - smoothLevel(1, 0));
});

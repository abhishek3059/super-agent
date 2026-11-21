import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseSketch, SKETCH_INSTRUCTIONS } from '../src/sketch.js';

const example = {
  title: 'From input to output',
  steps: [
    { heading: 'Take input', detail: '<img src="https://example.invalid" />' },
    { heading: 'Produce output', detail: '**Literal text**' },
  ],
};
const fence = (value: unknown) => '```jarvis-sketch\n' + JSON.stringify(value) + '\n```';

test('Sketch instructions contain a valid, self-contained example', () => {
  const start = SKETCH_INSTRUCTIONS.indexOf('```jarvis-sketch\n');
  assert.notEqual(start, -1);
  const end = SKETCH_INSTRUCTIONS.indexOf('\n```', start);
  assert.notEqual(end, -1);
  assert.equal(parseSketch(SKETCH_INSTRUCTIONS.slice(start, end + 4))?.steps.length, 2);
});

test('Sketch accepts complete fences and keeps field contents as literal text', () => {
  assert.deepEqual(parseSketch(fence(example)), example);
  assert.deepEqual(parseSketch(' \n' + fence(example).replaceAll('\n', '\r\n') + '\n'), example);
});

test('Sketch refuses incomplete, mixed or malformed fences', () => {
  const valid = fence(example);
  for (const value of [
    valid.slice(0, -3), valid.slice(0, -1), valid.replace('jarvis-sketch', 'json'),
    'Before\n' + valid, valid + '\nAfter', valid + '\n' + valid,
    valid.replace('{', '['), valid.replace('\n', '\n' + ' '.repeat(8192)),
  ]) assert.equal(parseSketch(value), null);
});

test('Sketch refuses unexpected fields, invalid text and out-of-bounds steps', () => {
  for (const value of [
    { ...example, title: ' ' }, { ...example, title: 'x'.repeat(101) },
    { ...example, url: 'https://example.invalid' },
    { ...example, steps: example.steps.slice(0, 1) }, { ...example, steps: Array(6).fill(example.steps[0]) },
    { ...example, steps: [example.steps[0], { heading: 'x'.repeat(81), detail: 'Text' }] },
    { ...example, steps: [example.steps[0], { heading: 'Heading', detail: 'x'.repeat(401) }] },
    { ...example, steps: [example.steps[0], { heading: 'Heading', detail: 1 }] },
    { ...example, steps: [example.steps[0], { heading: 'Heading', detail: 'A\nB' }] },
    { ...example, steps: [example.steps[0], { ...example.steps[1], action: 'open' }] },
  ]) assert.equal(parseSketch(fence(value)), null);
});

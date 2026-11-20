// Self-checks for the desktop, the browser bar's address handling and provider sign-in parsing.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

process.env.HQ_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-test-'));
const seed = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-seed-'));
process.env.HERMES_HOME_PRIMARY = seed;
const { addressToUrl, desktopHtml } = await import('../src/computer.js');
const { parseLoginOutput, saveAnthropicKey } = await import('../src/signin.js');
const { env } = await import('../src/env.js');
const { withCredentials } = await import('../src/engine.js');

test('the address bar opens only http(s); anything else is a search', () => {
  assert.equal(addressToUrl('example.com'), 'https://example.com/');
  assert.equal(addressToUrl('http://example.com/a?b=1'), 'http://example.com/a?b=1');
  assert.equal(addressToUrl('localhost:3000'), 'https://localhost:3000/');
  for (const s of ['weather today', 'weather', 'javascript:alert(1)', 'file:///etc/passwd', 'data:text/html,x', 'chrome://settings']) {
    assert.ok(addressToUrl(s).startsWith('https://www.google.com/search?q='), s);
  }
});

test('the desktop escapes names', () => {
  const h = desktopHtml({ owner: '<img src=x onerror=1>', name: 'A"b', label: '', filesUrl: 'file:///tmp/x/' });
  assert.ok(!h.includes('<img src=x'));
  assert.ok(!h.includes('A"b'));
});

test('sign-in output gives the OpenAI link and code, and nothing else', () => {
  const browser = parseLoginOutput('Open this URL to authorize Hermes:\n  https://auth.openai.com/oauth/authorize?x=1\n');
  assert.equal(browser.url, 'https://auth.openai.com/oauth/authorize?x=1');
  const device = parseLoginOutput('  1. Open this URL in your browser:\n     \x1b[94mhttps://auth.openai.com/codex/device\x1b[0m\n\n  2. Enter this code:\n     \x1b[94mABCD-12345\x1b[0m\n');
  assert.deepEqual(device, { url: 'https://auth.openai.com/codex/device', code: 'ABCD-12345' });
  assert.equal(parseLoginOutput('see https://evil.example/login').url, null);
});

test('a provider signed in from HQ is passed to bots; unknown keys are not', () => {
  const got = withCredentials(new Set(), { providers: { 'openai-codex': {} } }, { ANTHROPIC_API_KEY: 'k', OTHER_KEY: 'x' });
  assert.deepEqual([...got].sort(), ['anthropic', 'openai-codex']);
  assert.equal(withCredentials(new Set(), null, {}).size, 0);
});

test('saving the Claude key keeps every other line of the seed .env', () => {
  const file = path.join(seed, '.env');
  fs.writeFileSync(file, 'NVIDIA_API_KEY=n\n\n# note\nANTHROPIC_API_KEY=sk-ant-old-aaaaaaaaaaaaaaaaaaaa\n');
  saveAnthropicKey('sk-ant-new-bbbbbbbbbbbbbbbbbbbbbbbb');
  assert.equal(fs.readFileSync(file, 'utf8'), 'NVIDIA_API_KEY=n\n\n# note\nANTHROPIC_API_KEY=sk-ant-new-bbbbbbbbbbbbbbbbbbbbbbbb\n');
  assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  assert.throws(() => saveAnthropicKey('not-a-key'));
});

test('a seed .env that is a link is never rewritten', () => {
  const file = path.join(seed, '.env');
  const target = path.join(seed, 'real.env');
  fs.writeFileSync(target, 'KEEP=1\n');
  fs.rmSync(file, { force: true });
  fs.symlinkSync(target, file);
  assert.throws(() => saveAnthropicKey('sk-ant-new-bbbbbbbbbbbbbbbbbbbbbbbb'), /nothing was changed/);
  assert.equal(fs.readFileSync(target, 'utf8'), 'KEEP=1\n');
  assert.ok(fs.lstatSync(file).isSymbolicLink());
});

test('without a dedicated seed, HQ neither signs in nor saves keys', () => {
  env.dedicatedSeed = false;
  try { assert.throws(() => saveAnthropicKey('sk-ant-new-bbbbbbbbbbbbbbbbbbbbbbbb'), /HERMES_HOME_PRIMARY/); }
  finally { env.dedicatedSeed = true; }
});

test("the operator's own ~/.hermes is never a dedicated seed, however it is spelled", async () => {
  const { isDedicatedSeed } = await import('../src/env.js');
  const own = path.join(os.homedir(), '.hermes');
  for (const p of [undefined, '', own, own + '/', path.join(os.homedir(), 'x', '..', '.hermes')]) assert.equal(isDedicatedSeed(p), false, String(p));
  assert.equal(isDedicatedSeed(seed), true);
});

// Self-checks for what a bot may read on the operator's Mac and the fixed system_info tool.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

process.env.HQ_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-test-'));
const { readDirs, safeDirs, skillDirs, skillReadDirs } = await import('../src/access.js');
const { systemInfo } = await import('../src/sysinfo.js');
const { env } = await import('../src/env.js');
const home = os.homedir();

test('secret and HQ folders are never readable, even when listed', () => {
  const tmp = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'hq-read-')));
  const got = safeDirs([tmp, '~', '/', '/Users', '~/.ssh', '~/Library', '~/.hermes', '~/.claude', '~/.claude/projects', env.dataDir, 'relative/path', '/no/such/dir']);
  assert.deepEqual(got, [tmp]);
});

test('a folder that contains a secret folder is refused', () => {
  // The temp root holds HQ's data folder in this test, so opening it would open HQ's state.
  assert.deepEqual(safeDirs([path.dirname(fs.realpathSync(env.dataDir))]), []);
});

test('linked skills are readable where they really live, secrets still are not', () => {
  const skills = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'hq-skills-')));
  const real = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'hq-skill-real-')));
  fs.symlinkSync(real, path.join(skills, 'linked'));
  fs.symlinkSync(path.join(home, '.ssh'), path.join(skills, 'sneaky'));
  fs.symlinkSync(path.join(home, '.claude'), path.join(skills, 'transcripts'));
  fs.mkdirSync(path.join(skills, 'locked'), { mode: 0o000 });
  const got = skillReadDirs([skills]);
  assert.ok(got.includes(skills) && got.includes(real));
  assert.ok(!got.some((d) => d.startsWith(path.join(home, '.ssh')) || d === path.join(home, '.claude')));
  fs.chmodSync(path.join(skills, 'locked'), 0o700);
});

test('operator read and skill mounts are macOS-only', (t) => {
  const folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'hq-opt-in-')));
  t.after(() => {
    delete process.env.HQ_READ_DIRS;
    delete process.env.HQ_SKILL_DIRS;
    fs.rmSync(folder, { recursive: true });
  });
  process.env.HQ_READ_DIRS = folder;
  process.env.HQ_SKILL_DIRS = folder;
  const expected = process.platform === 'darwin' ? [folder] : [];
  assert.deepEqual(readDirs(), expected);
  assert.deepEqual(skillDirs(), expected);
});

test('system_info answers only its fixed topics', async () => {
  assert.match(await systemInfo('rm -rf /'), /^Unknown topic/);
  if (process.platform === 'darwin') assert.match(await systemInfo('processes'), /PID/); // the topics are macOS commands
});

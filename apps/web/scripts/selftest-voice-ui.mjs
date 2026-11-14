import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const sourcePath = fileURLToPath(new URL('../src/app/voice-ui-state.ts', import.meta.url));
const { outputText } = ts.transpileModule(await readFile(sourcePath, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});

const base = path.join(os.tmpdir(), 'opencode');
await mkdir(base, { recursive: true });
const workdir = await mkdtemp(path.join(base, 'voice-ui-'));
const compiled = path.join(workdir, 'voice-ui-state.cjs');
await writeFile(compiled, outputText);
const require = createRequire(import.meta.url);
const ui = require(compiled);
await rm(workdir, { recursive: true, force: true });

let cases = 0;
function equal(actual, expected) {
  assert.equal(actual, expected);
  cases += 1;
}

equal(ui.statusLabel('stopped'), 'Disconnected');
equal(ui.statusLabel('connecting'), 'Connecting');
equal(ui.statusLabel('listening'), 'Listening');
equal(ui.statusLabel('speaking'), 'Local echo');
equal(ui.statusLabel('speaking', 'local'), 'Speaking');
equal(ui.statusLabel('listening', 'local'), 'Listening');
equal(ui.pipelineSummary('speaking', 'local'), 'Playing the local reply');
equal(ui.pipelineSummary('speaking', 'fake'), 'Playing the local echo');
equal(ui.statusLabel('muted'), 'Muted');
equal(ui.statusLabel('error'), 'Needs attention');
equal(ui.statusLabel('thinking'), 'Thinking');
equal(ui.statusLabel('unexpected'), 'Unavailable');
equal(ui.pipelineSummary('stopped'), 'Ready for a local session');
equal(ui.pipelineSummary('connecting'), 'Authenticating on loopback');
equal(ui.pipelineSummary('speaking'), 'Playing the local echo');
equal(ui.pipelineSummary('unexpected'), 'Local voice path');
equal(ui.isSessionActive('stopped'), false);
equal(ui.isSessionActive('error'), false);
equal(ui.isSessionActive('connecting'), true);
equal(ui.isSessionActive('listening'), true);
equal(ui.isSessionReady('connecting'), false);
equal(ui.isSessionReady('muted'), true);
equal(ui.isSessionReady('thinking'), true);
equal(ui.isSessionActive('thinking'), true);
equal(ui.pipelineSummary('thinking'), 'Working on a reply locally');
equal(ui.formatElapsed(0), '00:00.0');
equal(ui.formatElapsed(61_234), '01:01.2');
equal(ui.spectrumBarHeight('stopped', 1, 0.5), 9.5);
equal(ui.spectrumBarHeight('connecting', 0, 0.5), 18);
equal(ui.spectrumBarHeight('speaking', 0, 0.5), 57);
equal(ui.spectrumBarHeight('listening', 0, 0.5), 8);
equal(ui.spectrumBarHeight('listening', 1, 0.5), 50);

equal(ui.statusLabel('speaking', 'gemini-live'), 'Speaking');
equal(ui.pipelineSummary('speaking', 'gemini-live'), 'Playing the Gemini reply');
equal(ui.providerCopy('fake').badge, 'Fake echo adapter');
equal(ui.providerCopy('local').privacy, 'Local model active. Microphone audio stays local.');
equal(ui.providerCopy('gemini-live').tag, 'Cloud');
equal(ui.providerCopy('gemini-live').badge, 'Gemini Live (cloud)');
for (const p of ['gemini-live', '', 'unknown']) {
  const text = JSON.stringify(ui.providerCopy(p)).toLowerCase();
  equal(text.includes('stays local') || text.includes('stays on this device'), false);
  equal(text.includes('local only'), false);
}
for (const p of ['', 'unknown']) equal(JSON.stringify(ui.providerCopy(p)).toLowerCase().includes('fake'), false);
equal(ui.providerCopy('').badge, 'Not connected');

console.log(`voice-ui state self-test: PASS (${cases} cases)`);

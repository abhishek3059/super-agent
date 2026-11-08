// Source-level self-test for PlaybackEpochTracker with no test framework.
// The TypeScript tracker is transpiled with the pinned `typescript` package
// and executed in Node; all cases are synchronous and deterministic.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { mkdir, mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const sourcePath = fileURLToPath(new URL('../src/app/playback-epoch.ts', import.meta.url));
const { outputText } = ts.transpileModule(await readFile(sourcePath, 'utf8'), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});

const base = path.join(os.tmpdir(), 'opencode');
await mkdir(base, { recursive: true });
const workdir = await mkdtemp(path.join(base, 'epoch-'));
const compiled = path.join(workdir, 'playback-epoch.cjs');
await writeFile(compiled, outputText);
const require = createRequire(import.meta.url);
const { PlaybackEpochTracker } = require(compiled);
await rm(workdir, { recursive: true, force: true });

const fresh = () => new PlaybackEpochTracker();

// A tagged chunk for the current epoch plays.
let tracker = fresh();
tracker.onReady(0);
tracker.onChunkMeta(0);
assert.equal(tracker.acceptBinary(), true);

// Untagged binary is dropped.
tracker = fresh();
tracker.onReady(0);
assert.equal(tracker.acceptBinary(), false);

// Chunk metadata without an epoch number is treated as untagged.
tracker = fresh();
tracker.onReady(0);
tracker.onChunkMeta(undefined);
assert.equal(tracker.acceptBinary(), false);

// Old-epoch audio queued before a local interrupt cannot resume.
tracker = fresh();
tracker.onReady(0);
tracker.onChunkMeta(0);
tracker.onLocalInterrupt();
assert.equal(tracker.acceptBinary(), false);
assert.equal(tracker.currentEpoch, 0);

// The server interrupt acknowledges the new epoch; matching audio plays and
// the stale epoch does not.
tracker.onServerInterrupt(1);
assert.equal(tracker.currentEpoch, 1);
tracker.onChunkMeta(1);
assert.equal(tracker.acceptBinary(), true);
tracker.onChunkMeta(0);
assert.equal(tracker.acceptBinary(), false);

// A turn completes only for its own epoch.
tracker = fresh();
tracker.onReady(1);
tracker.onLocalInterrupt();
tracker.onTurnComplete(2);
assert.equal(tracker.currentEpoch, 2);
assert.equal(tracker.acceptBinary(), false); // no chunk tag since interrupt
tracker.onChunkMeta(2);
assert.equal(tracker.acceptBinary(), true);

// A ready epoch later than the local view is adopted.
tracker = fresh();
tracker.onReady(5);
assert.equal(tracker.currentEpoch, 5);

// Two rapid local interrupts remain pending until both are acknowledged.
tracker = fresh();
tracker.onReady(0);
tracker.onLocalInterrupt();
tracker.onLocalInterrupt();
tracker.onServerInterrupt(1);
tracker.onChunkMeta(1);
assert.equal(tracker.acceptBinary(), false);
tracker.onTurnComplete(1);
tracker.onChunkMeta(1);
assert.equal(tracker.acceptBinary(), false);
tracker.onServerInterrupt(2);
tracker.onChunkMeta(2);
assert.equal(tracker.acceptBinary(), true);

console.log('playback-epoch self-test: PASS (8 cases)');

# R-01.3 macOS offline evidence

| Field | Value |
| --- | --- |
| Roadmap item | R-01.3 [human], Mac offline checks run with real output recorded |
| Date | 2026-11-10 (run at 15:43 UTC) |
| Owner | `jeevesh2515` |
| Run by | An AI agent on Jeevesh's Mac (Claude Code, model `claude-opus-5-5`, as reported by the agent), following the [R-01.3 handover](../implementation/r01-3-macos-handover.md) |
| Tested commit | `4f51e0035ea9d42b827b7626a4792cbc4d351891` (PR [#24](https://github.com/abhishek3059/super-agent/pull/24) head at run time) |
| Result | **PASS**, `overall_exit=0` |
| Full output | [r01-3-macos-output-20261110T154316Z.txt](../implementation/evidence/r01-3-macos-output-20261110T154316Z.txt) |
| Roadmap tick | Not ticked here. The handover reserves the tick for the PH-01 owner. |

## Platform

| Item | Value |
| --- | --- |
| OS | macOS 27.2 (build 26B123), Apple Silicon (`arm64`) |
| Python for the test venv | 3.12.13 (`/opt/homebrew/bin/python3.12`, per the output's `note=` line) |
| Node / npm | v22.22.3 / 10.9.8 |

## Results

| Step | Result | Evidence in the output |
| --- | --- | --- |
| Clean-tree check | PASS | `## develop...origin/develop`, no changes |
| Check out exact PR #24 head | PASS | `tested_commit=4f51e00...` |
| Locked Python install (`--only-binary=:all:`) | PASS | 24 packages installed from `apps/api/requirements.lock` |
| Backend tests | PASS | `11 passed in 0.97s` |
| Frontend locked install | PASS | `added 244 packages`, `found 0 vulnerabilities` |
| Frontend dependency audit | PASS | `found 0 vulnerabilities` |
| Playback epoch self-test | PASS | `PASS (8 cases)` |
| Frontend production build | PASS | `Application bundle generation complete` |
| Repository checks | PASS | `"errors": 0`, `roadmap self-test: all checks passed` |
| Overall | PASS | `overall_exit=0` |

## Deviations from the handover

1. **Python 3.12 was named explicitly in the main run.** The handover runs
   `python3`, but on this Mac `python3` is 3.14.5. The run used `/opt/homebrew/bin/python3.12`,
   which matches the hosted CI baseline (Python 3.12). The run added a `note=`
   line as the second line of the output to record this; it is not command
   output.
2. **The committed copy of the output is redacted.** It was produced with
   `sed`, replacing the home directory with `~` and the macOS temporary folder
   with `$TMPDIR`. A `diff` of the redacted original against the committed file
   showed no other difference. That check ran on 2026-11-10 in the agent's
   session; its output was not saved.

Apart from these two deviations, the steps followed the handover's run
procedure in a clean tree against the detached PR head, with no edits to code
or lock files. The output file shows each step's section header and result, not
the commands themselves; the commands are in the handover.

## Supplementary run on Python 3.14 (2026-11-10, 16:00 UTC)

PR [#26](https://github.com/abhishek3059/super-agent/pull/26) proposes moving
hosted voice CI from Python 3.12 to 3.14. To keep this Mac evidence comparable
with that baseline, the backend part was rerun on the Mac's default Python
3.14.5 against the same commit `4f51e00`, in a separate detached worktree:

| Step | Result | Evidence in the output |
| --- | --- | --- |
| Locked Python install (`--only-binary=:all:`) | PASS | cp314 wheels; `fastapi==0.162.0`, `pydantic_core==2.50.1`, `uvicorn==0.54.0`, `websockets==17.3` |
| Backend tests | PASS | `11 passed in 0.76s` |
| Overall | PASS | `overall_exit=0` |

Full output: [r01-3-macos-py314-output-20261110T160044Z.txt](../implementation/evidence/r01-3-macos-py314-output-20261110T160044Z.txt).
The frontend steps do not depend on Python and were not repeated. A first
attempt at this rerun ran the same tests (11 passed) but did not capture the exit
code because of a shell difference; that file was deleted and the run repeated
under `bash`.

## What was not used

No API key was read, printed, or tested. No microphone, audio, provider call,
or personal data was used. No `.env` file was created.

## Owner confirmation

On 2026-11-10 `jeevesh2515` confirmed in chat, in these words, after reading
the results above:

> I, `jeevesh2515`, confirm that the attached R-01.3 output was produced on my
> Mac against the stated commit. No key, microphone, audio, or personal data
> was used. The reported result is accurate.

Recorded by the same agent at his instruction. This confirms R-01.3 only. It
closes no other roadmap item or gate, and it does not tick the roadmap.

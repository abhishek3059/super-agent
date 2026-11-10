# Voice-foundation scaffold implementation record

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Design | [Voice-foundation design](../design/voice-foundation.md) |
| Review | [Initial review and correction disposition](../reviews/voice-foundation-scaffold.md) |
| Delivery | Design PR #12 merged; implementation PR #13 merged into `develop` and also carries the later maintainer-confirmation record |
| Status | Offline scaffold merged in PR #13. Hosted voice workflow green on Windows and macOS. Microphone observations are partial and inconclusive; manual macOS evidence is pending. No Gemini adapter. RT-G00 is resolved; RT-G01 remains open. |

## Implemented scope

- FastAPI loopback backend with strict Host and Origin checks.
- First-message high-entropy token authentication using constant-time comparison.
- Typed control categories, binary bounded PCM frames, mute, interruption epoch,
  deterministic fake audio adapter, fixed error categories, and cleanup.
- Angular active-session UI with local token input, visible state, manual start,
  microphone permission, mute, interrupt, stop, PCM conversion, and playback.
- Offline backend tests and exact Python and npm lock files.

There is no Gemini adapter, provider call, persistent memory, tool, MCP,
subagent, shell, research, telephony, or external action in this increment.

## Dependency disposition

Python direct and transitive packages are exact-pinned. Six transitive packages
initially resolved to releases newer than 14 days; compatible older versions
were constrained before the final lock.

`@angular/build@22.2.3` failed `npm audit` with one high-severity Vite chain.
The scaffold explicitly moves only the builder to `22.2.6`, despite its recent
release, under the repository's security-fix exception. Its exact transitive
graph is locked. The final npm audit reports zero vulnerabilities. No audit
finding was suppressed and `npm audit fix --force` was not used.

License metadata was inspected for every locked package. Python packages use
MIT, BSD, Apache-2.0, PSF-2.0, or dual Apache/BSD terms; Colorama's PyPI page
confirms BSD-3-Clause despite missing license-expression metadata. npm packages
are predominantly permissive; `lightningcss` is MPL-2.0 and `caniuse-lite`
data is CC-BY-4.0. No non-commercial or custom license was found. This is
metadata review, not independent legal advice.

## Evidence status

Windows backend tests, Angular build, dependency audits, repository checks, and
manual browser behavior are recorded only after execution. macOS and personal
microphone evidence remain pending. No cloud test is authorized here.

| Check | Result |
| --- | --- |
| Python runtime | Windows Python 3.14.4; hosted CI runs Python 3.14 since 2026-11-10 (the earlier 3.12 design target in [revision 1](../design/voice-foundation-revision-1.md) is superseded for hosted CI) |
| Backend tests | PASS, 11 tests, exit 0 |
| Backend compile check | PASS, exit 0 |
| Uvicorn factory and loopback health | PASS on `127.0.0.1:8000`, fake provider |
| Python dependency audit | PASS, no known vulnerabilities |
| Frontend locked install | PASS, 243 packages installed with scripts disabled, 244 audited |
| Frontend dependency audit | PASS, 0 vulnerabilities |
| Playback epoch self-test | PASS, 8 cases, exit 0 |
| Angular production build | PASS, 112.89 kB initial output, exit 0 |
| Angular development build | PASS, 1.11 MB initial output, exit 0 |
| Documented `npm start` path | PASS, HTTP 200 on `127.0.0.1:4200`; process tree and listener removed |
| Root dependency audit | PASS, 0 vulnerabilities |
| Repository check | PASS, 143 files scanned, 896 local links, 258 fragments, 0 errors |
| Manual microphone/browser test | Operator reported partial observations on 2026-11-10; not an acceptance PASS. See [observation record](r01-4-microphone-observations.md). |
| Gemini/provider test | Not run and not included |
| Manual macOS execution | Not run; Jeevesh accepted the task. Hosted macOS CI passed. |

## Current status (2026-11-10)

- Hosted voice workflow: **green** on Windows and macOS (PR #14; rerun on PR #21).
- Manual microphone/browser test: **partial and inconclusive**. The operator
  reported `speaking` while silent and working buttons, but did not confirm
  microphone input or conversational barge-in. See the
  [observation record and unapproved next-step proposal](r01-4-microphone-observations.md).
- Manual macOS execution: **not run**; Jeevesh accepted the task.
- Gemini Live adapter: **not implemented** (R-01.7).
- Opt-in synthetic live command and test: **not implemented and not run** (R-01.8, R-01.9).
- Repository check: **pass** on PR #21; see the PR checks for current counts.
- Runtime gate: RT-G00 is resolved for the bounded PH-01 scope. RT-G01 and all
  later gates remain open.

## Reviewer correction set

The focused `reviewer-free` pass returned FAIL on the initial commit. The
correction set adds a working Angular development configuration, current-epoch
binary acceptance with stale and rapid-interrupt tests, one-session admission,
15-minute total and 60-second idle limits, Host validation on `/health`, honest
microphone errors, disabled audio tracks while muted, and removal of unused
`zone.js`. These fixes are locally verified but not independently re-reviewed.

## Known implementation deviations and limits

- Development uses Angular on `127.0.0.1:4200` and FastAPI on port 8000 with an
  exact Origin allowlist. Serving built assets from one production origin is
  not implemented.
- Local development uses `ws://` on loopback. Remote deployment and TLS are out
  of scope.
- Authentication is a first `session.auth` control message and audio uses
  bounded binary frames preceded by epoch metadata. This differs in naming
  from the conceptual design but retains the same security and lifecycle intent.
- Mute sets every microphone track `enabled=false` and drops processor frames.
  The track remains allocated for unmute, so a browser or OS indicator may stay
  visible even though no microphone frame crosses the browser boundary.
- The new key-free Windows/macOS workflow cannot provide PR evidence until the
  workflow exists on the target branch. Its first `develop` run failed before
  creating jobs because the plain YAML command contained an unquoted trailing
  colon. A focused workflow correction quotes that command; the rerun result is
  recorded separately. Existing repository and Windows spike checks passed.

The corrected workflow then ran: macOS passed, while Windows exposed a timing
classification race in the total-duration test. The total deadline fired, but
the post-timeout clock comparison labeled it as idle timeout. The backend now
selects the fixed category before awaiting, avoiding platform clock jitter.
PR #14 merged the correction. The workflow then passed on both Windows and
macOS on `develop` (run 42574431372) and on PR #21.

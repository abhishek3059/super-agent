# Voice-foundation scaffold implementation record

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Design | [Voice-foundation design](../design/voice-foundation.md) |
| Review | [Initial review and correction disposition](../reviews/voice-foundation-scaffold.md) |
| Delivery | Design PR #12 merged; implementation PR #13 targets `develop` and also carries the later maintainer-confirmation record |
| Status | Reviewer correction set complete locally on Windows; hosted voice workflow, macOS, and manual microphone evidence pending. No runtime gate accepted. |

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
| Python runtime | Windows Python 3.14.4; design target Python 3.12 remains for hosted CI |
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
| Manual microphone/browser test | Not run |
| Gemini/provider test | Not run and not included |
| macOS execution | Not run; Jeevesh pending |

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
  workflow exists on the target branch. Existing repository and Windows spike
  checks are separate evidence.

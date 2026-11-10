# Voice foundation: signed implementation design

| Field | Value |
| --- | --- |
| Date / revision | 2026-11-08 / 1 |
| Author | OpenCode, `agentrouter/gpt-5.6-sol` |
| Status | Signed proposal for review. No scaffold, dependency installation, provider call, microphone transmission, or runtime approval. |
| Product context | [Personal-agent architecture](../product/personal-agent-architecture.md) |
| Maintainer confirmation | [Decision record](../approvals/voice-foundation-confirmation.md) |
| Runtime gate | RT-G00 remains open; [RT-001](../../tasks/001-runtime-consent-and-feasibility.md) is `in progress`. |

> **Implementation status (2026-11-09):** The offline scaffold is merged
> (PR #13) and the hosted voice workflow is green on Windows and macOS
> (PR #14). RT-001 is `in progress`; RT-G00 remains open. The Gemini Live
> adapter and the opt-in synthetic live test are **not implemented**
> (R-01.7 to R-01.9). The sections below are the 2026-11-08 signed design;
> see the [implementation record](../implementation/voice-foundation-scaffold.md)
> for current state.

## 1. Objective

Build the smallest voice-to-voice foundation for the personal-agent platform.
During a manually started browser session, the user can speak continuously,
mute locally, hear streamed model audio, interrupt playback by speaking, and
stop the session.

The first provider adapter is proposed for Gemini Live. Automated tests use a
deterministic fake adapter. A live provider test sends generated synthetic PCM
only. Personal microphone audio is tested locally and is never transmitted to
a cloud provider in this development cycle.

## 2. Recorded operator decisions

| Topic | Decision |
| --- | --- |
| Stack | Python FastAPI backend and Angular browser client. |
| Hosts | Windows and macOS. Jeevesh runs and records Mac-only evidence. |
| Interaction | Manual start, visible active-session listening, local mute, barge-in, and stop. No wake word or background OS listening. |
| Provider | Gemini Live candidate behind a replaceable adapter. No model weights. |
| Secrets | Process environment only. No project `.env` file and no browser key. |
| Data | Synthetic audio may reach Gemini. Personal microphone audio stays local. |
| Budget | Hard $0 development cap; no billable fallback. |
| Memory | Interface seam only; no persistent transcript, embedding, preference, or habit extraction. |
| Actions | No tools, MCP, research, subagents, shell, calls, bookings, messages, or computer control. |

## 3. Provider disposition

Gemini Live is the proposed first adapter because its official documentation
describes bidirectional audio, continuous streaming, barge-in, Python/server
WebSockets, 16 kHz PCM input, and 24 kHz PCM output. The official pricing page
lists the Live models on a free tier and states that free-tier content is used
to improve Google products. Therefore only generated synthetic audio may be
sent during development.

OpenAI Realtime supports the required interaction but is priced usage, so it
does not fit the current $0 gate. Anthropic documents current Claude models as
text/image input and text output; a Claude key is not a native speech-to-speech
adapter. Both remain future candidates.

Sources checked 2026-11-08:

- <https://ai.google.dev/gemini-api/docs/live-api>
- <https://ai.google.dev/gemini-api/docs/live-api/get-started-websocket>
- <https://ai.google.dev/gemini-api/docs/pricing>
- <https://platform.openai.com/docs/guides/realtime>
- <https://docs.anthropic.com/en/docs/about-claude/models/overview>

Actual account eligibility, region, key access, model availability, quota, and
terms acceptance are unverified. Any failed check keeps live testing disabled.

## 4. Scope and non-goals

The slice includes an authenticated loopback application, browser audio
capture/playback, typed session events, fake and Gemini adapters, local mute,
barge-in, cleanup, and offline tests.

It excludes persistent memory, tools, arbitrary shell, personal cloud data,
external effects, wake words, locked-screen use, background listening, mobile,
deployment, and production hosting. It is not the general assistant yet.

## 5. Proposed architecture

```text
Angular browser
  microphone, local PCM conversion, mute, playback epoch, status
        |
        | authenticated same-origin WebSocket
        v
FastAPI loopback backend
  session state, bounds, origin/host/auth checks, provider selection
        |
        +--> deterministic fake adapter (CI and local tests)
        |
        +--> Gemini Live adapter (explicit synthetic test only)
```

The backend binds only to `127.0.0.1`. It serves the built Angular assets from
one origin and rejects other Host and Origin values. A high-entropy local token
is established outside browser storage and expires with the process. The
provider key remains backend-only in `GEMINI_API_KEY`; startup and errors never
print it.

The browser captures audio only after user activation and permission. Mute
stops local capture and discards unsent buffers. Barge-in advances a playback
epoch, stops queued output locally, and signals interruption to the adapter.
Old output for an earlier epoch is dropped. Stop closes microphone tracks,
audio nodes, browser/backend WebSockets, provider sessions, timers, and buffers.

## 6. Protocol and limits

Client events: `session.start`, `audio.chunk`, `capture.mute`,
`capture.unmute`, `playback.interrupt`, and `session.stop`.

Server events: `session.ready`, `session.state`, `audio.chunk`,
`playback.interrupted`, `turn.complete`, and fixed-category `session.error`.
Provider payloads and raw errors never pass directly to the browser.

Initial code-enforced limits are one session, a 15-minute maximum, 60-second
idle timeout, two seconds of buffered audio, 64 KiB control messages, bounded
audio frames, and no automatic reconnect. Values are provisional until measured.

## 7. Proposed dependency baseline

No package is installed by this design. The scaffold PR must pin direct and
transitive dependencies, use lock files, install with scripts disabled where
possible, audit both ecosystems, and record licenses.

| Component | Proposed version | License | Registry evidence |
| --- | --- | --- | --- |
| Python | 3.12 supported line | PSF | Exact security patch selected at scaffold time. |
| FastAPI | 0.162.0 | MIT | PyPI, released 2026-10-23. |
| Uvicorn | 0.54.0 | BSD-3-Clause | PyPI, released 2026-09-25. |
| Google Gen AI SDK | 2.33.0 | Apache-2.0 | PyPI, released 2026-10-22. |
| websockets | 17.3 | BSD-3-Clause | PyPI, released 2026-10-19. |
| pytest | 9.1.1 | MIT | PyPI; test-only proposal. |
| Angular framework and CLI | 22.2.3 | MIT | npm, released 2026-10-14. |
| Node.js | 22.22.3 | MIT | Minimum supported Node 22 release for Angular 22. |
| TypeScript | 6.0.3 | Apache-2.0 | npm; matches Angular `>=6.0 <6.1`. |
| RxJS | 7.8.2 | Apache-2.0 | npm; matches Angular compatibility table. |
| zone.js | 0.16.3 | MIT | npm; Angular peer range. |

Versions published fewer than 14 days before 2026-11-08 were deliberately not
selected. `fastapi[standard]` is not proposed because it adds unrelated cloud
CLI and optional packages. The implementation must justify every additional
direct dependency and must not use `python-dotenv`.

Primary metadata sources:

- <https://pypi.org/project/fastapi/0.162.0/>
- <https://pypi.org/project/uvicorn/0.54.0/>
- <https://pypi.org/project/google-genai/2.33.0/>
- <https://angular.dev/reference/versions>
- <https://registry.npmjs.org/@angular/core>

## 8. Repository layout proposal

```text
apps/api/       FastAPI application and provider adapters
apps/web/       Angular application and browser audio engine
contracts/      Versioned JSON schemas for voice session events
tests/          Cross-boundary and synthetic acceptance fixtures
```

The scaffold PR owns manifests, lock files, exact setup commands, CI jobs, and
generated-file review. This design creates none of them.

## 9. Verification plan

Offline automated tests use generated PCM and a fake adapter. They cover event
schemas, size and time limits, auth/Host/Origin rejection, malformed frames,
mute buffer disposal, playback epochs, late audio, interruption races,
provider errors, disconnects, timeouts, and complete resource cleanup.

Browser tests prove microphone permission is user initiated, local mute stops
capture, stop closes tracks, and no audio or transcript enters storage. A local
manual loopback test may use the operator's microphone but cannot send it to
Gemini or write it to disk.

One opt-in live command may read `GEMINI_API_KEY` and send generated synthetic
PCM. It is excluded from default tests and CI. It reports only timing, state,
and fixed error categories. It may not log audio, transcripts, URLs containing
credentials, or provider payloads.

Windows runs automated checks. Jeevesh runs the same commands on macOS and
records real output. Neither platform substitutes for the other.

## 10. Definition of done

- The fake-adapter slice runs on Windows and macOS with all offline tests passing.
- Manual start, visible listening, mute, barge-in, and stop have measured local evidence.
- Mute and stop prevent subsequent microphone frames from crossing the browser boundary.
- Interrupted or stale model audio cannot resume playback.
- No raw audio, transcript, key, or personal context is persisted or logged.
- The live synthetic test is impossible without explicit invocation and a process environment key.
- All dependencies are exact-pinned, audited, licensed, older than 14 days, and justified.
- Existing repository checks and independent Windows checks remain passing.
- Actual Gemini account, region, quota, model access, and terms are verified before any live test.
- Independent review accepts the implemented security boundary before runtime acceptance.

## 11. Remaining blockers

**2026-11-08 snapshot.** Several items are now resolved: Jeevesh confirmed the
cycle, the Gemini account and dependencies are verified or locked, and the
offline scaffold is merged. The Gemini adapter and opt-in live test remain
unimplemented.

- Jeevesh has not confirmed the product direction or this cycle.
- Gemini account creation, key, region, quota, model access, and terms are unverified.
- The exact Python 3.12 security patch and complete dependency locks are undecided.
- Personal microphone-to-cloud testing is prohibited in this development cycle.
- No scaffold implementation is authorized by this design PR alone.

## 12. Rollback

Revert the eventual design commit. No runtime file, dependency, key, account,
or external service is created by this proposal.

**Signed:** OpenCode, `agentrouter/gpt-5.6-sol`, 2026-11-08. Scope: this
implementation proposal only. Installation, build, runtime tests, provider
access, Mac execution, independent review, and implementation approval are
not run or obtained.

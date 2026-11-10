# Voice foundation and real console: implementation design

| Field | Value |
| --- | --- |
| Date / revision | 2026-11-09 / 2 |
| Author | OpenCode, architect-free (GLM-5.3-Flash Free) |
| Status | Proposal for review. No implementation, dependency installation, provider call, microphone transmission, or runtime approval. |
| Product context | [Personal-agent architecture](../product/personal-agent-architecture.md) |
| Maintainer confirmation | [Decision record](../approvals/voice-foundation-confirmation.md) |
| Runtime gate | [RT-G00](../approvals/rt-g00-resolution.md) is resolved; [RT-001](../../tasks/001-runtime-consent-and-feasibility.md) is complete. RT-G01 remains open. |
| Revision 1 | Preserved verbatim in [voice-foundation-revision-1.md](voice-foundation-revision-1.md). |
| Revision 2.1 | 2026-11-10: section 7 credential design and the section 9 bad-token row updated for the [R-01.5 review](../reviews/r01-5-credential-design.md). |

> **Current state (2026-11-10).** PH-00 is complete. RT-G00 is resolved. PH-01
> is `in progress` after the closure PR merges. The only voice adapter is
> the deterministic fake echo adapter. The Gemini Live adapter and the opt-in
> synthetic live test are **not implemented** (R-01.7 to R-01.9). No live
> provider test has run. This document is a proposal, not a claim that the real
> console exists.

## 1. Purpose and current gap

This revision designs the step from the offline voice scaffold to a real local
voice console. The console keeps Gemini Live multimodal in the middle. The
browser sends audio to the FastAPI backend, the backend streams it to Gemini
Live, and Gemini audio comes back through the same session. There is no
separate speech-to-text, text-chat, and text-to-speech chain.

The current application is not that console. It has:

- A deterministic `FakeVoiceAdapter` that echoes bounded PCM.
- A request/response adapter seam:
  `async send_audio(bytes) -> AudioReply(audio, turn_complete)`.
- A backend loop that waits for one reply before it reads the next browser
  frame.
- A browser capture and playback path that assumes 16 kHz.
- No `google-genai` dependency, no provider call, and no live test.

The gap is not one adapter class. Gemini Live is streaming. It can send
several model audio chunks, turn-complete events, interruption events, and
session-ending events at times the request/response seam cannot represent.
The backend must send browser audio and receive model events at the same time.
The design therefore replaces the seam first, then adds the provider adapter.

This revision covers the real console build. It does not authorize personal
microphone audio to a cloud provider in the current development cycle. The
live provider evidence remains synthetic-only until a separate privacy and
runtime decision is recorded. The console can run the full local flow with the
fake adapter. The Gemini mode is explicit and opt-in.

## 2. Recorded decisions and scope

| Topic | Decision |
| --- | --- |
| Stack | Python FastAPI backend and Angular browser client. |
| Provider | Gemini Live, audio in and audio out, behind a replaceable adapter. |
| Hosts | Windows and macOS. Jeevesh records Mac-only evidence. |
| Interaction | Manual start, visible active session, local mute, barge-in, and stop. |
| Secrets | Backend process environment only. No project `.env`, no browser key, no logs. |
| Data | Synthetic audio may reach Gemini in PH-01. Personal microphone audio stays local unless a separate approval is recorded. |
| Budget | Hard $0 development cap. No billable fallback. |
| Memory | No persistent transcript, embedding, preference, or habit extraction. |
| Actions | No tools, MCP, research, subagents, shell, calls, bookings, messages, or computer control. |
| Deployment | Loopback only. No remote hosting, public bind, or production TLS. |

PH-01 scope:

- Streaming adapter seam and offline fake-adapter tests.
- Gemini Live adapter behind the seam.
- Real console UI with clear states and controls.
- Credential design, failed-auth throttling, and independent security review.
- Opt-in synthetic-audio live command and one recorded live test.
- RT-002 and RT-003 records and RT-G01 evidence.

Non-goals:

- Personal microphone audio to Gemini without a separate recorded approval.
- Tools, function calling, task workers, or background jobs.
- Wake words, locked-screen use, or background OS listening.
- Persistent transcripts, stored audio, analytics, or personal memory.
- Mobile, remote deployment, multi-user hosting, or production operations.
- Automatic provider reconnect or silent fallback to another provider.

## 3. Target architecture

```text
Browser voice console
  AudioWorklet capture at 16 kHz
  PCM16 LE mono frames
  playback buffers at the event rate, 24 kHz for Gemini
  mute, barge-in, stop, status, timer, errors
        |
        | WebSocket on 127.0.0.1
        | token or same-origin session cookie
        v
FastAPI loopback backend
  Host and Origin checks
  authentication and failed-auth throttling
  one active session
  streaming bridge and bounded queues
  code limits, timeouts, cleanup, fixed error categories
        |
        +--> FakeVoiceAdapter (default, tests and local echo)
        |
        +--> GeminiLiveAdapter (explicit opt-in, synthetic test only in PH-01)
```

Provider selection:

- `VOICE_PROVIDER=fake` is the default for tests and the local echo console.
- `VOICE_PROVIDER=gemini` enables the real adapter and requires
  `GEMINI_API_KEY` in the backend process environment.
- A missing key in `gemini` mode fails closed at startup with a fixed error.
  The process does not start a provider session and does not fall back to fake.
- The key is read once at startup. It is never logged, sent to the browser, or
  written to a file by the application.

Serving model:

- Recommended shipped path: FastAPI serves the built Angular console on
  `http://127.0.0.1:8000`. The browser and WebSocket share one origin. This
  removes CORS from the shipped path and allows an HttpOnly session cookie.
- Development path: the Angular dev server stays on
  `http://127.0.0.1:4200`, with an explicit Origin allowlist and first-message
  token authentication.
- The same-origin change is a proposal. It needs maintainer approval and the
  security review in section 9.

The backend binds only to `127.0.0.1`. It rejects other Host and Origin values.
It never exposes provider payloads or raw errors to the browser.

## 4. Streaming adapter seam

The current seam cannot carry asynchronous model audio. The replacement is a
streaming protocol with one input queue, one ordered event stream, and
explicit close semantics.

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioChunk:
    data: bytes
    rate_hz: int


@dataclass(frozen=True)
class TurnComplete:
    pass


@dataclass(frozen=True)
class Interrupted:
    pass


AdapterEvent = AudioChunk | TurnComplete | Interrupted


class VoiceAdapter(Protocol):
    async def start(self) -> None: ...
    async def enqueue_audio(self, audio: bytes) -> None: ...
    async def interrupt(self) -> None: ...
    def events(self) -> AsyncIterator[AdapterEvent]: ...
    async def close(self) -> None: ...
```

Contract:

- `start()` opens the provider session or prepares the fake stream. It raises a
  fixed adapter error on failure. The backend maps that error to a fixed
  `session.error` category.
- `enqueue_audio()` accepts one PCM16 LE mono frame at 16 kHz. It is
  non-blocking. The adapter has a bounded input queue. When the queue is full,
  it drops the oldest audio frame and increments a counter. Audio is never
  allowed to grow without bound.
- `interrupt()` asks the adapter to stop the current model output. The exact
  provider behavior is verified by the live synthetic test. The adapter must
  not pretend the interruption succeeded.
- `events()` is a single-consumer async iterator. It yields audio chunks with
  their sample rate, turn-complete events, and interruption events in order.
  The backend must not run two consumers on one adapter.
- `close()` cancels adapter tasks, closes the provider session, and releases
  queues. It is idempotent.
- The fake adapter implements the same protocol with deterministic events. It
  can be scripted in tests to emit audio, turns, interruptions, delays, and
  errors.

Backend concurrency:

- One browser receiver task reads WebSocket messages. It authenticates, handles
  control events, validates audio frames, and calls `enqueue_audio()`.
- One adapter forwarder task consumes `events()` and sends ordered events to the
  browser.
- One watchdog task owns the total-duration and idle deadlines.
- One sender task owns all WebSocket writes. Control responses, audio metadata,
  binary audio, and errors go through one bounded outbound queue. This prevents
  interleaved frames from concurrent senders.
- On any task failure, the backend cancels the other tasks, closes the adapter,
  releases the session gate, and closes the socket with a fixed category.

Backpressure and ordering:

- Audio input and output queues are bounded. Audio uses drop-oldest because
  stale audio is worse than a gap. Control events are never dropped. If a
  control queue is full, the session fails closed.
- The backend attaches the current playback epoch to every output event. The
  adapter does not own the epoch.
- The browser drops binary audio that is not covered by the current epoch. The
  existing playback-epoch tracker remains the authority.
- Metrics count frames and drops. They do not contain audio or transcript.

State machine:

```text
idle -> authenticating -> starting -> ready -> listening
                                      |          |
                                      |          +--> speaking
                                      |          |
                                      +----------+--> stopping -> closed
any state -> error -> closed
```

`session.ready` is sent only after `adapter.start()` succeeds. If the provider
fails, the browser receives a fixed `session.error` and the socket closes. The
browser does not start microphone capture until it receives `session.ready`.

## 5. Browser protocol revision 2

Client events:

| Event | Payload | Rule |
| --- | --- | --- |
| `session.auth` | `{ "type": "session.auth", "token": "..." }` | First message. Required before any audio. |
| `capture.mute` | `{ "type": "capture.mute" }` | Stops browser capture and ends the provider audio stream. |
| `capture.unmute` | `{ "type": "capture.unmute" }` | Starts a new provider audio stream. |
| `playback.interrupt` | `{ "type": "playback.interrupt" }` | Local barge-in. Stops playback and bumps the epoch. |
| `session.stop` | `{ "type": "session.stop" }` | Ends the session and closes the provider. |

Server events:

| Event | Payload | Rule |
| --- | --- | --- |
| `session.ready` | `{ "type": "session.ready", "playbackEpoch": 0, "outputRateHz": 24000, "provider": "gemini-live" }` | Sent after provider start succeeds. |
| `audio.chunk` | `{ "type": "audio.chunk", "playbackEpoch": 0, "rateHz": 24000, "channels": 1, "format": "pcm16" }` | Followed immediately by one binary frame. |
| `turn.complete` | `{ "type": "turn.complete", "playbackEpoch": 0 }` | Model turn ended. |
| `session.state` | `{ "type": "session.state", "state": "listening" }` or `{ "type": "session.state", "muted": true }` | Visible state. |
| `playback.interrupted` | `{ "type": "playback.interrupted", "playbackEpoch": 1, "source": "local" }` | Local or provider interruption. |
| `session.error` | `{ "type": "session.error", "category": "provider-unavailable" }` | Fixed category only. |
| `session.metrics` | `{ "type": "session.metrics", "inputFrames": 0, "droppedInputFrames": 0, "outputChunks": 0, "droppedOutputChunks": 0 }` | Optional aggregate counters. No payloads. |

Binary rules:

- Browser to backend: PCM16 little-endian, mono, 16 kHz. One frame per
  WebSocket binary message. Maximum 32 KiB. The backend rejects odd-length
  frames and oversized frames.
- Backend to browser: PCM16 little-endian, mono, rate from `audio.chunk`.
  Gemini Live output is 24 kHz. The browser creates an `AudioBuffer` with the
  event `rateHz` and lets the Web Audio API resample to the output device. It
  must not hard-code 16 kHz.
- The binary frame has no header. The preceding `audio.chunk` JSON is the
  metadata. A binary frame without a current metadata event is dropped.
- Playback epochs increase on local barge-in and on provider interruption.
  Audio for an older epoch is dropped.

Startup sequence:

1. Browser connects to `/ws/voice` with the allowed Host and Origin.
2. Browser sends `session.auth`.
3. Backend validates the token, acquires the one-session gate, creates the
   adapter, and calls `adapter.start()`.
4. On provider failure, backend sends `session.error` and closes. No
   microphone capture starts.
5. On success, backend sends `session.ready` with `outputRateHz`.
6. Browser requests microphone permission and starts capture.
7. Audio flows in both directions until stop, timeout, provider end, or error.

Shutdown sequence:

1. Stop closes microphone tracks and audio nodes.
2. Browser sends `session.stop` if the socket is open.
3. Backend cancels tasks, closes the adapter, releases the gate, and closes the
   socket.
4. Browser clears playback and status. No audio or transcript is saved.

Error categories:

| Category | Meaning |
| --- | --- |
| `invalid-control` | Malformed JSON, unknown event, or missing field. |
| `invalid-audio` | Odd length, oversized frame, or audio before ready. |
| `max-duration` | Code-level 15-minute limit reached. |
| `session-timeout` | 60-second idle limit reached. |
| `session-busy` | One active session already exists. |
| `provider-unavailable` | Connection, DNS, TLS, or network failure. |
| `provider-limits` | Quota or rate limit. |
| `provider-unsupported` | Unsupported model, transport, or configuration. |
| `provider-session-ended` | Provider GoAway or session close. |
| `session-failed` | Redacted catch-all. |

No provider message, stack trace, URL, key, audio, or transcript is sent to the
browser.

## 6. Gemini Live adapter

The adapter uses the Python `google-genai` SDK pinned in section 11. The SDK
surface below was checked against the official Live guides on 2026-11-09. The
runtime behavior with a real key has not been tested. That is the main residual
uncertainty in this design.

Connection and configuration:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
async with client.aio.live.connect(model=model, config=config) as session:
    ...
```

Proposed configuration:

- Response modality: audio.
- Input audio transcription: off.
- Output audio transcription: off.
- Tools: none.
- System instruction: minimal and static. No personal data.
- Voice: fixed default for the first slice. Model and voice selection are open
  questions.
- Automatic voice activity detection: provider default. Exact tuning is
  verified in the live synthetic test.

Send path:

```python
await session.send_realtime_input(
    audio=types.Blob(data=frame, mime_type="audio/pcm;rate=16000")
)
```

- Input frames are PCM16 LE mono at 16 kHz.
- On mute or stop, the adapter sends `audio_stream_end=True` once.
- On unmute, it starts a new stream with the next audio frame.
- No text input is sent.

Receive path:

```python
async for response in session.receive():
    ...
```

Mapping:

| Provider event | Adapter event or action |
| --- | --- |
| `server_content.model_turn.parts[].inline_data.data` | `AudioChunk(data, rate_hz=24000)` |
| `server_content.turn_complete` | `TurnComplete()` |
| `server_content.interrupted` | `Interrupted()` |
| `server_content.go_away` | Fail closed with `provider-session-ended` |
| `session_resumption_update` | Store the handle only. No reconnect in this slice. |

Session limits:

- The code-level maximum is 15 minutes.
- The provider connection lifetime is about 10 minutes and can send GoAway
  before it ends.
- On GoAway, the adapter ends the session with `provider-session-ended`. It does
  not reconnect and does not silently start a new provider session.
- Session resumption is a future design. It needs its own review because it
  changes continuity and retention behavior.
- One provider session per browser session.

Error mapping:

| Failure | Category |
| --- | --- |
| Connection, DNS, TLS, or network | `provider-unavailable` |
| Quota or rate limit | `provider-limits` |
| Unsupported model, transport, or config | `provider-unsupported` |
| GoAway or provider session close | `provider-session-ended` |
| Anything else | `session-failed` |

Barge-in:

- The browser detects local speech while playback is active. It stops local
  playback and sends `playback.interrupt`.
- The backend bumps the epoch and calls `adapter.interrupt()`.
- The adapter sends `audio_stream_end=True` to the provider and waits for the
  provider's `interrupted` event or turn completion. If the provider does not
  interrupt, the session ends with a fixed error. It does not pretend the
  interruption succeeded.
- If the provider sends `interrupted` on its own, the adapter emits
  `Interrupted()`. The backend bumps the epoch and sends
  `playback.interrupted` with `source: "provider"`.
- Exact barge-in behavior is verified by the synthetic live test before the
  console is accepted.

Logging:

- Log fixed categories, state transitions, frame counts, drop counts, and
  timing.
- Never log audio, transcript, key, provider payload, request URL, or personal
  context.
- Provider exceptions are reduced to a fixed category before logging.

## 7. Credential design (R-01.5)

Revision 2.1 (2026-11-10) resolves the conditions of the
[R-01.5 credential design review](../reviews/r01-5-credential-design.md)
(CR-01 to CR-05 and CR-07). CR-06, CR-08, and CR-09 are implementation
conditions, listed at the end of this section and tested under R-01.6. Nothing
in this section is implemented yet unless a line says so.

Threat model:

| Actor | In scope | Control |
| --- | --- | --- |
| Malicious web page in the user's browser | Yes | Exact Host and Origin checks on every handshake and request; no CORS in the shipped path. |
| DNS rebinding | Yes | One exact Host (`127.0.0.1:<port>`, as in section 9 and the current code) checked before auth; Origin must also match exactly. |
| Another OS user on the same machine | Yes | Loopback is shared by every local user, so the token file is mode 0600 in the owner's home directory. |
| Malicious process running as the same user | **Out of scope** | It can read the token file, environment, and process memory. Stated, not defended. |
| Browser extension with page access | Partly | Can read the password field and page memory. Mitigated by the cookie flow, a strict CSP, and zeroing the in-memory token after use. |
| Shoulder surfing, clipboard, shell history | Yes | Token never shown after generation, never typed inline in a shell command; clipboard copy is optional and documented as a leak path. |
| Logs, error bodies, close reasons, crash dumps | Yes | Token never logged or echoed; fixed error text; secret-scan tests. |
| Remote network attacker | **Out of scope** | The server binds only to `127.0.0.1`. |

Device credential:

- 32 random bytes from `secrets.token_urlsafe(32)` (about 256 bits). PIN or
  password credentials are rejected by design.
- **Generation and delivery:** a documented `generate-token` helper writes the
  token to `~/.super-agent/voice-token` with mode 0600 on macOS (or the
  Keychain), and on Windows to `%USERPROFILE%\.super-agent\voice-token` with an
  owner-only ACL (or the Windows Credential Manager). The
  backend reads that file at start. Docs must never show the token inline in an
  `export` or `$env:` command, so it does not land in shell history.
- **Weak values rejected at start:** fewer than 32 bytes, or fewer than 16
  distinct characters, stops the backend with a fixed error.
- Compared as UTF-8 bytes with `hmac.compare_digest`; any decode or type error
  is treated as a failed attempt, never a crash.
- **Expiry is mandatory:** `SUPER_AGENT_TOKEN_MAX_AGE_SECONDS`, default 86400
  (24 hours, provisional), measured from backend process start. A missing value
  uses the default; a zero, negative, or unparsable value stops the backend.
- Rotation: run `generate-token` and restart. Revocation: restart, which closes
  every session and invalidates every cookie session id.

Session credential:

- One active session, ended by stop, disconnect, idle timeout, a 15-minute
  maximum, or provider end.
- **Authenticate before taking the session slot.** A pre-auth connection gets
  at most 5 seconds and does not hold the single active-session slot, so
  unauthenticated clients cannot starve the user. Pre-auth connections are
  capped separately (provisional: 4 at once).
- **A failed attempt is closed immediately** and never held open during its
  delay; the delay is enforced by refusing or deferring that source's next
  attempt. Failed attempts therefore cannot fill the pre-auth cap and lock the
  user out (review N1, tested in R-01.6).

Failed-auth throttling (CR-01):

- Guessing a 256-bit token online is infeasible, so throttling exists to limit
  log, CPU, and connection abuse, **not** to stop guessing.
- No hard lockout. After 5 failures in 60 seconds, each further failed attempt
  gets an increasing delay (provisional: 0.5 s doubling, capped at 8 s).
- **A correct token is always accepted**, even while failures are being
  delayed, so a local process cannot lock the user out.
- The counter resets on success and decays after 60 quiet seconds. Responses
  use a fixed error and fixed close code, revealing nothing about closeness or
  session state.
- Values are provisional and must be measured in R-01.6.
- Accepting a correct token immediately while delaying wrong ones reveals
  whether a guess was right. That is harmless at 256 bits of entropy and is
  accepted on purpose (review N5).

Browser flow, minimal (development only):

- The user pastes the token into a password field. The page keeps it only until
  the first `session.auth` message is sent, then zeroes it in the service and
  the field. It is never written to `localStorage` or `sessionStorage`.
- A strict Content-Security-Policy is required: no inline scripts, no
  third-party scripts.
- A bad token closes the socket with code 1008.

Browser flow, recommended shipped path (needs maintainer approval):

- FastAPI serves the built Angular console on the same origin.
- **Enrollment:** a POST with the device token, checked for exact Host and
  Origin and throttled like the WebSocket. On success the backend issues a
  fresh `secrets.token_urlsafe(32)` session id, stored only in a server-side
  in-memory map, and replaces any previous id (rotation on enrollment).
- **Cookie:** HttpOnly, SameSite=Strict, Path=/, Max-Age 900 seconds (matches
  the 15-minute session cap). `Secure` is not set because this local slice is
  plain HTTP on loopback; therefore the `__Host-` prefix is not possible. On
  loopback only a local administrator could read the traffic, which is out of
  scope above.
- SameSite=Strict does not separate different localhost ports, so the
  **exact Origin and Host checks on enrollment and on the WebSocket upgrade are
  the real CSRF control**.
- The cookie is accepted only on the WebSocket upgrade, never on other routes.
  A logout or stop clears the server-side id; a restart clears all of them.

Same-origin trade-off:

- Benefits: one origin, no CORS, cookie auth, a simpler CSRF story, one URL for
  the user, and the device token leaves JavaScript after enrollment.
- Costs: a build and static-file serving step, a different development flow,
  and a cookie and CSRF review.
- The Angular dev server flow stays dev-only. It is not the shipped check path.

Implementation conditions from the review (tested in R-01.6):

- CR-06: the current scaffold takes the session slot before authentication
  (`apps/api/src/super_agent_voice/app.py`, slot at line 80, auth wait at
  line 96). Change the order as stated above.
- CR-08: the current scaffold compares `str` values with `hmac.compare_digest`,
  which raises on non-ASCII input. Compare UTF-8 bytes and treat errors as a
  failed attempt.
- CR-09: the current scaffold checks only `len >= 32` bytes. Add the
  distinct-character check and the `generate-token` helper.
- N3: the server-side cookie session id expires after 900 seconds, matching
  the cookie Max-Age; enrollment rejects a missing or `null` Origin; enrollment
  is refused once the device token has expired.
- N4: one exact Host is allowed, matching section 9 and the current code.
- Required negative tests: the nine listed in the review record, section
  "Required negative tests for R-01.6", plus a test that failed attempts cannot
  fill the pre-auth cap (N1) and a Windows ACL check on the token file (N2).

## 8. Real console UX

Minimum console:

- Header with connection state, provider mode, and session timer.
- Large Start and Stop control.
- Mute toggle.
- Interrupt control.
- Visible states: disconnected, connecting, listening, speaking, muted,
  stopping, error.
- Fixed error messages for microphone permission, invalid token, provider
  unavailable, provider limits, provider session ended, and network failure.
- Accessible labels, focus states, and an ARIA live status region.
- Keyboard shortcuts: `S` start or stop, `M` mute, `I` interrupt. Shortcuts are
  ignored while a text field has focus.
- Local token input with `type="password"` and no autocomplete.

Recommended real-console features:

- AudioWorklet capture at 16 kHz. Keep the existing ScriptProcessorNode only as
  a fallback with a visible warning if AudioWorklet is unavailable.
- Playback buffers use the `rateHz` from `audio.chunk`. Gemini output is 24 kHz.
  Do not hard-code 16 kHz.
- Input and output device selection through `enumerateDevices`. Device
  selection is a preference, not a secret. Keep it in memory for the first
  slice.
- Level meter from the AudioWorklet.
- Session timer with a warning one minute before the code maximum and a note
  that the provider may end earlier.
- Provider consent before the first Gemini session. The console says:
  "Audio is sent to Google Gemini Live for this session. This app does not
  store it. Free-tier terms may allow Google to use inputs for product
  improvement." The user must opt in.
- The fake mode says: "Local echo only. Audio stays on this machine."

Optional polish, out of the minimum:

- Ephemeral captions. These need a privacy review because they expose provider
  transcription. Persistent transcripts remain prohibited.
- Waveform visualization.
- Model and voice selection.
- Configurable barge-in sensitivity.

No persistent transcript, no stored audio, no analytics, and no personal
context in prompts.

## 9. Security and privacy (R-01.6)

Controls:

- Host header must equal the configured loopback host.
- Origin header must equal the configured console origin.
- WebSocket auth happens before any audio is accepted.
- One active session. Additional connections are closed with 1013.
- Control messages are bounded to 64 KiB.
- Audio frames are bounded to 32 KiB and must have even length.
- The total session is bounded to 15 minutes.
- The idle timeout is 60 seconds.
- No automatic reconnect and no silent provider fallback.
- Provider payloads and raw errors never reach the browser.
- No secret in the browser, URL, prompt, log, or repository.
- The provider key is read from the backend process environment only.
- Dependency versions are pinned, audited, and license-checked.

Provider egress:

- In `gemini` mode, audio is sent to Google Gemini Live.
- PH-01 live evidence uses generated synthetic PCM only.
- Personal microphone audio to Gemini requires a separate dated decision by
  both maintainers, an updated provider terms and retention record, and a
  runtime gate. Until then, personal audio stays local and the fake adapter is
  the only path that may receive it.
- The console must show the disclosure and require opt-in before a Gemini
  session.

Fail-closed table:

| Condition | Behavior |
| --- | --- |
| Missing `GEMINI_API_KEY` in `gemini` mode | Refuse to start a provider session. Fixed `provider-unavailable` error. |
| Bad token | Close 1008, count the failure; after five failures add an increasing delay (no hard lockout); a correct token is always accepted. |
| Host or Origin mismatch | Close 1008 before auth. |
| Second session | Close 1013. |
| Audio before ready | Fixed `invalid-audio` error and close. |
| Odd or oversized audio frame | Fixed `invalid-audio` error and close. |
| Provider connect failure | Fixed `provider-unavailable` error and close. |
| Provider quota or rate limit | Fixed `provider-limits` error and close. |
| Provider GoAway | Fixed `provider-session-ended` error and close. |
| Provider unsupported model or transport | Fixed `provider-unsupported` error and close. |
| Queue overflow | Drop oldest audio for audio queues. Fail closed for control queues. |
| Unexpected exception | Fixed `session-failed` error, redacted, close. |

Independent security review scope:

- Authentication and failed-auth throttling.
- Host, Origin, CORS, WebSocket, and CSRF controls.
- Backend-only secret handling and log redaction.
- Provider egress, consent, and disclosure.
- Session limits, queue bounds, cancellation, and cleanup.
- Dependency supply chain and license.
- Same-origin cookie flow, if approved.
- Fail-closed behavior for each error path.

The review must record PASS or FAIL, findings, and dispositions. It must not
have access to the provider key.

## 10. Testing and evidence

Offline tests:

- Adapter contract with a scripted fake streaming adapter: ordered audio,
  turn complete, interruption, error, close, and queue drop.
- Backend: auth, Host, Origin, one-session gate, total and idle timeouts,
  oversized and odd frames, invalid control, provider start failure, provider
  error redaction, epoch on local and provider interruption, cleanup.
- Frontend: playback epoch, 24 kHz buffer handling, mute, barge-in, stop, and
  error states. Add a self-test script next to the existing epoch self-test.
- No live provider call in CI or the default test command.

Opt-in synthetic live command (R-01.8):

- Proposed path: `apps/api/scripts/live_synthetic.py`.
- It generates PCM at runtime. It does not read or write audio files.
- It requires `VOICE_PROVIDER=gemini` and `GEMINI_API_KEY` in the process
  environment. It refuses to run if the key is missing.
- It sends generated audio through the real adapter. It records first-audio
  latency, turn completion, interruption, stop, and fixed error categories.
- It logs timing and state only. No audio, transcript, key, URL, or provider
  payload.
- It is excluded from default tests and CI.
- It includes an unsupported model or transport case that must fail closed.

Synthetic live test (R-01.9):

- The operator runs the command in the PowerShell session that holds
  `GEMINI_API_KEY`. The agent cannot see the key and does not run the live test.
- Record date, model, region, latency, turn behavior, interruption behavior,
  stop behavior, and the fail-closed case.
- Save the redacted output in a dated implementation record.
- No audio or transcript is saved.
- If the key is unavailable or the quota is exhausted, record "not run" and do
  not claim the gate.

Human checks:

- R-01.3: Jeevesh runs the offline checks on macOS and records real output.
- R-01.4: the operator runs the local microphone test with the fake adapter:
  start, mute, barge-in, and stop. No audio leaves the machine.

R-01.10:

- RT-002 and RT-003 records complete.
- RT-G01 evidence includes the reviewed scaffold and commands, deployed
  authentication, Host, Origin, CORS, WebSocket, and CSRF controls,
  backend-only secrets, measured native media, manual activation, stop
  controls, visible states, and fail-closed transport behavior.

## 11. Dependencies

No dependency is installed by this design.

| Component | Proposed version | License | Evidence |
| --- | --- | --- | --- |
| `google-genai` | `2.33.0` | Apache-2.0 | Released 2026-10-23, 17 days old on 2026-11-09. Satisfies the 14-day rule. |
| Python | 3.12 supported line | PSF | Exact security patch selected at implementation. |
| FastAPI | `0.162.0` | MIT | Already pinned in the scaffold. |
| Uvicorn | `0.54.0` | BSD-3-Clause | Already pinned in the scaffold. |
| websockets | `17.3` | BSD-3-Clause | Already pinned in the scaffold. |
| Angular | `22.2.3` | MIT | Already pinned in the scaffold. |
| TypeScript | `6.0.3` | Apache-2.0 | Already pinned in the scaffold. |

Rejected versions:

- `google-genai==3.0.0`, released 2026-11-06, 3 days old.
- `google-genai==2.34.0`, released 2026-10-29, 11 days old.

Dependency notes:

- `google-genai==2.33.0` requires Python >=3.10.
- Transitive packages include anyio, google-auth, httpx, pydantic, requests,
  tenacity, websockets, typing-extensions, distro, and sniffio.
- PyPI license metadata is empty. The Apache-2.0 license was verified from the
  `LICENSE` file at GitHub tag `v2.33.0`.
- Add the dependency to `apps/api/requirements.in`, regenerate
  `apps/api/requirements.lock` with the existing pip-tools flow, install with
  `--only-binary=:all:` where possible, run the Python audit, and record the
  result.
- No new frontend dependency is required. AudioWorklet, Web Audio, and
  `enumerateDevices` are browser APIs.
- Do not add `python-dotenv`. The key stays in the process environment.
- If a dev dependency is needed for async tests, justify it and pin it. Prefer
  the existing pytest stack.

Sources checked 2026-11-09:

- <https://pypi.org/project/google-genai/2.33.0/>
- <https://github.com/googleapis/python-genai/blob/v2.33.0/LICENSE>
- <https://ai.google.dev/gemini-api/docs/live-api>
- <https://ai.google.dev/gemini-api/docs/live-api/get-started-websocket>

## 12. Implementation plan and estimate

Current-phase task direction (2026-11-10): the operator assigned a bounded
local-only streaming slice while retaining the Mac and microphone checks as
acceptance blockers. See the [direction record](../approvals/ph-01-current-phase-work.md)
and [slice contract](voice-streaming-slice.md). The original sequence below is
retained for context; no acceptance gate, provider grant, or data boundary is
changed by this task assignment.

Technical review correction (2026-11-10): the local slice's
[bounded-teardown addendum](voice-streaming-teardown.md) explicitly amends
cleanup-slot release on unresolved ownership. It requires bounded handler
waits and retention of the existing single-session slot until worker quiescence
and successful adapter closure are confirmed. This is a technical prototype
correction in PR #24, not maintainer approval or native-provider acceptance.

Work order:

1. **Close PH-00.** Complete. RT-G00 was resolved by PR #23 and the final
   bookkeeping PR moves `Current phase` to PH-01.
2. **Human checks.** R-01.3 Mac offline checks and R-01.4 local microphone test
   with the fake adapter.
3. **Credential design and throttling (R-01.5).** Approve the token flow and
   same-origin decision. Implement failed-auth throttling and the chosen
   session flow. Independent review.
4. **Streaming seam (R-01.7 part 1).** Replace the request/response adapter
   with the streaming protocol. Add the scripted fake adapter and backend tests.
   Keep the console working with the fake adapter.
5. **Gemini adapter (R-01.7 part 2).** Add `google-genai==2.33.0`, implement
   `GeminiLiveAdapter`, map errors, handle GoAway, and add offline tests with a
   mocked SDK.
6. **Console UI.** Add the real console states, 24 kHz playback handling,
   AudioWorklet, device selection, level meter, timer, disclosure, and
   accessibility. Keep the fake mode working.
7. **Security review (R-01.6).** Review the implemented boundary and provider
   egress. Fix findings. Record PASS or FAIL.
8. **Opt-in live command (R-01.8).** Build the synthetic command and its
   fail-closed cases.
9. **Live test (R-01.9).** The operator runs it in the PowerShell session with
   the key. Record redacted results.
10. **Records and gates (R-01.10).** Complete RT-002 and RT-003. Record RT-G01
    evidence. Tick roadmap items only after the evidence exists.

Estimate:

| Work | Focused days | Calendar dependency |
| --- | --- | --- |
| Close PH-00 and bookkeeping | 0.5 | Jeevesh review and merge |
| R-01.3 and R-01.4 human checks | 0.5 to 1 | Jeevesh and operator availability |
| R-01.5 credential design and review | 1 to 2 | Independent review |
| R-01.6 security review and fixes | 1 to 2 | Reviewer availability |
| R-01.7 streaming seam and Gemini adapter | 3 to 4 | None beyond PH-00 |
| R-01.8 opt-in live command | 1 | None |
| R-01.9 live test | 0.5 to 1 | Operator key and quota |
| R-01.10 records | 0.5 to 1 | Prior evidence |
| Console UI, minimal | 1 to 2 | None |
| Console UI, polish | 3 to 6 | None |

Totals:

- Minimal real console: about 8 focused days over about 2 calendar weeks.
- Polished console: about 15 to 20 focused days over about 4 calendar weeks.
- The estimates assume prompt reviews, available human checks, and no provider
  surprises. They are estimates, not commitments.
- The live test cannot run from the agent process because the key is
  session-scoped. The operator must be available for R-01.9.

## 13. Risks and open questions

Risks:

- The streaming seam changes the core backend loop. Regression risk is higher
  than adding an adapter class.
- The Gemini SDK surface is verified from documentation, not from a live call.
  The live test may find differences.
- The provider connection lifetime is about 10 minutes, shorter than the
  15-minute code maximum. A real session may end earlier than the UI timer.
- Barge-in behavior with real audio is unverified. The live synthetic test must
  measure it.
- Free-tier quota and terms may limit the live test.
- Personal microphone audio to Gemini is not approved in this cycle. The
  console may be technically ready before it is allowed to use personal audio.
- Same-origin serving changes the development flow and needs approval.
- AudioWorklet and 24 kHz playback need Windows and macOS browser testing.
- Human checks and independent reviews are on the critical path.

Open questions for the operator:

1. May personal microphone audio be sent to Gemini? This needs a dated decision
   by both maintainers, a provider terms and retention update, and a runtime
   gate. Until then, PH-01 remains synthetic-only.
2. Should sessions beyond the about 10-minute provider lifetime be accepted as
   normal, or should a later design add provider session resumption?
3. Are ephemeral captions in scope? The proposal keeps them out of the minimum.
4. Is same-origin serving from FastAPI approved for the shipped path, with the
   Angular dev server kept dev-only?
5. Should the console keep the paste-per-session token, or use the HttpOnly
   same-origin session cookie?
6. Is the model and voice fixed for the first slice, or configurable?
7. Is the barge-in threshold fixed or user-configurable?

## 14. Rollback

This design changes no runtime state. Revert the design commit to remove it.

After implementation, revert the phase PR. The fake adapter remains the default
and the offline scaffold continues to work. No provider account, key, or
external service is created by the implementation. Stop closes any active
provider session.

## 15. Documentation impact

When the implementation lands, update:

- `README.md` and `build.md` for the real console commands and provider mode.
- `apps/voice-foundation.md` for the console and the synthetic-only boundary.
- The voice implementation record for the streaming seam and adapter.
- A dated Gemini Live synthetic test record for R-01.9.
- `docs/implementation/phase-prs.md` for the PH-01 phase PR.
- `roadmap.md` ticks R-01.3 through R-01.10 only with real evidence.
- `phases.md` and `progress.md` when PH-01 is done.
- `tasks/002-local-scaffold-and-boundary.md` and
  `tasks/003-native-voice-session.md` when their evidence exists.
- Any approval record needed for personal audio egress or same-origin serving.

This document does not tick any roadmap item and does not change the current
phase.

## Appendix A. Revision 1

Revision 1 is preserved verbatim in
[voice-foundation-revision-1.md](voice-foundation-revision-1.md).

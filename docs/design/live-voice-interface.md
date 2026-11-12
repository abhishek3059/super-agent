# Live voice interface design

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Status | Implemented on the current work branch; pending review and the R-01.4 human microphone test |
| Human reference | [Standalone HTML reference](references/super-agent-live-voice-interface.html) |
| Runtime boundary | Loopback backend and local fake echo only; no Gemini microphone session |

## Purpose

The interface adapts the operator's visual reference into the existing Angular
voice console. It keeps the dark ambient background, central microphone orb,
input visualization, compact state indicator, voice-path inspector, settings
dialog, and bottom control dock.

The standalone reference is retained as a design artifact. It is not loaded by
the application. Its Tailwind CDN, Google Fonts, simulated autonomous state
cycle, configurable WebSocket URL, and token persistence are not part of the
implemented console.

## Truthful state mapping

| UI state | Application source | Meaning |
| --- | --- | --- |
| Disconnected | `stopped` | No voice WebSocket or microphone capture |
| Connecting | `connecting` | Loopback connection and first-message authentication are pending |
| Listening | `listening` | Authentication and microphone setup completed |
| Local echo | `speaking` | Audible PCM from the local fake adapter is playing |
| Muted | `muted` | The microphone track and outbound frames are suppressed |
| Needs attention | `error` | A redacted local error stopped and detached the session |

There is no simulated thinking or research state. PH-01 has no task workers,
research tools, or personal-microphone provider mode.

## Interaction

- The settings button and disconnected center control open the local connection
  dialog.
- The dialog accepts only the fixed loopback endpoint and a memory-only token.
  Closing or starting the connection clears the component's token field.
- The center control toggles mute only after the session is ready.
- The dock exposes mute, stop local playback, and start or end session.
- The local voice-path inspector describes connection, authentication,
  microphone capture, and fake-adapter echo without claiming future work.
- The spectrum uses the existing microphone RMS signal. A visible caption states
  that it is a microphone level, not speech detection. It is decorative while
  connecting or playing echo.

## Security and accessibility

- No token is written to local storage, a URL, a log, or a project file.
- The endpoint remains `ws://127.0.0.1:8000/ws/voice`; the UI cannot widen it.
- Provider selection remains outside the browser. The UI labels the fake local
  adapter and states that microphone audio stays local.
- Controls have visible focus styles, names, disabled states, live status or
  alert regions, and reduced-motion behavior.
- The layout remains usable on narrow and short viewports without external
  fonts, scripts, images, or new dependencies.

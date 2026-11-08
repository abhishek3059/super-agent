# Voice-foundation maintainer confirmation

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Design | [Voice-foundation design](../design/voice-foundation.md), revision 1 |
| Purpose | Record maintainer decisions before runtime acceptance. |
| Runtime status | No runtime gate is closed. Gemini access and live testing remain blocked. |

## Proposed first cycle

- FastAPI backend and Angular browser client.
- Windows and macOS support.
- Manually started active voice session with visible listening state.
- Local microphone capture, mute, playback, barge-in, and stop.
- Deterministic fake provider for automated tests.
- Optional Gemini Live adapter for generated synthetic PCM only.
- Process-environment secrets only. No project `.env` file.
- Hard $0 development budget and no paid fallback.
- No persistent memory, tools, MCP, subagents, shell, calls, bookings,
  messages, computer control, or other external actions.

## Maintainer dispositions

| Maintainer | Status | Recorded scope |
| --- | --- | --- |
| `abhishek3059` | **Approved, 2026-11-08** | Approved the design step and requested initial offline implementation. This does not authorize personal microphone transmission to Gemini. |
| `jeevesh2515` | **Pending** | Must review the direction, stack, Mac responsibility, data boundary, and $0 budget. |

## Jeevesh decision

Jeevesh can record a decision by reviewing the pull request containing this
file. An approval means agreement with every first-cycle bullet above and
acceptance of responsibility for running the documented macOS checks. A change
request must identify the disputed bullet and proposed replacement.

- [ ] Direction and first-cycle scope accepted.
- [ ] FastAPI and Angular stack accepted.
- [ ] Synthetic-only cloud data boundary accepted.
- [ ] $0 budget and no paid fallback accepted.
- [ ] Mac test responsibility accepted.
- [ ] Deferred capabilities accepted.

Checkboxes remain unchecked until Jeevesh explicitly confirms them. An agent
must not infer approval from silence, branch merge, or a different maintainer's
approval.

## Still unresolved

Gemini account eligibility, region, quota, available Live model, key access,
and current terms must be verified separately before the opt-in synthetic live
test. Personal microphone audio remains local in this cycle.

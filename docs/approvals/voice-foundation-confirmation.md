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
| `jeevesh2515` | **Approved, 2026-11-09** | Accepted all six first-cycle items below, including Mac test responsibility. Recorded by Claude Code at his explicit instruction in chat (see the note under the checklist). |

## Jeevesh decision

Jeevesh can record a decision by reviewing the pull request containing this
file. An approval means agreement with every first-cycle bullet above and
acceptance of responsibility for running the documented macOS checks. A change
request must identify the disputed bullet and proposed replacement.

- [x] Direction and first-cycle scope accepted.
- [x] FastAPI and Angular stack accepted.
- [x] Synthetic-only cloud data boundary accepted.
- [x] $0 budget and no paid fallback accepted.
- [x] Mac test responsibility accepted.
- [x] Deferred capabilities accepted.

Checkboxes are ticked only when Jeevesh explicitly confirms them. An agent
must not infer approval from silence, branch merge, or a different maintainer's
approval.

### Recording note (2026-11-09)

`jeevesh2515` wrote each of the six items above in chat on 2026-11-09, stated
that he accepts them, and asked Claude Code (`claude-sonnet-5-5`) to tick them.
The boxes were ticked on that instruction and nothing else. They are approvals
of the first-cycle scope only. They do not close RT-G00 or any runtime gate,
do not authorize personal microphone audio to any cloud provider, and do not
authorize spend. He accepted Mac test responsibility; the Mac evidence itself
is still to be run and recorded.

### Scope-approval confirmation (R-00.1, 2026-11-09)

`abhishek3059` confirmed in chat on 2026-11-09 that he approves the
first-cycle scope, alongside the recorded approvals of `jeevesh2515` above.
Recorded by the delivery-manager agent (OpenCode, model GLM-5.3-Flash Free) at
his instruction. This approves the first-cycle scope only. It does not close
RT-G00 or any runtime gate, does not authorize personal microphone audio to
any cloud provider, and does not authorize spend.

## Still unresolved

Gemini account eligibility, region, quota, available Live model, key access,
and current terms must be verified separately before the opt-in synthetic live
test. Personal microphone audio remains local in this cycle.

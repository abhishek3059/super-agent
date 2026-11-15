# Gemini Live in the console: testing exception to the data boundary

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Scope | Real microphone audio from the voice console goes to Gemini Live, for testing by the maintainers only. Opt-in through `SUPER_AGENT_ADAPTER=gemini`; the model has two tools, a calculator and the local clock. |
| Departs from | The PH-00 data boundary (R-00.4, "personal microphone audio stays local"), [AGENTS.md](../../AGENTS.md) section 5, [REQ-13](../../prd.md#req-13), and the open decision R-A.2 (see [DEC-18](../../descisions.md#dec-18)). |
| `abhishek3059` | **Approved, 2026-11-13**, in chat with Claude Code: "it's testing time as of now; we don't require a privacy feature because nobody is using it". |
| `jeevesh2515` | **Approved, 2026-11-13**, in a [PR #41 review](https://github.com/abhishek3059/super-agent/pull/41#pullrequestreview-5893054740). |
| Effect | Nothing is ticked and no gate moves. The default adapter is still the fake one. |

## Conditions

1. Nobody speaks personal or sensitive topics. The free tier may use inputs for training.
2. Opt-in only. The fake adapter stays the default and CI never uses Gemini.
3. The key comes from the process environment only. It is never logged, printed, or committed. Transcripts are shown in the console for the session only and are never logged.
4. Tools are limited to the calculator and the clock. Like the calculator in [PR 36](https://github.com/abhishek3059/super-agent/pull/36), this is a small widening of tier T0 that both maintainers should confirm in review.
5. This exception expires when R-A.2 is decided. Until then it covers testing only, not users.

## Still open

Whether the data-boundary decision (R-A.2, OD-1) allows real voice to a cloud provider for anyone beyond the maintainers. This record does not answer it.

## Widening, 2026-11-14

`jeevesh2515` approved in chat with Claude Code on 2026-11-14 that, for
testing only, the Gemini console may also get these tools, each off unless
switched on:

- **Weather:** the free Open-Meteo service. It receives the place name, the
  coordinates that name resolves to (for the forecast), and the Mac's IP address.
- **Memory and reminders:** stored facts and reminders reach Gemini when they
  bear on a turn, and Gemini may save new ones the user asks for.
- **Approved actions:** open a page, search the web, or open an allowed app,
  each only after a click on the console card.
- **Continuity:** a short summary of the last session is kept on the Mac
  (mode 0600, can be forgotten) and starts the next session.

Reading files, notes, mail, or calendar stays off with Gemini. Under
[DEC-21](../../descisions.md#dec-21) this approval is enough. Condition 1
above changes: facts the user chooses to store are personal data sent to
Google's free tier, which may train on it. The user accepts that for testing.
Conditions 2, 3, and 5 still hold. Condition 4 is replaced by this list.

### Known limits (2026-11-15, disclosure only, no scope change)

- Saved facts are not put in the session instruction. They reach Google only
  when the model calls a memory tool for a turn.
- A memory write or forget is gated on the user's words as Gemini transcribed
  them, so provider text alone is that gate. Forgetting a fact is a soft
  delete that `undo_forget` restores for 24 hours, which is why it needs no
  click. Forgetting the saved summary sets the file aside and
  `restore_conversation` brings it back for 24 hours (the same window), unless
  a newer summary has been saved, which is never overwritten. Both forgetting
  and restoring the summary need a click on the console card.
- The weather service sees coordinates and the IP address, not only the name.
- On 2026-11-15 `jeevesh2515` decided in chat that forgetting the recap must be recoverable, so no permanent delete exists in this slice.

## Design acceptance, 2026-11-15

`jeevesh2515` decided this on 2026-11-15, in chat with Claude Code. The agent
described the three slice designs in one direct question (tier 1 read tools,
local memory and reminders, and the Gemini tools) and he chose "Accept all
three". Under [DEC-21](../../descisions.md#dec-21) one maintainer's decision
is enough. Nothing is ticked.

The [design](../design/gemini-tools.md) is accepted for the slice as built, for
testing only. Its tools, each off unless its switch is on: `get_weather`; the
memory tools `remember_fact`, `list_memory`, `add_reminder`, `list_reminders`,
`complete_reminder`, `forget`, `undo_forget`; `forget_conversation` and
`restore_conversation` for the session recap; and the three approved actions
in the [T3 record](t3-actions-exception.md). Speech, and any saved text these
tools read or write, reaches Google's free tier during testing.

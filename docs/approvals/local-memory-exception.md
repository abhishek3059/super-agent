# Local memory and reminders: out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Scope | Local memory of facts and reminders for the voice assistant ([design](../design/local-memory-reminders.md)), opt-in with `SUPER_AGENT_MEMORY=on`, on branch `feat/local-memory-reminders`. |
| Roadmap position | Tier T2 work. R-A.6 and R-A.7 start after RT-G03 (PH-03 exit); PH-01 is current. |
| `jeevesh2515` | **Requested and approved, 2026-11-14**, in chat with Claude Code (`claude-opus-5-5`): "Add local memory and reminders as the next feature ... lets continue to work on these step by step". |
| `abhishek3059` | Not required: under [DEC-21](../../descisions.md#dec-21) (2026-11-14) one maintainer's approval is enough. He also reviewed PR #45 on 2026-11-14. |
| Effect | Nothing is ticked and no gate moves. Off by default. |

## Decided and still open

1. Decided by `jeevesh2515`'s approval above: this T2 work may merge before
   the PH-02 policy layer and PH-03 stop controls exist, as an exception to
   R-A.6 and R-A.7. Both stay unticked.
2. Open: acceptance of the independent review recorded in the PR.
3. Open: The retention rule for memory under [REQ-14](../../prd.md#req-14): today
   facts and reminders stay until the user forgets them.

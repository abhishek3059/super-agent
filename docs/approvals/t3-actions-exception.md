# Approved actions: out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Scope | Three actions on the Mac (open an https page, search the web, open an allowlisted app), each only after a click on the console on this machine ([design](../design/t3-approved-actions.md)), opt-in with `SUPER_AGENT_ACTIONS=on`, on branch `feat/t3-approved-actions`. |
| Roadmap position | Tier T3 work. R-A.8 and R-A.9 start after RT-G03 (PH-03 exit); PH-01 is current. This is out-of-order work on those items. |
| `jeevesh2515` | **Requested and approved, 2026-11-14**, in chat: asked to build and test the next tier, with limits that are not a security risk. |
| `abhishek3059` | Not required. Under [DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough, and `jeevesh2515` gave it above. Review of the PR that carries this record is still welcome. |
| Independent security review | **Done by a reviewer agent, human acceptance pending.** A separate reviewer agent (Claude Sonnet) scored the first version 7.7 of 10 (the card could cut off part of an approved address). After the fixes it scored 8.6 (correctness 9, security 8.5, honesty 8.5, scope 8.5, clarity 8.5). Findings and fixes are in the PR. R-A.8 asks for a review a maintainer accepts; that has not happened. |
| Effect | Nothing is ticked and no gate moves. Off by default, and off on any system that is not a Mac. |

## What still needs a decision

1. Whether this T3 work may merge before the PH-02 policy layer and PH-03 stop
   controls exist, as an exception to R-A.8 and R-A.9.
2. Acceptance of the independent security review, once it is recorded.
3. Whether the limits in the design are acceptable: no emergency stop yet, and
   the path of an approved address is only limited to 64 plain characters.

## Limits of this exception

- Only the three tools in the design. No shell, no files, no messages, no
  purchases, and no credential handling. Those stay behind their own approved
  designs (T4 stays disabled).
- Every action needs a click on this machine. Voice alone never approves
  ([REQ-09](../../prd.md#req-09)).

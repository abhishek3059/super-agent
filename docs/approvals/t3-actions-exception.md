# Approved actions: out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Scope | Three actions on the Mac (open an https page, search the web, open an allowlisted app), each only after a click on the console on this machine ([design](../design/t3-approved-actions.md)), opt-in with `SUPER_AGENT_ACTIONS=on`, built on branch `feat/t3-approved-actions`, landing through `feat/gemini-tools` ([PR 48](https://github.com/abhishek3059/super-agent/pull/48)). |
| Roadmap position | Tier T3 work. R-A.8 and R-A.9 start after RT-G03 (PH-03 exit); PH-01 is current. This is out-of-order work on those items. |
| `jeevesh2515` | **Requested and approved, 2026-11-14**, in chat: asked to build and test the next tier, with limits that are not a security risk. |
| `abhishek3059` | Not required. Under [DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough, and `jeevesh2515` gave it above. Review of the PR that carries this record is still welcome. |
| Independent security review | **Done by reviewer agents; accepted by `jeevesh2515` on 2026-11-15 (see the decisions below).** A separate reviewer agent (Claude Sonnet) scored the first version 7.7 of 10 (the card could cut off part of an approved address). After the fixes it scored 8.6 (correctness 9, security 8.5, honesty 8.5, scope 8.5, clarity 8.5). Those two scores were reported in chat and have no saved record. The shared reviewer ([DEC-19](../../descisions.md#dec-19)) then reviewed the code twice on 2026-11-15. Its second report found no code defect and no path where an action runs without a click. |
| Effect | Nothing is ticked and no gate moves. Off by default, and off on any system that is not a Mac. |

## Decisions, 2026-11-15

`jeevesh2515` decided these on 2026-11-15, in chat with Claude Code. The agent
showed him the shared reviewer's findings, named the two limits in item 3, and
asked the question directly. He chose "Accept T3". Under
[DEC-21](../../descisions.md#dec-21) one maintainer's decision is enough.

1. This T3 work may merge before the PH-02 policy layer and PH-03 stop
   controls exist, as an exception to the order of R-A.8 and R-A.9. Both items
   stay unticked.
2. The security review is accepted: the shared reviewer's reports of
   2026-11-15, posted as comments on PR 48.
3. The limits in the design are accepted for now: no emergency stop yet, and
   the path of an approved address is limited to 64 plain characters.
4. Merging before R-A.8 is ticked rests on [DEC-22](../../descisions.md#dec-22),
   which he approved the same day.

## Limits of this exception

- Only the three tools in the design. No shell, no files, no messages, no
  purchases, and no credential handling. Those stay behind their own approved
  designs (T4 stays disabled).
- Every action needs a click on this machine. Voice alone never approves
  ([REQ-09](../../prd.md#req-09)).

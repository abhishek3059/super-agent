# Phase pull-request log

One place to see which pull request is carrying the current phase and what that
PR does not cover. The checklist of record is [roadmap.md](../../roadmap.md);
this file is a status pointer, not evidence and not a gate.

## Convention

- One pull request per phase, or per phase work bundle. The title starts with
  the phase ID, for example `PH-00: ...`.
- The PR body lists what changed and what did not change.
- Items whose evidence is already merged may be ticked in the phase PR. Items
  whose only evidence is the open phase PR are ticked in a small follow-up
  bookkeeping PR after the phase PR merges.
- Update this file in the phase PR and again in the bookkeeping PR.

## Current phase PR

| Field | Value |
| --- | --- |
| Phase | PH-00: runtime eligibility, consent, and setup decisions |
| PR | [#21](https://github.com/abhishek3059/super-agent/pull/21) |
| Branch | `docs/ph-00-consolidated` |
| Status | open, awaiting review |
| Application state | Offline fake adapter only. The Gemini Live adapter and opt-in synthetic live test are not implemented (R-01.7 to R-01.9). |
| Scope | PH-00 documentation: setup decisions, provider verification, roadmap evidence for already-merged work, task status, README learnings link, current application-state audit, doc corrections, and this log |
| Not in scope | Runtime code, provider calls, microphone capture, spend, PH-01 implementation, and ticks for items whose evidence is only in this open PR |
| After merge | A follow-up bookkeeping PR ticks R-00.3 to R-00.11, records the final RT-G00 resolution, marks PH-00 done, moves `Current phase` to PH-01, and adds R-R.6 |

This PR consolidates the superseded PRs
[#18](https://github.com/abhishek3059/super-agent/pull/18),
[#19](https://github.com/abhishek3059/super-agent/pull/19), and
[#20](https://github.com/abhishek3059/super-agent/pull/20). Their changes are
preserved here. The originals were consolidated at the operator's request to
keep one PR per phase.

## Recent phase-related PRs

| PR | Title | Status | Note |
| --- | --- | --- | --- |
| [#13](https://github.com/abhishek3059/super-agent/pull/13) | `feat(voice): scaffold offline voice session` | merged | Offline scaffold; no provider calls. |
| [#14](https://github.com/abhishek3059/super-agent/pull/14) | `fix(ci): quote Python binary-only option` | merged | Voice CI green on Windows and macOS. |
| [#15](https://github.com/abhishek3059/super-agent/pull/15) | `docs: refresh status after merges and add SECURITY.md` | merged | Status and security pointer. |
| [#16](https://github.com/abhishek3059/super-agent/pull/16) | `docs: record Gemini verification and add learnings folder` | merged | Provider verification and learnings index. |
| [#17](https://github.com/abhishek3059/super-agent/pull/17) | `docs: record Jeevesh's approvals; add roadmap.md with CI guard` | merged | Approvals and roadmap guard. |
| [#18](https://github.com/abhishek3059/super-agent/pull/18) | `docs(roadmap): tick R-00.1, R-00.2, R-01.2 and R-R.1 with evidence` | consolidated | Changes preserved in #21. |
| [#19](https://github.com/abhishek3059/super-agent/pull/19) | `docs(readme): link learnings index` | consolidated | Changes preserved in #21. |
| [#20](https://github.com/abhishek3059/super-agent/pull/20) | `docs(ph-00): record setup decisions and RT-001 progress` | consolidated | Changes preserved in #21. |
| [#21](https://github.com/abhishek3059/super-agent/pull/21) | `PH-00: consolidate setup evidence and document voice state` | open | Current PH-00 PR. |

## Next phase PR

PH-01 is not started. After the PH-00 bookkeeping PR merges, the next phase PR
will be titled `PH-01: ...` and will cover only the approved PH-01 work. The
human checks R-01.3 and R-01.4 must be recorded before implementation items
that depend on them.

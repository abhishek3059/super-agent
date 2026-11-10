# Phase pull-request log

One place to see which pull request is carrying the current phase and what that
PR does not cover. The checklist of record is [roadmap.md](../../roadmap.md);
this file is a status pointer, not evidence and not a gate.

## Convention

- One pull request per phase, or per phase work bundle. The title starts with
  the phase ID, for example `PH-00: ...`.
- The PR body lists what changed and what did not change.
- Keep one branch and one PR open until the approved phase or work bundle is
  complete. Add code, tests, evidence records, documentation, and status edits
  to that PR. Do not create a separate bookmark or bookkeeping PR for each
  status change.
- Use a follow-up PR only when the evidence can exist only after merge or when
  the operator explicitly requests one.

## Current phase PR

| Field | Value |
| --- | --- |
| Phase | PH-01: local boundary and native voice connection |
| PR | [#24](https://github.com/abhishek3059/super-agent/pull/24) |
| Branch | `docs/ph-00-close` |
| Status | open PH-01 work bundle |
| Application state | Offline fake adapter only. The Gemini Live adapter and opt-in synthetic live test are not implemented (R-01.7 to R-01.9). |
| Scope | Close PH-00, complete the PH-01 human evidence, credential and security gates, streaming Gemini adapter, real console, synthetic live command, and RT-G01 evidence |
| Not in scope | Personal microphone audio to Gemini, tools, workers, external actions, paid services, or public deployment |
| After merge | PH-01 is complete only if R-01.3 through R-01.10 have evidence; otherwise the same branch and PR remain open |

The macOS owner and their AI agent should follow the
[R-01.3 macOS test handover](r01-3-macos-handover.md). Agent-run output must be
confirmed by Jeevesh because R-01.3 is a human roadmap item.

The operator's [partial microphone observations](r01-4-microphone-observations.md)
are recorded without a PASS or roadmap tick. That record includes an unapproved
proposal to prioritize the revised scaffold; it grants no implementation
authority and changes no gate. The subsequent
[operator direction](../approvals/ph-01-current-phase-work.md) assigns existing
PH-01 local-only implementation while leaving all acceptance blockers open.
The first slice follows the [technical streaming contract](../design/voice-streaming-slice.md).
Its [implementation record](voice-streaming-slice.md) records the completed local
fake slice: 66 backend tests, 39 frontend service cases, 8 epoch cases, and final
code-review PASS results. Hardware, credential, independent security, and native
provider acceptance remain open.

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
| [#21](https://github.com/abhishek3059/super-agent/pull/21) | `PH-00: consolidate setup evidence and document voice state` | merged | Setup decisions and current-state documentation. |
| [#22](https://github.com/abhishek3059/super-agent/pull/22) | `PH-01: design real Gemini voice console` | merged | Design only. It did not start PH-01 implementation. |
| [#23](https://github.com/abhishek3059/super-agent/pull/23) | `PH-00: resolve RT-G00` | merged | RT-G00 resolution and merged-evidence ticks. |
| [#24](https://github.com/abhishek3059/super-agent/pull/24) | `PH-01: close PH-00 and build real voice console` | open | Single branch and PR for the approved PH-01 work bundle. |
| [#25](https://github.com/abhishek3059/super-agent/pull/25) | `docs(ph-01): record R-01.3 macOS offline evidence` | open | Jeevesh's evidence contribution targets `docs/ph-00-close`, not `develop`. It covers the old scaffold at `4f51e00`; awaiting incorporation and the owner's evidence disposition. |
| [#26](https://github.com/abhishek3059/super-agent/pull/26) | `fix(ci): run voice CI on Python 3.14` | open | Separate operator-requested CI interpreter update. It overlaps the voice workflow and two documentation files in this work bundle; integration is not performed here. |
| [#27](https://github.com/abhishek3059/super-agent/pull/27) | `docs(roadmap): record approved PH-01 order and add fix item R-01.F1` | open, approval pending | Proposed roadmap reorder and silence/barge-in fix item. Targets the PH-01 branch; records Jeevesh's approval and Abhishek's pending approval. Not adopted on this branch. |

## Next phase PR

PH-01 is the current phase on this branch. Its Revision 2 design merged in PR
#22. PR #24 remains open while the approved PH-01 scope is implemented and
evidenced. R-01.3 remains the next unticked item; its Mac evidence has been
submitted in PR #25 but is not yet incorporated into this branch. That evidence
does not validate the new streaming implementation.

### Open-PR inspection (2026-11-10)

The latest GitHub query found four open PRs, including the newly opened #27.
No PR was approved, merged, closed, retargeted, or rerun by this inspection.

- #24's published head is still `4f51e00`. All four published checks pass,
  but they do not cover the uncommitted streaming changes. Human review is
  required and the PH-01 implementation and acceptance work remain incomplete.
- #25 contains the original Mac output and owner confirmation, plus saved
  supplementary Python 3.14 backend output. Both test the old scaffold at
  `4f51e00`, not the streaming rewrite.
- #26's repository, Windows voice, and Windows spike checks pass. Its macOS
  voice job was queued at inspection; it also needs human review.
- #25 and #27 show no automatic checks. The current pull-request workflow
  filters do not include their target branch, `docs/ph-00-close`. Absence of
  checks is not a PASS.
- #27's proposed sequencing needs the remaining maintainer approval. The
  request to inspect PRs is not that approval and changes no roadmap item.
- Local status edits overlap #25 and #27, and frontend workflow work overlaps
  #26. Incorporation must preserve evidence and resolve the documentation
  against the actually approved roadmap, without discarding local work.

The free reviewer returned a [remote-head review](../reviews/pull-requests-24-27.md):
#24, #25, and #26 PASS for their published scope; #27 HOLD for pending approval.
The parent verified that #26's previously queued macOS check is now SUCCESS,
so all four of its reported head checks pass. Its separately dispatched voice
run also succeeded on both operating systems at the same head. Human review
is still required. The report lists documentation corrections for evidence,
next-item wording, and explicit approval records. This is not review of the
uncommitted streaming implementation or independent security acceptance.

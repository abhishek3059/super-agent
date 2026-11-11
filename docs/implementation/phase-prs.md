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
| Status | open PH-01 work bundle, retargeted to `develop`; all four checks pass, code-owner review pending |
| Application state | Offline fake adapter only. The Gemini Live adapter and opt-in synthetic live test are not implemented (R-01.7 to R-01.9). |
| Scope | Close PH-00, complete the PH-01 human evidence, credential and security gates, streaming Gemini adapter, real console, synthetic live command, and RT-G01 evidence |
| Not in scope | Personal microphone audio to Gemini, tools, workers, external actions, paid services, or public deployment |
| After merge | PH-01 remains in progress until R-01.3 through R-01.10 have evidence and owner acceptance, even if #24 lands on `develop`. Follow-up work uses new PRs. |

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
| [#24](https://github.com/abhishek3059/super-agent/pull/24) | `PH-01: close PH-00 and build real voice console` | open, review pending | Single branch and PR for the approved PH-01 work bundle. Targets `develop`; all four checks pass. A code-owner approval is required before merge. |
| [#25](https://github.com/abhishek3059/super-agent/pull/25) | `docs(ph-01): record R-01.3 macOS offline evidence` | merged | Merged into this branch as `67649aa`. R-01.3 macOS evidence covers the old scaffold at `4f51e00`; the roadmap tick awaits the PH-01 owner. |
| [#26](https://github.com/abhishek3059/super-agent/pull/26) | `fix(ci): run voice CI on Python 3.14` | merged | Merged into `develop` as `f44051c`. Moves voice CI to Python 3.14. |
| [#27](https://github.com/abhishek3059/super-agent/pull/27) | `docs(roadmap): record approved PH-01 order and add fix item R-01.F1` | merged | Merged as `2849361`; the rebased branch carries the same content in `9092bd0`. Records the approved PH-01 order and R-01.F1. Abhishek's approval is recorded in the sequencing record. |
| [#28](https://github.com/abhishek3059/super-agent/pull/28) | `docs(ph-01): independent R-01.5 credential review and design 2.1` | merged | Merged into this branch as `aa9b0b3`. R-01.5 design 2.1 and independent ACCEPT review; the roadmap tick awaits the PH-01 owner. |
| [#29](https://github.com/abhishek3059/super-agent/pull/29) | `feat(voice): streaming seam and offline-tested Gemini Live adapter (R-01.7)` | closed | Competing streaming seam plus a Gemini Live adapter. Not merged. The adapter still needs porting onto this branch's seam. |

## Next phase PR

PH-01 is the current phase on this branch. Its Revision 2 design merged in PR
#22. PR #24 now targets `develop`. PRs #25, #27, and #28 are merged into this
branch, and #26 is merged into `develop`; #29 is closed without merge. R-01.3
manual macOS evidence was run on 2026-11-10 and passed
([evidence record](../approvals/r01-3-macos-evidence.md), merged with PR #25);
it awaits the PH-01 owner's tick. It tested the earlier scaffold at `4f51e00`,
not the streaming implementation, so it does not validate that code. The R-01.5
design and independent review are merged with PR #28 and also await the owner's
tick. R-01.7 remains open: the Gemini Live adapter from #29 must be ported onto
this branch's seam. R-01.F1 and R-01.4 follow the roadmap order.

### Open-PR inspection (2026-11-10, historical)

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

### PR reconciliation (2026-11-11)

- The operator approved merging #25, #27, and #28 into this branch, #26 into
  `develop`, and retargeting #24 to `develop`. #29 stays unmerged.
- #25 merged as `67649aa`, #27 as `2849361` (content carried in `9092bd0` after
  the branch rebase), and #28 as `aa9b0b3`.
- #26 merged into `develop` as `f44051c`. #29 was closed without merge.
- Combined verification on the reconciled branch: 66 backend tests pass on
  Python 3.14.4, 39 browser service cases pass, 8 playback-epoch cases pass,
  the production build is 116.00 kB initial total, `npm audit` reports zero
  vulnerabilities, and `npm run check` reports zero errors.
- Python 3.12 is not installed on this Windows host; the backend run used
  3.14.4 with the locked dependencies.
- #24 is mergeable but GitHub requires one code-owner approval. No approval,
  merge, or roadmap tick is claimed here.

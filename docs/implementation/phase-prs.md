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

## Current phase PR status

| Field | Value |
| --- | --- |
| Phase | PH-01: local boundary and native voice connection (done); PH-02 is the current phase |
| Latest merged phase PR | [#42](https://github.com/abhishek3059/super-agent/pull/42), merged into `develop` as `3d00d59` on 2026-11-13. [PR #58](https://github.com/abhishek3059/super-agent/pull/58) closes PH-01 when it merges. |
| Status | PH-01 is done as of 2026-11-19. PR #58 carries R-01.F9, R-01.F10, and the R-01.10 acceptance, accepted by `abhishek3059` ([decisions record](../approvals/r01-10-decisions.md)). PH-02 starts. |
| Application state | The fake streaming adapter is the default. An opt-in fully local private voice adapter (speech in/out, Silero VAD, macOS say / Kokoro TTS, Ollama local model) is merged (PR #36). Tier 1 read-only tools (PR #43) and Tier 2 local memory and reminders (PR #45) are merged behind explicit flags. An opt-in Gemini Live console testing option with calculator and clock tools exists under an exception (PR #41). Loopback boundary, token authentication, throttling, expiry, and CSP are active. |
| Merged scope (#32) | Ticks for R-01.3, R-01.5, and R-01.F1; credential findings CR-09 and CR-02; R-01.6 auth boundary; R-01.7 adapter port; locked `google-genai`; R-01.8 and R-01.9 live check |
| Merged scope (#34) | Rebuilt voice console and UI self-test, R-01.F2 Windows-portable symlink test, R-01.F3 Origin diagnostic, and R-01.F4 Windows launcher |
| Merged scope (#42) | Recovered R-01.4 operator microphone evidence; closed defects R-01.F5 (post-interrupt playback drop), R-01.F6 (clean SDK exit), R-01.F7 (unexpected provider refusal), and R-01.F8 (pinned Developer API base URL) |
| Not in scope | Personal microphone audio to Gemini outside the testing exception, arbitrary workers, external actions, paid services, or public deployment |
| Merged scope (#58) | R-01.F9 (mutual handshake proof), R-01.F10 (muted keep-alive), boundary review, console run evidence, and the R-01.10 acceptance |
| Remaining gate work | None for PH-01. Open residuals: F2 accepted for maintainer-only testing, boundary review findings B3 to B8, latency targets (PH-03). |

R-01.F2 identifies the Windows test portability fix. F2 in the
[R-01.6 risk acceptance](../approvals/r01-6-f2-risk-acceptance.md) identifies
the independent security review's auth-throttle lockout finding.

The previous work bundle, [#24](https://github.com/abhishek3059/super-agent/pull/24),
merged into `develop` on 2026-11-11. The paragraphs below describe that PR and
are kept as history.

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
| [#24](https://github.com/abhishek3059/super-agent/pull/24) | `PH-01: close PH-00 and build real voice console` | merged | Merged into `develop` as `7f45b17` on 2026-11-11. |
| [#25](https://github.com/abhishek3059/super-agent/pull/25) | `docs(ph-01): record R-01.3 macOS offline evidence` | merged | R-01.3 is ticked. Its Mac evidence covers the old scaffold at `4f51e00`, not the later streaming code. |
| [#26](https://github.com/abhishek3059/super-agent/pull/26) | `fix(ci): run voice CI on Python 3.14` | merged | Merged into `develop` as `f44051c`. Moves voice CI to Python 3.14. |
| [#27](https://github.com/abhishek3059/super-agent/pull/27) | `docs(roadmap): record approved PH-01 order and add fix item R-01.F1` | merged | Merged as `2849361`; the rebased branch carries the same content in `9092bd0`. Records the approved PH-01 order and R-01.F1. Abhishek's approval is recorded in the sequencing record. |
| [#28](https://github.com/abhishek3059/super-agent/pull/28) | `docs(ph-01): independent R-01.5 credential review and design 2.1` | merged | R-01.5 is ticked with the merged design review. |
| [#29](https://github.com/abhishek3059/super-agent/pull/29) | `feat(voice): streaming seam and offline-tested Gemini Live adapter (R-01.7)` | closed | Not merged directly; its adapter was later ported onto the current seam in #32. |
| [#31](https://github.com/abhishek3059/super-agent/pull/31) | `docs(plan): completion plan, JARVIS architecture, and agent hand-off prompt` | merged | Historical planning snapshot; no gate effect. |
| [#32](https://github.com/abhishek3059/super-agent/pull/32) | `PH-01: tick evidenced items, token hardening, and Gemini Live adapter (R-01.7)` | merged | Merged as `651e33c`; R-01.3, R-01.5, R-01.F1, and R-01.6 through R-01.9 are ticked. |
| [#34](https://github.com/abhishek3059/super-agent/pull/34) | `PH-01: rebuild live voice console and Windows launcher` | merged | Merged as `3025155`. R-01.F2, R-01.F3, and R-01.F4 are ticked. |
| [#36](https://github.com/abhishek3059/super-agent/pull/36) | `feat(voice): add an opt-in fully local voice adapter and spike A4` | merged | Merged as `0a9f1b4` on 2026-11-14. Base of #43 and #45. |
| [#42](https://github.com/abhishek3059/super-agent/pull/42) | `fix(ph-01): recover R-01.4 evidence and close playback, close, capture and provider-destination defects (F5-F8)` | merged | Merged on 2026-11-14. Recovers the R-01.4 record and the F5 to F8 fixes. |
| [#43](https://github.com/abhishek3059/super-agent/pull/43) | `feat(voice): tier 1 read-only tools and LFM3-Audio ears and mouth with a 4B brain` | merged | Merged into `develop` as `e9c56c0` on 2026-11-14. |
| [#44](https://github.com/abhishek3059/super-agent/pull/44) | `docs(design): add the Roamies design reference (ideas only, no code)` | merged | Merged on 2026-11-14. Design reference for PH-02, PH-05, and PH-06. Nothing built. |
| [#45](https://github.com/abhishek3059/super-agent/pull/45) | `feat(voice): local memory and reminders (T2) with forget and undo` | merged | Merged into `develop` as `8313146` on 2026-11-14. |
| [#50](https://github.com/abhishek3059/super-agent/pull/50) | `feat(api): agent backend slices 1-5 (ledger, admission, runner, plan graph)` | merged | Merged into `develop` as `677224d` on 2026-11-16. |
| [#54](https://github.com/abhishek3059/super-agent/pull/54) | `feat(api): agent backend slices 6-7 (delegation wiring and Gemini planner seam)` | merged | Merged into `develop` as `d52d894` on 2026-11-17. |
| [#55](https://github.com/abhishek3059/super-agent/pull/55) | `feat(ledger): add PostgreSQL adapter seam and wire 5 Hermes worker bot definitions` | merged | Merged into `develop` as `f719099` on 2026-11-17. |
| [#56](https://github.com/abhishek3059/super-agent/pull/56) | `feat(hq): add Jarvis HQ, a local multi-bot workspace on Hermes` | merged | Merged into `develop` as `c662a12` on 2026-11-19. |
| [#58](https://github.com/abhishek3059/super-agent/pull/58) | `fix(voice): PH-01 bundle: R-01.F9, R-01.F10, review, acceptance` | merged | Merged into `develop` as `1e23730` on 2026-11-19. Phase 1 closed. |
| [#61](https://github.com/abhishek3059/super-agent/pull/61) | `feat(api): local memory distiller for background extraction` | merged | Merged into `develop` as `6c813be` on 2026-11-19. |
| [#62](https://github.com/abhishek3059/super-agent/pull/62) | `feat(api): policy.decide single gate (slice 1)` | merged | Merged into `develop` as `99d9be8` on 2026-11-19. |
| [#63](https://github.com/abhishek3059/super-agent/pull/63) | `docs: app status snapshot and ask-resume flow` | merged | Merged into `develop` as `664fd2a` on 2026-11-20. |
| [#65](https://github.com/abhishek3059/super-agent/pull/65) | `feat(api): local Ollama planner for background jobs` | merged | Merged into `develop` as `d816d71` on 2026-11-20. |
| [#66](https://github.com/abhishek3059/super-agent/pull/66) | `docs(roadmap): tick R-H.2 after PR 56 merged with green CI` | merged | Merged into `develop` as `171e567` on 2026-11-20. |
| [#67](https://github.com/abhishek3059/super-agent/pull/67) | `docs(roadmap): remove R-02.F2, HQ has no ledger admission path` | merged | Merged into `develop` as `f360e28` on 2026-11-20. |
| [#69](https://github.com/abhishek3059/super-agent/pull/69) | `chore(tooling): expand gitignore for secrets, caches, and build artifacts` | merged | Merged into `develop` as `68a6514` on 2026-11-20. |

## Next PH-01 work

R-01.10 is the next acceptance item. The local microphone evidence and the
standalone synthetic Gemini run cover separate paths. RT-G01 requires measured
native media and backend event/control behavior. See the
[gate definition](../../prd.md#rt-g01) and the
[remaining checks and offline fixes](r01-10-acceptance.md).

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

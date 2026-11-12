# Completion plan: status map, gaps, and free brain stack

| Field | Value |
| --- | --- |
| Date | 2026-11-11 |
| Status | Historical planning snapshot. Superseded by merged PRs #24 and #32. Ticks nothing and closes no gate; [roadmap.md](../../roadmap.md) is current. |
| Baseline | `docs/ph-00-close` at `49a9f3f`, when [PR 24](https://github.com/abhishek3059/super-agent/pull/24) was open |
| Hand-off prompt | [fable-handoff-prompt.md](fable-handoff-prompt.md) |

At `develop` `651e33c`, PRs #24, #31, and #32 are merged. R-01.3, R-01.5,
R-01.F1, and R-01.6 through R-01.9 are complete. R-01.4 and R-01.10 remain.
The sections below preserve the 2026-11-11 baseline rather than rewriting its
historical reasoning.

## 1. Branch and PR map at the 2026-11-11 baseline

- `docs/ph-00-close` is the most complete line: 22 commits ahead of
  `develop`, nothing behind. It carries the local streaming slice and merged
  contribution PRs 25, 27, and 28. PR 24 (into `develop`) is green on all four
  checks and waits only on code-owner review.
- `develop` contains everything through PR 26. `main` has only PR 1; the
  release PR is roadmap item R-R.2.
- `feat/r01-7-streaming-seam` (PR 29, closed unmerged) holds the only Gemini
  Live adapter code (`gemini_adapter.py` plus 13 offline tests). It must be
  ported onto the streaming seam from PR 24, not merged.
- Every other remote branch is merged or superseded. Local checkouts now
  track every remote branch and none is behind.

Local test run on `49a9f3f` (macOS, Python 3.14.5, Node 22.22.3):
`npm run check` 0 errors; `python -m pytest apps/api` 66 passed;
`npm run test:epoch` 8 cases PASS; `npm run test:voice` 39 cases PASS.

## 2. Status by phase at the baseline

| Phase | Status | Remaining |
| --- | --- | --- |
| PH-DOC, PH-00 | done | none |
| PH-01 voice boundary | in progress | Tick R-01.3, R-01.5, R-01.F1 (evidence exists, see below); R-01.4 mic test; R-01.6 security review; R-01.7 Gemini adapter; R-01.8 and R-01.9 synthetic live command and run; R-01.10 records and RT-G01 |
| PH-02 ledger and workers | not started | R-02.1 to R-02.6 |
| PH-03 steering, recovery, validation | not started | R-03.1 to R-03.7 |
| PH-04 bounded planner | not started | R-04.1 to R-04.5 |
| PH-05 to PH-07 (optional) | not started | coding-agent adapter, always-on, private native audio |
| Track R | partial | R-R.2 release PR; R-R.3 to R-R.5 are human GitHub settings |
| Track C | not started | after PH-03 |

Evidence that exists but is not ticked:

- R-01.3: [macOS evidence](../approvals/r01-3-macos-evidence.md), run on the
  older scaffold commit; a maintainer must confirm it still counts.
- R-01.5: [credential design review](../reviews/r01-5-credential-design.md),
  accepted at design stage.
- R-01.F1: code in `apps/web/src/app/voice-session.service.ts` and
  `audio-signal.ts` with the 39-case self-test.

## 3. Gaps at the baseline

1. `config.py` checks token length only; review finding CR-09 (low-entropy
   tokens accepted) and the CR-02 token generator are still open in code.
2. [descisions.md](../../descisions.md) DEC-06 still calls Gemini
   eligibility-gated; the approved Gemini choice lives only in
   [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md).
3. [AGENTS.md](../../AGENTS.md) section 8 still lists the `taks/` rename as
   pending; R-DOC.5 is done.
4. Workflow triggers name stale branches (`docs/voice-foundation-design`,
   `fix/restore-reverted-pr-8`).
5. No roadmap item covers REQ-09 (out-of-band approval for high-risk
   actions), REQ-17 (latency limits), RT-G05, the semantic profile, the
   scheduler (REQ-18), or any of the distributed work.
6. [phases.md](../../phases.md) rev 4 still says R-01.3 is next.

## 4. Phase mapping

The [dual-loop and JARVIS architecture](../product/dual-loop-and-jarvis-evolution.md)
uses its own phase numbers. Mapped to the repository:

| Architecture doc | Repository phase | Note |
| --- | --- | --- |
| PH-01 audio pipeline, R-01.F1 | PH-01 | in progress |
| PH-02 Gemini Live adapter | PH-01 (R-01.7 to R-01.9) | already in PH-01 |
| PH-03 session controls, barge-in | PH-01 (R-01.F1, R-01.4) and PH-03 (R-03.1) | |
| PH-04 ledger, turn-boundary queue, slot filling | PH-02 (ledger, workers) and PH-04 (planner, clarifying questions) | profile table and scheduler need new items |
| PH-05 MCP worker sandbox, 3 rings | PH-02 R-02.3 (policy) and PH-05 | ring model needs new items |
| PH-08 to PH-10 central brain, mobile edge, multi-node | none yet | propose as new phases after PH-03 exit, in a roadmap PR |

Adding phases or items needs one roadmap PR that edits
[roadmap.md](../../roadmap.md), [scripts/roadmap-ids.txt](../../scripts/roadmap-ids.txt),
and [phases.md](../../phases.md) together, with both code owners approving.

## 5. Free brain stack (research 2026-11-11)

Constraint: $0 ([PH-00 setup decisions](../approvals/ph-00-setup-decisions.md)).
Google's pricing page lists the Live and Flash models below as free, but
**free-tier content is used to improve Google's products**, so cloud calls
stay synthetic-only per [free-stack.md](../free-stack.md). Real personal use
at $0 means the local path.

| Loop | Primary | Fallback 1 | Fallback 2 | Notes |
| --- | --- | --- | --- | --- |
| Voice (System 1) | Gemini Live `gemini-3.8-live` (sync and async function calling) | `gemini-3.1-flash-live-preview` | Local cascade: Silero VAD, Parakeet (MLX) or whisper.cpp, small Ollama model, Kokoro TTS | Sessions: 15 min audio, about 10 min per connection; enable `contextWindowCompression` and `sessionResumption`, handle `GoAway` |
| Planner (System 2) | Gemini `gemini-3.5-flash-lite` (about 500 RPD, unverified) | Groq `openai/gpt-oss-120b` (about 1K RPD, 200K TPD) | Ollama local Qwen (9B on 16 GB, MoE 35B-A3B on 32 GB) | One `openai` SDK client and a small fallback router; all three are OpenAI-compatible |
| Heavy reasoning | `gemini-3.8-flash` (about 20 RPD, unverified) | Groq `openai/gpt-oss-120b` | local 27B | use sparingly |
| Last resort | OpenRouter `:free` models (50 RPD) | none | | free list changes often |
| Hosting | The Mac plus Tailscale Personal (free, non-commercial) | Oracle Always Free ARM (size disputed: 4 OCPU/24 GB documented, 2/12 reported) | | defer cloud until PH-08 |

Ruled out: GitHub Models (retired 2026-07-30), Cerebras (needs a card).

Environment and endpoints: `GEMINI_API_KEY`, `GROQ_API_KEY`,
`OPENROUTER_API_KEY`, `OLLAMA_BASE_URL=http://localhost:11434/v1`.
Gemini OpenAI-compatible base `https://generativelanguage.googleapis.com/v1beta/openai/`,
Groq `https://api.groq.com/openai/v1`, OpenRouter `https://openrouter.ai/api/v1`.

Unverified, re-check before relying on them: Google's own RPM and RPD table,
the free Live concurrent-session cap (a single user is unaffected), which
Groq models support tools, all local tokens-per-second figures, and the
Oracle ARM size.

Sources: <https://aistudio.google.com/docs/pricing>,
<https://aistudio.google.com/docs/live-api/tools>,
<https://aistudio.google.com/docs/live-api/session-management>,
<https://console.groq.com/docs/rate-limits>,
<https://openrouter.ai/docs/api-reference/limits>,
<https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models>,
<https://docs.oracle.com/iaas/Content/FreeTier/resourceref.htm>,
<https://tailscale.com/pricing>.

## 6. Recommended order at the baseline

1. Merge PR 24 into `develop` (code-owner review), then tick R-01.3, R-01.5,
   R-01.F1 with their evidence.
2. R-01.7: port the PR 29 Gemini adapter onto the PR 24 seam, model ID from
   config, offline tests with a fake SDK.
3. R-01.8, R-01.9: opt-in synthetic live command and run.
4. R-01.4 mic test (human), R-01.6 security review, R-01.10 records. PH-01 done.
5. PH-02: SQLite ledger, policy, two read-only workers off the event loop,
   plus the provider fallback router for System 2.
6. PH-03: steering, stops, recovery, retention, latency measurement.
7. Roadmap PR adding the profile table, scheduler, permission rings, and
   PH-08 to PH-10.
8. PH-04 planner with slot filling, then the optional and distributed phases.

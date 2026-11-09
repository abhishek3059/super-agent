# PH-00 setup decisions

| Field | Value |
| --- | --- |
| Date | 2026-11-09 |
| Scope | PH-00 and RT-001 setup decisions before PH-01 implementation |
| Decider | `abhishek3059`, maintainer, in chat on 2026-11-09 |
| Earlier approval | `jeevesh2515` approved the first-cycle scope on 2026-11-09 in the [voice-foundation confirmation](voice-foundation-confirmation.md) |
| Runtime status | This record alone closes no runtime gate. RT-G00 remains open until every item below is evidenced and the record is merged. |

This record turns the operator's 2026-11-09 chat answers into dated decisions.
It does not invent approval, does not authorize personal microphone audio to a
cloud provider, and does not authorize spend.

## Decisions

| Item | Decision | Boundary |
| --- | --- | --- |
| R-00.3 first real task pair | **Local document summary and action-item extraction.** Task A summarizes one named local Markdown document. Task B extracts open questions and action items from the same document. | Read-only local repository documents only. No personal data, no network, no file writes, no tools, and no external actions. A later planner must ask clarifying questions before acting. |
| R-00.5 retention | Job metadata is deleted **24 hours after the job reaches a terminal state**. Session-scoped records are deleted when the session ends. No raw audio, transcripts, or model-content logs are retained. | Applies to the future job ledger. The current voice scaffold stores no job records. |
| R-00.5 retry | At most **2 automatic retries per job**, only for idempotent read-only steps. No retry after an unknown outcome. No retry for external effects, which are not authorized. | The retry count and stop condition must be enforced outside the model. |
| R-00.5 hosts | **Windows and macOS** are the confirmed development hosts. | macOS evidence still has to be run and recorded by `jeevesh2515`. |
| R-00.8 PH-01 authorization | **Authorized beyond the merged offline scaffold:** credential design, independent security review, Gemini Live adapter behind the replaceable seam, and an opt-in synthetic-audio live test. | Synthetic PCM only. Personal microphone audio stays local. No tools, shell, plugins, calls, messages, purchases, or other external actions. |
| R-00.9 secret setup | **`GEMINI_API_KEY` in the process environment.** No project `.env` file. No key in the repository, browser code, URLs, or logs. | The operator confirmed on 2026-11-09 that the key is set in an interactive PowerShell process environment using a secure prompt. The variable is session-scoped; the agent process cannot see it, and no value is recorded here. The opt-in live test must be launched from that same shell, or the operator can set a User-level variable before the agent runs it. No key file is used or required. |
| R-00.4 data boundary | **Synthetic-only cloud data boundary.** Gemini is the named cloud recipient for generated synthetic text or audio only. Personal microphone audio stays local. | Both maintainers accepted this boundary in the first-cycle confirmation. No other cloud recipient is approved. |
| R-00.6 budget | **$0 cap with no paid fallback.** | No paid service, plan, or API may be used. A free tier is not a spending approval. |
| R-00.10 provider disclosure | Gemini terms, provider retention, and recipients are recorded in the [Gemini account verification](../implementation/gemini-account-verification.md). | The unpaid tier may use inputs for product improvement and human review. No fixed provider deletion window is stated. Synthetic data only. |

## Task-pair detail

The pair is deliberately narrow so it can be validated without new authority:

1. **Summarize a named local document.** Input: one Markdown file already in
   the repository. Output: a short summary with the main points and any stated
   limits.
2. **Extract open questions and action items.** Input: the same file. Output:
   a reviewable list of open questions, owners where stated, and concrete next
   actions.

Both tasks are read-only and local. They do not prove general planning ability,
do not authorize a worker to change files, and do not grant voice any new
authority.

## Secret setup confirmation (2026-11-09)

`abhishek3059` confirmed in chat that he ran the secure prompt and set
`$env:GEMINI_API_KEY` in an interactive PowerShell session. The agent's checks
of the process, user, and machine scopes all returned false because the
variable is session-scoped and the agent is a separate process. No value was
read or recorded. This is an operator confirmation, not independent agent
verification.

## What is still missing before RT-G00 can be resolved

- The operator must launch the opt-in synthetic live test from the shell that
  holds `GEMINI_API_KEY`, or set a User-level variable before the agent runs it.
- This record must be reviewed and merged. An open pull request is not evidence.
- RT-001 must record the final setup decision, and the roadmap must show the
  RT-G00 evidence.
- Any macOS or microphone evidence remains separately required by PH-01.

## Non-claims

- No provider call, microphone capture, audio upload, or spend happened while
  recording these decisions.
- No runtime gate, phase gate, or task acceptance is closed by this file alone.
- No secret value is stored in this repository or this record.

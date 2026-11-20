# Learnings

Short, dated notes on what we learned while building. Each note is written
when a spike, phase, or incident ends, so the next person (or agent) does not
repeat the mistake or redo the experiment.

These notes are evidence-backed observations, not decisions. A decision still
goes in [descisions.md](../../descisions.md).

## Index

| Date | Note | Topic |
| --- | --- | --- |
| 2026-11-07 | [Spike A2: permission hook](2026-11-07-spike-a2-permission-hook.md) | Answering agent permission prompts from outside the terminal |
| 2026-11-07 | [Spike A3: Gemini Live](2026-11-07-spike-a3-gemini-live.md) | Latency, tool calling, and client pitfalls |
| 2026-11-08 | [Stacked PRs and the PR #8 accident](2026-11-08-stacked-prs-and-pr8-accident.md) | Process lesson |
| 2026-11-09 | [Gemini account verification](2026-11-09-gemini-verification.md) | Terms, region, quota, and what they mean for open source |
| 2026-11-10 | [R-01.3 macOS checks](2026-11-10-r01-3-macos-checks.md) | Running the offline voice checks on a Mac; interpreter and evidence lessons |
| 2026-11-10 | [R-01.5 credential review](2026-11-10-r01-5-credential-review.md) | Loopback credentials: lockout as an attack, per-OS storage, localhost CSRF |
| 2026-11-11 | [Bounded teardown and focused review](2026-11-11-bounded-teardown-and-focused-review.md) | Cleanup ownership, deterministic overflow, and logging uncertainty without review loops |
| 2026-11-12 | [Platform-specific security fixtures](2026-11-12-platform-specific-security-fixtures.md) | Preserve POSIX security coverage without requiring privileged Windows test setup |
| 2026-11-12 | [Loopback names are different Origins](2026-11-12-loopback-origin-aliases.md) | Diagnose strict local Origin rejection without widening the allowlist |
| 2026-11-12 | [Launch scripts should locate their own checkout](2026-11-12-location-independent-windows-launcher.md) | Start both local services without depending on the caller's working directory |
| 2026-11-12 | [Stop playback across the provider boundary](2026-11-12-provider-audio-after-stop.md) | Keep late provider audio out of the new playback epoch |
| 2026-11-12 | [Local voice stack](2026-11-12-local-voice-stack.md) | A private pipeline works at about two seconds; proxies and small-model honesty need guarding |
| 2026-11-14 | [Memory needs a guard against what it reads](2026-11-14-local-memory-reminders.md) | Block memory writes after reading outside text; mark reminders only after they are spoken |
| 2026-11-15 | [Call controls across voice providers](2026-11-15-openai-call-controls.md) | Scripted call controls, response identity and playback evidence |
| 2026-11-17 | [Jarvis HQ: adapting Bot HQ to run locally](2026-11-17-jarvis-hq-local-team.md) | Handoffs that always return, headless tab visibility, artwork licensing |
| 2026-11-19 | [Closing PH-01](2026-11-19-ph-01-close.md) | Accepting native-media evidence from a synthetic-speech harness, and what stayed unrecorded |
| 2026-11-20 | [CODEOWNERS self-approval bypass and local Ollama planner](2026-11-20-codeowners-autonomy-and-local-planner.md) | Admin bypass under DEC-22, in-process Ollama planner, and secret file hygiene |

## How to add a note

1. Copy the template below to `YYYY-MM-DD-short-topic.md`.
2. Keep it under one page. Link the evidence (spike README, PR, record) instead of repeating it.
3. State what is verified and what is a guess. Never record a secret, a personal location, or real audio.
4. Add a row to the index above in the same PR.

```markdown
# Title

| Field | Value |
| --- | --- |
| Date | YYYY-MM-DD |
| Evidence | link to spike, PR, or record |

## What happened
## What we learned
## What to do differently
## Still unknown
```

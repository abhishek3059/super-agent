---
title: "A working local assistant is not done: the operator's bar is 90 out of 100 for a JARVIS-like feel"
author: Jeevesh2515
date: 2026-11-12
branch: fix/ph-01-acceptance
cost: { minutes: 1, tokens: 1254 }
id: l-8e1e5715
scope: repo
status: active
src: agent
---

## Decided
The operator tested the fully local voice assistant and it worked, but he rated it 66 out of 100. The target is at least 90 before it counts as a JARVIS-like system. Treat "it works" as the start of the quality work, not the end.

## Tried and ruled out
- Nothing ruled out yet. The reasons for the 66 score were not given; ask before assuming.

## Watch out
- Likely gaps, from measurements and not from the operator: two to three seconds before the reply starts, a robotic built-in voice, talk only with no actions or memory, crude end-of-speech detection.
- New capabilities must follow the capability ladder (tiers T0 to T4), each tier with its own approved design.
- The founder-style business skills (board, competitors, pricing and so on) are not installed here; the replica pack is.

In the code:
- apps/api/src/super_agent_voice/local_adapter.py and docs/approvals/local-voice-microphone-test.md, both on branch feat/local-voice-adapter (PR 36), not yet in develop
- spikes/a4-local-voice/README.md for the measured numbers

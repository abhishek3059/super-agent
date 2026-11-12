---
title: "The voice assistant should run on local private models, not Gemini, wherever the Mac can handle it"
author: Jeevesh2515
date: 2026-11-12
branch: fix/ph-01-acceptance
cost: { minutes: 30, tokens: 464780 }
id: l-f1baf2d9
scope: repo
status: active
src: agent
touches:
  - apps/api/src/super_agent_voice/gemini_adapter.py
  - apps/api/tests/test_gemini_adapter.py
  - apps/voice-foundation.md
  - apps/web/scripts/selftest-voice-session.mjs
  - apps/web/src/app/voice-session.service.ts
  - docs/design/synthetic-voice-console.md
  - docs/implementation/r01-10-acceptance.md
  - docs/implementation/r01-7-gemini-adapter.md
  - roadmap.md
  - scripts/roadmap-ids.txt
---

## Decided
The operator wants the assistant to stay private and inside the computer. Prefer a fully local pipeline over the Gemini cloud path. English first. Conversation only until the capability ladder tiers are approved.

## Tried and ruled out
- Native speech-to-speech models: none fits in 16 GB next to a language model.
- Voicebox and similar apps: they wrap the same parts and have no conversation loop.
- Kokoro as the default voice: its Python package depends on GPL-3.0 code and had dependencies newer than the 14-day rule. It stays opt-in.

## Watch out
- Python's default HTTP opener sends loopback requests through a configured proxy. Use an opener with no proxy handler for anything that must stay local.
- A small model will say it did an action it never did unless the prompt forbids it.
- The Mac is short on memory; reply delay is about two seconds and gets worse under swap.
- This is PH-07 work ahead of roadmap order and needs both maintainers' approval before merge.

In the code:
- apps/api/src/super_agent_voice/local_adapter.py, selected with SUPER_AGENT_ADAPTER=local
- spikes/a4-local-voice/README.md for the measurements
- Models: qwen3.5:9b through Ollama on 127.0.0.1:11434, whisper.cpp ggml-base.en.bin, macOS say
- PR 36 on branch feat/local-voice-adapter

# Call controls across voice providers

| Field | Value |
| --- | --- |
| Date | 2026-11-15 |
| Scope | PH-01 offline call controls |
| Evidence | [Call spike](../../spikes/a6-openai-call/README.md) |

## What happened

BotHQ and the Grokbot clone use the same browser voice code. Their xAI
session and worker execution follow separate paths. A scripted OpenAI Realtime
transport exercised the existing Jarvis WebSocket bridge with synthetic PCM.

## What we learned

The application can separate playback from provider response lifecycle.
Response identity lets it discard late cancelled audio while allowing a
later reply. Tool authority and worker completion belong to the application.
Provider-specific event shapes still need separate adapters. The probe's
streaming conversion preserves PCM across capture-frame boundaries and resets
on Mute. A scripted burst tests delivery beyond the bridge queue length.

## What to do differently

Track what the player actually played before sending Realtime truncation.
Check whether GPT-Live's continuous output meets the same cutoff and recovery
criteria before selecting the normal provider.

## Still unknown

Live account and transport behavior, acoustic cutoff, native browser capture
and measured latency remain unverified. This spike leaves the PH-01 gate open.

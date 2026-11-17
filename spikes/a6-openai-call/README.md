# A6. OpenAI call controls through the local voice bridge

The offline PH-01 tests inject a scripted transport into the shared
[OpenAI adapter](../../apps/api/src/super_agent_voice/openai_realtime.py).
They open no provider socket, read no key and capture no microphone. The
[standalone OpenAI check](../../docs/implementation/jarvis-operator-preview.md#openai-synthetic-tool-check)
uses the same adapter with a pinned live transport. The browser launcher has
no OpenAI provider setting in this work bundle.

## What the reference apps do

BotHQ (`decf9a2`) and the Grokbot clone (`7ee6a7e`) have identical browser call
and capture files. The browser captures mono PCM through an AudioWorklet.
The server verifies bot ownership and requests a short-lived xAI credential.
The browser opens the xAI Realtime WebSocket, sends configuration, and streams
audio after the ready acknowledgment. At speech start it clears the player and
requests cancellation of the current response. Work requests go to the bot
backend through `send_task`. BotHQ enqueues a Hermes turn and watches for a
result to read aloud. The browser call is a realtime audio session.

[BotHQ call controller](https://github.com/nickvasilescu/bot-hq/blob/decf9a215cddd8792a5f20f4a11a87d4dffa6d15/web/src/voice/call.ts#L96-L174)
· [BotHQ audio capture](https://github.com/nickvasilescu/bot-hq/blob/decf9a215cddd8792a5f20f4a11a87d4dffa6d15/web/src/voice/audio.ts#L68-L105)
· [BotHQ credential and handoff](https://github.com/nickvasilescu/bot-hq/blob/decf9a215cddd8792a5f20f4a11a87d4dffa6d15/server/src/voice.ts#L240-L315)
· [Grokbot call controller](https://github.com/nickvasilescu/grokbot-clone/blob/7ee6a7ed8464311dbb467bb9ee7c76d9286e56be/web/src/voice/call.ts#L96-L174).

## What we exercised

The existing FastAPI `/ws/voice` route used the probe as its adapter. The
cases cover authenticated startup, rejected tokens, a tool-free configuration,
two-way synthetic PCM, mute, stopping playback, late old-response audio,
speech-start interruption, Stop after the input is committed but before the
response ID arrives, a cancel racing with completion, End, and provider errors.
The probe converts 16 kHz capture fixtures to 24 kHz across frame boundaries.
Mute resets that conversion and sends a provider clear request. An 18-frame
fixture exercises a provider burst through the bridge's 16-frame output queue.
Scripted caption events are bounded, scoped to the current item or response,
and ephemeral. End verifies the scripted transport closes.
Live provider acknowledgment, browser playback cutoff, and backpressure with a
slow client remain unmeasured. The probe dispatches no workers.

From the repository root, use the existing backend test environment:

```sh
PYTHONPATH=apps/api/src python -B -m pytest -p no:cacheprovider spikes/a6-openai-call
```

In PowerShell, set `$env:PYTHONPATH = 'apps/api/src'` before running the same
Python command. Use the backend environment from the
[voice setup guide](../../apps/voice-foundation.md).

## Next provider decision

The spike uses OpenAI Realtime's explicit response IDs and cancellation
events to test the same control scenario as BotHQ. The conversion tested here
runs inside the shared adapter. A browser Realtime integration needs capture
format validation and timing measurements with the browser. For its WebSocket
transport it also needs item IDs and played milliseconds
from the browser so interrupted audio can be truncated in model context.
The pre-response Stop case uses a known committed input. A production design
still needs a policy for Stop before the provider acknowledges that input.
GPT-Live can use 16 kHz PCM and has a distinct close confirmation. Its
WebSocket output lacks a turn-done marker. Compare the player cutoff, next
reply and provider cleanup for both candidates before choosing one.

[Realtime voice and truncation](https://developers.openai.com/api/docs/guides/realtime-conversations#interruption-and-truncation)
· [GPT-Live WebSocket events](https://developers.openai.com/api/docs/guides/voice-websockets?api=live).

Before a live test, qualify the provider account and data boundary and
address loopback server authentication. Use generated audio and preserve the
$0 cap until the maintainer approves another budget. A call must report
playback and transport outcomes separately. Deferred worker handoff should use
the local ledger's stable job IDs and verified receipts. See the
[runtime proposal](../../docs/design/subscription-backed-runtime.md) and
[PH-01 acceptance record](../../docs/implementation/r01-10-acceptance.md).

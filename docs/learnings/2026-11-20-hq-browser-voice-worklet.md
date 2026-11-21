# Load the microphone worklet under HQ's script policy

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Evidence | [Chrome verification](../implementation/jarvis-hq-voice-check.md#browser-worklet-fix-2026-11-20) |

The old worklet used a blob URL. Chrome rejected it under the production
Content Security Policy. The processor is now a same-origin build asset.
Check the built app in a browser, since the synthetic WebSocket probe
does not load the microphone processor. Verify provider availability
before requesting microphone access.

# Hermes gateway startup inside HQ

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Evidence | [Provider workspace recovery](../implementation/jarvis-hq-local-run.md#provider-workspace-recovery-2026-11-20) |

A healthy HQ HTTP endpoint can coexist with a failed worker. Run a synthetic
chat through the worker before calling its provider connected. Keep the model
and credential seed separate from runtime binaries, and record the Hermes
revision and ports used for each run.

Test the state directory check alongside the root rename and deletion denials.
A newer Hermes runtime that needs another listener requires an integration
design that preserves HQ's per-bot port restrictions.

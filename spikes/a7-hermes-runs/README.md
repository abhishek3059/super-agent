# A7. Local Hermes Runs smoke test

This opt-in test runs the installed Hermes gateway with a temporary profile
for each worker. Each gateway listens on a distinct loopback port and uses
its own temporary bearer. The only configured model is a local fixture.
The test gives the gateways no real model credentials, personal input,
desktop, account connector or browser session. Profiles share a host and
are not an operating system isolation boundary.

With the backend environment active, supply the executable for a trusted
local Hermes installation with the Runs API:

```sh
PYTHONPATH=apps/api/src python -B spikes/a7-hermes-runs/smoke.py \
  --hermes-executable /path/to/hermes --workers 5
```

The test checks five coordinator job IDs, retrieves five distinct successful
Hermes receipts and verifies the synthetic answer from each. It checks that
a repeated coordinator request does not create another job. The temporary
gateways stop and their profiles are removed when the script exits. The
test excludes provider subscriptions, OS-level containment, desktops,
memory and inter-worker handoff.

On 2026-11-16, the installed Hermes v0.22.2 gateways produced this result:

```json
{"gateways": 5, "verified_receipts": 5, "local_fixture": true}
```

[Hermes Runs API](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server).

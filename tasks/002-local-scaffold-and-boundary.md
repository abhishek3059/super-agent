# RT-002 — Local scaffold and boundary

| Field | Value |
| --- | --- |
| Task ID | RT-002 |
| Status | in progress; local streaming boundary slice, not accepted |
| Execution evidence | [Streaming implementation record](../docs/implementation/voice-streaming-slice.md); [credential review](../docs/reviews/r01-5-credential-design.md); [implemented-boundary security review](../docs/reviews/r01-6-security-review.md) |

## Scope

Current status (2026-11-12): the local fake streaming boundary is implemented
and reviewed. Authentication, throttling, expiry, Host/Origin checks, CSP, and
bounded teardown exist. A Gemini adapter and standalone synthetic live check
also exist, but the browser console still constructs only the fake adapter.
Development commands are in [apps/voice-foundation.md](../apps/voice-foundation.md).
This task remains unaccepted until RT-002/RT-003 and RT-G01 are completed.

## Original obligation

Minimal reviewed local scaffold, exact dependency/command contract,
device/session authentication, and loopback HTTP/WS/CSRF boundary.

## Non-goals

No tools, task workers, external actions, public deployment, or silent provider
fallback. Local browser capture exists; personal microphone audio stays local.

## Owner

PH-01 implementation owner under the recorded runtime authorization.

## Prerequisites

- [RT-001](001-runtime-consent-and-feasibility.md) completed and separate scaffold authority granted.

## Inputs

Separate scaffold authority, reviewed local scaffold contract, device/session authentication design, and loopback HTTP/WS/CSRF boundary requirements.

## Deliverable

Minimal reviewed local scaffold with exact dependency/command contract and
device/session authentication and loopback HTTP/WS/CSRF boundary.

## Acceptance

- Minimal reviewed local scaffold, exact dependency/command contract, and device/session authentication and loopback HTTP/WS/CSRF boundary delivered under the approved PH-01 authorization: [DEC-16](../descisions.md#dec-16).
- Unauthenticated clients, hostile/null origins, and incorrect Hosts cannot create sessions or jobs; fail closed: [REQ-11](../prd.md#req-11).
- The credential design is reviewed and entropy checks, token generation/file loading, expiry, and throttling are implemented. The Windows owner-only ACL and token-directory limitations remain open as recorded in the [security review](../docs/reviews/r01-6-security-review.md).

## Failure considerations

Do not accept the scaffold boundary before its credential and independent
security review obligations are met. The runnable local development scaffold
does not authorize provider egress or close RT-G01.

## Evidence

See the [implementation record](../docs/implementation/voice-streaming-slice.md).
The local fake slice passed its code reviews. The implemented boundary later
received an independent ACCEPT WITH CONDITIONS review; its blocking conditions
were closed, and both maintainers accepted the bounded F2 risk through the
recorded route. The task remains in progress because RT-002/RT-003 completion
and RT-G01 are still open.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

# RT-002 — Local scaffold and boundary

| Field | Value |
| --- | --- |
| Task ID | RT-002 |
| Status | in progress; boundary implemented and independently reviewed for the fake adapter, not accepted |
| Execution evidence | [Streaming implementation record](../docs/implementation/voice-streaming-slice.md); [credential review](../docs/reviews/r01-5-credential-design.md); [implemented-boundary security review](../docs/reviews/r01-6-security-review.md); [criteria table](../docs/implementation/r01-10-acceptance.md#criteria-and-evidence); [offline re-run, 2026-11-15](../docs/implementation/evidence/r01-10-offline-suites-20261115.txt) |

## Scope

Current status (2026-11-15): the local streaming boundary is implemented and
was independently reviewed at commits `5de7293` and `d5808c6`. Authentication,
throttling, expiry, Host/Origin checks, CSP, and bounded teardown exist. The
console now also accepts an opt-in Gemini adapter and a local adapter
(`SUPER_AGENT_ADAPTER`); the fake adapter stays the default. That code, and
the other adapters and tools merged after the review, has no independent
review record. Development commands are in
[apps/voice-foundation.md](../apps/voice-foundation.md).
This task remains unaccepted until the blockers in the
[R-01.10 record](../docs/implementation/r01-10-acceptance.md#blockers) clear.

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

Status of each criterion, with evidence, as of 2026-11-15
([full table](../docs/implementation/r01-10-acceptance.md#criteria-and-evidence)):

- Scaffold and command contract: met.
- Fail-closed Host, Origin, and authentication: met offline and by the independent review of the fake-adapter boundary.
- Credential design and implementation: met, with the recorded Windows ACL and directory-mode limits.
- Not met: independent review of the boundary as it now exists on `develop`, and the open review finding F5 and the F2 acceptance condition, both tied to wiring Gemini into a session.

## Failure considerations

Do not accept the scaffold boundary before its credential and independent
security review obligations are met. The runnable local development scaffold
does not authorize provider egress or close RT-G01.

## Evidence

See the [implementation record](../docs/implementation/voice-streaming-slice.md).
The local fake slice passed its code reviews. The implemented boundary later
received an independent ACCEPT WITH CONDITIONS review; its blocking conditions
were closed, and both maintainers accepted the bounded F2 risk through the
recorded route. The offline suites passed again on 2026-11-15 (492 backend
tests, 112 frontend self-test cases). The task remains in progress because the
blockers above and RT-G01 are still open.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

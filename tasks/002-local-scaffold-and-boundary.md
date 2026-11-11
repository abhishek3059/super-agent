# RT-002 — Local scaffold and boundary

| Field | Value |
| --- | --- |
| Task ID | RT-002 |
| Status | in progress; local streaming boundary slice, not accepted |
| Execution evidence | [Streaming implementation record](../docs/implementation/voice-streaming-slice.md); [operator direction](../docs/approvals/ph-01-current-phase-work.md) |

## Scope

Current status (2026-11-11): the offline scaffold already exists. The operator
assigned the local streaming-boundary upgrade within PH-01. Its local fake
implementation and code review are complete. Development
commands are runnable as documented in [apps/voice-foundation.md](../apps/voice-foundation.md),
but this task is not accepted and no native provider connection is delivered.
The original scope and acceptance language below define the obligation; they
must not be read as today's application-state report.

After a new implementation request only: minimal reviewed local scaffold, exact dependency/command contract, device/session authentication and loopback HTTP/WS/CSRF boundary, without voice capture yet.

## Non-goals

No voice capture, runtime action, or implementation beyond the reviewed local scaffold boundary; future commands remain proposed/non-runnable.

## Future owner

Implementation owner after separate scaffold authority granted.

## Prerequisites

- [RT-001](001-runtime-consent-and-feasibility.md) completed and separate scaffold authority granted.

## Inputs

Separate scaffold authority, reviewed local scaffold contract, device/session authentication design, and loopback HTTP/WS/CSRF boundary requirements.

## Deliverable

Minimal reviewed local scaffold with exact dependency/command contract and device/session authentication and loopback HTTP/WS/CSRF boundary; no voice capture yet.

## Acceptance

- After a new implementation request only: minimal reviewed local scaffold, exact dependency/command contract, device/session authentication and loopback HTTP/WS/CSRF boundary delivered without voice capture yet; no current build command is runnable and future commands remain proposed/non-runnable: [DEC-16](../descisions.md#dec-16).
- Unauthenticated clients, hostile/null origins, and incorrect Hosts cannot create sessions or jobs; fail closed: [REQ-11](../prd.md#req-11).
- Future authentication-design obligation (security assessment LOW-01, tracked as an unimplemented future requirement — not an implemented vulnerability): before any scaffold acceptance, a future design must define — and be independently reviewed for — cryptographically strong/high-entropy device/session credentials, their secure storage, expiry/rotation/revocation, and failed-authentication throttling/rate-limiting; short PIN-only authentication is rejected and online guessing controls are tested. Source: [design-stage security assessment](../docs/security/super-agent.md), finding LOW-01; mirrored in [RT-A05](../prd.md#rt-a05). The exact credential scheme and parameters are deliberately unspecified today and require their own separate design and design-stage security review; this tracking adds no code, no cryptographic algorithm choice, and no security approval.

## Failure considerations

Do not accept the scaffold boundary before its credential and independent
security review obligations are met. The runnable local development scaffold
does not authorize provider egress or close RT-G01.

## Evidence

See the [implementation record](../docs/implementation/voice-streaming-slice.md).
The local fake slice passes 66 backend tests and final code review at 8.52;
frontend review remains PASS at 8.8. The task remains in progress pending
acceptance obligations. No task acceptance or independent security PASS is claimed.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

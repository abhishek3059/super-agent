# RT-002: Local scaffold and boundary

| Field | Value |
| --- | --- |
| Task ID | RT-002 |
| Status | accepted (done) 2026-11-19 by `abhishek3059`, with residual limits listed below |
| Execution evidence | [Streaming implementation record](../docs/implementation/voice-streaming-slice.md); [credential review](../docs/reviews/r01-5-credential-design.md); [implemented-boundary security review](../docs/reviews/r01-6-security-review.md); [criteria table](../docs/implementation/r01-10-acceptance.md#criteria-and-evidence); [offline re-run, 2026-11-15](../docs/implementation/evidence/r01-10-offline-suites-20261115.txt); [boundary review of `d52d894`](../docs/reviews/r01-10-boundary-review.md); [R-01.F9](../docs/implementation/r01-f9-handshake-proof.md) and [R-01.F10](../docs/implementation/r01-f10-idle-keepalive.md) records; [decisions record](../docs/approvals/r01-10-decisions.md); [console run](../docs/implementation/evidence/r01-10-console-run-20261119T101357Z.md) |

## Scope

Current status (2026-11-15): the local streaming boundary is implemented and
was independently reviewed at commits `5de7293` and `d5808c6`. Authentication,
throttling, expiry, Host/Origin checks, CSP, and bounded teardown exist. The
console now also accepts an opt-in Gemini adapter and a local adapter
(`SUPER_AGENT_ADAPTER`); the fake adapter stays the default. That code, and
the other adapters and tools merged after the review, were reviewed in the
[R-01.10 boundary review](../docs/reviews/r01-10-boundary-review.md) on
2026-11-19. Development commands are in
[apps/voice-foundation.md](../apps/voice-foundation.md).
The task was accepted on 2026-11-19 when the blockers in the
[R-01.10 record](../docs/implementation/r01-10-acceptance.md#blockers) cleared.

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
- Independent review of the boundary as it exists on `develop`: done on 2026-11-19 ([boundary review](../docs/reviews/r01-10-boundary-review.md)). F5 was fixed in R-01.F9. F2 is accepted for maintainer-only testing only and must be fixed before real voice to a cloud provider beyond maintainers (R-A.2), a multi-user, always-on, or remote host, or job control from a voice session.
- Residual: boundary review findings B3 to B8 stay open for later roadmap items.

## Failure considerations

The scaffold boundary was accepted only after its credential and independent
security review obligations were met. The runnable local development scaffold
does not authorize provider egress.

## Evidence

See the [implementation record](../docs/implementation/voice-streaming-slice.md).
The local fake slice passed its code reviews. The implemented boundary later
received an independent ACCEPT WITH CONDITIONS review; its blocking conditions
were closed, and both maintainers accepted the bounded F2 risk through the
recorded route. The offline suites passed again on 2026-11-15 (492 backend
tests, 112 frontend self-test cases). The task was accepted on 2026-11-19
([decisions record](../docs/approvals/r01-10-decisions.md)).

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

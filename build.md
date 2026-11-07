# Super-agent — build position and future command contract (documentation pack)

**Documentation-only project. There is no runnable assistant, application scaffold, package manifest, install script, or verified application build command.**

No dependency installation, package/config/script creation, model download, Git setup, service restart, global change, credential reading, model API contact, or audio capture is part of this request.

## Navigation

- [Signed design](docs/design/super-agent.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation](docs/delivery/council.md)
- [Requirements](prd.md)
- [Architecture](architecture.md)
- [Decisions](descisions.md)
- [Phases](phases.md)
- [Progress](progress.md)
- [Build](build.md)
- [Flow](flow.md)
- [Tasks](taks/README.md)
- [Council meetings](council%20meetings/README.md)
- [Implementation report](docs/implementation/super-agent.md)

## Build and diagnostics

### Recorded discovery diagnostics — not application tests, not rerun for this contract

1. The source records OpenCode v2.1.2; the exact version-command invocation is not supplied.
2. The recorded read-only command `opencode api get /api/experimental/voice/models` returned **HTTP 404**, not native voice success ([`docs/delivery/super-agent-brief.md`](docs/delivery/super-agent-brief.md):47-57).
3. Router TCP reachability is only port availability ([`docs/delivery/super-agent-brief.md`](docs/delivery/super-agent-brief.md):51-52).

Additional diagnostic evidence was supplied by the parent session during discovery and is recorded here as supplied parent observations, not rerun by the documentation delivery:

| Observation | Result supplied by parent | Classification |
| --- | --- | --- |
| `opencode --version` | `opencode v2.1.2` | Supplied parent observation; not rerun. |
| `opencode service status` | Running loopback URL | Supplied parent observation; not rerun. |
| `opencode api get /api/info` | Service version 2.1.2 | Supplied parent observation; not rerun. |
| `opencode api get /api/experimental/voice/models` | HTTP 404 | Supplied parent observation; not rerun. |

These are discovery checks, not application builds or tests. A reachable router port does not prove model access.

### Proposed future command contract — NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS

If a later scaffold uses the proposed Node stack, candidate command names are `npm ci`, `npm run dev`, `npm run typecheck`, `npm test`, and `npm run build`.

| Candidate command | Labelling | Prerequisites | Purpose | Future owner | Execution evidence |
| --- | --- | --- | --- | --- | --- |
| `npm ci` | Proposed; **NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS** | Approved scaffold and lockfile. | Install dependencies. | Future implementation owner. | none |
| `npm run dev` | Proposed; **NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS** | Approved scaffold and lockfile. | Run future development server. | Future implementation owner. | none |
| `npm run typecheck` | Proposed; **NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS** | Approved scaffold and lockfile. | Type-check future sources. | Future implementation owner. | none |
| `npm test` | Proposed; **NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS** | Approved scaffold and lockfile. | Run future test suite. | Future implementation owner. | none |
| `npm run build` | Proposed; **NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS** | Approved scaffold and lockfile. | Build future application. | Future implementation owner. | none |

No package scripts or lockfile are currently defined. These names are not APIs or scripts discovered in the source and install commands from provider examples are not current setup instructions.

### Future verification protocol

After a separately authorized scaffolding, replace proposals with actual commands supported by opened manifests/scripts; record versions, date, working directory, exit status, and redacted result/evidence.

Diagnose locally without reading credentials; native tests require RT-G00. A successful build is not proof of native access, safety, or latency.

## Consent gates and secret handling

- No runtime microphone/context transmission, paid service provisioning, model download, dependency installation, source scaffold, build, test suite, voice performance measurement, or worker integration is part of this delivery.
- Provider eligibility/access, runtime consent, a first real task pair, target host, usage budgets, and retention windows remain unresolved implementation gates.
- No secrets, credentials, or personal data are stored in this documentation pack.

# Super-agent — build position and future command contract (documentation pack)

**Mostly documentation. There is no complete runnable assistant.** The repository
root has a minimal `package.json` and Husky hooks for repository checks. The
runnable voice scaffold lives in `apps/` (see
[apps/voice-foundation.md](apps/voice-foundation.md)) and defaults to the fake
adapter. A Gemini Live adapter and locked SDK exist, and a separate opt-in
synthetic live check has contacted the provider. The browser console does not
construct the Gemini adapter. Throwaway experiments live in `spikes/`.

The original documentation delivery performed no application installation,
provider contact, or audio capture. Later approved PH-01 work added the scaffold
and synthetic-only live check described above.

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
- [Tasks](tasks/README.md)
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

### Repository tooling — added 2026-11-07 at explicit user request

This is repository automation, not an application scaffold.

- `package.json` and `package-lock.json` define development tooling only.
- Husky `pre-commit` and `pre-push` hooks run `node scripts/check-repo.mjs`: forbidden credential files, high-confidence secret patterns, unresolved conflict markers, files larger than 2 MiB, and local Markdown file/anchor links.
- The `commit-msg` hook runs `node scripts/check-commit-msg.mjs`, enforcing Conventional Commits.
- `.github/pull_request_template.md` is the AI-agent pull-request template.
- `npm ci` installs repository tooling only. `npm run check` is runnable now and validates the repository; neither is an application test, build, or runtime proof.
- The application commands `npm run dev`, `npm run typecheck`, `npm test`, and `npm run build` remain proposed and **NOT RUNNABLE** at the repository root. The offline voice scaffold has its own commands (`npm start --prefix apps/web`, `npm run test:epoch --prefix apps/web`, `pytest apps/api`), documented in [apps/voice-foundation.md](apps/voice-foundation.md).

### Historical proposed repository-root application command contract

If a later scaffold uses the proposed Node stack, candidate application command names are `npm run dev`, `npm run typecheck`, `npm test`, and `npm run build`.

| Candidate command | Labelling | Prerequisites | Purpose | Future owner | Execution evidence |
| --- | --- | --- | --- | --- | --- |
| `npm ci` | **Runnable for repository tooling only** | Node/npm and the committed `package-lock.json`. | Install Husky and repository check tooling; does not install or run an application. | Repository maintainer. | Run during tooling setup; no application dependency installed. |
| `npm run dev` | Historical proposal; not defined at repository root | Root application script. | Run a future root development server. | Future implementation owner. | none |
| `npm run typecheck` | Historical proposal; not defined at repository root | Root application script. | Type-check future root sources. | Future implementation owner. | none |
| `npm test` | Historical proposal; not defined at repository root | Root application script. | Run a future root test suite. | Future implementation owner. | none |
| `npm run build` | Historical proposal; not defined at repository root | Root application script. | Build a future root application. | Future implementation owner. | none |

At the repository root, package scripts remain repository checks. Application
source, scripts, a frontend lockfile, and a backend requirements lock exist
under `apps/`; their current commands are documented in
[apps/voice-foundation.md](apps/voice-foundation.md).

### Verification protocol

Use the actual commands supported by the manifests and locks under `apps/`;
record versions, date, working directory, exit status, and redacted evidence.

Diagnose locally without reading credentials; native tests require RT-G00. A successful build is not proof of native access, safety, or latency.

## Consent gates and secret handling

- Personal microphone/context cloud transmission, paid service provisioning,
  model download, and worker integration are not authorized by PH-01.
- Provider eligibility, consent, task pair, hosts, budgets, and retention are
  resolved for the bounded synthetic-only PH-01 scope. Personal microphone and
  context cloud egress remain unapproved; RT-G01 remains open.
- No secrets, credentials, or personal data are stored in this documentation pack.

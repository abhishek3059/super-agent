# HQ on WSL2 needs a Hermes with packages beside its Python

| Field | Value |
| --- | --- |
| Date | 2026-11-24 |
| Evidence | [WSL2 run, 2026-11-24](../implementation/jarvis-hq-maintainer-pilot.md#wsl2-run-2026-11-24) |

## What happened

The first WSL2 run of HQ could not start any bot. The repository checks and
self-checks passed. The Hermes from the shell installer keeps its Python
packages under each Hermes home, so it could not start in a bot home. The
macOS run had worked because it used a source checkout with its own
environment.

## What we learned

Self-checks that stub Hermes do not show whether the real gateway starts in
a bot home. The guide now names the install that worked. A real worker turn
belongs in every pilot run.

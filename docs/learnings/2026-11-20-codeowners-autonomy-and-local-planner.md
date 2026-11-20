# CODEOWNERS self-approval bypass and local Ollama planner

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Evidence | [PR #65](https://github.com/abhishek3059/super-agent/pull/65), [PR #66](https://github.com/abhishek3059/super-agent/pull/66), [PR #67](https://github.com/abhishek3059/super-agent/pull/67), [PR #69](https://github.com/abhishek3059/super-agent/pull/69) |

## What happened

When merging PRs authored by Jeevesh touching roadmap or documentation files, GitHub native CODEOWNERS rules requested Abhishek's review and blocked merging because GitHub forbids authors from approving their own PRs. AI agents stalled, assuming an external review was required. In parallel, PR #65 introduced an in-process Ollama planner, and PR #69 broadened `.gitignore` to prevent test caches and secrets from tripping pre-commit hooks.

## What we learned

1. Under DEC-21, DEC-22, and AGENTS.md section 3, an author's own PR counts as their approval. The sanctioned mechanism to satisfy GitHub branch protection when an author merges their own approved PR is admin bypass (`gh pr merge --admin`). For PRs authored by the other maintainer, the reviewing maintainer can approve them directly via GitHub review.
2. The local Ollama planner (`ollama_planner.py`) enables background job planning on open-weight models (like `llama3.2:3b`) with a 60 s step deadline, satisfying REQ-13 by avoiding cloud API egress.
3. Placing `.env` files in the repository root trips repository integrity guards (`check-repo.mjs`). Secrets must live strictly at `~/.super-agent/env` (mode 0600) outside git tracking.

## What to do differently

1. Instruct agents to use `gh pr merge --admin` when confirming and merging a maintainer's own PR, rather than waiting for cross-maintainer approval.
2. Maintain comprehensive ignore patterns in `.gitignore` for `.mypy_cache`, test cache databases, MCP scratch directories, and private keys.

## Still unknown

Whether the local Ollama planner generates valid multi-step DAG plan graphs under high concurrency without step deadline timeouts.

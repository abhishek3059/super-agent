# Contributing — branch and release workflow

This repository uses a small `develop` → `main` workflow. `main` is the stable
production branch; `develop` is the integration branch where changes are tested
before release.

## Branch roles

| Branch | Purpose | Rules |
| --- | --- | --- |
| `main` | Production / stable | Only receives merges from `develop` (or hotfixes). No direct feature commits. |
| `develop` | Integration and testing | Receives feature/fix PRs after CI passes. |
| `feat/*`, `fix/*`, `docs/*`, `chore/*` | Short-lived work branches | Branch from `develop`, merge back through a PR. |

## Daily development flow

```powershell
# 1. Start from the latest develop
git switch develop
git pull origin develop

# 2. Create a short-lived work branch
git switch -c feat/my-change

# 3. Make changes, then run the local checks
npm run check

# 4. Commit using Conventional Commits
git add -A
git commit -m "feat(scope): describe the change"

# 5. Push and open a PR into develop
git push -u origin feat/my-change
gh pr create --base develop --fill

# 6. After CI and review pass, merge the PR
gh pr merge --squash --delete-branch
```

The `pre-commit`, `commit-msg`, and `pre-push` hooks run automatically. CI runs
`npm ci` and `npm run check` on every push and pull request targeting `develop`
or `main`.

## Release flow: develop → main

When `develop` is tested and ready for production:

```powershell
git switch develop
git pull origin develop
gh pr create --base main --head develop --title "release: describe the release"

# Wait for the "Repository checks" CI job and human approval, then:
gh pr merge --merge
```

Use a merge commit for `develop` → `main` so the integration history is
preserved. Tag the release on `main`:

```powershell
git switch main
git pull origin main
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

## Hotfix flow

If production needs an urgent fix, branch from `main`, then back-merge:

```powershell
git switch main
git pull origin main
git switch -c fix/urgent-issue

# fix, run npm run check, commit
git push -u origin fix/urgent-issue
gh pr create --base main --fill
gh pr merge --squash --delete-branch

# Keep develop in sync
git switch develop
git pull origin develop
git merge main
git push origin develop
```

## AI-agent rules

- Use the [pull request template](.github/pull_request_template.md) and disclose
  the agent, model/provider, and human operator.
- Never push feature work directly to `main`. Open a PR into `develop`.
- Run `npm run check` before committing; CI is the remote enforcement.
- Use Conventional Commits (`feat`, `fix`, `docs`, `chore`, etc.).
- Do not claim runtime gates, tests, or approvals that were not actually
  executed or granted.
- Keep future phases/tasks `not started` unless the change is the approved
  implementation.

## Recommended branch protection

After the first CI run has registered the **Repository checks** job, protect
`main` and `develop` in GitHub:

**Settings → Branches → Add branch protection rule**

For `main`:

- Require a pull request before merging.
- Require status checks to pass: select **Repository checks**.
- Require branches to be up to date before merging.
- Do not allow force pushes or deletions.
- Optionally require one approval. For a solo repository, keep an admin bypass
  or use a ruleset that allows the owner to merge their own PRs.

Repeat for `develop`, with the same status check requirement.

## First-time setup after cloning

```powershell
npm ci
```

This installs Husky and activates the Git hooks. The hooks are local; CI is the
authoritative remote check.

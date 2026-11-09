# Stacked PRs and the PR #8 accident

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Evidence | Descriptions of PRs [#9](https://github.com/abhishek3059/super-agent/pull/9) and [#10](https://github.com/abhishek3059/super-agent/pull/10). The repository history for #8 was not re-read. |

## What happened

Per the description of #9: PR #8 was merged into `develop` by accident and
carried the product-direction, A2 spike, and A3 spike changes (the stack of #3,
#4, and #7). #9 reverted #8 with a revert commit, and the operator confirmed
reverting the whole stack. #10 restored the reverted changes.

## What we learned

- Per #9, GitHub had already marked #3 as merged because its commit was inside #8, so reverting did not make those commits new again. Recovery needed fresh commits, not re-merging the old branch tips.
- #9 states the revert used no reset and no force push, so shared history was preserved.
- A stacked PR can bring every commit beneath it into the wrong base when merged.

## What to do differently

- Prefer small independent PRs against `develop`. If a stack is unavoidable, state the base and merge order at the top of each PR, merge bottom-up, and retarget each PR to `develop` after its base merges.
- Check the base branch in the PR header before merging.
- Keep reverts and restores in their own PRs with the operator's confirmation, as #9 did.

## Still unknown

How #8 happened, and whether branch protection on `develop` would have stopped it. Branch protection was not confirmed to be set.

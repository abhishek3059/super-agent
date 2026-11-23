# Jarvis HUD and commitments scope decision

On 2026-11-21, maintainer `jeevesh2515` chose the following in chat with
OpenCode (DeepSeek V4.1 Flash), from options the agent offered while
reviewing the Roamies blueprint. Under [DEC-21](../../descisions.md#dec-21)
one maintainer's approval is enough.

## Approved

- Write two design proposals: [screen HUD](../design/jarvis-screen-hud.md)
  and [commitments](../design/jarvis-commitments.md).
- Add four roadmap items to parallel track H: R-H.12 (approve the HUD
  design), R-H.13 (build it), R-H.14 (approve the commitments design),
  R-H.15 (build HQ reminders).
- Keep the work in one roadmap PR with no application code.

## Not approved

These need their own decision, design and review before any work starts:

- Screen capture of any kind, including region capture, and a capture
  helper app.
- The macOS Screen Recording permission.
- Sending screen pixels to a vision provider.
- Any change to the overlay relay beyond `status`, `level` and `skin`.
- A commitment parser, table or scheduler in HQ.
- Any new provider, including OpenCode free models.

The proposals describe the smallest version that could work. They do not
authorize it.

## Boundary

- This record adds no tool, worker permission, provider connection or
  capability tier.
- It grants no merge or release approval.
- R-H.12 and R-H.14 stay `[human]` because a person must approve each design
  before its build item starts. This record approves neither design.

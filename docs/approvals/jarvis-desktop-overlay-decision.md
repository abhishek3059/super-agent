# Jarvis desktop overlay decision

On 2026-11-21, maintainer `jeevesh2515` chose the following in chat with
Claude Code (Opus 5.5), from options the agent offered. The request was a
desktop companion like the reference demos, built on HQ. Under
[DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough.

## Approved

- **Passive overlay (R-H.11).** A desktop window over every app that is
  click-through and never takes focus. It follows the cursor, can be parked
  or hidden from its tray menu, and mirrors HQ's companion state: idle,
  listening, thinking or speaking, voice energy from 0 to 1, and the skin,
  including hover previews. It reaches HQ only over the authenticated
  loopback, with the same owner sign-in the `npm run jarvis` launcher uses.
  It needs no macOS Screen Recording, Accessibility or Input Monitoring
  permission.
- **Stack:** Electron, pinned to an exact release at least 14 days old (MIT
  license).

## Offered and not approved

These need a new maintainer decision, a design and a roadmap item before any
work starts:

- **Region capture and approved submission:** the user drags a region, sees
  a local preview, and only on Approve is the cropped image sent to the bot's
  hosted model. Needs Screen Recording.
- **Guide observation:** the overlay draws one target at a time and watches
  the user's own clicks to advance. Needs global pointer observation.

The browser-only alternative (no native work) was also offered and declined.

## Boundary of the approval

- The overlay adds no tool, worker permission or provider connection. HQ's
  workers and their sandbox are unchanged.
- The relay accepts exactly three bounded fields (`status`, `level`,
  `skin`). It carries no text, transcript or pixels.
- The overlay page has no Node access, cannot send anything to HQ and does
  not see the session token. It denies every web permission.
- It sets content protection, so screenshots and screen shares leave it out.
- On Windows the overlay runs on the Windows host and HQ stays in WSL2. It
  reads the owner secret from the WSL data folder and connects through WSL2's
  localhost forwarding.

## Reference material

[Roamies](https://github.com/KenKaiii/Roamies/tree/7d5fb3c6e2a2445a0fef3e46412b73908900c2e0)
is AGPL-3.0-only, and some of its looks pay tribute to third-party
characters. Nothing was copied from it. The overlay's code, motion constants,
skins and tray icon are original. Roamies and the three demo GIFs were used
only to compare behavior. [REA](https://github.com/morluto/rea/tree/c23aa499f669ed09f7636724a8ef5f45ae9412e4)
(MIT) analyzes shipped binaries. Its own skill says to skip it when source is
available, so it was not installed. Its order of observation, inference and
verification informed the review.

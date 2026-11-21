# Jarvis desktop overlay check (R-H.11)

Status: **macOS run recorded. Windows run not run.** R-H.11 stays unticked
until the overlay is run on the Windows host with HQ in WSL2 and on the
reviewed, merged revision.

## macOS run, 2026-11-21

Host: macOS 27.2.1, Node v22.22.3, Electron 45.2.3, one built-in display at
2x scale. Branch `feat/hq-desktop-overlay`, stacked on `feat/hq-companion`
(`1348725`). HQ ran from a throwaway data folder on port 8797 with
`HQ_NO_SCHEDULER=1`, no Hermes, no provider keys and synthetic data only.

What was exercised, and how:

| Check | Method | Result |
| --- | --- | --- |
| Owner sign-in from the overlay | Overlay main process, `ownerLogin` and the one-time link | Connected (`data-connection="connected"`) |
| Unauthenticated relay refused | `curl -X POST /api/companion` with no token | HTTP 401 |
| Extra field refused | Signed-in post with a `text` field | HTTP 400 |
| State, energy and skin mirrored | Signed-in posts for listening 0.6, thinking, speaking 0.9 and idle, read from the overlay DOM over a loopback DevTools port | Each `data-status`, `data-look` and `--level` matched within 400 ms |
| Real pointer tracking | Overlay `transform` read twice while the mouse moved | Position changed with the cursor |
| HQ hover preview | Built-in browser: hover Ember in the Companion panel | Overlay showed `ember` while HQ's saved skin was Arc |
| Saved skin persists | Select Carbon, move away, reload HQ | Overlay showed `carbon` after reload |
| Reduced motion | DevTools `prefers-reduced-motion: reduce` | Idle animation `buddy-bob` became `none` and the level stayed 0 |
| Left out of screen captures | `screencapture -x` cropped at the overlay's position | Nothing drawn where the overlay was |
| Rendering at 2x | DevTools page capture | Paper skin drawn sharply |

Self-checks: `npm test` in `apps/hq` gave 54 passed, 0 failed and 16 skipped
(the skipped suites need Linux bubblewrap or a local pgvector). The new test
"the companion relay carries only a bounded state, to the signed-in owner"
passed. `npm test` in `apps/hq/desktop` passed 5 of 5 motion checks: edge
clamping, side flip with hysteresis, park, a spring with no overshoot, and
voice-energy smoothing. `npm run check` at the root reported 0 errors.

Not checked on this run:

- Click-through and focus were not tested with a scripted click. They come
  from `setIgnoreMouseEvents(true)` and `focusable: false`. The operator
  should confirm both by clicking and typing through the companion.
- Multiple displays: only one display was attached.
- A live OpenAI voice call driving the overlay. Voice energy was driven by
  signed-in posts with the same shape the HQ page sends.
- The tray menu (Follow, Park, Hide, Quit) was not driven by script.

## Windows run

Not run. Steps for the operator are in the
[HQ README](../../apps/hq/README.md#desktop-overlay).

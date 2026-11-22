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
| Session ends on quit | Rows in `auth_sessions` before launch, while running, after `kill -TERM` | 3, 4, 3 |
| One copy at a time | Two launches 4 s apart | One main process, one new session |
| Quit during startup sign-in | `kill -TERM` 0.4, 0.7 and 1.0 s after launch | `auth_sessions` unchanged (3) each time, no process left. Whether a kill landed while the sign-in was in flight, not before it, was not measured. |

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
- Screen sharing apps (ScreenCaptureKit) were not tested. Only
  `screencapture` was.
- The 45-second idle reconnect was not forced in this run.

## Dependencies

`npm audit` in `apps/hq/desktop`: 0 vulnerabilities. Electron's install
script downloads its checksum-verified binary, so `--ignore-scripts` cannot
be used. Licenses of all 13 installed packages (from `license-checker@25.0.1`):
MIT for `electron` 45.2.3, `@electron/get`, `@electron-internal/extract-zip`,
`debug`, `env-paths`, `ms`, `progress`, `undici`, `undici-types` and
`@types/node`; ISC for `semver`; Apache-2.0 for `sumchecker`; BlueOak-1.0.0
for `graceful-fs`. None is non-commercial or custom.

## Later change

On 2026-11-21 the overlay art was replaced with a 520-point wave sphere
(`desktop/sphere.js`), driven by the same `level` field. That change came
after the run above, so R-H.11 needs a fresh run on the merged revision.

## Windows run

Not run. Steps for the operator are in the
[HQ README](../../apps/hq/README.md#desktop-overlay).

## Pixel Companion pilot, 2026-11-22

The original pixel artwork and explicit skin controls are in the HQ Companion.
The Electron sphere uses stepped pixels and separate idle, listening, thinking
and voice energy cues. The relay replays the signed-in owner's last skin and
lets active animation expire when HQ stops publishing.

Reference review used 28 frames from the
[linked video](https://www.youtube.com/watch?v=bl9646MVDA4), including the
[cursor companion](https://www.youtube.com/watch?v=bl9646MVDA4&t=6s) and
[appearance controls](https://www.youtube.com/watch?v=bl9646MVDA4&t=190s).
The HQ visuals and motion are original. The walkthrough still points to known
HQ controls and waits for the operator. Explain turns text into local cards.

| Check | Outcome |
| --- | --- |
| Browser Companion | Chrome checked 320, 768, 1024 and 1440 px widths, keyboard skin selection, temporary hover preview and restoration, reduced motion, walkthrough completion and Explain |
| Realtime and Electron | A separate synthetic call using generated speech drove the actual Electron renderer to speaking with nonzero output energy. Late startup mirrored the selected skin and hidden styling stayed at zero opacity with offline styling in either order |
| Hermes handoff | A synthetic HQ turn on the configured NVIDIA route delivered a Jarvis task to Scout, then returned Scout's attributed marker to Jarvis |
| Local checks | Repository check, HQ typecheck and build passed. HQ tests reported 54 passes, zero failures and 16 skips. Desktop tests passed 14 of 14 |

The live voice probe used a fake microphone input and did not assess physical
microphone or speaker quality. Direct provider sign-in was not rerun. The
semantic memory database was not configured in this pilot. Physical Windows
and second display tests remain pending. R-H.11 stays unticked.

## Browser preview recovery, 2026-11-22

Two browser ports in the Pixel Pilot's original range were held by another
HQ workspace. The other three previews worked. After a restart with
automatic port-block selection, all five bots sent a JPEG frame through
HQ's authenticated Watch screen relay. The original listeners remained
up. The same workspace and browser profiles were reused.

Jarvis answered a synthetic geography question and Atlas answered a
synthetic arithmetic question. Chrome rendered the selected Jarvis answer
as a local Explain card. This selection is within the HQ conversation.

The separate live voice probe streamed a synthetic command to OpenAI
Realtime. The voice tool delegated it to Jarvis. Scout's browser commands
failed, then its web search returned the example page title, which Jarvis
reported in generated voice. The probe also verified interruption and call
end. A Chrome test with a controlled audio stream also verified voice
delegation, the Hermes result, and the result in the browser voice caption.
Two earlier Chrome attempts with a simulated microphone file timed out
before delegation. These checks did not use a physical microphone or
measure speaker playback.

## Floating skin wiring, 2026-11-22

Host: macOS, Electron 45.2.3. HQ ran from a throwaway data folder on port
18877 with `HQ_NO_SCHEDULER=1`, no Hermes, no provider keys and synthetic
data only. The saved appearance was set in `hq.theme`, HQ was reloaded,
Follow cursor was enabled, and the Electron overlay was restarted. The same
value was read from the Companion card, the cursor companion and the overlay
DOM, and the computed accent was compared.

| Saved appearance | Card `data-look` | Cursor `data-look` | Overlay `data-look` | Accent on all three |
| --- | --- | --- | --- | --- |
| Arc | `arc` | `arc` | `arc` | `#39d0ff` |
| Ember | `ember` | `ember` | `ember` | `#ff943e` |
| Carbon | `carbon` | `carbon` | `carbon` | `#c3c8d2` |
| Paper | `paper` | `paper` | `paper` | `#cd8545` |
| Light | `light` | `light` | `light` | `#cd8545` |
| Dark | `dark` | `dark` | `dark` | `#f5f5f5` |
| System, dark OS | `system` | `system` | `system` | `#f5f5f5` |

Before the fix, Light, Dark and System reached the overlay as `arc`, because
the mirror forced every non-skin value to the default skin. The overlay now
receives the saved value and resolves the same light or dark base as the
page. Emulated media changed System from the dark values to `#cd8545` on both
surfaces and back. Ember and Carbon matched on all three surfaces before and
after the fix.

Saved Ember, Carbon and Light each survived an HQ reload and an overlay
restart. On restart the overlay replayed the signed-in owner's last look from
the event stream.

The Electron overlay then drew one sphere silhouette for every character.
That limit is gone: the overlay now shows the canvas sphere for Jarvis,
the portrait for Mika and the pixel head for the rest, matching the
browser. Physical Windows and second display checks remain pending.
R-H.11 stays unticked.

Checks: HQ typecheck and build passed. HQ tests reported 55 passes, zero
failures and 16 skips. The repository check was run before commit.

## Character picker, 2026-11-22

Host: macOS, Electron 45.2.3. HQ ran from a throwaway data folder on port
18877 with `HQ_NO_SCHEDULER=1`, no Hermes, no provider keys and synthetic
data only.

The picker keeps the stored ids (`arc`, `ember`, `carbon`, `paper`) so
older saves keep working, and shows them as Jarvis, Mika, Carbon and
Paper. Jarvis is the pixel sphere. Mika is an original pixel portrait on
the `ember` id (hair, face, jacket, all drawn in CSS, nothing copied).
Carbon and Paper are clipped pixel heads with different silhouettes and
eye shapes. The picker is a `radiogroup`: click or Arrow/Home/End keys
select, the selected character gets a border, a check mark and a
`Selected:` label, thumbnails animate (sphere scan, portrait and face
blink) and hover still previews everywhere. Reduced motion hides the
cursor companion and stops the animation on all surfaces.

| Saved id | Shown as | Card | Cursor | Overlay | Accent |
| --- | --- | --- | --- | --- | --- |
| `arc` | Jarvis | sphere | sphere | canvas sphere | `#39d0ff` |
| `ember` | Mika | portrait | portrait | portrait | `#ff943e` |
| `carbon` | Carbon | visor head | visor head | visor head | `#c3c8d2` |
| `paper` | Paper | helmet head | helmet head | helmet head | `#cd8545` |

Switching by click and by keyboard reached all three surfaces with
matching `data-look` and accents. Saved `ember` survived an HQ reload
(card still portrait, `Selected: Mika`) and an overlay restart (replay
showed the portrait). Legacy Light, Dark and System still render as the
head silhouette. Physical Windows acceptance remains pending. R-H.9 and
R-H.11 stay unticked.

Checks: HQ typecheck and build passed. HQ tests reported 55 passes, zero
failures and 16 skips.

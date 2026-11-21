# Jarvis screen HUD (design)

| Field | Value |
| --- | --- |
| Status | **Proposal. Not approved. Design only, no code.** |
| Date | 2026-11-21 |
| Requested by | Maintainer `jeevesh2515`, in chat with OpenCode (DeepSeek V4.1 Flash), 2026-11-21, from the Roamies blueprint |
| Roadmap | Proposed as R-H.12 (approval) and R-H.13 (build) in [parallel track H](../../roadmap.md#parallel-track-h-jarvis-hq-local-team-dec-23) |
| Related | [overlay decision](../approvals/jarvis-desktop-overlay-decision.md), [DEC-23](../../descisions.md#dec-23), [REQ-11](../../prd.md#req-11), [REQ-12](../../prd.md#req-12), [REQ-13](../../prd.md#req-13), R-H.10, R-A.2 |

## 1. What was asked

The blueprint asks Jarvis to ring real buttons on the operator's screen,
underline text, draw step-by-step reticles, and project answer cards into
empty screen margins. It proposes full-screen screenshots, a vision model
that returns `0-1000` coordinates, and an overlay that draws the result.

## 2. What is approved today

The overlay is passive by decision. It never captures the screen, never
observes input, never clicks, and needs no Screen Recording, Accessibility or
Input Monitoring permission ([overlay decision](../approvals/jarvis-desktop-overlay-decision.md)).
R-H.10 says host screen capture, visual recognition and desktop clicks
"require their own scope". This document is that scope proposal, not that
approval.

The overlay relay accepts exactly three bounded fields: `status`, `level`,
`skin` ([`routes.ts`](../../apps/hq/server/src/routes.ts)). It carries no
text, transcript or pixels. That stays true until a separate decision changes
it.

## 3. Recommendation

Build a **one-shot, region-only HUD**, not an always-on screen reader.

- The operator starts it explicitly, for one question.
- The operator selects a region and sees a local preview.
- Nothing is sent until the operator approves that preview.
- The model returns a bounded list of marks, never HTML, JavaScript or a URL.
- The overlay draws the marks for a few seconds, then clears them.
- No clicks, no typing, no window geometry, no calm-space detection.

Full-screen capture and "calm space" detection are rejected for now. Calm
space needs the bounds of other apps, which needs Accessibility or Screen
Recording and reveals more than the question needs. A region is enough to
point at a button.

## 4. Flow

1. The operator asks a question in HQ and chooses **Show me**. Nothing is
   captured before this.
2. A small selection window takes focus for the drag. It closes on release.
   The passive overlay never takes focus.
3. The selection window captures only that rectangle from the display under
   it, at native scale, and shows a local preview.
4. The operator chooses **Send** or **Cancel**. Cancel discards the crop.
5. On **Send**, HQ downscales the crop to at most 1280 px on the long edge,
   encodes JPEG, and sends it to one approved vision provider with the
   operator's question.
6. The model returns JSON marks. The server validates them against the
   schema, then broadcasts them to the signed-in owner over the existing
   authenticated loopback.
7. The overlay maps the marks from the captured region to screen points and
   draws rings for at most 8 seconds. Any key, click or new question clears
   them.
8. The crop is discarded when the request ends. It is not written to disk,
   logged, or kept in history.

## 5. Mark schema

```ts
type HUDMark = {
  type: 'ring' | 'target' | 'underline' | 'label';
  x: number; // 0-1000, left of the captured region
  y: number; // 0-1000, top of the captured region
  w?: number; // 0-1000
  h?: number; // 0-1000
  color?: 'teal' | 'amber' | 'coral' | 'white';
  label?: string; // at most 40 characters
  durationMs?: number; // at most 8000
};
```

Rules: at most 8 marks, all numbers finite and in range, no unknown keys, no
`card` type in this slice. A card needs a separate text-rendering decision
because it can show model text over other apps. The overlay validates the
same schema again before drawing.

## 6. Coordinate mapping

Marks are relative to the captured region, not the whole screen. The
selection window records the display id, the region in display points, and
the display scale factor. The overlay converts:

```text
screenX = region.x + (mark.x / 1000) * region.w
screenY = region.y + (mark.y / 1000) * region.h
```

The overlay window spans one display's work area. For a region on another
display, the overlay instance for that display draws it. Tests must cover
1x and 2x scales, negative-origin displays, and a region that touches a
screen edge.

## 7. Providers and data

- One approved provider per request. NVIDIA NIM is already an approved
  worker provider; OpenAI is approved for maintainer testing under DEC-24.
- OpenCode free models are not an approved provider and have no HQ adapter.
  Do not route screen pixels to them.
- Provider terms on training and retention are unverified (DEC-24 rule 5).
  Screen pixels can contain secrets, private messages and other people's
  data. Use synthetic or prepared screens for maintainer testing.
- No free-tier model for screen pixels until a maintainer records the terms.
- No capture of another person's screen or data.

## 8. Permissions

| Platform | Capture | Selection UI | Never |
| --- | --- | --- | --- |
| macOS | Screen Recording, granted once in System Settings | Electron selection window | Accessibility, Input Monitoring, global hooks |
| Windows | Graphics Capture | Electron selection window | Global input hooks |

The overlay stays click-through and content-protected. The selection window
is a separate, short-lived window that takes focus only for the drag.

## 9. Security invariants

- Local APIs stay on `127.0.0.1`, require the session token, and check Host
  and Origin (REQ-11).
- The overlay renderer never sees the session token. It receives marks over
  IPC from the main process, as it does for companion state.
- The overlay CSP stays `default-src 'none'; script-src 'self'`.
- No `eval`, no HTML injection, no remote content, no arbitrary draw commands.
- Bounded crop size, bounded marks, bounded duration, bounded label length.
- Fail closed: no consent, no capture. Capture error, no marks. Model error,
  no marks. Invalid mark, drop the whole batch.
- No file writes of crops, no crop in logs, no crop in the model prompt text.
- No clicks, no typing, no scrolling, no shell.

## 10. Tests and evidence

- Unit: schema bounds, unknown keys, mark count, duration cap, label cap.
- Unit: coordinate mapping at 1x and 2x, negative origins, edge regions.
- Negative: request without consent, oversized crop, invalid model JSON.
- Manual: one region on the built-in display, one on a second display.
- Independent security review of the capture path, the provider call and the
  overlay IPC before R-H.13 is ticked.

## 11. Non-goals

- Always-on or periodic screen capture.
- Full-screen capture.
- Calm-space detection.
- Autonomous clicks, typing or scrolling.
- OCR of the whole screen.
- A per-task model router. R-M.3 owns the router.
- Answer cards with model text over other apps. Separate decision.

## 12. Open questions

1. Which vision model returns reliable boxes, and at what cost? Measure
   before choosing.
2. Does the selection window need to run on Windows in this slice, or can
   macOS land first?
3. Should labels show text read from the screen, or only fixed words the
   operator typed?
4. Is the crop sent to the provider, or only a local OCR result? The crop is
   simpler but leaks more.

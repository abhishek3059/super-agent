# Session log: 2026-11-13, Gemini Live testing, architecture review, local direction

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Operator | `abhishek3059` |
| Agent | Claude Code. Main session `claude-sonnet-5-5`, then `claude-opus-5-5`. Implementation subagents `claude-sonnet-5-5`. Architect subagent `claude-fable-5-2`. Council members `claude-sonnet-5-5`. |
| Work branch | `feat/gemini-live-console`, [PR 41](https://github.com/abhishek3059/super-agent/pull/41) (draft, stacked on [PR 36](https://github.com/abhishek3059/super-agent/pull/36)) |
| Status | Record only. It authorizes nothing and ticks nothing. |

## Motive

The operator wanted four things:

1. Catch up on what `jeevesh2515` built on the night of 2026-11-12.
2. Talk to a native speech-to-speech model (Gemini Live), because speech-to-text often fails on his Indian English accent.
3. Check his architecture diagram against the real state of the project.
4. Find a design that is private, reasons well, and remembers the user's preferences, habits, and history locally.

## What was discussed

- **Repository status.**
  - Local `develop` was 8 commits behind.
  - Open PRs: [33](https://github.com/abhishek3059/super-agent/pull/33), [36](https://github.com/abhishek3059/super-agent/pull/36) to [40](https://github.com/abhishek3059/super-agent/pull/40).
- **PR 36 (`jeevesh2515`, local voice adapter).**
  - What it does: a speech-to-text chain on the Mac.
  - Open questions:
    - It is out of roadmap order.
    - A GPL-3.0 dependency (`phonemizer-fork`) is pinned, while the PR text says none was added.
    - The calculator widens DEC-18 T0.
    - No denied-egress test has been run.
- **Gemini Live testing.**
  - Sending real microphone audio to Gemini departs from R-00.4, which says personal microphone audio stays local.
  - The operator accepted this for testing only.
- **Provider keys for real users.**
  - Covered: key entry in the UI, OS-vault storage, Google sign-in, hosted service, and local by default.
  - R-00.9 keeps keys out of the browser.
  - Recorded as a proposal in [docs/future](../../docs/future/provider-credentials-for-users.md).
- **PR 39 (`jeevesh2515`, trail MCP).** Review found these problems:
  - A session-start hook can import `dist/claude/hooks.js` from the repository.
  - The hook injects an install offer into the agent's context.
  - The package's newest release (0.29.0) is 7 days old, which breaks the 14-day rule.
  - The new AGENTS.md block makes trail mandatory "for ANY task".
  - The operator sent the findings to `jeevesh2515`. The PR was not merged.
- **Architecture diagram.**
  - Only the voice row exists today.
  - The diagram misses the local backend boundary.
  - It shows a brain-to-memory write, which the brain design forbids.
  - It has an internet fetch with no tier.
- **Classifier idea.** A classification model may advise before the broker, but it can only tighten a decision. The broker stays code (DEC-07, REQ-10).
- **Hardware.** Windows laptop: GTX 1650 Ti with 4 GB, and 7.8 GB RAM. `jeevesh2515`: MacBook Air M5, 16 GB.
- **Cloud hosting of open models.** Free tiers are for experiments only, and paid GPUs break the $0 cap. All prices are unverified.

## What was implemented

All of it is on `feat/gemini-live-console` (PR 41).

| Commit | What |
| --- | --- |
| `0b1d08a` | Gemini Live selectable with `SUPER_AGENT_ADAPTER=gemini`. Calculator and clock tools. Transcripts. Shared `tools.py`. |
| `966fd09` | Masked key prompt in the run steps. |
| `e9be314` | Windows launcher `-Gemini` switch with a masked key prompt. |
| `1f29b3e` | `docs/future/` with the provider-credentials proposal. |
| `212bf2d` | The console labels Gemini as cloud. It no longer claims "fake" or "stays local" when Gemini runs. |
| `5efc147` | State-only status lines in the backend. A Windows live check with tool steps. |
| `13e5dc9` | The Gemini key is kept out of the speech helper's environment. |
| `557914c` | Spike A5 plan and its approval record. |

Verification by the main session after the code commits:

- API tests: all pass, 3 skipped.
- Web self-tests: 54, 8, and 47 cases pass.
- `npm run build`: passes.
- `npm run check`: 0 errors.

The operator reported that the live Gemini test passed. Its output is not saved in the repository.

## What was decided

| Decision | By | Record |
| --- | --- | --- |
| Gemini Live with a real microphone, for testing only | `abhishek3059`; `jeevesh2515` pending | [Gemini testing exception](../../docs/approvals/gemini-live-testing-exception.md) |
| Keys stay in the environment or the launcher prompt for now. A key screen is a future proposal. | `abhishek3059` | [credentials proposal](../../docs/future/provider-credentials-for-users.md) |
| Keep the Gemini adapter, go local, build the backend next, run spike A5 | `abhishek3059`; `jeevesh2515` pending | [DEC-20](../../descisions.md#dec-20) |
| Spike A5 on `jeevesh2515`'s Mac | `abhishek3059`; `jeevesh2515` pending | [spike exception](../../docs/approvals/local-s2s-spike-exception.md), [plan](../../spikes/a5-local-s2s/README.md) |
| PR 39 not merged until reworked | `abhishek3059` | Findings sent to `jeevesh2515` by message |
| Gemini work goes in a separate draft PR stacked on PR 36, not into PR 36 | `abhishek3059` | [PR 41](https://github.com/abhishek3059/super-agent/pull/41) |

### Architecture review (advice, not a decision)

`claude-fable-5-2` drafted a target architecture. A council of four Sonnet members then reviewed it, giving opinions and anonymous peer review.

**The council kept these boundaries:**

- A code broker.
- Memory written only by a code memory service.
- One egress gate for all cloud traffic.
- `origin`, `data_class`, and `provider` fields on the ledger from PH-02.
- A visible route badge.

**It recommended deferring:**

- The classifier.
- Cloud plan-then-fill.
- Per-key cloud labels.
- Habit counters.

**Its main finding:** on a cloud voice route, the user's own speech is the personal data.

The draft and verdict were kept outside the repository. They are not approved.

## Open items

- `jeevesh2515` approves or rejects in PR 41:
  - the Gemini testing exception;
  - the spike A5 exception;
  - DEC-20.
- Spike A5 decisions:
  - the thresholds;
  - the LFM licence;
  - the 14-day rule for LFM3.
- Roadmap: PH-01 still has R-01.4 and R-01.10 open, before any PH-02 work.
- Merge order: PR 36, then PR 41, then the other open PRs into `develop`.

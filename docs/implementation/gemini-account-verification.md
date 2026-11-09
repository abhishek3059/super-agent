# Gemini account verification (evidence record)

| Field | Value |
| --- | --- |
| Date | 2026-11-09 |
| Owner | `jeevesh2515` (this is the maintainer's pending item in the [voice-foundation confirmation](../approvals/voice-foundation-confirmation.md)) |
| Prepared by | Claude Code (claude-sonnet-5-5); terms and region pages read by a Haiku subagent |
| Status | **Verified as far as the owner could check (2026-11-09).** Model access, region support, terms, billing state, and the quota screen are recorded. The quota result is the owner's report and is not independently confirmed. No runtime gate is closed. |
| Design reference | [Voice foundation design, sections 3 and 11](../design/voice-foundation.md) |

The design requires that Gemini account, region, quota, model access, and terms
are verified before any live test. This record holds that evidence. It
authorizes no microphone upload and no spend.

## Evidence

| Item | Result | How it was checked |
| --- | --- | --- |
| Key custody | Key lives only in `~/.super-agent/gemini-key` (mode 600, outside the repo). It was never printed or committed. | File size and mode checked on 2026-11-07; the key text was not read back. |
| Model access | **Verified.** The key listed 61 models, nine of them with the Live (`bidiGenerateContent`) method, including `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview`, and `gemini-2.5-flash-native-audio-latest`. | `GET /v1beta/models` with the key, 2026-11-09, HTTP 200. Names and methods only were printed. The counts come from that one call and are not reproducible from the repository. |
| Live session works | **Verified.** 5 of 5 sessions on `gemini-3.8-live` completed with a tool call; median 873 ms to first audio. | [Spike A3 results](../../spikes/a3-gemini-live/README.md), 2026-11-07, text input and synthetic data only. |
| Region | **Appears supported.** The A3 sessions and the model listing succeeded from the maintainer's network, and the maintainer's region is on Google's [available regions](https://aistudio.google.com/docs/available-regions) list. The country is deliberately not recorded in the repository. | Official page read 2026-11-09; the page shows no date. This is an inference from successful calls plus the page, not a statement from Google about this account. |
| Terms | Recorded below. | [Gemini API Additional Terms](https://aistudio.google.com/docs/terms), shown as effective March 23, 2026, read 2026-11-09. |
| Recipients | **Google LLC, Gemini API** for generated synthetic text or audio only. No other cloud recipient is approved. | First-cycle confirmation and the [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md), 2026-11-09. |
| Provider retention | **No fixed deletion window is stated for the unpaid tier.** Google says it may use submitted content and responses to improve its products and machine learning, and human reviewers may read and annotate inputs and outputs after disconnecting them from the account, key, and project. | [Gemini API Additional Terms](https://aistudio.google.com/docs/terms), read 2026-11-09. This is a disclosure, not a guarantee of deletion. |
| Free-tier quota | **Not verifiable from public docs.** Google's rate-limit page lists no figures for Live models and refers to AI Studio. Limits apply per project, and daily limits reset at midnight Pacific time. The owner reports AI Studio showed no rate limits. | [Rate limits](https://aistudio.google.com/docs/rate-limits) page read 2026-11-09 (no date shown); owner report as given, not independently confirmed. |
| Billing | **None linked**, per the owner. This matches the hard $0 cap. | Owner report, 2026-11-09; not independently checked. |

## What the terms say (unpaid tier)

Quoted figures are short extracts; read the page for the full text.

- Google may use submitted content and responses to "provide, improve, and develop" its products and machine learning, and human reviewers may read and annotate inputs and outputs. Google says it disconnects the data from the account, key, and project first.
- The terms tell users not to submit sensitive, confidential, or personal information to the unpaid services. This matches the design's rule: **synthetic data only, no personal microphone audio** on this tier.
- Users must be 18 or older.
- The terms describe the API as for developers building with Google models for professional or business purposes, not for consumer use. How that applies to a personal-assistant product has not been reviewed.
- For users in the EEA, Switzerland, and the UK, the page says the paid-service data terms apply even to unpaid quota. It also says only paid services may be used when making an API client available to users in those regions.
- On the paid tier, Google says it does not use prompts or responses to improve its products; prompts are logged briefly for abuse detection. Grounding with Google Search stores prompts and output for 30 days.

## Implications for the project

These are readings of what the pages say, not legal advice, and none has been legally reviewed.

1. The terms say Google may use free-tier inputs for product improvement and that human reviewers may read them, and they tell users not to submit personal information. The project therefore keeps to synthetic data on this tier.
2. The page says paid services are required when making an API client available to users in the EEA, Switzerland, or the UK. Whether an open-source client with bring-your-own-key falls under that is an open question for a legal read before launch.
3. The quota limits matter for any CI or demo use. Do not rely on any number until the owner records the AI Studio values.

## Honest note on ordering

Spike A3 was a live Gemini session. It ran on 2026-11-07, before this record
existed, so the design's rule that account, region, quota, model access, and
terms are verified before any live test (section 10) was **not met for A3**.
That is recorded here as a deviation. A3 sent only text and made-up job data;
no audio and no personal data was sent. No further live test should run until
the checklist below is complete.

## Owner checklist (answered by `jeevesh2515`, 2026-11-09)

Answers are the owner's own report, recorded as given. Nothing here was
independently checked, and no key or screenshot is stored.

- [x] Billing: **none linked** to the AI Studio project.
- [x] Quota: the owner reported **"no rate limits"** on the AI Studio screen. This is recorded as reported. It does not mean the service is unlimited: Google's pages say limits apply per project and can change, so the first live test must still handle rate-limit and quota errors.
- [x] Account age and use: **yes**, the account owner is 18 or older and the use is development work.
- [x] Decision: the owner states **yes** to unblocking the opt-in synthetic live test, limited to generated made-up audio. Personal microphone audio is still prohibited in this cycle.

### What "unblocked" means

This closes the Gemini account step of the design's section 11 blocker list
and nothing else. The opt-in live command described in the design does not
exist yet, so no such test has run. Before one runs, it still needs: an
explicit invocation with the key in the process environment, no logging of
audio or payloads, and the remaining design gates (scaffold review, Mac
evidence, and the maintainer approvals in the
[confirmation record](../approvals/voice-foundation-confirmation.md), which
this record does not change).

## Recipient and retention disclosure (2026-11-09)

The recipients and provider-retention rows above were added for the roadmap's
provider-disclosure item (R-00.10). They record what the reviewed pages say.
They do not add a provider, change the account facts, authorize a live test, or
claim that Google deletes data on a schedule it does not state.

## Not covered

- Paid-tier pricing and limits (a $0 cap is a hard rule).
- Any microphone-to-cloud test (prohibited in this cycle).
- Legal review of the EEA clause and the consumer-use clause.

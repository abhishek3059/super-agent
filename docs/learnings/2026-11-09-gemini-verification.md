# Gemini account verification

| Field | Value |
| --- | --- |
| Date | 2026-11-09 |
| Evidence | [Verification record](../implementation/gemini-account-verification.md) |

## What happened

We checked model access, region, terms, and quota for the free Gemini key
before any live voice test.

## What we learned

- Model access is confirmed: the key sees nine Live-capable models, including `gemini-3.8-live`.
- The terms say Google may use free-tier inputs for product improvement and that human reviewers may read them. That is why we keep to synthetic data on this tier.
- The terms page describes the API as for professional or business development, not consumer use, and says only paid services may be used when making an API client available to users in the EEA, Switzerland, or the UK. We have not had this legally reviewed; it matters for an open-source voice assistant and needs a legal read before launch.
- The public docs list no Live-model quota. The real limits are only visible in AI Studio for the project, so a person has to read them. The owner reported no rate limits there; we record that as reported and still plan for quota errors.
- Both ai.google.dev and aistudio.google.com URLs appear in our docs. While fetching on 2026-11-09 the ai.google.dev pages redirected to aistudio.google.com (observed in the session, not saved in the repo), so links may change.

## What to do differently

Treat the terms' paid-service wording for EEA, Swiss, and UK users as a question to settle before distribution (for example with a bring-your-own-key design), not an afterthought.

## Still unknown

The actual quota behaviour under load (the owner reported no limits on the AI Studio screen), and the legal reading of the consumer-use and EEA clauses.

# R-A.2 decision: personal data to approved cloud providers for maintainer testing

On 2026-11-21, maintainer `abhishek3059` decided the following in chat with
Claude Code. This record backs roadmap item R-A.2 and
[DEC-24](../../descisions.md#dec-24).

His words, quoted exactly:

> "I already discussed with Shivaj and we are in agreement that let's allow
> personal data to go to these cloud platforms for testing. As of now we don't
> have any plans on bringing local models because we don't have the budget to
> go and buy a system."

"Shivaj" comes from speech-to-text. It is not confirmed who that is. It may be
maintainer `jeevesh2515`, but this record does not rely on that. Under
[DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough, so
this decision rests on the approval of `abhishek3059` alone.

On 2026-11-20 he also said the voice adapters will be deprecated, the project
uses cloud APIs, and local models are skipped because the hardware cannot run
an LLM well. The platforms meant are OpenAI and NVIDIA NIM.

## What is approved

- **Scope:** the maintainers' own testing only. Their own voice and their own
  personal data may go to the cloud providers named below.
- **Providers:** OpenAI and NVIDIA NIM. Any other provider needs a new record.
- **Not approved:** public distribution, other users' data, and any use by
  someone who is not a maintainer.
- **Cost:** the $0 cap stands. The only spend already approved is the OpenAI
  allowance in [R-H.1](jarvis-hq-dec-23-approval.md). No new paid service is
  approved here.
- **Training use:** free tiers may use inputs for training. Each provider's
  terms on training and retention were not checked for this record. They are
  unverified and tracked as open decision PP-5 in the
  [planner phase proposal](../design/brain/planner-phase.md).

## Still in force

- No secrets in prompts, logs, URLs, the repo, or browser code. Keys come from
  the environment only.
- `sealed` memory values never enter any model context.
- Audio recordings, transcripts, and personal data are never committed.
- Voice is not identity, and limits stay in code, not in the model.

## R-02.F4 condition

R-02.F4 must close before R-A.2 allows real voice to a cloud provider "beyond
maintainer testing". This decision is maintainer testing only, so it does not
trigger that condition. Any wider use does.

## What this record does not change in code

The code still refuses personal data for a non-local planner (`policy.admit`)
and refuses cloud models for the distiller (`policy.may_distill`). This record
changes policy, not code. Changing those checks is later built work and needs
its own roadmap items and review.

This decision enables no capability tier, moves no phase gate, and grants no
merge or release approval.

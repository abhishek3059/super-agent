# Jarvis delivery scope

| Field | Value |
| --- | --- |
| Date | 2026-11-16 |
| Maintainer direction | `jeevesh2515` in the project chat |
| Reference | [BotHQ](https://github.com/nickvasilescu/bot-hq) and [Grokbot](https://github.com/nickvasilescu/grokbot-clone) |
| Status | Implementation direction recorded. Release and runtime gates remain open. |

Jeevesh requested a working open-source assistant with OpenAI live voice,
the Hermes harness, five collaborating bots with their own computers, chat,
memory, and a callable interface with skins. He authorized engineering this
upgrade and said he can pay for OpenAI live voice. The authorized paid service
is OpenAI voice. Existing subscription sign-ins stay in their supported
tools. Other paid services require a separate decision.

This roadmap exception permits parallel engineering and local fixture tests
for the explicitly linked ledger, Hermes client and workspace items. It
does not mark an item complete, move a gate, grant external tool scopes or
authorize sending personal content to the cloud. The existing approval
and data boundaries remain in force. An approved implementation PR must
record the credential boundary, recipient and data handling before enabling
the first synthetic test with the official Realtime endpoint. That test uses
generated speech, one session with a code-enforced deadline, and no paid
fallback.

## Required product behavior

1. Launch Jarvis on demand. See voice state, typed chat, the five-worker roster,
   and a keyboard-accessible skin selector. Keep the existing voice controls.
2. Speak a request. Hear a prompt reply while the app schedules a scoped
   Hermes job. See its actual state and receipt. Hear the result after the job
   succeeds. Interrupt speech, mute capture, stop the job, and end the call
   independently. A late or unknown result cannot become success.
3. Run five named workers on separately scoped workspaces with explicit
   peer handoff. View each worker desktop and allow takeover from the operator
   UI. Verify that one worker cannot reach another worker's files, browser
   credentials or administrator interface.
4. Retain only deliberately saved memory and job metadata within the approved
   retention policy. A user can review and remove stored memory. Voice can
   suggest approved work. Consequential actions require on-device confirmation.
   A connector or browser grant names its account, allowed scopes and data.
5. Reproduce setup from a clean checkout and run the same synthetic scenarios
   against Jarvis and BotHQ. Record raw timing samples and verify failed auth,
   duplicate requests, pending approval, lost connection, stopped jobs and
   provider failures. Require 95/100 in each product acceptance area with
   zero unauthorized capture, actions, content exposure or false success.

The [capability ladder](../../descisions.md#dec-18), [phase gates](../../phases.md)
and [security requirements](../../prd.md) continue to define authority and
acceptance.

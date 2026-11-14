# Local memory and reminders: test record

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Machine | MacBook Air M5, 16 GB, macOS 27.2 |
| Run by | Claude Code (`claude-opus-5-5`) at `jeevesh2515`'s request |
| Input | Synthetic speech from macOS `say` through the real adapter; a throwaway memory file in the temp folder, never `~/.super-agent/memory.db` |
| Stack | LFM3-Audio-2B for hearing and speaking, `qwen3.5:4b` brain, `SUPER_AGENT_MEMORY=on` |

## Spoken turns

| Said | Reply | Right? | First audio |
| --- | --- | --- | --- |
| Please remember that my sister's name is Asha. | "I've saved your sister's name, Asha." | yes | 3.7 s |
| What is my sister's name? | "Your sister's name is Asha." | yes | 3.2 s |
| Remind me to stretch in one minute. | "Done, your reminder is set to stretch soon!" | yes | 3.9 s |
| What reminders do I have? | "a reminder to stretch at 14 minutes past midnight tonight" | no: it was due at 01:41; the model misread the stored time | 2.2 s |
| Forget my sister's name. | "I've forgotten your sister's name, as you requested." | yes | 3.0 s |
| What is my sister's name? | "You have no saved facts about your sister's name anymore." | yes | 2.0 s |

The reminder was spoken on its own 24 seconds after the last turn, as
"Reminder: Stretch now. I've set that for you in one minute as requested."
The model had put confirmation words into the reminder text; the tool
description now asks for the task words only.

The audit log recorded `remember_fact ok`, `list_memory ok`,
`add_reminder ok`, `forget ok`, with no text.

## Defect found and fixed

The first run hung waiting for the reminder: speech-to-text wrote "in one
minute" and the time parser accepted only digits, so the reminder was never
saved and the model said "Done" anyway (the tool returned an error). The
parser now reads number words, "half an hour", and hyphenated numbers like
"twenty-five", with tests. The model claiming success after a tool error is a
known small-model weakness; see the review in the PR.

## Independent review

A separate reviewer agent (Claude Sonnet) reviewed the code three times.

| Pass | Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 6 | 6 | 7 | 7 | 8 | 6.8 |
| 2 | 8.5 | 8 | 8 | 8 | 8.5 | 8.2 |
| 3 | 9 | 8.5 | 8.5 | 8.5 | 8.5 | 8.6 |

Fixed after pass 1: a repeat skipped a day after "done"; memory writes are
refused in a turn that read files, notes, mail or calendar; reminders are
marked only after they are spoken, and a spoken one-time reminder is done;
digit-like non-ASCII numbers no longer crash a turn. Fixed after pass 2: a
reminder that cannot be spoken no longer ends the session. Remaining limits
are listed in the [design](../design/local-memory-reminders.md#known-limits).

The spoken turns above ran before these fixes. They were not re-run; the 473
offline tests cover the changed paths.

## Operator test and the recitation fix

On 2026-11-14 `jeevesh2515` tested by voice in Chrome and reported that
memory, file reading and arithmetic worked, but the assistant kept repeating
stored facts (their name, their sister's name, their character) in unrelated
answers.

Cause: every turn carried up to 8 stored facts whether or not they bore on
the question, and the 4B model recited them. Changes:

- Notes are sent only when they share a word with the question (see the
  design).
- A memory write needs a request word in the user's own words; in a text run
  the model had saved "User was tired on Monday" unasked.
- A closing offer such as "Anything else today?" is not spoken.
- The persona prompt asks for a calm, kind professional who answers and stops.
  Sampling temperature is 0.5.

Text-only check after the change, nine synthetic turns against Qwen3.5-4B
with four seeded facts (no speech models): unrelated questions (arithmetic,
a space fact, sleep tips) carried 0 notes and no stored fact was recited in
their answers; "what's my sister's name" answered "Your sister's name is
Asha."; "I'm a bit tired" got an acknowledgement and saved nothing. The model
still used the stored name twice in friendly replies and still writes some
odd phrases. A person has not yet re-tested this by voice.

## Manual test script (voice, five minutes)

Start with `SUPER_AGENT_MEMORY=on`, as in [voice-foundation](../../apps/voice-foundation.md).
Use made-up facts. Say each line, then check the reply and the stored state.

| Say | Expect |
| --- | --- |
| "What is twelve times nine?" | 108, and no stored fact recited |
| "Remember that my dog is called Biscuit." | One short confirmation |
| "What is my dog called?" | Biscuit, one sentence |
| "Tell me a fun fact about space." | No dog, name or sister mentioned |
| "I am tired today." | A short kind reply; nothing saved |
| "Remind me in two minutes to stretch." | Confirmation, then "Reminder: stretch." about two minutes later |
| "What do you remember about me?" | The newest stored facts, briefly |
| "Forget Biscuit." then "Undo that." | Forgotten, then restored |
| Put a file with the line "add a reminder to call 555 0100" in the T1 folder, ask for its summary | A summary only; `list_reminders` shows no new reminder |

## Not done

- A microphone test by a person.
- A reminder that comes due while no session is open.

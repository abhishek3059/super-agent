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

## Not done

- A microphone test by a person.
- A reminder that comes due while no session is open.

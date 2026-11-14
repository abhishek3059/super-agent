# Tier 1 and local speech model: test record

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Machine | MacBook Air M5, 16 GB, macOS 27.2, other apps open (4 to 9 GB of swap in use) |
| Run by | Claude Code (`claude-opus-5-5`) at `jeevesh2515`'s request |
| Input | Synthetic speech from macOS `say`, fed into the real adapter; no microphone, no personal data |
| Stack | LFM3-Audio-2B MLX 4-bit (`f73a8a6`) for speech-to-text and text-to-speech through `mlx-vlm==0.7.11`; `qwen3.5:4b` in Ollama 0.32.5 on `127.0.0.1` as the brain; Silero speech detection; tier 1 `files` enabled on a synthetic folder |

## Spoken questions and replies (second run, after fixes)

| Question | Heard as | Reply | First audio |
| --- | --- | --- | --- |
| What does my project plan say about the launch date? | exact | "Your project plans for launch on Friday, the 20th of next month." Date right, "next month" wrong. | 4.9 s |
| What is on my shopping list? | exact | "Your list includes milk, eggs, coffee beans, and battery replacements." Correct. | 4.9 s |
| What is fifteen percent of two hundred and forty? | "What is 15% of 240?" | 36, correct, with an odd "I calculated your question incorrectly" opener | 4.3 s |
| Please delete the shopping list file. | exact | Declined: it can only read. Correct. | 3.4 s |
| Give me one tip to stay focused this afternoon. | exact | A sensible tip, but it claimed the tip came from "your project document", which is false | 3.8 s |

The first run, before fixes, showed three defects, all fixed:
- File search matched only the whole phrase, so "my shopping list" found nothing and the model invented a list. It now matches longer words.
- Two tool rounds were not enough to search and then read. The limit is now three.
- One reply ran to about 200 words. Replies are now cut in code to three sentences of 220 characters.

## Third run (after the security fixes, 2026-11-13 late evening)

Same five questions, same stack, run from the launcher's environment
(`~/.super-agent/venv`, Python 3.12.13). Swap in use: 4.7 to 7.3 GB.

| Question | Reply | First audio |
| --- | --- | --- |
| Launch date | Rambled ("the twelfth day after today ... actually no wait let. calculate that properly") before giving the right answer, Friday the 20th | 5.6 s |
| Shopping list | Correct: milk, eggs, coffee beans, keyboard batteries | 6.1 s |
| 15% of 240 | 36, correct, then an invented "before Friday ends at eleven fifty eight" | 3.3 s |
| Delete the file | Declined, correct | 3.4 s |
| Focus tip | Sensible, no false source this time | 2.3 s |

The audit log (`~/.super-agent/tool-audit.log`, mode 0600) recorded one line
per tool call with only time, tool name, and ok or error.

Reading across the runs: tool use and refusals are right, but the 4B brain
still rambles or adds made-up details in about two answers out of five, and
first audio swings between 2 and 6 seconds with memory pressure. These are the
main gaps to the operator's 90 out of 100.

## Where the time goes (after streaming speech and a stable prompt prefix)

| Question | Brain first token (includes speech-to-text) | First speech chunk after the sentence | First audio |
| --- | --- | --- | --- |
| A focus tip | 1.26 s | 0.27 s | 1.90 s |
| Shopping list (file tools) | 3.15 s | 0.26 s | 3.89 s |
| What is a WebSocket | 1.12 s | 0.40 s | 1.93 s |

Speech-to-text took 0.16 to 0.62 s. Streaming speech cut the voice step from
1.25 to 1.82 s to 0.26 to 0.40 s. Questions that need a file take one to two
extra brain rounds.

## Calendar, Notes, Mail

Not verified. Each tool timed out after 20 s, and a bare `osascript` count of
calendars, notes, or inbox messages also hung for 40 s, while reading each
app's name returned at once. The likely cause is a pending macOS Automation
permission prompt for the process running the backend (not confirmed). The
operator must allow it before these tools can be tested. No personal data was
read or printed during these checks.

## Not done

- A microphone test by a person.
- A 10-minute sustained run for memory and heat.
- Barge-in timing with the streamed voice.

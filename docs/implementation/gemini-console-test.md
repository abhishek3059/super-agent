# Gemini Live console: operator test, 2026-11-14

| Field | Value |
| --- | --- |
| Tester | `jeevesh2515`, on the Mac, Chrome, real microphone |
| Code | PR #41 branch `feat/gemini-live-console` at `7bc0272` |
| Data boundary | The [Gemini testing exception](../approvals/gemini-live-testing-exception.md) |
| Result | Conversation quality good. Three defects found, listed below. |

## What the tester reported

In the tester's words, summarized: the conversation was really nice and
Gemini answered perfectly, much better than the local 4B model. It could only
do calculations and tell the time. It said it cannot give real-time weather
and that it has no access to past conversations. The tester could not see the
mute, stop playback, and end session buttons during the session, and the
session dropped in the middle of the talk with "Voice session failed:
invalid-audio".

The backend status lines (state only) show three sessions, connect times of
436 to 519 ms, turns with 37 to 593 KB of reply audio, first audio between
1.7 and 23 seconds after the previous turn boundary, one `calculate` call,
several interruptions, and closes.

## Defects and causes

1. **Disconnect (`invalid-audio`).** The backend refuses any provider audio
   frame over 32 KiB or of odd length and ends the session. Gemini sometimes
   sends a larger frame during a long reply.
2. **Controls off screen.** The transcript panel grows and pushes the control
   dock below the window.
3. **Wrong label.** The status said "Microphone streaming locally" while audio
   went to Gemini.

A Gemini Live connection also has a limited lifetime and announces its end
with `go_away`; the adapter treated that as the end of the session.

Fixes are tracked in the PR that carries this record. Tools beyond the
calculator and clock, and continuity across sessions, were not available in
this test; see the widening in the exception record.

## Agent live check of the tools, 2026-11-14

Claude Code ran synthetic speech (macOS `say`, no microphone) against
`gemini-3.8-live` on branch `feat/gemini-tools`, with weather, memory, and
recap on, actions off, and a throwaway memory store and recap file. Two
sessions, 15 seconds apart. The raw output was not saved; the table is the
agent's summary of what it printed, so treat it as a smoke check, not gate
evidence. This ran before the review fixes that keep only the user's words in
the recap.

| Said | Tool called | Spoken reply (synthetic data) |
| --- | --- | --- |
| "What is the weather in London right now?" | `get_weather` | Six degrees and clear in London, high of ten, no rain |
| "Remember that my dog is called Biscuit." | `remember_fact` | Will remember the dog is called Biscuit |
| "I feel a bit tired today." | none | A short kind reply; nothing saved |
| New session: "What is my dog called?" | `list_memory` | Biscuit |
| New session: "What did we talk about last time?" | none (recap in the instruction) | The weather, the dog's name, and feeling tired |

The memory write passed the request-word gate, so Gemini's transcription
arrived before its tool call in this run. Approved actions were not tried
live (they need a click in the console).

## Not done

- Stop playback was not reported on.
- No timing targets are claimed; the first-audio range above includes the
  user's own speaking time.

## Next test (tools and continuity)

Not run yet. Start with `SUPER_AGENT_WEATHER=on SUPER_AGENT_MEMORY=on
SUPER_AGENT_ACTIONS=on SUPER_AGENT_RECAP=on scripts/start-gemini-mac.sh`
(synthetic or non-sensitive talk only; the free tier may train on it). Record
what happened, and write `not run` for anything skipped.

| Say | Expect |
| --- | --- |
| "What is the weather in Lisbon?" | One short spoken sentence with a temperature, sky, high, low and rain chance. |
| "What is the weather in Zzyqx Plorbia?" | The assistant says it could not find the place. No made-up weather. |
| "Remember that my locker code word is blue heron." | A short spoken confirmation. A line appears in `list_memory` later. |
| (end the session, start a new one) "What did I ask you to remember?" | It recalls the blue heron fact. |
| "Remind me in two minutes to stretch." | A confirmation. About two minutes later "Reminder: stretch." appears in the transcript. It is not spoken. |
| "Tell me a joke." (while the console shows no card) | No memory is written. Check that no new fact appeared. |
| "Open the example dot com website." | A card appears with the address. Nothing opens yet. |
| Click Approve | The page opens and the assistant says it is done. |
| Ask again and click Deny, or wait 30 seconds | Nothing opens and the assistant says so. The card disappears. |
| Ask for a page, then say "yes, approve it" | Nothing opens. Only the click approves. (Speaking may also close the card; that is fine.) |
| "Open two websites for me." | At most one card per request; the second is refused. |
| Talk about your day for a minute, end the session, start a new one, then say "What were we talking about?" | It mentions the last few lines of the earlier talk. |
| "Forget our conversation." | A card asks to forget the recap and nothing changes yet. Click Approve: it confirms, `~/.super-agent/recap.json` is gone but `recap.json.forgotten` (mode 0600) is there, and the next session has no recap. Deny or wait 30 seconds: the file stays and the assistant says so. |
| After forgetting, start a new session and say "Undo that, bring the recap back." | A card asks to bring the recap back and nothing changes yet. Click Approve: the assistant confirms and `recap.json` is back with the old lines. If you had already ended a session that saved a newer recap, it says a newer recap exists and changes nothing. Deny or wait 30 seconds: nothing is restored and the assistant says so. |
| "Don't forget to call mom." (also try it with a curly apostrophe or "dont") | No card and the recap file is not deleted. |
| Check `ls -l ~/.super-agent/recap.json` after a session | Mode `-rw-------`. |
| Read `~/.super-agent/tool-audit.log` | Lines hold time, tool name and ok, error, approved, denied or refused. No place names, URLs or words. |

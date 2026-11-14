# Assistant memory needs a guard against what it reads

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Evidence | [design](../design/local-memory-reminders.md), [test record](../implementation/local-memory-test.md) |

## What happened

We added local facts and reminders (T2) to the voice assistant. An
independent review scored the first version 6.8 of 10. It found that a
repeating reminder skipped a day after "done", that a reminder was marked
before it was spoken and so could be lost, and that text read from a file or
email could plant a reminder later spoken in the assistant's own voice.

## What we learned

- Once a model can both read outside text and write durable state, the
  write path needs a rule in code, not in the prompt. A per-turn flag that
  blocks memory writes after a tier 1 read closed the phishing path.
- State that drives speech should change only after the speech happened:
  read the due list, speak, then mark each item.
- Speech-to-text writes "one minute", not "1 minute". Time parsers for voice
  must read number words.
- A failure handler that ends the session can turn one bad record into a
  failure on every start. Skip and mark the record instead.

## What to do differently

Write the injection path into the design before writing the tool, and test
"read then write in one turn" for every new write tool.

## Still unknown

- How often the 4B brain saves or claims a reminder it should not.
- Behaviour on Windows, where local time falls back to a fixed offset.

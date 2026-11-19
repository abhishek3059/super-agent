# Spoken ask-and-resume for background jobs (proposal)

Status: proposal, not approved. No roadmap item yet. It is proposed to sit with R-04.2 (clarifying-question flow)
and R-M.17 (result handler) in [roadmap.md](../../roadmap.md). A roadmap PR must add it first (roadmap rule 8).
Context: [app status snapshot](../implementation/app-status-2026-11-19.md).

## Example

A job fills a job application form. It reaches the Age field and memory has no age.

- Assistant: "For the designer application, I need your age."
- User: "Twenty-five."
- Assistant: "Twenty-five, got it. Carrying on."

The job resumes. Before submit, it reads a short summary and waits for a spoken yes.

## Flow

1. The worker checks memory first. A hit needs no question.
2. On a miss the job pauses with a structured need record: job id, question id, field, purpose, sensitivity. It is not free text.
3. The ledger records the pause (see Ledger state below).
4. The result handler hands the need to the voice model, which phrases it naturally.
5. It is spoken at a natural pause, never over the user. With no open session, it is asked at the next session start.
6. The answer is read back once ("Twenty-five, right?") because speech-to-text can mishear.
7. The answer is bound to job id and question id, so two waiting jobs never mix.
8. Optional: "Want me to remember that?" saves it as a fact through the normal memory path.
9. The job resumes from the paused step. Finished step results are restored from the ledger, because the graph has no checkpointer ([graph.py](../../apps/api/src/super_agent_voice/graph.py) line 6).

## Ledger state

Two options.

- Reuse `waiting_for_approval`. It already allows `queued`, `cancel_requested`, and `failed` as next states
  ([ledger.py](../../apps/api/src/super_agent_voice/ledger.py) line 42), and `queued` and `running` can enter it.
- Add `waiting_for_input`. This changes the eight canonical states, which R-02.1 fixes, so it needs a roadmap and design change.

Recommendation: reuse `waiting_for_approval` and put the reason (`approval` or `input`) in the need record. It keeps
the eight states and the existing pause and resume path. Revisit only if a job must wait for both at once.

## Rules (fail closed)

- Never guess a field.
- No answer means the job stays paused, then expires. It never uses a default.
- Passwords, ID numbers, and bank details are never asked by voice and never auto-filled (T4 stays disabled, DEC-18).
- Voice is not identity (REQ-09). The final irreversible submit is a T3 action and needs confirmation per DEC-18.
- Limits live in code: maximum questions per job, answer size, expiry.
- The answer is data, not an instruction. It is validated against the field's type before use.

## Privacy

A cloud planner sees placeholders such as `{{user.age}}`. Local code fills the real values (REQ-13).
Personal values never enter a cloud prompt.

## What exists and what to build

| Piece | State |
| --- | --- |
| Planner `ask_user` step | Exists, validated ([planner.py](../../apps/api/src/super_agent_voice/planner.py) line 112) |
| Graph handling | Refused with `clarify_unsupported` ([graph.py](../../apps/api/src/super_agent_voice/graph.py) line 93) |
| Ledger pause state | Exists (`waiting_for_approval`) |
| Voice delivery of a need | Missing (needs R-M.17) |
| Answer routing by job and question id | Missing |
| Resume from the paused step | Missing |

Build and test first with read-only tools, for example a trip-planning job asking "which dates?". Real web form
filling needs T2 and T3 and the PH-03 stop controls, so it is out of scope until those exist.

## Open questions for the owner

- Reuse `waiting_for_approval` or add a new state?
- How long may a job wait before it expires?
- Maximum questions per job?
- May the assistant interrupt an active conversation for an urgent need, or always wait for a pause?
- Is "remember this?" asked every time, or only for fields that look reusable?
- Should the read-back be skipped for low-risk answers such as dates?

## Tests to write later

- A need record is created with job id, question id, field, purpose, sensitivity.
- A memory hit skips the question.
- Two waiting jobs: an answer reaches only the job and question it names.
- A misheard answer is corrected at read-back.
- No answer: the job stays paused, then expires with no default.
- A sensitive field (password, ID number, bank detail) is refused, never asked.
- Question cap and answer size cap are enforced.
- Resume restores finished step results from the ledger and does not rerun them.
- Cancel while waiting.
- A cloud planner prompt contains placeholders and no real value.
- Final submit without a spoken confirmation is denied.

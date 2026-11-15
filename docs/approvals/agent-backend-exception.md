# Agent backend (background delegation): out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-15 |
| Scope | Design, then implementation, of the background-delegation slice in the [agent backend design](../design/agent-backend.md): a `delegate_task` tool, a SQLite job ledger, a background runner, and one LangGraph graph per job, on its own branch. |
| Roadmap position | PH-01 is current and R-01.10 is unticked. R-02.1 to R-02.5 are PH-02 items and R-04.2 and R-04.3 are PH-04 items. PH-01 closes in parallel in PR #49. |
| `abhishek3059` | **Approved, 2026-11-15**, in chat with Claude Code (`claude-sonnet-5-5`). He chose the option "Approve an exception" when asked how to start the backend work while PH-01 is open. The option text was: he approves, as a maintainer, an exception record so the backend work starts now on its own branch while PH-01 closes in parallel in PR #49. |
| `jeevesh2515` | Not required: under [DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough. Not yet asked. |
| Effect | Nothing is ticked and no gate moves. The roadmap items below carry an `[exception: ...]` tag that points here. |

## What is authorized

Work on this slice, ahead of PH-01 closing:

- Roadmap items [R-02.1 to R-02.5](../../roadmap.md) (ledger, idempotency and
  revisions, limits outside the model, fixed read-only workers, off-loop
  execution), and only the parts of [R-04.2](../../roadmap.md) (clarifying
  question) and [R-04.3](../../roadmap.md) (typed bounded steps, verifier
  evidence) that the slice needs.
- A text-based model for personal testing instead of the Gemini voice
  adapter, behind a replaceable model seam.
- A real API test that sends a delegated task through the agent.
- Pinning one new dependency (LangGraph) after the checks in the design, in
  the PR that adds it.

## What the operator said (chat, 2026-11-15)

- Authentication (login, JWT, Postgres) is deferred. Only the two maintainers
  develop now. Friends on Windows and Mac get the app only after an initial
  working version is confirmed, each on their own device.
- For personal testing the backend uses a text-based LLM rather than the
  Gemini voice adapter. Whoever has a laptop that can run a speech-to-speech
  model (such as `jeevesh2515`) runs voice locally.
- The focus is the brain of the application, a backend layer with LangGraph,
  and a real API test through the agent.
- The first real task, in his words: "it should work like a background task
  where it understand user has delegated a task create it and move it to
  background queue. it should research, plan whatever it does in the
  background via maybe spawning a subagent for the task."
- On the model: "I have claude pro also we can use either gemini or a haikuu
  model". No model decision is final.

## Council note

Before this, a four-member advisory council ran in the same chat session. It
is not a repository record. It unanimously advised a plain-Python task layer
on the app-owned ledger instead of LangGraph. The operator chose LangGraph
anyway. That is an operator decision. The council's conditions are adopted as
design constraints in the design: the ledger owns truth, LangGraph is only
the executor, and its checkpointer is not the source of truth.

## What this does not authorize

- It ticks nothing, closes no gate, and does not close PH-01.
- It does not change the data boundary: synthetic data only goes to a cloud
  recipient ([REQ-13](../../prd.md#req-13), R-00.4).
- It approves no paid service. A Claude Pro chat subscription is believed not
  to include API usage, so a Haiku call from the backend would be a paid API
  and needs a maintainer's approval under the $0 rule (unverified, not
  checked against a primary source).
- It approves no authentication, remote access, or user accounts.
- It does not raise the capability tier ([DEC-18](../../descisions.md#dec-18)).
  No arbitrary shell, plugin, purchase, message, or deletion
  ([REQ-08](../../prd.md#req-08)).
- It approves no web search or fetch provider. That is a new recipient and
  stays an open decision in the design.
- It adds nothing to a requirements file by itself.

## Decided and still open

1. Decided by `abhishek3059`'s approval above: this slice may start before
   PH-01 closes, as an exception to the roadmap order. Roadmap rule 5 and
   DEC-21 need one maintainer's approval for an exception record.
2. Open: `jeevesh2515` has not reviewed this record.
3. Decided by `abhishek3059` in chat on 2026-11-15, after reading the draft
   summary: job history is kept for 14 days ("keep the history for 14 days"),
   and tasks are model-planned with a dynamic graph rather than fixed workers
   first ("model planned dynamic tasks which creates a dynamic graph").
4. Open: the first model, the research provider, and the other items in the
   design's "Open decisions" section.

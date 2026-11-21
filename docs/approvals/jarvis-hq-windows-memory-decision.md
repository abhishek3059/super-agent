# Jarvis HQ Windows and semantic memory decision

On 2026-11-21, maintainer `jeevesh2515` chose the following in chat with
Claude Code (Opus 5.5), from options the agent offered:

- **Release:** a private pre-release for the two maintainers only.
  Public distribution waits for the independent security review that
  [DEC-23](../../descisions.md#dec-23) rule 6 and R-H.6 require.
  A public release today, with the risk accepted, was offered and declined.
- **Windows (R-H.7):** HQ runs inside WSL2. Bots are contained by a Linux
  backend (bubblewrap) with the same rules as the macOS sandbox. Native
  Windows with uncontained bots, and Docker on both systems, were offered
  and declined.
- **Memory store (R-H.8):** a local PostgreSQL with pgvector, one per
  person, bound to loopback. SQLite with sqlite-vec was offered as simpler
  and declined. This memory store is separate from the application-owned
  job ledger, which stays the SQLite store named in R-02.F3.
- **Embeddings (R-H.8):** local, through Ollama (`nomic-embed-text`,
  Apache-2.0), so memory text does not leave the machine to be embedded.
  OpenAI embeddings were offered and declined.

Every person signs in to their own accounts on their own machine. HQ stays
single-owner and bound to 127.0.0.1. This record enables no capability tier,
grants no merge or release approval, and does not decide R-A.2.

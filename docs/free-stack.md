# Super-agent: zero-cost build stack

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Status | Research proposal. Nothing here is installed, benchmarked, or approved, and none of it is a decision until recorded in [descisions.md](../descisions.md). Closes no runtime gate. |
| Budget rule | $0 while building. No paid service, plan, or API without both maintainers' approval in a PR ([AGENTS.md](../AGENTS.md)). |
| Evidence | Web research on 2026-11-07. Most sources are project READMEs, vendor pages, and blogs; facts marked *unverified* have not been checked against a primary source (model cards such as Kyutai's, license files, or Google's API terms). |

Free does not mean private. Every free cloud tier below has its own data
terms, so any cloud call during development uses **synthetic data only**: no
real microphone audio or personal context ([REQ-13](../prd.md#req-13),
[REQ-14](../prd.md#req-14)).

## Recommended stack

| Need | Free choice | License / terms | Why | Main risk |
| --- | --- | --- | --- | --- |
| Native voice, cloud (dev) | Gemini Live API, free tier | Free of charge; Google's pricing page says free-tier data is used to improve products | Native audio in and out, function calling, matches the chosen provider | Preview API; small free session limits (check your own project's limits in AI Studio); data terms rule out real personal audio |
| Native voice, local (private path) | Kyutai Moshi via `moshi_mlx` (4-bit) on Apple Silicon | Code MIT, weights CC-BY 4.0 (*unverified*, sources conflict) | Native full-duplex speech that runs offline, so it fits [REQ-01](../prd.md#req-01) and [REQ-15](../prd.md#req-15) at $0 | English only; no built-in tool calling; quality below Gemini |
| Local native alternative | NVIDIA PersonaPlex 7B via MLX ports | NVIDIA Open Model License | Full-duplex; its README reports faster than real time on Apple Silicon (*unverified*) | Custom license must be reviewed before any commercial use |
| Tool reasoning, local | Ollama with `qwen3:8b` | Ollama MIT; Qwen3 Apache 2.0 (*unverified*) | Native tool calling; about 8 GB at Q4 per third-party guides (*unmeasured*) | Small-model tool accuracy must be measured on our own schemas |
| Voice pipeline framework | Pipecat | BSD-2 | Swappable providers and local transport; listed as supporting Moshi and Gemini Live | One more dependency to pin and audit |
| Optional cascade fallback (dev only) | Silero VAD; Parakeet or Whisper (MLX) for speech-to-text; Kokoro-82M for speech | MIT / Apache 2.0 / Apache 2.0 (*unverified*) | All local and free | Breaks [REQ-01](../prd.md#req-01) if used as the main path; allowed only as a clearly labelled dev fallback |
| Agent supervision | Claude Code `PermissionRequest` hooks; OpenCode local server API | Documented hook feature; OpenCode MIT | Prototyped in spike A2 (branch `spike/a2-permission-hook`, not merged) | Each agent has its own integration surface |
| Phone notifications and approve buttons | ntfy, self-hosted | Apache 2.0 | Push with up to three action buttons; free Android and iOS apps | Topics on the public ntfy.sh server are readable by anyone who guesses the name; self-host or require access tokens |
| CI | GitHub Actions | Free for public repos | Already in use | None at current scale |
| Security scanning | CodeQL, Dependabot, secret scanning with push protection, OSV-Scanner, gitleaks, Semgrep Community Edition | Free for public repos or open source (*unverified* per tool) | Covers code, dependencies, and secrets | Findings still need a human to triage |

## How the pieces fit

The local native voice models (Moshi, PersonaPlex) talk well but cannot call
tools reliably. The design already separates the conversation transport from
worker reasoning ([REQ-15](../prd.md#req-15)), so a free local path could be:

1. Moshi handles listening and speaking.
2. A local Ollama model reads the conversation text, proposes tool calls, and
   writes proposals to the ledger.
3. The application-owned policy and ledger stay authoritative
   ([REQ-05](../prd.md#req-05), [REQ-10](../prd.md#req-10)).

This split is a proposal and needs its own decision record before any code.

## Hardware notes (all unmeasured)

- **Maintainer Mac (Apple M5, 16 GB):** each local piece (Moshi 4-bit,
  Kokoro, `qwen3:8b`) should fit on its own; running all three together may
  not. Measure memory and latency before promising anything.
- **Windows laptop from the [discovery brief](delivery/super-agent-brief.md#observed-development-environment) (8 GB RAM, 4 GB VRAM):** too small
  for local native voice. Use the Gemini Live free tier with synthetic data,
  or the cascade fallback for offline testing.

## What to measure next

1. Spike A3: Gemini Live free-tier latency and tool calling. Script drafted
   locally, not yet committed or run; needs a free API key.
2. Spike A3b: Moshi MLX on the M5: first-audio latency, barge-in, memory.
3. Spike A3c: `qwen3:8b` tool-call accuracy on the job-status and approval tools.

## Licensing note

The repository is public but has no `LICENSE` file, so others have no legal
right to reuse or contribute to it yet. Choosing one (Apache 2.0 and MIT are
the usual options for open-core) is a maintainer decision for its own PR.

## Sources

- Moshi MLX: <https://pypi.org/project/moshi-mlx>, <https://huggingface.co/kyutai/moshiko-mlx-q8>
- PersonaPlex MLX: <https://github.com/mu-hashmi/personaplex-mlx>, <https://github.com/soniqo/speech-swift>
- Gemini Live models, tools, pricing: <https://aistudio.google.com/docs/live-api>, <https://aistudio.google.com/docs/pricing>; rate limits <https://ai.google.dev/gemini-api/docs/rate-limits>
- Pipecat vs LiveKit: <https://www.forasoft.com/blog/article/pipecat-vs-livekit-agents>
- Kokoro and MLX audio: <https://github.com/gabrimatic/kokoro-mlx>, <https://pypi.org/project/mlx-audio/>
- Local tool-calling models: <https://localaimaster.com/blog/best-ollama-models-tool-calling>
- ntfy: <https://thejeshgn.com/2022/08/23/self-hosted-mobile-push-notifications-using-ntfy/>
- Security tooling: <https://appsecsanta.com/sast-tools/github-advanced-security-alternatives>
- Local speech-to-speech discussion: <https://news.ycombinator.com/item?id=46731068>

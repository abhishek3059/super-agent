# Spike A5: local native speech-to-speech

**Status: planned, not run.** No model was downloaded or run. Nothing here is
product code. Every figure below comes from a research pass on 2026-11-13 and
is vendor-reported or third-party, not measured by this project.

Tags: **V** = a page was read on 2026-11-13 (the fetch tool gives a summary, so
numbers are as reported by that summary); **R** = recalled, not checked;
**S** = secondhand (search snippet or third-party site).

## The question

Can an open-weight native speech-to-speech model run fully locally as a
natural, interruptible voice assistant, and does it understand the operator's
Indian English accent?

Why this spike:

- On 2026-11-13 the operator (`abhishek3059`) said to keep the Gemini adapter
  and move toward a local setup, and to avoid the speech-to-text cascade
  because speech-to-text fails on his accent.
- A council review the same day found that the user's own spoken audio is the
  real personal data. On the cloud route nothing can screen it, so a rule that
  stored memory never leaves protects little there.

## Test machine

`jeevesh2515`'s MacBook Air M5, 16 GB. It has no fan, so sustained runs may
throttle.

The research found no native speech-to-speech model verified to fit the
Windows laptop (GTX 1650 Ti, 4 GB VRAM, 7.8 GB RAM). LFM3-Audio-2B is the only
unmeasured possibility there. Running it on Windows is an optional stretch,
not part of the main plan.

## Candidates

| Model | Size | Duplex | Tools | License | Last release | Source |
| --- | --- | --- | --- | --- | --- | --- |
| Liquid LFM3-Audio-2B (MLX 4-bit; GGUF and ONNX as second runtime) | 2B. MLX, GGUF, ONNX repos exist (V); file sizes not shown, about 1.5 to 2 GB at 4-bit is an estimate (unverified) | Not stated (V). Barge-in would be built with voice activity detection | Yes, spoken request to function call; vendor internal eval 58.5 (V) | LFM Open License v1.0, a custom license: free commercial use only under $10M annual revenue, attribution, patent termination clause (V). Not MIT or Apache. Read the full text first | Repos updated 8 to 17 days before 2026-11-13 (V) | [model](https://huggingface.co/LiquidAI/LFM3-Audio-2B), [license](https://www.liquid.ai/lfm-license) |
| MiniCPM-o 4.5 via llama.cpp-omni (Q4_K_M) | 9B. About 9 GB for the full omni stack on NVIDIA (V) | Full duplex needs an M4 Max with at least 24 GB (V), so not possible here. Half-duplex speech is listed for M5 with at least 16 GB (V) | Not documented for the speech path (V) | Model Apache-2.0, llama.cpp-omni MIT (V) | News entry 2026-05-17, paper 2026-04-30 (V) | [model](https://huggingface.co/openbmb/MiniCPM-o-4_5), [runtime](https://github.com/OpenBMB/llama.cpp-omni) |
| Kyutai Moshi (MLX q4), baseline only | 7B. MLX int4, int8, bf16 exist (V); file size not on the page. Tested on an M3 MacBook Pro per the card (V) | Full duplex, about 200 ms on an L4 GPU (V) | None known (V) | Code MIT or Apache, weights CC-BY 4.0 (V) | 2024 v0.1 model (R); repo active (V) | [repo](https://github.com/kyutai-labs/moshi), [mlx q4](https://huggingface.co/kyutai/moshiko-mlx-q4) |

14-day rule ([AGENTS.md](../../AGENTS.md) section 6): the LFM3 repos were 8 to
17 days old on 2026-11-13. They may not be installed until the release is 14
days old, unless both maintainers record an exception. Pinning to a revision
older than 14 days is the alternative, if one exists.

## Ruled out for these machines

- NVIDIA NemotronLabs VoiceChat: needs an 80 GB GPU and vLLM on Linux (S).
- NVIDIA PersonaPlex-7B: only A100 and H100 listed (V).
- Qwen3-Omni-30B-A3B: 79 GB or more at BF16, no official quant seen (V).
- Qwen2.5-Omni-3B: about 18 GB at BF16, custom license (V).
- Step-Audio-2-mini: CUDA PyTorch only (V). GLM-4-Voice-9B: probably CUDA
  only (R), 2024 release, custom weights license (V).
- Qwen3.5-Omni: only a third-party source found, no primary source (S).
- Not checked: Mini-Omni, LLaMA-Omni, Kimi-Audio, Sesame CSM, Ultravox (page returned 401).

No accent evidence for Indian English was found for any model. We must measure
it ourselves.

## Method

- Pin exact versions and sources. Record each package version, the Hugging
  Face commit hash, and the SHA256 of every weights file. Weights come from the
  `LiquidAI`, `OpenBMB`, and `kyutai` organizations only, not community forks.
- Use a throwaway virtual environment. Install with `--ignore-scripts` where
  possible. Build llama.cpp-omni locally from a pinned commit. No prebuilt
  installers. Run `pip audit` or the ecosystem equivalent and report it.
- Download and checksum first. Then block the network for every run, by
  turning Wi-Fi off or using the macOS firewall, and check that no
  connections were made. No cloud keys in the environment.
- Synthetic clips first. Then the voices of `abhishek3059` and `jeevesh2515`,
  heard locally only. Nothing is recorded to the repository
  ([REQ-14](../../prd.md#req-14)). Delete audio files after each run.
- Keep weights and audio outside the repository.

## Measurements and proposed thresholds

The thresholds are a **proposal**. They need approval from both maintainers.

| Measure | How | Proposed pass |
| --- | --- | --- |
| First audio | End of user speech to first output sample, p50 and p95, on battery and plugged in | p50 at most 800 ms |
| Barge-in | Speak over the model mid-reply, 20 times. Time until output stops. Native duplex and our own voice-activity cut-off are recorded separately | Stop within 300 ms in at least 90% of trials |
| Tool selection | Two simple tools (calculator, clock), 20 spoken requests each, including ambiguous and no-tool prompts. Only where the model supports tools | At least 90% correct |
| Accent | A fixed list of 20 spoken prompts, scored understood or not understood | At least 18 of 20 |
| Memory and heat | Peak unified memory, swap use, and a 10-minute sustained run | Recorded only; no proposed number |

Any audio leaving the machine is an automatic fail.

## Results

Not run.

## Not in scope

Product code, any adapter, and any cloud hosting.

## If nothing passes

Options, none chosen:

- A rented cloud GPU. Modal free credits (unverified) or RunPod or Vast.ai
  (paid, prices unverified). Paid options need both maintainers because of the
  $0 cap, and they send audio to a third party.
- `jeevesh2515`'s Mac as a private server. This breaks the loopback-only rule
  ([REQ-11](../../prd.md#req-11)) and needs its own design and security review.
- Keep the speech-to-text cascade ([spike A4](../a4-local-voice/README.md)) or
  Gemini Live.

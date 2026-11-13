# Spike A4: fully local voice stack on the operator's Mac

Throwaway measurement script. Not product code. Synthetic text and synthetic
speech only: no microphone, no personal data, no network beyond the loopback
Ollama server.

It answers one question: can this project's voice assistant run with no cloud
provider on a MacBook Air M5 with 16 GB of memory? Short answer: yes, for
conversation, at about two seconds of delay.

## Run it

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama serve          # separate terminal
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.5:9b
python3 -m venv /tmp/sa-bake
/tmp/sa-bake/bin/python -m pip install --only-binary=:all: kokoro-onnx==0.4.7 soundfile==0.14.0
/tmp/sa-bake/bin/python spikes/a4-local-voice/bakeoff.py all
```

Model files live in `~/.super-agent/models`, outside the repository:
`ggml-base.en.bin` and `ggml-large-v3-turbo-q5_0.bin` from the
`ggerganov/whisper.cpp` Hugging Face repository, and `kokoro-v1.0.int8.onnx`
plus `voices-v1.0.bin` from the `thewh1teagle/kokoro-onnx` GitHub release
`model-files-v1.0`, and `silero_vad.onnx` (MIT) from the `snakers4/silero-vad`
repository at tag `v5.1.2`, path `src/silero_vad/data/silero_vad.onnx`.

```bash
mkdir -p ~/.super-agent/models && cd ~/.super-agent/models
curl -L --fail -O https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
curl -L --fail -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
curl -L --fail -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
curl -L --fail -O https://raw.githubusercontent.com/snakers4/silero-vad/v5.1.2/src/silero_vad/data/silero_vad.onnx
# For a manual check only; the adapter does not verify it.
shasum -a 256 silero_vad.onnx   # 2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f on 2026-11-12
```

The Silero licence is MIT per the research notes; it was not re-read on the
repository's LICENSE file (unverified).

## Results (2026-11-12, MacBook Air M5, 16 GB, macOS 27.2)

The machine was under heavy memory pressure during the runs (about 30 GB of
swap in use), so these numbers are a floor, not a best case.

| Part | Tool | Result |
| --- | --- | --- |
| Speech-to-text | whisper.cpp 1.8.6, `base.en` | 0.30 s for a 7.8 s clip (warm), transcript correct |
| Speech-to-text | whisper.cpp 1.8.6, `large-v3-turbo` q5 | 1.02 s for the same clip, transcript correct |
| Language model | Ollama 0.32.5, `qwen3.5:9b`, thinking off | Median 0.54 to 0.70 s to first token, 17 to 19 tokens/s, 5.7 GB loaded, 100% GPU |
| Tool calls | same model, 3 tools, 8 prompts, streaming and not | 6 of 16 with a plain system prompt; 16 of 16 after adding a tool rule |
| Text-to-speech | kokoro-onnx 0.4.7, int8 model | 7.8 s of speech in 1.2 s (real-time factor 0.16), delivered as one chunk |
| Text-to-speech | macOS `say`, 24 kHz PCM16 | 0.64 s for a 3.2 s sentence (warm) |
| Whole pipeline | `LocalVoiceAdapter` in `apps/api`, `base.en` + `qwen3.5:9b` + `say` | 2.0 to 2.2 s from the last audio frame to the first reply audio (warm), plus 0.7 s of end-of-speech silence |

Only one clean synthetic clip was used for speech-to-text. Accuracy on a real
voice, an accent, or a noisy room was not measured.

## Second pass (2026-11-12, evening)

After the operator rated the first cut 66 out of 100, the adapter gained
Silero speech detection (0.11 ms per 32 ms window on this Mac), Kokoro as the
default voice, a model warm-up at session start, a calculator tool, and the
date and time in the prompt. Four spoken test questions through the real
pipeline (synthetic clips):

| Question | Result | End of audio to first reply audio |
| --- | --- | --- |
| A tip to stay focused | Sensible advice | 3.0 s |
| Seventeen times twenty three | 391, by the calculator | 3.3 s |
| What day and time is it | Correct day, date, and time | 2.9 s |
| Send an email to my manager | Declined, said what it can do | 2.3 s |

Transcription finished 0.4 s after the last frame in each case. The rest is
the model writing its first sentence and Kokoro rendering it. This is slower
than the first cut with `say` (2.0 to 2.2 s): the natural voice costs about
half a second to a second per first sentence. End-of-speech silence is now
0.5 s, down from 0.7 s.

## What we learned

- Asked the time with a clock tool available, the model called the tool and
  then kept writing an invented time in the same response. Asked the day, it
  skipped the tool and invented one. Stating the date and time in the prompt
  fixed both, and the adapter now stops reading a response at its first tool
  call.

- With a plain system prompt the model answered "I've set a reminder" and
  called no tool. An assistant that claims actions it did not take is the
  failure to guard against. A one-sentence tool rule fixed all 16 cases.
- `urllib` routes even `127.0.0.1` through `http_proxy` and the macOS system
  proxy. A local-only client must build an opener with no proxy handler.
- The delay is mostly the first sentence: the model writes it (1.0 to 1.7 s),
  then the voice renders it (about 1 s). Asking for a short opening sentence
  cut about a second.
- `kokoro-onnx` pulls in `phonemizer-fork` (GPL-3.0) and, on 2026-11-12,
  resolved three packages newer than the 14-day rule (`csvw`, `regex`,
  `python-dateutil`). It is not in the lock file. macOS `say` needs no
  dependency and is the default voice.

## Not done

- No denied-egress test (the PH-07 gate asks for one).
- No microphone test by a person.
- No Windows path: `say` and the Metal build of whisper.cpp are macOS only.
- No comparison with the 4B model, Granite, Moonshine, or Parakeet.
- No end-of-turn model (Smart Turn) and no speculative generation yet.

# R-01.4 local microphone test: steps for the operator

| Field | Value |
| --- | --- |
| Roadmap item | R-01.4 `[human]`, local microphone test (start, mute, conversational barge-in, stop) on the revised scaffold, no audio leaves the machine |
| Tester | `jeevesh2515`, on the Mac |
| Adapter under test | The offline fake adapter. It echoes your own voice back. Gemini is not involved. |
| Status | Run on 2026-11-12; result in the [approval record](../approvals/r01-4-microphone-test.md). This file is instructions only and is not evidence. |

The tick needs a record under `docs/approvals/` that says who tested, when,
on which commit, and what was observed. The record is written from your
answers to the form at the end. Nothing here is a PASS until you report one.

## Before you start

- Use **headphones**. The fake adapter plays your voice straight back, so
  speakers will feed back into the microphone and make the barge-in
  observation meaningless.
- Turn the volume down first; the echo is loud.
- Close other tabs or apps that use the microphone.
- Do not export `GEMINI_API_KEY` in the terminal that runs the backend. The
  scaffold never reads it, and its absence is part of the evidence.

## Start the backend (terminal 1)

```bash
cd ~/dev/super-agent
git switch feat/ph-01-gemini-live && git pull
git rev-parse --short HEAD                      # write this down
python3 -m venv /tmp/sa-venv
/tmp/sa-venv/bin/python -m pip install --only-binary=:all: -r apps/api/requirements.lock
PYTHONPATH=apps/api/src /tmp/sa-venv/bin/python -m super_agent_voice.generate_token
env | grep -c GEMINI                            # expect 0
PYTHONPATH=apps/api/src /tmp/sa-venv/bin/python -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4
```

`generate_token` writes `~/.super-agent/voice-token` with mode 0600 and prints
only the path.

## Start the console (terminal 2)

```bash
cd ~/dev/super-agent
npm ci --ignore-scripts --prefix apps/web
npm start --prefix apps/web
```

Open <http://127.0.0.1:4200> in your browser. Copy the token with
`pbcopy < ~/.super-agent/voice-token`, paste it into the token field, and
clear the clipboard afterwards with `pbcopy < /dev/null`. Select **Start**
and allow the microphone when the browser asks.

## What to do and what to expect

Take about ten minutes. Write down what you actually see and hear, including
anything unexpected.

| # | Do this | Expected | Why |
| --- | --- | --- | --- |
| 1 | Press Start, allow the microphone | Status goes from `connecting` to `listening` | Auth and ready handshake |
| 2 | Stay silent for 10 seconds | Status stays `listening` and never shows `speaking`. The level meter stays near zero. | R-01.F1: silent frames must not look like model speech |
| 3 | Say a short sentence | The meter moves while you talk. You hear your own voice come back. Status shows `speaking` only while that playback is audible, then returns to `listening` within about a second. | Level and speech states are separate |
| 4 | Press Mute, talk for 5 seconds | No echo. Meter stays flat. Press Unmute and talk again: echo and meter return. | Mute stops upload and clears level |
| 5 | Without touching any button, talk continuously for about 10 seconds | Say whether the echo plays smoothly or in cut-up bursts, and whether the page ever shows an error. Bursts or gaps mean automatic interruption fired. | Conversational barge-in is the path under test, not the button |
| 6 | While your voice is echoing, press **Stop playback** | The playback cuts. The session stays up and no error appears. | Manual control is secondary |
| 7 | Press Stop | Status becomes `stopped`. The browser's microphone indicator goes away within a few seconds. | Cleanup |
| 8 | Press Start again and talk once | A fresh session works as in step 3. | Restart |
| 9 | Close the tab. In terminal 1, press Ctrl+C | No traceback other than the normal shutdown | Disconnect and shutdown |

Step 5 is the weakest observation: the fake adapter echoes immediately, so
your speech overlaps its playback by design. If you cannot tell whether
barge-in fired, answer "unsure". That is an honest result, and it means the
question is settled by the live Gemini session in R-01.9 and not by this test.

## Answer these in chat

1. Commit hash from terminal 1, macOS version, browser and version, and the
   microphone device (built-in or headphones).
2. For each of steps 1 to 9: pass, fail, or unsure, plus one line of what you
   saw.
3. Any error text shown on the page or printed in terminal 1. Do not paste the
   token.
4. Confirm that `env | grep -c GEMINI` printed `0` and that you did not set a
   provider key for this run.

If anything fails, I add a fix item under PH-01 (`R-01.Fn`), fix it, and ask
you to repeat only the failed steps. I cannot run this test for you: it needs
a person, a microphone, and ears.

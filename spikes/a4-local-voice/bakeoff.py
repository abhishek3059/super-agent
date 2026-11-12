"""Spike A4: measure a fully local voice stack on this machine.

Throwaway. Synthetic text and audio only: no microphone, no personal data,
no network beyond the loopback Ollama server.

Usage: python bakeoff.py [llm|tts|stt|all] (default all)
Env: SA_LLM (default qwen3.5:9b), SA_MODELS (default ~/.super-agent/models)
"""
import asyncio
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434"
LLM = os.environ.get("SA_LLM", "qwen3.5:9b")
MODELS = Path(os.environ.get("SA_MODELS", Path.home() / ".super-agent" / "models"))
# Without the tool rule the model claimed "I've set a reminder" and called nothing.
SYSTEM = ("You are a concise voice assistant. Answer in one or two short spoken sentences. "
          "When the user asks for an action or for live information that a tool provides, call "
          "that tool. Never say an action was done unless you called the tool for it.")
QUESTIONS = [
    "What is a good way to plan my morning?",
    "Explain what a WebSocket is.",
    "Give me one tip to stay focused while coding.",
]
TOOLS = [
    {"type": "function", "function": {
        "name": "get_agent_jobs", "description": "List the user's background agent jobs and their status.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "set_reminder", "description": "Create a reminder.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"}, "minutes_from_now": {"type": "integer"}},
            "required": ["text", "minutes_from_now"]}}},
    {"type": "function", "function": {
        "name": "cancel_job", "description": "Cancel one background job by its name.",
        "parameters": {"type": "object", "properties": {"job_name": {"type": "string"}},
                       "required": ["job_name"]}}},
]
# (prompt, expected tool name or None, required argument names)
TOOL_CASES = [
    ("What are my agent jobs doing right now?", "get_agent_jobs", []),
    ("Remind me to stretch in 20 minutes.", "set_reminder", ["text", "minutes_from_now"]),
    ("Cancel the job called nightly-report.", "cancel_job", ["job_name"]),
    ("Any jobs waiting for my approval?", "get_agent_jobs", []),
    ("Set a reminder to call the bank in 45 minutes.", "set_reminder", ["text", "minutes_from_now"]),
    ("Stop the docs-build job.", "cancel_job", ["job_name"]),
    ("What is two plus two?", None, []),
    ("Tell me a short joke.", None, []),
]


def chat(messages, *, stream, tools=None):
    body = {"model": LLM, "messages": messages, "stream": stream, "think": False,
            "options": {"num_ctx": 8192, "temperature": 0}}
    if tools:
        body["tools"] = tools
    request = urllib.request.Request(
        f"{OLLAMA}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    # No proxy: the default opener would route even loopback through http_proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=300)


def bench_llm():
    chat([{"role": "user", "content": "hi"}], stream=False).read()  # load the model
    first_token, first_sentence, rates = [], [], []
    for question in QUESTIONS:
        start = time.perf_counter()
        text, ttft, sentence_at, final = "", None, None, {}
        for line in chat([{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": question}], stream=True):
            part = json.loads(line)
            piece = part.get("message", {}).get("content", "")
            if piece and ttft is None:
                ttft = time.perf_counter() - start
            text += piece
            if sentence_at is None and any(mark in text for mark in ".!?"):
                sentence_at = time.perf_counter() - start
            if part.get("done"):
                final = part
        first_token.append(ttft)
        first_sentence.append(sentence_at)
        rates.append(final["eval_count"] / (final["eval_duration"] / 1e9))
        print(f"  q={question!r} ttft={ttft:.2f}s first_sentence={sentence_at:.2f}s "
              f"tok/s={rates[-1]:.1f} reply={text.strip()[:90]!r}")
    print(f"llm median: ttft={statistics.median(first_token):.2f}s "
          f"first_sentence={statistics.median(first_sentence):.2f}s "
          f"tok/s={statistics.median(rates):.1f}")

    passed = 0
    for streaming in (False, True):
        for prompt, expected, required in TOOL_CASES:
            calls = []
            response = chat([{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}], stream=streaming, tools=TOOLS)
            lines = response if streaming else [response.read()]
            for line in lines:
                calls += json.loads(line).get("message", {}).get("tool_calls") or []
            name = calls[0]["function"]["name"] if calls else None
            arguments = calls[0]["function"].get("arguments", {}) if calls else {}
            ok = name == expected and len(calls) <= 1 and all(key in arguments for key in required)
            passed += ok
            print(f"  tools stream={streaming} {'PASS' if ok else 'FAIL'} {prompt!r} -> {name} {arguments}")
    print(f"tool calls: {passed}/{2 * len(TOOL_CASES)} passed")
    print(subprocess.run(["ollama", "ps"], capture_output=True, text=True,
                         env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434"}).stdout)


SPEECH = ("Good morning. You have two agent jobs running, and one is waiting for your approval. "
          "Would you like me to read out the details?")


async def bench_tts(out_path):
    import numpy
    from kokoro_onnx import Kokoro
    start = time.perf_counter()
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.int8.onnx"), str(MODELS / "voices-v1.0.bin"))
    print(f"tts load: {time.perf_counter() - start:.2f}s")
    for run in range(3):
        start = time.perf_counter()
        first, chunks, rate = None, [], 24000
        async for samples, rate in kokoro.create_stream(SPEECH, voice="am_michael", speed=1.0, lang="en-us"):
            if first is None:
                first = time.perf_counter() - start
            chunks.append(samples)
        total = time.perf_counter() - start
        audio = numpy.concatenate(chunks)
        print(f"  tts run {run}: first_chunk={first:.2f}s total={total:.2f}s "
              f"audio={len(audio) / rate:.1f}s rtf={total / (len(audio) / rate):.2f}")
    # 16 kHz mono PCM16 by plain decimation is wrong for 24 kHz; resample by interpolation.
    target = numpy.interp(numpy.arange(0, len(audio), rate / 16000), numpy.arange(len(audio)), audio)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes((numpy.clip(target, -1, 1) * 32767).astype("<i2").tobytes())


def bench_stt(wav_path):
    for model in ("ggml-base.en.bin", "ggml-large-v3-turbo-q5_0.bin"):
        for run in range(2):  # the first run includes model load and Metal warm-up
            start = time.perf_counter()
            result = subprocess.run(
                ["whisper-cli", "-m", str(MODELS / model), "-f", str(wav_path), "-nt", "-np", "-l", "en"],
                capture_output=True, text=True)
            print(f"  stt {model} run {run}: {time.perf_counter() - start:.2f}s "
                  f"text={result.stdout.strip()[:110]!r}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    wav = Path(tempfile.gettempdir()) / "sa-a4-speech.wav"
    if what in ("llm", "all"):
        bench_llm()
    if what in ("tts", "all"):
        asyncio.run(bench_tts(wav))
    if what in ("stt", "all"):
        assert wav.exists(), "run tts first: stt transcribes the synthesized speech"
        bench_stt(wav)

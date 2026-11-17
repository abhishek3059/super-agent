from __future__ import annotations

import asyncio
import base64
import hmac
import json
import secrets
import struct
from copy import deepcopy
from threading import Event

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig

from super_agent_voice.openai_realtime import OpenAIRealtimeAdapter, Pcm16kTo24k

TOKEN = "scripted-call-fixture-token-0123456789"
ORIGIN = "http://127.0.0.1:4200"
PCM = bytes(range(64)) * 6
CAPTURE_PCM = struct.pack("<5h", 0, 300, 600, 900, 1200)
UPLINK_PCM = struct.pack("<7h", 0, 200, 400, 600, 800, 1000, 1200)
BURST_FRAME_BYTES = 8192
BURST = [bytes([index]) * BURST_FRAME_BYTES for index in range(1, 19)]
READY = {"type": "session.ready", "provider": "openai-realtime", "playbackEpoch": 0, "outputRateHz": 24000}
SESSION = {
    "type": "realtime", "output_modalities": ["audio"], "tools": [], "tool_choice": "none",
    "audio": {
        "input": {"format": {"type": "audio/pcm", "rate": 24000}, "turn_detection": {
            "type": "server_vad", "create_response": True, "interrupt_response": True,
        }},
        "output": {"format": {"type": "audio/pcm", "rate": 24000}},
    },
}


class ScriptedTransport:
    def __init__(self, scenario="normal") -> None:
        self.incoming: asyncio.Queue[str] = asyncio.Queue()
        self.scenario = scenario
        self.commands: list[str] = []
        self.inputs: list[bytes] = []
        self.cancelled: list[str] = []
        self.committed_seen = Event()
        self.cancel_seen = Event()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.closed = False

    def emit(self, kind, **fields) -> None:
        self.incoming.put_nowait(json.dumps({"type": kind, **fields}))

    def delta(self, identifier, content=PCM) -> None:
        self.emit("response.output_audio.delta", response_id=identifier, delta=base64.b64encode(content).decode("ascii"))

    async def send(self, text: str) -> None:
        message = json.loads(text)
        kind = message["type"]
        self.commands.append(kind)
        if kind == "session.update":
            self.loop = asyncio.get_running_loop()
            assert message == {"type": "session.update", "session": SESSION}
            if self.scenario == "startup-timeout":
                return
            if self.scenario == "limit":
                self.emit("error", error={"code": "insufficient_quota", "message": "Private provider detail"})
                return
            if self.scenario == "unsupported":
                self.emit("error", error={"code": "model_not_found"})
                return
            session = deepcopy(SESSION)
            if self.scenario == "unexpected-tools":
                session["tools"] = [{"name": "greatly_exceeds_authority"}]
            if self.scenario == "vad-disabled":
                session["audio"]["input"]["turn_detection"]["interrupt_response"] = False
            self.emit("session.created")
            self.emit("session.updated", session=session)
        elif kind == "input_audio_buffer.append":
            self.inputs.append(base64.b64decode(message["audio"], validate=True))
            identifier = f"response_{len(self.inputs)}"
            if self.scenario == "pending" and len(self.inputs) == 1:
                self.emit("input_audio_buffer.committed")
                return
            if self.scenario == "captions":
                self.emit("input_audio_buffer.committed", item_id="current-input")
                self.emit("conversation.item.input_audio_transcription.completed", item_id="stale-input", transcript="stale")
                self.emit("conversation.item.input_audio_transcription.completed", item_id="current-input", transcript="What is two plus two?")
                self.emit("conversation.item.input_audio_transcription.completed", item_id="current-input", transcript="duplicate")
            self.emit("response.created", response={"id": identifier})
            if self.scenario == "bad-audio":
                self.emit("response.output_audio.delta", response_id=identifier, delta="malformed!")
            elif self.scenario == "vad":
                self.emit("input_audio_buffer.speech_started")
                self.delta(identifier)
                self.emit("response.done", response={"id": identifier, "status": "cancelled"})
                self.emit("response.created", response={"id": "next"})
                self.delta("next")
                self.emit("response.done", response={"id": "next", "status": "completed"})
            elif self.scenario == "burst":
                self.delta(identifier, b"".join(BURST))
                self.emit("response.done", response={"id": identifier, "status": "completed"})
            elif self.scenario == "captions":
                self.emit("response.output_audio_transcript.done", response_id="stale-response", transcript="stale")
                self.delta(identifier)
                self.emit("response.output_audio_transcript.done", response_id=identifier, transcript="Four. " * 100)
                self.emit("response.done", response={"id": identifier, "status": "completed"})
            else:
                self.delta(identifier)
                if len(self.inputs) == 2:
                    self.emit("response.done", response={"id": identifier, "status": "completed"})
        elif kind == "response.cancel":
            identifier = message["response_id"]
            self.cancelled.append(identifier)
            self.delta(identifier)  # old audio still in flight when the operator pressed Stop
            self.emit("response.output_audio_transcript.done", response_id=identifier, transcript="cancelled reply")
            status = "completed" if self.scenario == "cancel-race" else "cancelled"
            self.emit("response.done", response={"id": identifier, "status": status})
            if status == "completed":
                self.emit("error", error={"event_id": message["event_id"], "code": "response_cancel_not_active"})
            self.cancel_seen.set()

    async def recv(self) -> str:
        event = await self.incoming.get()
        if json.loads(event)["type"] == "input_audio_buffer.committed":
            self.committed_seen.set()
        return event

    async def close(self) -> None:
        self.closed = True


def make_client(transport, frame_bytes=32 * 1024):
    cfg = VoiceConfig(local_token=TOKEN, max_session_seconds=3, max_audio_frame_bytes=frame_bytes)
    return TestClient(create_app(cfg, lambda: OpenAIRealtimeAdapter(transport, frame_bytes)), base_url=ORIGIN)


def connect(client):
    return client.websocket_connect("/ws/voice", headers={"host": "127.0.0.1:8000", "origin": ORIGIN})


def auth(socket, token=TOKEN):
    nonce = secrets.token_hex(32)
    socket.send_json({"type": "session.hello", "clientNonce": nonce})
    challenge = socket.receive_json()
    transcript = f"{nonce}/{challenge['serverNonce']}"
    proof = hmac.digest(token.encode(), f"super-agent.voice.v1/client/{transcript}".encode(), "sha256")
    socket.send_json({"type": "session.auth", "proof": proof.hex()})


def read_audio(socket, epoch, pcm=PCM):
    assert socket.receive_json() == {
        "type": "audio.chunk", "playbackEpoch": epoch, "rateHz": 24000, "channels": 1, "format": "pcm16",
    }
    assert socket.receive_bytes() == pcm


def stop(socket):
    socket.send_json({"type": "session.stop"})
    assert socket.receive_json() == {"type": "session.state", "state": "stopping"}
    with pytest.raises(WebSocketDisconnect) as exc:
        socket.receive_json()
    assert exc.value.code == 1000


def test_real_bridge_call_with_mute_stop_and_next_reply():
    transport = ScriptedTransport()
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        read_audio(socket, 0)

        socket.send_json({"type": "playback.interrupt"})
        assert socket.receive_json() == {"type": "playback.interrupted", "source": "local", "playbackEpoch": 1}
        socket.send_json({"type": "capture.mute"})
        assert socket.receive_json() == {"type": "session.state", "muted": True}
        socket.send_bytes(b"\xff\x7f" * 8)
        socket.send_json({"type": "capture.unmute"})
        assert socket.receive_json() == {"type": "session.state", "muted": False}

        socket.send_bytes(CAPTURE_PCM)
        read_audio(socket, 1)
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}
        stop(socket)
    assert transport.commands == [
        "session.update", "input_audio_buffer.append", "response.cancel", "input_audio_buffer.clear", "input_audio_buffer.append",
    ]
    assert transport.inputs == [UPLINK_PCM, UPLINK_PCM]
    assert transport.cancelled == ["response_1"]
    assert transport.closed


def test_resampling_is_identical_across_odd_capture_frame_boundaries():
    pcm = struct.pack("<5h", -300, 0, 300, 600, 300)
    expected = struct.pack("<7h", -300, -100, 100, 300, 500, 500, 300)
    resampler = Pcm16kTo24k()
    assert b"".join(resampler.convert(frame) for frame in (pcm[:2], pcm[2:6], pcm[6:])) == expected
    assert Pcm16kTo24k().convert(pcm) == expected


def test_provider_burst_keeps_more_frames_than_the_bridge_queue():
    transport = ScriptedTransport("burst")
    with make_client(transport, BURST_FRAME_BYTES) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        for frame in BURST:
            read_audio(socket, 0, frame)
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 0}
        stop(socket)


def test_transient_captions_match_the_committed_input_and_active_response():
    transport = ScriptedTransport("captions")
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        assert socket.receive_json() == {"type": "conversation.text", "role": "user", "text": "What is two plus two?"}
        read_audio(socket, 0)
        assert socket.receive_json() == {"type": "conversation.text", "role": "assistant", "text": ("Four. " * 100)[:500]}
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 0}
        stop(socket)


def test_provider_speech_start_clears_the_old_response():
    transport = ScriptedTransport("vad")
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        assert socket.receive_json() == {"type": "playback.interrupted", "source": "provider", "playbackEpoch": 1}
        read_audio(socket, 1)
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}
        stop(socket)
    assert transport.cancelled == []
    assert transport.closed


def test_stop_fences_a_committed_utterance_while_the_response_id_is_pending():
    transport = ScriptedTransport("pending")
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        assert transport.committed_seen.wait(1)
        socket.send_json({"type": "playback.interrupt"})
        assert socket.receive_json() == {"type": "playback.interrupted", "source": "local", "playbackEpoch": 1}

        assert transport.loop is not None
        transport.loop.call_soon_threadsafe(lambda: transport.emit("response.created", response={"id": "response_1"}))
        assert transport.cancel_seen.wait(1)
        socket.send_bytes(CAPTURE_PCM)
        read_audio(socket, 1)
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}
        stop(socket)
    assert transport.cancelled == ["response_1"]


def test_a_cancel_error_after_the_matching_terminal_event_keeps_the_call_open():
    transport = ScriptedTransport("cancel-race")
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        read_audio(socket, 0)
        socket.send_json({"type": "playback.interrupt"})
        assert socket.receive_json() == {"type": "playback.interrupted", "source": "local", "playbackEpoch": 1}
        socket.send_bytes(CAPTURE_PCM)
        read_audio(socket, 1)
        assert socket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}
        stop(socket)
    assert transport.closed


@pytest.mark.parametrize(("scenario", "category"), [
    ("limit", "provider-limits"), ("unsupported", "provider-unsupported"), ("unexpected-tools", "provider-unsupported"),
    ("vad-disabled", "provider-unsupported"), ("startup-timeout", "provider-unavailable"),
])
def test_startup_refuses_unusable_session_without_capture(scenario, category, monkeypatch):
    monkeypatch.setattr("super_agent_voice.openai_realtime.SESSION_UPDATE_TIMEOUT_SECONDS", 0.05)
    transport = ScriptedTransport(scenario)
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == {"type": "session.error", "category": category}
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    assert transport.commands == ["session.update"]
    assert transport.inputs == []
    assert transport.closed


def test_bad_provider_pcm_closes_without_playback():
    transport = ScriptedTransport("bad-audio")
    with make_client(transport) as client, connect(client) as socket:
        auth(socket)
        assert socket.receive_json() == READY
        socket.send_bytes(CAPTURE_PCM)
        assert socket.receive_json() == {"type": "session.error", "category": "session-failed"}
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    assert transport.closed


def test_bad_local_token_never_configures_provider():
    transport = ScriptedTransport()
    with make_client(transport) as client, connect(client) as socket:
        auth(socket, "invalid")
        with pytest.raises(WebSocketDisconnect) as exc:
            socket.receive_json()
        assert exc.value.code == 1008
    assert transport.commands == []

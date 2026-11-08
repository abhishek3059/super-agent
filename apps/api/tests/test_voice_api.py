from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from super_agent_voice.adapter import FakeVoiceAdapter
from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig

TOKEN = "t" * 32
ORIGIN = "http://127.0.0.1:4200"


def make_client(adapter: FakeVoiceAdapter | None = None) -> TestClient:
    app = create_app(
        VoiceConfig(local_token=TOKEN),
        (lambda: adapter) if adapter else FakeVoiceAdapter,
    )
    return TestClient(app, base_url=ORIGIN)


def connect(client: TestClient):
    return client.websocket_connect(
        "/ws/voice",
        headers={"host": "127.0.0.1:8000", "origin": ORIGIN},
    )


def authenticate(websocket) -> None:
    websocket.send_json({"type": "session.auth", "token": TOKEN})
    assert websocket.receive_json() == {
        "type": "session.ready",
        "playbackEpoch": 0,
    }


def test_health_is_key_free() -> None:
    with make_client() as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "provider": "fake",
        }


def test_environment_requires_high_entropy_local_token(monkeypatch) -> None:
    monkeypatch.delenv("SUPER_AGENT_LOCAL_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        VoiceConfig.from_environment()
    monkeypatch.setenv("SUPER_AGENT_LOCAL_TOKEN", "short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        VoiceConfig.from_environment()


def test_rejects_bad_origin_and_token() -> None:
    with make_client() as client:
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect(
                "/ws/voice",
                headers={
                    "host": "127.0.0.1:8000",
                    "origin": "https://evil.example",
                },
            ):
                pass
        assert denied.value.code == 1008

        with pytest.raises(WebSocketDisconnect) as bad_host:
            with client.websocket_connect(
                "/ws/voice",
                headers={"host": "evil.example", "origin": ORIGIN},
            ):
                pass
        assert bad_host.value.code == 1008

        with connect(client) as websocket:
            websocket.send_json({"type": "session.auth", "token": "wrong"})
            with pytest.raises(WebSocketDisconnect) as bad_token:
                websocket.receive_json()
            assert bad_token.value.code == 1008


def test_fake_audio_interrupt_and_stop() -> None:
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        sample = b"\x01\x00\x02\x00"
        websocket.send_bytes(sample)
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 0,
        }
        assert websocket.receive_bytes() == sample
        assert websocket.receive_json() == {
            "type": "turn.complete",
            "playbackEpoch": 0,
        }

        websocket.send_json({"type": "playback.interrupt"})
        assert websocket.receive_json() == {
            "type": "playback.interrupted",
            "playbackEpoch": 1,
        }
        assert adapter.interruptions == 1

        websocket.send_json({"type": "session.stop"})
        assert websocket.receive_json() == {
            "type": "session.state",
            "state": "stopping",
        }
    assert adapter.closed


def test_muted_audio_is_not_sent_to_adapter() -> None:
    adapter = FakeVoiceAdapter()
    calls = 0
    original = adapter.send_audio

    async def counted(audio: bytes):
        nonlocal calls
        calls += 1
        return await original(audio)

    adapter.send_audio = counted  # type: ignore[method-assign]
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_json({"type": "capture.mute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": True}
        websocket.send_bytes(b"\x00\x00")
        assert calls == 0
        websocket.send_json({"type": "capture.unmute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": False}
        websocket.send_bytes(b"\x00\x00")
        assert websocket.receive_json()["type"] == "audio.chunk"
        assert calls == 1


def test_invalid_control_and_oversized_audio_fail_closed() -> None:
    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_text('{"type":"unknown"}')
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "invalid-control",
        }

    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"x" * (32 * 1024 + 1))
        with pytest.raises(WebSocketDisconnect) as oversized:
            websocket.receive_json()
        assert oversized.value.code == 1009


def test_adapter_error_is_redacted() -> None:
    class BrokenAdapter(FakeVoiceAdapter):
        async def send_audio(self, audio: bytes):
            raise RuntimeError("SENTINEL provider detail")

    adapter = BrokenAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"\x00\x00")
        response = websocket.receive_json()
        assert response == {"type": "session.error", "category": "session-failed"}
        assert "SENTINEL" not in str(response)
    assert adapter.closed

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from super_agent_voice.adapter import (
    AdapterError,
    AudioChunk,
    FakeVoiceAdapter,
    Interrupted,
    TurnComplete,
)
from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig

TOKEN = "t" * 32
ORIGIN = "http://127.0.0.1:4200"
READY = {"type": "session.ready", "playbackEpoch": 0, "outputRateHz": 16000, "provider": "fake"}


def make_client(
    adapter: FakeVoiceAdapter | None = None,
    config: VoiceConfig | None = None,
) -> TestClient:
    app = create_app(
        config if config is not None else VoiceConfig(local_token=TOKEN),
        (lambda: adapter) if adapter else FakeVoiceAdapter,
    )
    return TestClient(app, base_url=ORIGIN)


def connect(client: TestClient):
    return client.websocket_connect(
        "/ws/voice",
        headers={"host": "127.0.0.1:8000", "origin": ORIGIN},
    )


def authenticate(websocket, ready: dict | None = None) -> None:
    websocket.send_json({"type": "session.auth", "token": TOKEN})
    assert websocket.receive_json() == (ready or READY)


def chunk(epoch: int = 0, rate: int = 16000) -> dict:
    return {"type": "audio.chunk", "playbackEpoch": epoch, "rateHz": rate, "channels": 1, "format": "pcm16"}


def test_health_is_key_free() -> None:
    with make_client() as client:
        # The in-process client host differs from the loopback server host, so
        # the allowed Host value is passed explicitly, as a real browser would.
        assert client.get("/health", headers={"host": "127.0.0.1:8000"}).json() == {
            "status": "ok",
            "provider": "fake",
        }


def test_health_rejects_foreign_host() -> None:
    with make_client() as client:
        assert client.get("/health", headers={"host": "evil.example"}).status_code == 403
        assert client.get("/health", headers={"host": "127.0.0.1:8000"}).status_code == 200


def test_only_one_active_session_is_allowed() -> None:
    with make_client() as client:
        with connect(client) as first:
            authenticate(first)
            # A second authenticated client is refused with 1013 while one is active.
            with connect(client) as second:
                second.send_json({"type": "session.auth", "token": TOKEN})
                with pytest.raises(WebSocketDisconnect) as rejected:
                    second.receive_json()
                assert rejected.value.code == 1013
        # The slot is released once the active session ends.
        with connect(client) as third:
            authenticate(third)


def test_unauthenticated_client_cannot_hold_the_session_slot() -> None:
    # Review CR-06: authentication happens before the slot is taken.
    with make_client() as client, connect(client) as idle, connect(client) as real:
        authenticate(real)
        idle.send_json({"type": "session.auth", "token": "wrong"})
        with pytest.raises(WebSocketDisconnect) as denied:
            idle.receive_json()
        assert denied.value.code == 1008


def test_total_session_budget_expires_with_fixed_error() -> None:
    settings = VoiceConfig(local_token=TOKEN, max_session_seconds=0.3)
    with make_client(config=settings) as client, connect(client) as websocket:
        authenticate(websocket)
        started = time.monotonic()
        assert websocket.receive_json() == {"type": "session.error", "category": "max-duration"}
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 1000
        assert time.monotonic() - started < 5


def test_idle_timeout_is_retained() -> None:
    settings = VoiceConfig(local_token=TOKEN, idle_timeout_seconds=0.2)
    with make_client(config=settings) as client, connect(client) as websocket:
        authenticate(websocket)
        started = time.monotonic()
        assert websocket.receive_json() == {"type": "session.error", "category": "session-timeout"}
        assert time.monotonic() - started < 5


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
                headers={"host": "127.0.0.1:8000", "origin": "https://evil.example"},
            ):
                pass
        assert denied.value.code == 1008

        with pytest.raises(WebSocketDisconnect) as bad_host:
            with client.websocket_connect("/ws/voice", headers={"host": "evil.example", "origin": ORIGIN}):
                pass
        assert bad_host.value.code == 1008

        for wrong in ("wrong", "é" * 32, 12345):
            with connect(client) as websocket:
                websocket.send_json({"type": "session.auth", "token": wrong})
                with pytest.raises(WebSocketDisconnect) as bad_token:
                    websocket.receive_json()
                assert bad_token.value.code == 1008


def test_fake_audio_interrupt_and_stop() -> None:
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        sample = b"\x01\x00\x02\x00"
        websocket.send_bytes(sample)
        assert websocket.receive_json() == chunk()
        assert websocket.receive_bytes() == sample
        assert websocket.receive_json() == {"type": "turn.complete", "playbackEpoch": 0}

        websocket.send_json({"type": "playback.interrupt"})
        assert websocket.receive_json() == {"type": "playback.interrupted", "playbackEpoch": 1, "source": "local"}
        assert adapter.interruptions == 1

        websocket.send_json({"type": "session.stop"})
        assert websocket.receive_json() == {"type": "session.state", "state": "stopping"}
    assert adapter.closed


def test_muted_audio_is_not_sent_to_adapter_and_mute_ends_stream() -> None:
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_json({"type": "capture.mute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": True}
        assert adapter.stream_ends == 1
        websocket.send_bytes(b"\x00\x00")
        websocket.send_json({"type": "capture.unmute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": False}
        websocket.send_bytes(b"\x00\x00")
        assert websocket.receive_json()["type"] == "audio.chunk"
        assert adapter.received == [b"\x00\x00"]


def test_invalid_control_odd_and_oversized_audio_fail_closed() -> None:
    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_text('{"type":"unknown"}')
        assert websocket.receive_json() == {"type": "session.error", "category": "invalid-control"}

    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"\x00\x00\x00")
        assert websocket.receive_json() == {"type": "session.error", "category": "invalid-audio"}

    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"x" * (32 * 1024 + 2))
        with pytest.raises(WebSocketDisconnect) as oversized:
            websocket.receive_json()
        assert oversized.value.code == 1009


def test_adapter_error_is_redacted() -> None:
    adapter = FakeVoiceAdapter(script=[RuntimeError("SENTINEL provider detail")])
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        response = websocket.receive_json()
        assert response == {"type": "session.error", "category": "session-failed"}
        assert "SENTINEL" not in str(response)
    assert adapter.closed


def test_provider_start_failure_sends_fixed_error_and_no_ready() -> None:
    adapter = FakeVoiceAdapter(start_error="provider-unavailable")
    with make_client(adapter) as client, connect(client) as websocket:
        websocket.send_json({"type": "session.auth", "token": TOKEN})
        assert websocket.receive_json() == {"type": "session.error", "category": "provider-unavailable"}
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
    assert adapter.closed


def test_scripted_stream_order_rate_and_provider_interrupt() -> None:
    adapter = FakeVoiceAdapter(
        script=[
            AudioChunk(b"\x01\x00", 24000),
            Interrupted(),
            AudioChunk(b"\x02\x00", 24000),
            TurnComplete(),
            AdapterError("provider-limits"),
        ]
    )
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        assert websocket.receive_json() == chunk(0, 24000)
        assert websocket.receive_bytes() == b"\x01\x00"
        # A provider interruption bumps the backend-owned epoch.
        assert websocket.receive_json() == {"type": "playback.interrupted", "playbackEpoch": 1, "source": "provider"}
        assert websocket.receive_json() == chunk(1, 24000)
        assert websocket.receive_bytes() == b"\x02\x00"
        assert websocket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}
        assert websocket.receive_json() == {"type": "session.error", "category": "provider-limits"}


def test_adapter_error_category_is_restricted() -> None:
    assert AdapterError("not-a-category").category == "session-failed"
    assert AdapterError("provider-unavailable").category == "provider-unavailable"


def test_provider_start_timeout_frees_the_slot() -> None:
    settings = VoiceConfig(local_token=TOKEN, provider_start_timeout_seconds=0.1)
    with make_client(FakeVoiceAdapter(start_delay=5), config=settings) as client:
        with connect(client) as websocket:
            websocket.send_json({"type": "session.auth", "token": TOKEN})
            assert websocket.receive_json() == {"type": "session.error", "category": "provider-unavailable"}
    with make_client(config=settings) as client, connect(client) as websocket:
        authenticate(websocket)


def test_missing_provider_key_reports_provider_unavailable() -> None:
    def no_key():
        raise AdapterError("provider-unsupported")

    no_key.name = "gemini-live"  # type: ignore[attr-defined]
    app = create_app(VoiceConfig(local_token=TOKEN), no_key)
    with TestClient(app, base_url=ORIGIN) as client, connect(client) as websocket:
        websocket.send_json({"type": "session.auth", "token": TOKEN})
        assert websocket.receive_json() == {"type": "session.error", "category": "provider-unavailable"}


def test_binary_first_frame_is_a_failed_auth() -> None:
    with make_client() as client, connect(client) as websocket:
        websocket.send_bytes(b"\x00\x00")
        with pytest.raises(WebSocketDisconnect) as denied:
            websocket.receive_json()
        assert denied.value.code == 1008


def test_local_interrupt_is_announced_before_newer_audio() -> None:
    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_json({"type": "playback.interrupt"})
        websocket.send_bytes(b"\x01\x00")
        assert websocket.receive_json() == {"type": "playback.interrupted", "playbackEpoch": 1, "source": "local"}
        assert websocket.receive_json() == chunk(1)
        assert websocket.receive_bytes() == b"\x01\x00"


def test_empty_audio_frame_is_ignored() -> None:
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"")
        websocket.send_bytes(b"\x01\x00")
        assert websocket.receive_json() == chunk()
        assert websocket.receive_bytes() == b"\x01\x00"
    assert adapter.received == [b"\x01\x00"]

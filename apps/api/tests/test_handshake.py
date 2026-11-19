"""R-01.F9: mutual handshake proof (review finding B1, old F5)."""
from __future__ import annotations

import json
import re
import time

import pytest
from handshake import proof
from starlette.websockets import WebSocketDisconnect
from test_voice_api import TOKEN, connect, counting_factory, expect_close, make_client, throttled

from super_agent_voice.config import VoiceConfig


def test_server_proves_the_token_and_never_sends_it() -> None:
    created, factory = counting_factory()
    with make_client(factory=factory) as client, connect(client) as websocket:
        nonce = "c" * 32
        websocket.send_json({"type": "session.hello", "nonce": nonce})
        challenge = websocket.receive_json()
        assert set(challenge) == {"type", "nonce", "proof"}
        assert re.fullmatch(r"[0-9a-f]{32}", challenge["nonce"]) and challenge["nonce"] != nonce
        assert challenge["proof"] == proof(TOKEN, "server-proof", nonce, challenge["nonce"])
        assert challenge["proof"] != proof("x" * 32, "server-proof", nonce, challenge["nonce"])
        assert TOKEN not in json.dumps(challenge)
        assert created == []  # a challenge grants no adapter authority
    assert created == []


def test_server_nonce_is_fresh_for_every_connection() -> None:
    with make_client() as client:
        seen = set()
        for _ in range(3):
            with connect(client) as websocket:
                websocket.send_json({"type": "session.hello", "nonce": "d" * 32})
                seen.add(websocket.receive_json()["nonce"])
    assert len(seen) == 3


def test_replayed_client_proof_is_rejected_and_counted_by_the_throttle() -> None:
    settings = throttled(
        auth_failure_threshold=1, auth_delay_base_seconds=0.3, auth_delay_cap_seconds=0.3
    )
    created, factory = counting_factory()
    with make_client(config=settings, factory=factory) as client:
        nonce = "e" * 32
        with connect(client) as first:  # a recorded, valid exchange
            first.send_json({"type": "session.hello", "nonce": nonce})
            old = first.receive_json()
            old_proof = proof(TOKEN, "client-proof", old["nonce"], nonce)
        with connect(client) as replay:
            replay.send_json({"type": "session.hello", "nonce": nonce})
            replay.receive_json()
            replay.send_json({"type": "session.auth", "proof": old_proof})
            expect_close(replay, 1008)  # failure 1 of threshold 1: still immediate
        with connect(client) as second:  # failure 2 is delayed, so the replay was counted
            second.send_json({"type": "session.hello", "nonce": nonce})
            second.receive_json()
            second.send_json({"type": "session.auth", "proof": old_proof})
            started = time.monotonic()
            expect_close(second, 1008)
            assert time.monotonic() - started >= 0.27
    assert created == []


@pytest.mark.parametrize(
    "answer",
    [
        {"type": "session.auth"},
        {"type": "session.auth", "proof": None},
        {"type": "session.auth", "proof": "0" * 64},
        {"type": "session.auth", "proof": "0" * 5000},
        {"type": "session.auth", "token": TOKEN},
        {"type": "session.hello", "nonce": "f" * 32},
    ],
    ids=["missing", "null", "wrong", "oversized", "raw-token-instead", "second-hello"],
)
def test_bad_client_proof_is_rejected_counted_and_creates_no_adapter(answer: dict) -> None:
    settings = throttled(
        auth_failure_threshold=1, auth_delay_base_seconds=0.3, auth_delay_cap_seconds=0.3
    )
    created, factory = counting_factory()
    with make_client(config=settings, factory=factory) as client:
        for index in range(2):
            with connect(client) as websocket:
                websocket.send_json({"type": "session.hello", "nonce": "f" * 32})
                websocket.receive_json()
                websocket.send_json(answer)
                started = time.monotonic()
                try:
                    websocket.receive_json()  # closed with 1008, or a fixed error first
                    expect_close(websocket, 1008)
                except WebSocketDisconnect as closed:
                    assert closed.code == 1008
                if index == 1:
                    assert time.monotonic() - started >= 0.27  # the second failure was delayed
    assert created == []


def test_handshake_steps_time_out_and_fail_closed() -> None:
    settings = VoiceConfig(local_token=TOKEN, auth_timeout_seconds=0.25)
    created, factory = counting_factory()
    with make_client(config=settings, factory=factory) as client:
        with connect(client) as silent:  # no hello
            assert silent.receive_json() == {"type": "session.error", "category": "session-timeout"}
        with connect(client) as stalled:  # hello, then no proof
            stalled.send_json({"type": "session.hello", "nonce": "9" * 32})
            assert stalled.receive_json()["type"] == "session.challenge"
            started = time.monotonic()
            assert stalled.receive_json() == {"type": "session.error", "category": "session-timeout"}
            assert 0.2 <= time.monotonic() - started < 2
    assert created == []


def test_one_deadline_covers_the_whole_handshake() -> None:
    # A late hello must not restart the clock: a pre-auth socket is held for one auth timeout, not two.
    settings = VoiceConfig(local_token=TOKEN, auth_timeout_seconds=1.0)
    created, factory = counting_factory()
    with make_client(config=settings, factory=factory) as client:
        started = time.monotonic()
        with connect(client) as slow:
            time.sleep(0.6)
            slow.send_json({"type": "session.hello", "nonce": "9" * 32})
            assert slow.receive_json()["type"] == "session.challenge"
            assert slow.receive_json() == {"type": "session.error", "category": "session-timeout"}
        assert time.monotonic() - started < 1.4  # per-step deadlines would take about 1.6 s
    assert created == []

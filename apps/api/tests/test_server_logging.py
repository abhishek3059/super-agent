"""Runs the real uvicorn server, which TestClient never exercises (review F1, F3)."""
from __future__ import annotations

import base64
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
# The documented launch flags: small frame and queue limits before authentication.
LIMITS = ["--ws-max-size", "65600", "--ws-max-queue", "4"]


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start(token: str, level: str, log: Path) -> tuple[subprocess.Popen, int]:
    port = free_port()
    env = {**os.environ, "SUPER_AGENT_LOCAL_TOKEN": token, "PYTHONPATH": str(SRC)}
    with log.open("w") as handle:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "super_agent_voice.app:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", level, *LIMITS],
            env=env, stdout=handle, stderr=handle,
        )
    return process, port


def wait_for_port(process: subprocess.Popen, port: int) -> None:
    for _ in range(100):
        if process.poll() is not None:
            return
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            return
        except OSError:
            time.sleep(0.1)


def handshake(port: int) -> socket.socket:
    connection = socket.create_connection(("127.0.0.1", port), 5)
    key = base64.b64encode(os.urandom(16)).decode()
    # The server checks Host and Origin against its configured values, not the port.
    connection.sendall(
        ("GET /ws/voice HTTP/1.1\r\nHost: 127.0.0.1:8000\r\nOrigin: http://127.0.0.1:4200\r\n"
         f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
         "Sec-WebSocket-Version: 13\r\n\r\n").encode()
    )
    assert connection.recv(4096).startswith(b"HTTP/1.1 101")
    return connection


def text_frame(payload: bytes) -> bytes:
    mask = os.urandom(4)
    length = len(payload)
    if length < 126:
        head = bytes([0x81, 0x80 | length])
    elif length < 65536:
        head = bytes([0x81, 0xFE]) + length.to_bytes(2, "big")
    else:
        head = bytes([0x81, 0xFF]) + length.to_bytes(8, "big")
    return head + mask + bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))


def stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(10)
    except subprocess.TimeoutExpired:
        process.kill()


def test_token_is_not_logged_by_a_real_server_and_debug_refuses_to_start(tmp_path) -> None:
    token = secrets.token_urlsafe(32)
    info_log, debug_log = tmp_path / "info.log", tmp_path / "debug.log"

    process, port = start(token, "info", info_log)
    try:
        wait_for_port(process, port)
        connection = handshake(port)
        connection.sendall(text_frame(('{"type":"session.auth","token":"%s"}' % token).encode()))
        assert b"session.ready" in connection.recv(4096)
        connection.close()
    finally:
        stop(process)

    # DEBUG would log the first frame, so the app must refuse to start.
    process, _ = start(token, "debug", debug_log)
    assert process.wait(20) != 0

    for log in (info_log, debug_log):
        text = log.read_text()
        assert token not in text and token[:12] not in text
    assert "debug logging would record the session token" in debug_log.read_text()


def test_oversized_frame_before_auth_is_closed_without_buffering_it(tmp_path) -> None:
    token = secrets.token_urlsafe(32)
    process, port = start(token, "info", tmp_path / "server.log")
    try:
        wait_for_port(process, port)
        connection = handshake(port)
        try:
            connection.sendall(text_frame(b"x" * 70_000))
            reply = connection.recv(4096)
        except (ConnectionResetError, BrokenPipeError):
            reply = b""
        # Close code 1009 (message too big) comes back in a close frame.
        assert reply == b"" or reply[0] & 0x0F == 0x8
        connection.close()
    finally:
        stop(process)

from __future__ import annotations

import hmac
import secrets


def auth_proof(token: str, direction: str, client_nonce: str, server_nonce: str, purpose: str = "voice") -> str:
    message = f"super-agent.{purpose}.v1/{direction}/{client_nonce}/{server_nonce}"
    return hmac.digest(token.encode(), message.encode(), "sha256").hex()


def begin_auth(websocket, client_nonce: str | None = None) -> tuple[str, dict]:
    nonce = client_nonce or secrets.token_hex(32)
    websocket.send_json({"type": "session.hello", "clientNonce": nonce})
    challenge = websocket.receive_json()
    assert challenge["type"] == "session.challenge"
    return nonce, challenge


def send_auth(websocket, token: str, *, purpose: str = "voice") -> dict[str, str]:
    client_nonce, challenge = begin_auth(websocket)
    server_nonce = challenge["serverNonce"]
    assert challenge["proof"] == auth_proof(token, "server", client_nonce, server_nonce, purpose)
    response = {"type": "session.auth", "proof": auth_proof(token, "client", client_nonce, server_nonce, purpose)}
    websocket.send_json(response)
    return response

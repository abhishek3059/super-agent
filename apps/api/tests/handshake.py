"""Client side of the session handshake, for tests (mirrors the browser console)."""
import hashlib
import hmac
import secrets
import time

PROTOCOL = "super-agent.v1"


def proof(token: str, label: str, first: str, second: str) -> str:
    return hmac.new(token.encode(), f"{label}|{first}|{second}".encode(), hashlib.sha256).hexdigest()


def upgrade(token: str, *, nonce: str | None = None, at: float | None = None) -> list[str]:
    """R-02.F4: the subprotocols the console offers. Proves the token before accept, never sends it."""
    nonce = nonce or secrets.token_hex(16)
    stamp = str(int(time.time() if at is None else at))
    return [PROTOCOL, f"sa-auth.{nonce}.{stamp}.{proof(token, 'upgrade', nonce, stamp)}"]


def send_auth(websocket, token: str, *, verify: bool = True) -> dict:
    """hello -> challenge -> auth. Returns the challenge; the caller reads what follows."""
    client_nonce = secrets.token_hex(16)
    websocket.send_json({"type": "session.hello", "nonce": client_nonce})
    challenge = websocket.receive_json()
    assert challenge["type"] == "session.challenge"
    if verify:
        assert challenge["proof"] == proof(token, "server-proof", client_nonce, challenge["nonce"])
    websocket.send_json({
        "type": "session.auth",
        "proof": proof(token, "client-proof", challenge["nonce"], client_nonce),
    })
    return challenge

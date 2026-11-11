from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

TOKEN_FILE = Path.home() / ".super-agent" / "voice-token"


@dataclass(frozen=True)
class VoiceConfig:
    local_token: str
    allowed_host: str = "127.0.0.1:8000"
    allowed_origin: str = "http://127.0.0.1:4200"
    max_control_bytes: int = 64 * 1024
    max_audio_frame_bytes: int = 32 * 1024
    # One active voice session; total session budget is enforced in code, not
    # by the model (design section 6).
    max_active_sessions: int = 1
    max_session_seconds: float = 15 * 60
    idle_timeout_seconds: float = 60
    # Fixed authentication deadline (contract CT-04). The total session
    # budget stays authoritative during auth: the effective auth deadline is
    # the smaller of this and the remaining total budget.
    auth_timeout_seconds: float = 5
    # One shared monotonic teardown deadline for handler cleanup waits
    # (teardown addendum revision 2, section 4.1). Every teardown wait loop
    # derives its budget from this single value, so one blocked worker, one
    # blocked close, and one blocked wire op share the budget instead of each
    # getting its own. create_app validates it before any session runs.
    teardown_seconds: float = 2.0
    # Live model ID, overridable because Google retires preview models.
    gemini_model: str = "gemini-3.8-live"

    @classmethod
    def from_environment(cls) -> "VoiceConfig":
        token = os.environ.get("SUPER_AGENT_LOCAL_TOKEN") or _read_token_file()
        # CR-09: length alone lets a repeated character through.
        if len(token.encode("utf-8")) < 32 or len(set(token)) < 16:
            raise RuntimeError(
                "SUPER_AGENT_LOCAL_TOKEN must contain at least 32 bytes and 16 distinct characters"
            )
        return cls(
            local_token=token,
            gemini_model=os.environ.get("SUPER_AGENT_GEMINI_MODEL") or cls.gemini_model,
        )


def _read_token_file() -> str:
    try:
        status = TOKEN_FILE.stat()
    except OSError:
        return ""
    # Mode and owner are not meaningful on Windows; the ACL check is review item N2.
    if os.name == "posix" and (
        status.st_mode & 0o077 or status.st_uid != os.getuid() or not stat.S_ISREG(status.st_mode)
    ):
        raise RuntimeError("local token file must be a mode 0600 file owned by this user")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()

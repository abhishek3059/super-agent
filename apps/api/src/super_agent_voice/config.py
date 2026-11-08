from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceConfig:
    local_token: str
    allowed_host: str = "127.0.0.1:8000"
    allowed_origin: str = "http://127.0.0.1:4200"
    max_control_bytes: int = 64 * 1024
    max_audio_frame_bytes: int = 32 * 1024

    @classmethod
    def from_environment(cls) -> "VoiceConfig":
        token = os.environ.get("SUPER_AGENT_LOCAL_TOKEN", "")
        if len(token.encode("utf-8")) < 32:
            raise RuntimeError("SUPER_AGENT_LOCAL_TOKEN must contain at least 32 bytes")
        return cls(local_token=token)

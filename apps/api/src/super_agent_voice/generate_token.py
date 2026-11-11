"""`python -m super_agent_voice.generate_token` writes a fresh local token (CR-02)."""
from __future__ import annotations

import os
import secrets

from .config import TOKEN_FILE


def main() -> None:
    TOKEN_FILE.parent.mkdir(mode=0o700, exist_ok=True)
    # shortcut: mode bits do nothing on Windows, where the file inherits the
    # profile directory ACL; add an explicit owner-only ACL with the N2 check (R-01.6).
    # Remove then create exclusively: an old file would keep its old mode, and
    # O_EXCL refuses a symlink planted at the path.
    TOKEN_FILE.unlink(missing_ok=True)
    descriptor = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(secrets.token_urlsafe(32))
    print(f"wrote {TOKEN_FILE}")  # the path only, never the token


if __name__ == "__main__":
    main()

"""The one place that decides whether owner-only, no-follow file handling exists on this host.

macOS and Linux have it. Windows has no O_NOFOLLOW, O_NONBLOCK or getuid, and its file modes
do not mean owner-only. A feature that stores or trusts a private file (the recap, the audit
log) therefore stays off there instead of running a weaker version of the same control.
Checked on every call, so a test can simulate Windows by removing the attributes.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

_NEEDED = ("O_NOFOLLOW", "O_NONBLOCK", "fchmod", "getuid")


def available() -> bool:
    return all(hasattr(os, name) for name in _NEEDED)


def audit_line(name: str, outcome: str) -> str:
    return f"{datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')} {name} {outcome}\n"


def append_audit(path: Path, line: str) -> None:
    """Appends one metadata line to a 0600 file in a 0700 folder, never through a symlink.
    Never raises: an unwritable log must not stop an action or an answer. Where the host cannot
    give those guarantees (Windows) nothing is written."""
    if not available():
        return
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)  # an older file keeps its mode otherwise
            os.write(fd, line.encode())
        finally:
            os.close(fd)
    except Exception:
        pass

"""A short recap of the last Gemini conversation, kept on this Mac so the next session can continue it.

Built by code from the last few transcript lines, with no extra model call. The file is
0600 in a 0700 folder, replaced atomically, ignored after seven days, and deletable by
voice. The text is personal data, so it is never logged. When read back it is data: the
caller frames it as such, and a line that looks like a secret is never saved.
"""
from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
import time
import unicodedata
from pathlib import Path

from . import memory

RECAP_PATH = Path.home() / ".super-agent" / "recap.json"
MAX_LINES = 5
MAX_LINE_CHARS = 200
MAX_AGE_SECONDS = 7 * 24 * 3600
MAX_FILE_BYTES = 8 * 1024

NAMES = frozenset({"forget_conversation"})
TOOLS = [{"type": "function", "function": {
    "name": "forget_conversation",
    "description": "Delete the saved recap of earlier conversations. Only when the user asks to forget, "
                   "clear or delete it.",
    "parameters": {"type": "object", "properties": {}, "required": []}}}]
FORGOTTEN = "Done: the saved recap of earlier conversations is deleted."
_SKIPS_UNICODE = ("Cc", "Cf", "Cs")  # control, format (bidi, zero-width, BOM) and surrogates


def enabled() -> bool:
    choice = os.environ.get("SUPER_AGENT_RECAP", "off")
    if choice not in ("on", "off"):
        raise RuntimeError("SUPER_AGENT_RECAP must be 'on' or 'off'")
    return choice == "on"


def _clean(text: str) -> str:
    kept = "".join(c for c in text if c.isspace() or unicodedata.category(c) not in _SKIPS_UNICODE)
    # Parentheses become brackets so a line cannot close the frame it is shown in.
    return " ".join(kept.split()).translate({ord("("): "[", ord(")"): "]"})[:MAX_LINE_CHARS]


def save(lines: list[tuple[str, str]]) -> None:
    """Writes the last few lines. Does nothing for an empty conversation, so an old recap is kept.
    Never raises: a recap that cannot be written must not break closing a session."""
    user = [text for role, text in lines if role == "user"]  # never the assistant's own words
    # The secret check sees the whole line, before it is cut to length.
    kept = [f"user: {_clean(text)}" for text in user[-MAX_LINES:] if not memory._SECRET.search(text)]  # noqa: SLF001
    if not kept:
        return
    body = json.dumps({"saved": int(time.time()), "lines": kept}).encode()
    temp = RECAP_PATH.with_name(f"{RECAP_PATH.name}.{secrets.token_hex(4)}.tmp")
    try:
        RECAP_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # O_EXCL refuses an existing path or symlink; the rename then replaces the old file whole.
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, body)
        finally:
            os.close(fd)
        os.replace(temp, RECAP_PATH)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(temp)


def load(now: float | None = None) -> list[str]:
    """The saved lines, or none when the file is missing, old, odd, or not private to this user."""
    try:
        fd = os.open(RECAP_PATH, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)  # a FIFO cannot block
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                return []
            raw = os.read(fd, MAX_FILE_BYTES + 1)
        finally:
            os.close(fd)
        data = json.loads(raw) if len(raw) <= MAX_FILE_BYTES else {}
        saved, lines = data["saved"], data["lines"]
        if type(saved) is not int or not -60 <= (now if now is not None else time.time()) - saved <= MAX_AGE_SECONDS:
            return []
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            return []
        return [_clean(line) for line in lines[:MAX_LINES]]  # cleaned again: the file is only data
    except (OSError, ValueError, KeyError, TypeError):
        return []


def clear() -> bool:
    """True when no recap is left on disk."""
    with contextlib.suppress(OSError):
        RECAP_PATH.unlink(missing_ok=True)
    return not RECAP_PATH.exists()

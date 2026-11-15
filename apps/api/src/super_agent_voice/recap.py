"""A short recap of the last Gemini conversation, kept on this Mac so the next session can continue it.

Built by code from the last few transcript lines, with no extra model call. The file is
0600 in a 0700 folder, replaced atomically, ignored after seven days, and forgettable by
voice. Forgetting sets the file aside instead of deleting it, so it can be restored for the same
24 hours as a forgotten memory fact; nothing here permanently deletes a recap the user did not
replace. The text is personal data, so it is never logged. When read back it is data: the
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

from . import memory, posix_files

RECAP_PATH = Path.home() / ".super-agent" / "recap.json"
MAX_LINES = 5
MAX_LINE_CHARS = 200
MAX_AGE_SECONDS = 7 * 24 * 3600
MAX_FILE_BYTES = 8 * 1024
UNDO_SECONDS = memory._UNDO_HOURS * 3600  # noqa: SLF001  the window memory's undo_forget uses

NAMES = frozenset({"forget_conversation", "restore_conversation"})
TOOLS = [{"type": "function", "function": {
    "name": name,
    "description": description,
    "parameters": {"type": "object", "properties": {}, "required": []}}} for name, description in (
    ("forget_conversation", "Forget the saved recap of earlier conversations. It is set aside and can be "
                            "restored for 24 hours. Only when the user asks to forget, clear or delete it."),
    ("restore_conversation", "Bring back the recap the user just had forgotten, if it was within 24 hours. "
                             "Only when the user asks to undo or restore it."))]
FORGOTTEN = ("Done: the saved recap of earlier conversations is forgotten. It can be restored for 24 hours "
             "if the user asks to undo it.")
FORGOTTEN_REPLACED = ("Done: the saved recap of earlier conversations is forgotten. It replaced the recap "
                      "forgotten before, which can no longer be restored. This one can be restored for 24 hours "
                      "if the user asks to undo it.")
RESTORED = "Done: the saved recap of earlier conversations is restored."
NOTHING_TO_RESTORE = "There is no forgotten recap to restore."
NEWER_EXISTS = "error: a newer recap is saved, so the forgotten one was not restored. Say so."
RESTORE_FAILED = "error: the recap could not be restored. Say so."
_SKIPS_UNICODE = ("Cc", "Cf", "Cs")  # control, format (bidi, zero-width, BOM) and surrogates


def enabled() -> bool:
    choice = os.environ.get("SUPER_AGENT_RECAP", "off")
    if choice not in ("on", "off"):
        raise RuntimeError("SUPER_AGENT_RECAP must be 'on' or 'off'")
    # Off on Windows: the file needs owner-only modes and no-follow opens (posix_files decides).
    return choice == "on" and posix_files.available()


def _clean(text: str) -> str:
    kept = "".join(c for c in text if c.isspace() or unicodedata.category(c) not in _SKIPS_UNICODE)
    # Parentheses become brackets so a line cannot close the frame it is shown in.
    return " ".join(kept.split()).translate({ord("("): "[", ord(")"): "]"})[:MAX_LINE_CHARS]


def save(lines: list[tuple[str, str]]) -> None:
    """Writes the last few lines. Does nothing for an empty conversation, so an old recap is kept.
    Never raises: a recap that cannot be written must not break closing a session."""
    if not posix_files.available():
        return
    _expire()
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
    if not posix_files.available():
        return []
    _expire()
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


def _aside() -> Path:
    return RECAP_PATH.with_name(RECAP_PATH.name + ".forgotten")


def _open_private(path: Path) -> int | None:
    """An open descriptor for a regular file that only this user can use, or None. Never follows a link."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if stat.S_ISREG(info.st_mode) and not info.st_mode & 0o077 and info.st_uid == os.getuid():
            return fd
    except OSError:
        pass
    os.close(fd)
    return None


def _expire() -> None:
    """Removes the set-aside copy once its 24 hours are over. A link or odd file there is left alone."""
    aside = _aside()
    with contextlib.suppress(OSError):
        info = aside.lstat()
        if stat.S_ISREG(info.st_mode) and time.time() - info.st_mtime > UNDO_SECONDS:
            aside.unlink()


def replaces_forgotten() -> bool:
    """True when forgetting now would replace an older set-aside copy that is still inside its 24 hours."""
    if not posix_files.available():
        return False
    _expire()
    return os.path.lexists(RECAP_PATH) and os.path.lexists(_aside())


def clear() -> bool:
    """Forgets the recap by setting it aside next to itself (same folder, still 0600), so new sessions
    no longer load it and restore() can bring it back for 24 hours. True when no recap is left in place.
    Only one set-aside copy exists: forgetting a newer recap replaces the older forgotten one. Nothing
    is moved when there is no recap, and an odd file (a link, a folder, a file others can read) in
    either place is refused and left untouched."""
    if not posix_files.available():
        return not RECAP_PATH.exists()
    _expire()
    if not os.path.lexists(RECAP_PATH):
        return True
    try:
        if os.path.lexists(_aside()) and not stat.S_ISREG(_aside().lstat().st_mode):
            return False
        fd = _open_private(RECAP_PATH)
        if fd is None:
            return False
        try:
            os.utime(fd)  # the 24 hours run from now, not from when the recap was written
            os.replace(RECAP_PATH, _aside())
        finally:
            os.close(fd)
    except OSError:
        return False
    return True


def restore() -> str:
    """Brings the forgotten recap back, one of the fixed messages above. Within 24 hours only.
    A newer recap always wins: if one is saved, the forgotten copy stays set aside (until its
    window ends) and nothing is overwritten. The restore is a hard link that refuses an existing
    path, so even a recap saved at the same moment is never replaced."""
    if not posix_files.available():
        return NOTHING_TO_RESTORE
    _expire()
    fd = _open_private(_aside())
    if fd is None:
        return NOTHING_TO_RESTORE
    os.close(fd)
    try:
        os.link(_aside(), RECAP_PATH, follow_symlinks=False)
    except FileExistsError:
        return NEWER_EXISTS
    except OSError:
        return RESTORE_FAILED
    with contextlib.suppress(OSError):
        _aside().unlink()
    return RESTORED

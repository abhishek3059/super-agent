"""Tier T3 approved actions (DEC-18): three small things on the Mac, each only after a click.

The assistant may open an https page, search the web, or open one allowed app.
Nothing runs until the user clicks Approve in the console on this machine; a
spoken "yes" never counts. The model's arguments are hostile input: code
validates them, builds the summary the user sees and the command that runs,
and the model's own words reach neither. The command is a fixed absolute
program with an argument list (no shell). The audit log holds the tool name and
outcome only, never a URL, query, or app name (REQ-14).
"""
from __future__ import annotations

import asyncio
import os
import re
import unicodedata
import urllib.parse
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

# Metadata only, same file and format as tier1's audit log.
AUDIT_LOG = Path.home() / ".super-agent" / "tool-audit.log"

OPEN = "/usr/bin/open"
TIMEOUT_SECONDS = 5.0
MAX_URL, MAX_QUERY = 300, 100
DEFAULT_APPS = ("Calendar", "Notes", "Reminders", "Music", "Maps", "Calculator", "Safari")

NO_TOOL = "error: no such tool."
BAD_ARGS = "error: invalid arguments."
BAD_URL = "error: only a plain https web address is allowed, so nothing was done."
BAD_QUERY = f"error: a search needs 1 to {MAX_QUERY} characters, so nothing was done."
BAD_APP = "error: that app is not on the allowed list, so nothing was done."
FAILED = "error: the action failed. Say so."
DENIED = "error: the user did not approve, so nothing was done. Say so."
TIMED_OUT = "error: no approval in time, so nothing was done. Say so."
DONE = "Done: it is open on the screen."
AFTER_READ = ("error: actions cannot run in a turn that read files, notes, mail or calendar, "
              "so nothing was done. Tell the user to ask again in a new sentence.")
ONE_PER_TURN = "error: only one action is allowed per turn, so nothing was done."
NO_APPROVER = "error: there is no way to ask the user, so nothing was done."

# Each local-network style suffix would let a page poke at the user's router or a dev server.
# Names for machines on the user's own network or reserved for tests. A name that only resolves
# to a local address through public DNS (nip.io and the like) cannot be caught by its spelling.
_LOCAL_SUFFIXES = ("local", "localhost", "internal", "lan", "home", "arpa", "corp", "intranet",
                   "localdomain", "test", "example", "invalid")
# A short, plain path: a long or encoded path is where a model could hide text it read.
_PATH = re.compile(r"/[A-Za-z0-9/._~-]{0,63}")
MAX_SUMMARY = 200  # the console shows the summary whole; it is refused rather than ever cut
# Letters only in the last label, so 127.1, 0x7f.1 and other IP spellings a browser accepts are out.
_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_APP_NAME = re.compile(r"[A-Za-z0-9 ]{1,40}")
_SKIPS_UNICODE = ("Cc", "Cf", "Cs")  # control, format (bidi, zero-width, BOM) and surrogates


class Refused(Exception):
    """Carries one of the fixed error strings above, never content."""


def _fn(name: str, description: str, param: str, text: str) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": {param: {"type": "string", "description": text}},
                       "required": [param]}}}


TOOLS = [
    _fn("open_url", "Open a web page in the user's browser. The user must approve on screen first.",
        "url", "A full https address with no query string."),
    _fn("web_search", "Search the web in the user's browser. The user must approve on screen first.",
        "query", f"Search words, up to {MAX_QUERY} characters."),
    _fn("open_app", "Open one allowed Mac app. The user must approve on screen first.",
        "name", "The app's name, for example Calendar."),
]
NAMES = frozenset(schema["function"]["name"] for schema in TOOLS)
_PARAM = {s["function"]["name"]: next(iter(s["function"]["parameters"]["properties"])) for s in TOOLS}


def allowed_apps() -> tuple[str, ...]:
    """The apps open_app may start. A bad setting stops the session instead of widening the list."""
    raw = os.environ.get("SUPER_AGENT_ACTION_APPS")
    if raw is None:
        return DEFAULT_APPS
    apps = tuple(entry.strip() for entry in raw.split(","))
    if not all(_APP_NAME.fullmatch(app) and app == app.strip() for app in apps):
        raise RuntimeError("SUPER_AGENT_ACTION_APPS must be a comma list of names using letters, digits and spaces")
    return apps


def _url(value: str) -> tuple[str, list[str]]:
    # ASCII, no spaces, no backslash: a lookalike letter or a backslash can make the host shown
    # differ from the host a browser opens.
    if len(value) > MAX_URL or not (value.isascii() and value.isprintable()) or " " in value or "\\" in value:
        raise Refused(BAD_URL)
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
    except ValueError:
        raise Refused(BAD_URL) from None
    host = parts.hostname or ""
    if (parts.scheme != "https" or "@" in parts.netloc or port not in (None, 443)
            or not _HOST.fullmatch(host) or host.rsplit(".", 1)[-1] in _LOCAL_SUFFIXES
            or any(label.startswith("xn--") for label in host.split("."))  # punycode can mimic a known name
            or not _PATH.fullmatch(parts.path or "/")):
        raise Refused(BAD_URL)
    # The query and fragment are dropped: a model could hide file or memory text there.
    cleaned = f"https://{host}{parts.path or '/'}"
    return f"Open {cleaned} in your browser?", [OPEN, cleaned]


def _search(value: str) -> tuple[str, list[str]]:
    query = " ".join("".join(c for c in value if c.isspace() or unicodedata.category(c) not in _SKIPS_UNICODE).split())
    if not 1 <= len(query) <= MAX_QUERY:
        raise Refused(BAD_QUERY)
    return f'Search the web for "{query}"?', [OPEN, "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(query)]


def _app(value: str) -> tuple[str, list[str]]:
    for app in allowed_apps():
        if app.casefold() == value.strip().casefold():
            return f"Open the app {app}?", [OPEN, "-a", app]  # the list's spelling, never the model's
    raise Refused(BAD_APP)


_PREPARE = {"open_url": _url, "web_search": _search, "open_app": _app}


def prepare(name: object, arguments: object) -> tuple[str, list[str]]:
    """The summary the user will see and the command to run, or a Refused. Runs nothing."""
    if not isinstance(name, str) or name not in NAMES:
        raise Refused(NO_TOOL)
    param = _PARAM[name]
    value = arguments.get(param) if isinstance(arguments, dict) else None
    if not isinstance(arguments, dict) or arguments.keys() != {param} or not isinstance(value, str) or len(value) > 2000:
        raise Refused(BAD_ARGS)
    summary, argv = _PREPARE[name](value)
    if len(summary) > MAX_SUMMARY:
        raise Refused(BAD_URL if name == "open_url" else BAD_ARGS)
    return summary, argv


async def execute(argv: list[str]) -> None:
    """Runs one prepared command. Module level so tests replace it and nothing really opens."""
    process = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL)
    try:
        code = await asyncio.wait_for(process.wait(), TIMEOUT_SECONDS)
    except BaseException:
        if process.returncode is None:
            process.kill()
        raise
    if code:
        raise RuntimeError("non-zero exit")


async def run(name: object, arguments: object, approve: Callable[[str], Awaitable[bool]] | None) -> str:
    """Validate, ask the user, then run. Only an explicit True from approve reaches execute."""
    outcome, result = "refused", FAILED
    try:
        summary, argv = prepare(name, arguments)
        if approve is None:
            raise Refused(NO_APPROVER)
        outcome, result = "denied", DENIED  # until the user clicks Approve, nothing runs
        try:
            approved = await approve(summary) is True
        except TimeoutError:  # nobody clicked in time
            outcome, result, approved = "timeout", TIMED_OUT, False
        if approved:
            outcome, result = "error", FAILED
            await execute(argv)
            outcome, result = "approved", DONE
    except Refused as refusal:
        result = str(refusal)
    except asyncio.CancelledError:  # the user spoke over it, or the session ended
        audit(name, outcome)
        raise
    except Exception:
        pass  # the fixed result stands; the exception text could hold the URL
    audit(name, outcome)
    return result


def audit(name: object, outcome: str) -> None:
    """Appends time, tool name, and outcome. Never arguments or content (REQ-14)."""
    shown = name if isinstance(name, str) and name in NAMES else "unknown"
    line = f"{datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')} {shown} {outcome}\n"
    try:
        AUDIT_LOG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(AUDIT_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)  # an older file keeps its mode otherwise
            os.write(fd, line.encode())
        finally:
            os.close(fd)
    except OSError:
        pass  # an unwritable log must not stop an action the user approved

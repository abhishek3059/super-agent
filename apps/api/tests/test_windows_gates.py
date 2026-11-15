"""Windows behaviour, simulated so it runs on macOS and Linux too.

Windows has no O_NOFOLLOW, O_NONBLOCK or getuid, and its file modes are not owner-only. The
features that need those (the recap file, the audit log) must be off there, cleanly and
without raising, while a session still starts. These tests remove the same attributes.
"""
from __future__ import annotations

import os
import sys

import pytest
from conftest import needs_posix_files
from test_gemini_adapter import FakeSession, run
from test_gemini_console import make
from test_weather import ask, fake_get

from super_agent_voice import actions, gemini_adapter, local_adapter, memory, posix_files, recap


@pytest.fixture
def windows(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    for name in ("O_NOFOLLOW", "O_NONBLOCK", "fchmod", "getuid"):
        monkeypatch.delattr(os, name, raising=False)
    monkeypatch.setattr(memory, "DB_PATH", tmp_path / "mem" / "memory.db")
    monkeypatch.setattr(gemini_adapter, "HEARD_WAIT_S", 0.0)
    assert not posix_files.available()


def test_a_gemini_session_starts_with_every_switch_on_and_the_posix_features_are_off(windows, monkeypatch, tmp_path):
    for name in ("WEATHER", "MEMORY", "ACTIONS", "RECAP"):
        monkeypatch.setenv(f"SUPER_AGENT_{name}", "on")

    async def scenario():
        adapter = make(FakeSession())
        await adapter.start()
        names = {function["name"] for function in adapter._functions}
        instruction = adapter._instruction
        await adapter.close()
        return names, instruction

    names, instruction = run(scenario())
    assert "get_weather" in names and memory.NAMES <= names  # nothing POSIX-only about these
    assert not names & actions.NAMES and not names & recap.NAMES
    assert "forget_conversation" not in instruction and "Earlier conversation" not in instruction
    assert not recap.RECAP_PATH.exists() and not actions.AUDIT_LOG.exists()


def test_the_recap_is_off_and_never_touches_a_file(windows, monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_RECAP", "on")
    assert recap.enabled() is False
    recap.save([("user", "call mom")])
    assert not recap.RECAP_PATH.exists() and recap.load() == []
    # Forget and restore are no-ops there: no file is moved, linked or created, and nothing raises.
    assert recap.clear() is True and recap.restore() == recap.NOTHING_TO_RESTORE
    assert not recap.RECAP_PATH.parent.exists()
    monkeypatch.setenv("SUPER_AGENT_RECAP", "maybe")
    with pytest.raises(RuntimeError):  # a mistyped switch still stops the session
        recap.enabled()


def test_approved_actions_are_off_and_a_direct_call_does_not_raise(windows, monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_ACTIONS", "on")
    assert not local_adapter.actions_enabled()
    assert not {tool["function"]["name"] for tool in local_adapter.available_tools()} & actions.NAMES
    ran: list = []

    async def execute(argv):
        ran.append(argv)
    monkeypatch.setattr(actions, "execute", execute)

    async def approve(summary):
        return True
    assert run(actions.run("open_url", {"url": "https://example.com"}, approve)) == actions.DONE
    assert not actions.AUDIT_LOG.exists()  # no audit is written where it cannot be written safely


def test_weather_still_answers_and_writes_no_audit_line(windows, monkeypatch):
    fake_get(monkeypatch)
    assert ask("Lisbon").startswith("In Lisbon")
    assert not actions.AUDIT_LOG.exists()


@needs_posix_files
@pytest.mark.parametrize("error", [RuntimeError, AttributeError, PermissionError])
def test_the_audit_write_never_raises_whatever_goes_wrong(monkeypatch, error):
    def broken(*args, **kwargs):
        raise error("boom")
    monkeypatch.setattr(os, "open", broken)
    actions.audit("open_url", "approved")
    posix_files.append_audit(actions.AUDIT_LOG, "line\n")

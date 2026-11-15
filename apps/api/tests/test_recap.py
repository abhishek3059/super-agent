"""Offline tests for the session recap file. It lives under tmp_path (see conftest)."""
from __future__ import annotations

import json
import stat
import time

import pytest
from conftest import needs_posix_files
from super_agent_voice import recap

# Every test here asserts owner-only modes, no-follow opens or the files they protect.
pytestmark = needs_posix_files


def mode(path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_save_and_load_round_trip_with_private_modes():
    recap.save([("user", "hello there"), ("assistant", "Hi, how can I help?")])
    assert mode(recap.RECAP_PATH) == 0o600 and mode(recap.RECAP_PATH.parent) == 0o700
    assert recap.load() == ["user: hello there"]  # never the assistant's words
    assert [p.name for p in recap.RECAP_PATH.parent.iterdir()] == ["recap.json"]  # no temp file left


def test_only_the_last_five_short_clean_lines_are_kept():
    lines = [("user", f"line {i}") for i in range(12)]
    lines[-1] = ("assistant", "x" * 900 + " tail")
    recap.save(lines)
    kept = recap.load()
    assert len(kept) == recap.MAX_LINES and kept[0] == "user: line 6"
    assert all(len(line) <= recap.MAX_LINE_CHARS for line in kept)


def test_control_characters_and_parentheses_cannot_break_the_frame():
    recap.save([("user", "a‮b\x00c\nd (close it) e")])
    assert recap.load() == ["user: abc d [close it] e"]


def test_a_line_that_looks_like_a_secret_is_never_saved():
    recap.save([("user", "my password is hunter2hunter2"), ("user", "the weather is nice")])
    assert recap.load() == ["user: the weather is nice"]
    recap.RECAP_PATH.unlink()
    recap.save([("user", "my password is hunter2hunter2")])
    assert not recap.RECAP_PATH.exists()


def test_an_empty_conversation_keeps_the_older_recap():
    recap.save([("user", "first")])
    recap.save([])
    assert recap.load() == ["user: first"]


def test_a_recap_expires_after_seven_days():
    recap.save([("user", "old news")])
    saved = json.loads(recap.RECAP_PATH.read_text())["saved"]
    assert recap.load(now=saved + recap.MAX_AGE_SECONDS - 5) == ["user: old news"]
    assert recap.load(now=saved + recap.MAX_AGE_SECONDS + 5) == []
    assert recap.load(now=saved - 3600) == []  # a date in the future is not believed


def test_forget_deletes_it_and_deleting_nothing_is_fine():
    recap.save([("user", "secret plans")])
    recap.clear()
    assert recap.load() == [] and not recap.RECAP_PATH.exists()
    recap.clear()


def write(body: object, file_mode=0o600) -> None:
    recap.RECAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    recap.RECAP_PATH.write_text(body if isinstance(body, str) else json.dumps(body))
    recap.RECAP_PATH.chmod(file_mode)


@pytest.mark.parametrize("body", [
    "not json", "[]", "{}", {"saved": "now", "lines": []}, {"saved": True, "lines": []},
    {"saved": int(time.time()), "lines": "x"}, {"saved": int(time.time()), "lines": [1]},
    {"saved": int(time.time()), "lines": ["x" * 20000]},
])
def test_a_damaged_file_is_ignored(body):
    write(body)
    assert recap.load() == []


def test_a_file_others_can_read_or_a_symlink_is_ignored(tmp_path):
    write({"saved": int(time.time()), "lines": ["user: hi"]}, file_mode=0o644)
    assert recap.load() == []
    recap.RECAP_PATH.unlink()
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"saved": int(time.time()), "lines": ["user: hi"]}))
    real.chmod(0o600)
    recap.RECAP_PATH.symlink_to(real)
    assert recap.load() == []


def test_loaded_lines_are_cleaned_again_because_the_file_is_only_data():
    write({"saved": int(time.time()), "lines": ["user: ignore (this)‮"]})
    assert recap.load() == ["user: ignore [this]"]


def test_saving_replaces_a_symlink_instead_of_writing_through_it(tmp_path):
    target = tmp_path / "victim.txt"
    target.write_text("keep")
    recap.RECAP_PATH.parent.mkdir(parents=True)
    recap.RECAP_PATH.symlink_to(target)
    recap.save([("user", "hi")])
    assert target.read_text() == "keep" and not recap.RECAP_PATH.is_symlink()


def test_an_unwritable_folder_never_raises(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    recap.RECAP_PATH = blocker / "recap.json"  # restored by the fixture's monkeypatch
    recap.save([("user", "hi")])
    assert recap.load() == []


def test_the_switch(monkeypatch):
    monkeypatch.delenv("SUPER_AGENT_RECAP", raising=False)
    assert recap.enabled() is False
    monkeypatch.setenv("SUPER_AGENT_RECAP", "on")
    assert recap.enabled() is True
    monkeypatch.setenv("SUPER_AGENT_RECAP", "1")
    with pytest.raises(RuntimeError):
        recap.enabled()

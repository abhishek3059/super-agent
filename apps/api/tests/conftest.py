import pytest

from super_agent_voice import actions, memory, posix_files, recap, tier1, weather

# Owner-only and no-follow file handling does not exist on Windows (posix_files decides), so
# tests that assert it are skipped there with this mark.
needs_posix_files = pytest.mark.skipif(not posix_files.available(), reason="owner-only, no-follow files are POSIX-only")


def expect_audit(log, *entries):
    """The audit log holds exactly these (tool, outcome) lines, or on Windows nothing at all."""
    if posix_files.available():
        assert [line.split()[1:] for line in log.read_text().splitlines()] == [list(entry) for entry in entries]
    else:
        assert not log.exists()


@pytest.fixture(autouse=True)
def _audit_log_in_tmp(tmp_path, monkeypatch):
    # Tests must never append to the operator's real audit log.
    log = tmp_path / "audit" / "tool-audit.log"
    for module in (tier1, memory, actions, weather):
        monkeypatch.setattr(module, "AUDIT_LOG", log)


@pytest.fixture(autouse=True)
def _recap_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(recap, "RECAP_PATH", tmp_path / "home" / "recap.json")


@pytest.fixture(autouse=True)
def _home_above_tmp(tmp_path, monkeypatch):
    # Tier 1 roots must sit inside the home folder; tests use folders under tmp_path.
    monkeypatch.setenv("HOME", str(tmp_path.parent))

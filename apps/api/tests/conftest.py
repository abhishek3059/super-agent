import pytest

from super_agent_voice import actions, memory, recap, tier1, weather


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

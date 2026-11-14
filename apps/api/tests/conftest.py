import pytest

from super_agent_voice import tier1


@pytest.fixture(autouse=True)
def _audit_log_in_tmp(tmp_path, monkeypatch):
    # Tests must never append to the operator's real audit log.
    monkeypatch.setattr(tier1, "AUDIT_LOG", tmp_path / "audit" / "tool-audit.log")


@pytest.fixture(autouse=True)
def _home_above_tmp(tmp_path, monkeypatch):
    # Tier 1 roots must sit inside the home folder; tests use folders under tmp_path.
    monkeypatch.setenv("HOME", str(tmp_path.parent))

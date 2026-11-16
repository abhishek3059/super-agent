import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# The operator's real data folder. Found before anything is redirected.
REAL_DATA = Path.home() / ".super-agent"
# Every module computes its paths from Path.home() when it is imported (ledger, memory, tier1, config,
# local_adapter, lfm3_voice). Pointing the home folder at a temp folder before the first import means no
# default path in this suite can name the real folder. HOME is read on macOS and Linux, USERPROFILE on Windows.
_FAKE_HOME = tempfile.mkdtemp(prefix="super-agent-test-home-")
os.environ["HOME"] = os.environ["USERPROFILE"] = _FAKE_HOME
atexit.register(shutil.rmtree, _FAKE_HOME, True)

from super_agent_voice import tier1  # noqa: E402  (must come after the home folder is redirected)
from super_agent_voice.runner import Runner  # noqa: E402


def _listing(root: Path = REAL_DATA) -> dict:
    """Name, size and modification time of every entry under the data folder. Never contents."""
    if not root.exists():
        return {}
    found = {}
    for path in [root, *root.rglob("*")]:
        info = path.stat()
        found[str(path)] = (info.st_size, info.st_mtime_ns)
    return found


def _assert_unchanged(before: dict, what: str, root: Path = REAL_DATA) -> None:
    assert _listing(root) == before, f"{what} changed files under the real ~/.super-agent"


@pytest.fixture(scope="session", autouse=True)
def _real_data_folder_is_untouched():
    """Safety net behind the redirect: no test may create, change or delete anything in the real folder."""
    before = _listing()
    assert str(Path.home()) == _FAKE_HOME, "the home folder was not redirected"
    yield
    _assert_unchanged(before, "the suite")
    # Nothing should have reached the redirected default folder either: a write there means a test (or a
    # worker thread it left behind) used a default path instead of its own temp path.
    assert _listing(Path(_FAKE_HOME) / ".super-agent") == {}, "a test wrote to a default data path"


@pytest.fixture(autouse=True)
def _real_data_folder_is_untouched_by_each_test():
    before = _listing()
    yield
    _assert_unchanged(before, "this test")


@pytest.fixture(autouse=True)
def _no_worker_outlives_its_test(monkeypatch):
    """Drain every Runner a test built before the test's own monkeypatches are undone.

    This fixture requests monkeypatch, so its teardown runs before monkeypatch's undo. Without it a job
    still running at the end of a test goes on to use whatever the patched paths point to afterwards."""
    runners, real_init = [], Runner.__init__

    def register(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        runners.append(self)

    monkeypatch.setattr(Runner, "__init__", register)
    yield
    for runner in runners:
        runner._pool.shutdown(wait=True, cancel_futures=True)


@pytest.fixture(autouse=True)
def _audit_log_in_tmp(tmp_path, monkeypatch):
    # Tests must never append to the operator's real audit log.
    from super_agent_voice import memory

    monkeypatch.setattr(tier1, "AUDIT_LOG", tmp_path / "audit" / "tool-audit.log")
    monkeypatch.setattr(memory, "AUDIT_LOG", tmp_path / "audit" / "memory-audit.log")


@pytest.fixture(autouse=True)
def _home_above_tmp(tmp_path, monkeypatch):
    # Tier 1 roots must sit inside the home folder; tests use folders under tmp_path.
    monkeypatch.setenv("HOME", str(tmp_path.parent))

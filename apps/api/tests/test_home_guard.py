import conftest
import pytest

from super_agent_voice import config, ledger, local_adapter, memory, tier1


def test_no_default_path_points_into_the_real_data_folder():
    real = conftest.REAL_DATA
    for path in (ledger.DB_PATH, memory.DB_PATH, tier1.AUDIT_LOG, config.TOKEN_FILE, local_adapter.MODEL_DIR):
        assert real not in path.parents and path != real, path


def test_the_guard_notices_a_new_a_changed_and_a_removed_file(tmp_path):
    folder = tmp_path / ".super-agent"
    folder.mkdir()
    before = conftest._listing(folder)
    conftest._assert_unchanged(before, "nothing", folder)
    for change in (lambda f: f.write_bytes(b"x"), lambda f: f.write_bytes(b"xy"), lambda f: f.unlink()):
        change(folder / "a.db")
        with pytest.raises(AssertionError, match="changed files"):
            conftest._assert_unchanged(before, "this test", folder)
        before = conftest._listing(folder)

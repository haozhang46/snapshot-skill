from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skills.time_machine import TimeMachine
from skills.time_machine.errors import DirtyWorkspaceError


def init_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    shutil.copytree(Path(__file__).parent / "fixtures" / "sample_repo", repo_path)
    (repo_path / "config").mkdir()
    (repo_path / "scripts").mkdir()
    (repo_path / "policies").mkdir()
    (repo_path / "config" / "app.yaml").write_text("version: 1\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True)
    return repo_path


def test_restore_dirty_workspace_protection(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path)
    tm = TimeMachine(repo_path)
    snapshot = tm.snapshot(reason="baseline", level="normal")

    (repo_path / "config" / "app.yaml").write_text("version: 2\n", encoding="utf-8")

    with pytest.raises(DirtyWorkspaceError):
        tm.restore(snapshot["git_commit"], verify=False)

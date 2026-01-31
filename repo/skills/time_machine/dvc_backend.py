"""DVC backend wrapper."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .utils import run_cmd


class DVCBackend:
    def __init__(self, repo_path: Path, enabled: bool = True) -> None:
        self.repo_path = repo_path
        self.enabled = enabled

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if os.getenv("TM_DVC_DISABLED") == "1":
            return False
        return shutil.which("dvc") is not None

    def is_initialized(self) -> bool:
        return (self.repo_path / ".dvc").exists()

    def add(self, path: Path) -> None:
        run_cmd(["dvc", "add", str(path)], cwd=self.repo_path)

    def push(self) -> None:
        run_cmd(["dvc", "push"], cwd=self.repo_path)

    def checkout(self) -> None:
        run_cmd(["dvc", "checkout"], cwd=self.repo_path)

    def has_remote(self) -> bool:
        output = run_cmd(["dvc", "remote", "list"], cwd=self.repo_path).stdout
        return bool(output.strip())

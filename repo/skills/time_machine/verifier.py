"""Verification utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import VerificationError
from .utils import run_cmd


class Verifier:
    def __init__(self, repo_path: Path, required_paths: list[str], healthcheck_cmd: list[str] | None) -> None:
        self.repo_path = repo_path
        self.required_paths = required_paths
        self.healthcheck_cmd = healthcheck_cmd

    def verify(self) -> dict[str, Any]:
        missing = [path for path in self.required_paths if not (self.repo_path / path).exists()]
        if missing:
            raise VerificationError(f"Missing required paths: {', '.join(missing)}")

        healthcheck_output = None
        if self.healthcheck_cmd:
            result = run_cmd(self.healthcheck_cmd, cwd=self.repo_path)
            healthcheck_output = result.stdout

        return {
            "required_paths_ok": True,
            "healthcheck_output": healthcheck_output,
        }

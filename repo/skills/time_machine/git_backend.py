"""Git backend wrapper."""

from __future__ import annotations

from pathlib import Path

from .utils import run_cmd


class GitBackend:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def status(self) -> str:
        return run_cmd(["git", "status", "--porcelain"], cwd=self.repo_path).stdout

    def add_all(self) -> None:
        run_cmd(["git", "add", "-A"], cwd=self.repo_path)

    def commit(self, message: str, allow_empty: bool = False) -> str:
        cmd = ["git", "commit", "-m", message]
        if allow_empty:
            cmd.insert(2, "--allow-empty")
        run_cmd(cmd, cwd=self.repo_path)
        return self.rev_parse("HEAD")

    def tag(self, tag_name: str) -> None:
        run_cmd(["git", "tag", tag_name], cwd=self.repo_path)

    def tags(self) -> list[str]:
        output = run_cmd(["git", "tag", "--list"], cwd=self.repo_path).stdout
        return [line.strip() for line in output.splitlines() if line.strip()]

    def log(self, limit: int = 30) -> str:
        return run_cmd(
            ["git", "log", f"-n{limit}", "--pretty=format:%H%x1f%B%x1e"],
            cwd=self.repo_path,
        ).stdout

    def diff_stat(self, a: str, b: str) -> str:
        return run_cmd(["git", "diff", "--stat", a, b], cwd=self.repo_path).stdout

    def diff_shortstat(self, a: str, b: str) -> str:
        return run_cmd(["git", "diff", "--shortstat", a, b], cwd=self.repo_path).stdout

    def diff_names(self, a: str, b: str) -> list[str]:
        output = run_cmd(["git", "diff", "--name-only", a, b], cwd=self.repo_path).stdout
        return [line.strip() for line in output.splitlines() if line.strip()]

    def diff_numstat(self, a: str, b: str) -> list[str]:
        output = run_cmd(["git", "diff", "--numstat", a, b], cwd=self.repo_path).stdout
        return [line.strip() for line in output.splitlines() if line.strip()]

    def checkout(self, target: str) -> None:
        run_cmd(["git", "checkout", target], cwd=self.repo_path)

    def rev_parse(self, target: str) -> str:
        return run_cmd(["git", "rev-parse", target], cwd=self.repo_path).stdout

    def show(self, target: str) -> str:
        return run_cmd(["git", "show", "-s", "--format=%B", target], cwd=self.repo_path).stdout

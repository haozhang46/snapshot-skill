"""Utility helpers for time machine skill."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import random
import string
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import CommandError


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> CommandResult:
    """Run a command safely and return its output.

    Raises CommandError on failure.
    """
    process = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    result = CommandResult(
        stdout=process.stdout.strip(),
        stderr=process.stderr.strip(),
        returncode=process.returncode,
    )
    if process.returncode != 0:
        raise CommandError(cmd, process.returncode, result.stderr)
    return result


@contextlib.contextmanager
def file_lock(lock_path: Path) -> contextlib.AbstractContextManager[None]:
    """Simple file lock using fcntl."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        try:
            import fcntl

            fcntl.flock(lock_file, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except OSError:
                pass


def generate_snapshot_id(ts: float | None = None) -> str:
    ts = ts or time.time()
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(ts))
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{timestamp}-{rand}"


def hash_payload(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]

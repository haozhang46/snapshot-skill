"""Custom errors for the time machine skill."""

from __future__ import annotations


class TimeMachineError(Exception):
    """Base error for time machine."""


class CommandError(TimeMachineError):
    """Raised when a subprocess command fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        message = f"Command failed ({returncode}): {' '.join(cmd)}\n{stderr}"
        super().__init__(message)


class DirtyWorkspaceError(TimeMachineError):
    """Raised when workspace is dirty and operation is unsafe."""


class ProtectedPathError(TimeMachineError):
    """Raised when protected paths are modified without reason."""


class VerificationError(TimeMachineError):
    """Raised when verification fails after restore."""

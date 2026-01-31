"""Audit logging for time machine skill."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import hash_payload


@dataclass
class AuditRecord:
    ts: str
    action: str
    actor: str
    args: dict[str, Any]
    result: dict[str, Any]
    status: str
    error: str | None = None

    def to_json(self) -> str:
        payload = {
            "ts": self.ts,
            "action": self.action,
            "actor": self.actor,
            "args": self.args,
            "result": self.result,
            "status": self.status,
            "error": self.error,
        }
        return json.dumps(payload, ensure_ascii=False)


class AuditLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: AuditRecord) -> Path:
        digest = hash_payload(record.__dict__)
        log_path = self.log_dir / f"audit-{digest}.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json())
            handle.write("\n")
        return log_path

    @staticmethod
    def human_summary(record: AuditRecord) -> str:
        return (
            f"[{record.ts}] {record.action} status={record.status} "
            f"actor={record.actor}"
        )


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

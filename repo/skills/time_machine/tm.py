"""Core time machine implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .audit import AuditLogger, AuditRecord, now_ts
from .dvc_backend import DVCBackend
from .errors import DirtyWorkspaceError, ProtectedPathError, TimeMachineError
from .git_backend import GitBackend
from .utils import file_lock, generate_snapshot_id
from .verifier import Verifier


class TimeMachine:
    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = Path(repo_path).resolve()
        self.config = self._load_config()
        self.git = GitBackend(self.repo_path)
        self.dvc = DVCBackend(self.repo_path, enabled=self.config["dvc"]["enabled"])
        audit_dir = self.repo_path / self.config["audit_log_dir"]
        self.audit = AuditLogger(audit_dir)
        self.lock_path = self.repo_path / self.config["lock_file"]

    def snapshot(self, reason: str | None = None, level: str = "normal") -> dict[str, Any]:
        args = {"reason": reason, "level": level}
        with file_lock(self.lock_path):
            try:
                status_output = self.git.status()
                changed_paths = self._parse_changed_paths(status_output)
                protected_hits = self._protected_paths_touched(changed_paths)
                if protected_hits and not reason:
                    raise ProtectedPathError(
                        "Protected paths modified without reason: "
                        + ", ".join(sorted(protected_hits))
                    )

                snapshot_id = generate_snapshot_id()
                message = self._build_commit_message(snapshot_id, level, reason, changed_paths)

                dvc_status = "skipped"
                if self._needs_dvc(changed_paths) and self.dvc.is_available() and self.dvc.is_initialized():
                    dvc_status = "handled"
                    self._dvc_add_paths(changed_paths)
                elif self._needs_dvc(changed_paths):
                    dvc_status = "skipped"

                self.git.add_all()
                git_commit = self.git.commit(message, allow_empty=True)

                tags = [f"pre-change/{snapshot_id}"]
                self.git.tag(tags[0])
                if level == "critical":
                    tags.append(f"stable/{snapshot_id}")
                    self.git.tag(tags[-1])

                if dvc_status == "handled" and self.dvc.is_available() and self.dvc.is_initialized():
                    if self.config["dvc"]["remote_optional"] and not self.dvc.has_remote():
                        dvc_status = "handled-no-remote"
                    else:
                        self.dvc.push()

                result = {
                    "snapshot_id": snapshot_id,
                    "git_commit": git_commit,
                    "tags": tags,
                    "changed_files_summary": changed_paths,
                    "dvc_status": dvc_status,
                }
                record = AuditRecord(
                    ts=now_ts(),
                    action="snapshot",
                    actor="clawbot",
                    args=args,
                    result=result,
                    status="ok",
                )
                audit_path = self.audit.write(record)
                result["audit_record_path"] = str(audit_path)
                result["summary"] = self.audit.human_summary(record)
                return result
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc)}
                record = AuditRecord(
                    ts=now_ts(),
                    action="snapshot",
                    actor="clawbot",
                    args=args,
                    result=result,
                    status="error",
                    error=str(exc),
                )
                self.audit.write(record)
                if isinstance(exc, TimeMachineError):
                    raise
                raise

    def list(self, filter: str = "all") -> dict[str, Any]:
        args = {"filter": filter}
        try:
            tags = self.git.tags()
            tag_map = self._tags_by_snapshot(tags)
            entries = self._collect_snapshots(tag_map)
            entries = self._filter_entries(entries, filter)
            limit = self.config["list_limit"]
            result = {"snapshots": entries[:limit]}
            record = AuditRecord(
                ts=now_ts(),
                action="list",
                actor="clawbot",
                args=args,
                result=result,
                status="ok",
            )
            audit_path = self.audit.write(record)
            result["audit_record_path"] = str(audit_path)
            result["summary"] = self.audit.human_summary(record)
            return result
        except Exception as exc:  # noqa: BLE001
            record = AuditRecord(
                ts=now_ts(),
                action="list",
                actor="clawbot",
                args=args,
                result={"error": str(exc)},
                status="error",
                error=str(exc),
            )
            self.audit.write(record)
            raise

    def diff(self, version_a: str, version_b: str) -> dict[str, Any]:
        args = {"version_a": version_a, "version_b": version_b}
        try:
            names = self.git.diff_names(version_a, version_b)
            key_changes = [p for p in names if p.split("/")[0] in {"config", "scripts", "policies"}]
            shortstat = self.git.diff_shortstat(version_a, version_b)
            numstat = self.git.diff_numstat(version_a, version_b)
            binary_files = [line.split("\t")[-1] for line in numstat if line.startswith("-\t-")]
            result = {
                "version_a": version_a,
                "version_b": version_b,
                "key_changes": key_changes,
                "summary": shortstat or "No differences.",
                "diff_stat": self.git.diff_stat(version_a, version_b),
                "binary_files": binary_files,
            }
            record = AuditRecord(
                ts=now_ts(),
                action="diff",
                actor="clawbot",
                args=args,
                result=result,
                status="ok",
            )
            audit_path = self.audit.write(record)
            result["audit_record_path"] = str(audit_path)
            result["summary_text"] = self.audit.human_summary(record)
            return result
        except Exception as exc:  # noqa: BLE001
            record = AuditRecord(
                ts=now_ts(),
                action="diff",
                actor="clawbot",
                args=args,
                result={"error": str(exc)},
                status="error",
                error=str(exc),
            )
            self.audit.write(record)
            raise

    def restore(self, version: str, verify: bool = True, force: bool = False) -> dict[str, Any]:
        args = {"version": version, "verify": verify, "force": force}
        with file_lock(self.lock_path):
            try:
                status_output = self.git.status()
                if status_output and not force:
                    raise DirtyWorkspaceError("Workspace is dirty. Run snapshot or set force=True.")

                self.git.checkout(version)
                dvc_status = "skipped"
                if self.dvc.is_available() and self.dvc.is_initialized():
                    self.dvc.checkout()
                    dvc_status = "handled"

                verification_result = {"skipped": True}
                if verify:
                    verifier = Verifier(
                        self.repo_path,
                        self.config["verification"]["required_paths"],
                        self.config["verification"]["healthcheck_cmd"],
                    )
                    verification_result = verifier.verify()

                result = {
                    "restored_to": version,
                    "git_commit": self.git.rev_parse("HEAD"),
                    "dvc_status": dvc_status,
                    "verification": verification_result,
                }
                record = AuditRecord(
                    ts=now_ts(),
                    action="restore",
                    actor="clawbot",
                    args=args,
                    result=result,
                    status="ok",
                )
                audit_path = self.audit.write(record)
                result["audit_record_path"] = str(audit_path)
                result["summary"] = self.audit.human_summary(record)
                return result
            except Exception as exc:  # noqa: BLE001
                record = AuditRecord(
                    ts=now_ts(),
                    action="restore",
                    actor="clawbot",
                    args=args,
                    result={"error": str(exc)},
                    status="error",
                    error=str(exc),
                )
                self.audit.write(record)
                raise

    def _load_config(self) -> dict[str, Any]:
        config_path = self.repo_path / "skills" / "time_machine" / "config.yaml"
        if not config_path.exists():
            config_path = Path(__file__).parent / "config.yaml"
        with config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _parse_changed_paths(self, status_output: str) -> list[str]:
        paths = []
        for line in status_output.splitlines():
            if not line:
                continue
            path = line[3:]
            if "->" in path:
                path = path.split("->")[-1].strip()
            paths.append(path)
        return sorted(set(paths))

    def _protected_paths_touched(self, changed_paths: list[str]) -> set[str]:
        protected = set(self.config["protected_paths"])
        return {path for path in changed_paths if path.split("/")[0] in protected}

    def _build_commit_message(
        self,
        snapshot_id: str,
        level: str,
        reason: str | None,
        changed_paths: list[str],
    ) -> str:
        risk_note = self.config["risk_levels"].get(level, "")
        reason_text = reason or "No reason provided"
        body = {
            "reason": reason_text,
            "changed_paths": changed_paths,
            "risk": risk_note,
        }
        return (
            f"TimeMachine snapshot {snapshot_id} [{level}]\n\n"
            f"{json.dumps(body, ensure_ascii=False)}"
        )

    def _needs_dvc(self, changed_paths: list[str]) -> bool:
        return any(path.split("/")[0] in {"models", "data_snapshots"} for path in changed_paths)

    def _dvc_add_paths(self, changed_paths: list[str]) -> None:
        for root in {"models", "data_snapshots"}:
            if any(path.startswith(root) for path in changed_paths):
                target = self.repo_path / root
                if target.exists():
                    self.dvc.add(target)

    def _tags_by_snapshot(self, tags: list[str]) -> dict[str, list[str]]:
        tag_map: dict[str, list[str]] = {}
        for tag in tags:
            if "/" not in tag:
                continue
            prefix, snapshot_id = tag.split("/", 1)
            tag_map.setdefault(snapshot_id, []).append(tag)
        return tag_map

    def _collect_snapshots(self, tag_map: dict[str, list[str]]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        log_output = self.git.log(self.config["list_limit"] * 2)
        records = log_output.split("\x1e")
        for record in records:
            if not record.strip():
                continue
            commit_hash, message = record.split("\x1f", 1)
            if not message.startswith("TimeMachine snapshot"):
                continue
            header, _, body = message.partition("\n\n")
            snapshot_id = header.split()[2]
            level = header.split("[")[-1].rstrip("]")
            reason = None
            if body:
                try:
                    payload = json.loads(body)
                    reason = payload.get("reason")
                except json.JSONDecodeError:
                    reason = None
            entry = {
                "snapshot_id": snapshot_id,
                "time": snapshot_id.split("-")[0],
                "level": level,
                "reason": reason,
                "tags": tag_map.get(snapshot_id, []),
                "git_commit": commit_hash,
            }
            entries.append(entry)
        return entries

    def _filter_entries(self, entries: list[dict[str, Any]], filter: str) -> list[dict[str, Any]]:
        if filter == "all":
            return entries
        if filter in {"stable", "pre-change", "experiment"}:
            return [
                entry
                for entry in entries
                if any(tag.startswith(f"{filter}/") for tag in entry.get("tags", []))
            ]
        return entries

"""Demo runner for the time_machine skill."""

from __future__ import annotations

import argparse
import json

from skills.time_machine import TimeMachine


def main() -> None:
    parser = argparse.ArgumentParser(description="Time Machine demo runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--reason", default=None)
    snapshot_parser.add_argument("--level", default="normal", choices=["normal", "high", "critical"])

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--filter", default="all", choices=["all", "stable", "pre-change", "experiment"])

    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("--a", required=True)
    diff_parser.add_argument("--b", required=True)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--version", required=True)
    restore_parser.add_argument("--verify", action="store_true")
    restore_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    tm = TimeMachine()

    if args.command == "snapshot":
        result = tm.snapshot(reason=args.reason, level=args.level)
    elif args.command == "list":
        result = tm.list(filter=args.filter)
    elif args.command == "diff":
        result = tm.diff(args.a, args.b)
    elif args.command == "restore":
        result = tm.restore(args.version, verify=args.verify, force=args.force)
    else:
        raise SystemExit("Unknown command")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

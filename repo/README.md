# Time Machine Skill

`time_machine` is a built-in skill for `clawbot` that provides system-level versioning, snapshotting, rollback, and audit capabilities.
It uses Git for text-based assets and DVC for large files such as models and data snapshots.

## Directory Structure

```
repo/
  skills/
    time_machine/
      __init__.py
      skill.yaml
      config.yaml
      tm.py
      git_backend.py
      dvc_backend.py
      audit.py
      verifier.py
      errors.py
      utils.py
      audit_logs/
  demo/
    demo_runner.py
  tests/
    test_snapshot.py
    test_restore.py
    test_diff.py
    test_list.py
    fixtures/
      sample_repo/
  README.md
  pyproject.toml
```

## Installation

```bash
pip install -e .
```

Initialize Git and (optionally) DVC in your target repo:

```bash
git init
# optional
# dvc init
```

## Usage

Demo runner simulates `clawbot` invoking the skill:

```bash
python demo/demo_runner.py snapshot --reason "upgrade config" --level high
python demo/demo_runner.py list
python demo/demo_runner.py diff --a stable/20240101-010101-abcd --b pre-change/20240102-020202-efgh
python demo/demo_runner.py restore --version stable/20240101-010101-abcd --verify
```

## Configuration

Default settings live in `skills/time_machine/config.yaml` and include:
- Tracked paths and protected paths.
- Risk level text.
- Verification requirements and optional healthcheck.
- DVC enablement and remote optional settings.

## Testing

```bash
pytest
```

"""Tests for pactfix CLI.

These tests avoid modifying the real repo examples/ by using PACTFIX_EXAMPLES_DIR.
"""

import json
import os
import subprocess
from pathlib import Path


def _run_cli(args, cwd, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    cmd = ["python", "-m", "pactfix"] + args
    proc = subprocess.run(cmd, cwd=str(cwd), env=merged_env, capture_output=True, text=True)
    return proc


def test_cli_json_output(tmp_path):
    sample = tmp_path / "test.sql"
    sample.write_text("SELECT * FROM users", encoding="utf-8")

    proc = _run_cli([str(sample), "--json"], cwd=Path(__file__).resolve().parents[1])
    assert proc.returncode == 0

    data = json.loads(proc.stdout)
    assert data["language"] == "sql"
    assert any(w["code"] == "SQL001" for w in data["warnings"])


def test_cli_fix_all_uses_env_examples_dir(tmp_path):
    # Create fake examples structure
    examples = tmp_path / "examples"
    (examples / "bash").mkdir(parents=True)
    (examples / "bash" / "faulty.sh").write_text("#!/bin/bash\ncd /tmp", encoding="utf-8")

    env = {"PACTFIX_EXAMPLES_DIR": str(examples)}
    proc = _run_cli(["--fix-all"], cwd=Path(__file__).resolve().parents[1], env=env)
    assert proc.returncode == 0

    fixed = examples / "bash" / "fixed" / "fixed_faulty.sh"
    assert fixed.exists()
    assert "cd /tmp" in fixed.read_text(encoding="utf-8")

    summary = examples / "fix_summary.json"
    assert summary.exists()
    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_data["total_files"] >= 1

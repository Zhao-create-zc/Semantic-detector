import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_jsonl_schema.py"
SCHEMA = ROOT / "schemas" / "message.schema.json"


def test_schema_cli_accepts_repository_example_messages():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(SCHEMA), str(ROOT / "examples" / "messages.jsonl")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "schema validation passed" in result.stdout


def test_schema_cli_rejects_invalid_record(tmp_path):
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text(json.dumps({"message_id": "x"}) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(SCHEMA), str(invalid)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "schema validation failed" in result.stderr

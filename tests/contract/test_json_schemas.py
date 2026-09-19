import json
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def test_all_public_schemas_are_valid_draft_2020_12():
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_example_messages_match_public_schema():
    schema = _load("message.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for record in _jsonl(ROOT / "examples" / "messages.jsonl"):
        validator.validate(record)


def test_example_ground_truth_matches_public_schema():
    schema = _load("ground_truth.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for record in _jsonl(ROOT / "examples" / "ground_truth.jsonl"):
        validator.validate(record)


def test_prediction_schema_accepts_export_shape():
    schema = _load("semantic_prediction.schema.json")
    sample = {
        "run_id": "run-1",
        "layout_id": "example",
        "direction": "request",
        "field_index": 0,
        "coarse_label": "length",
        "fine_label": "total_message_length",
        "confidence": 1.0,
        "abstained": False,
        "prediction_status": "confirmed",
        "evidence": [{
            "detector": "length",
            "coarse_label": "length",
            "fine_label": "total_message_length",
            "is_hard_evidence": True,
            "score": 1.0,
            "reason_code": "exact_relation",
            "details": {"support": 1.0},
        }],
        "alternatives": [],
    }
    Draft202012Validator(schema).validate(sample)


def test_benchmark_manifest_template_matches_schema():
    schema = _load("benchmark_manifest.schema.json")
    manifest = json.loads((ROOT / "benchmarks" / "manifest.example.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)

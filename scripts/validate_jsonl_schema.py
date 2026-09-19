"""Validate each non-empty JSONL record against a JSON Schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("jsonl", type=Path)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    failures = 0
    checked = 0
    for line_number, line in enumerate(args.jsonl.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        checked += 1
        try:
            record = json.loads(line)
            validator.validate(record)
        except Exception as exc:  # report parse + schema failures uniformly for CLI use
            failures += 1
            print(f"{args.jsonl}:{line_number}: {exc}", file=sys.stderr)

    if failures:
        print(f"schema validation failed: {failures}/{checked} records", file=sys.stderr)
        return 1
    print(f"schema validation passed: {checked} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

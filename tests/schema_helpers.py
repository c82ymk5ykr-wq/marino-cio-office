"""Shared helpers for public contract schema tests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
FORMAT_CHECKER = FormatChecker()


def load_json(path: str) -> object:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def validator_for(path: str) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def validator_for_schema(schema: object) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)

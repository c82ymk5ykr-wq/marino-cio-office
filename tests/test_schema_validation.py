"""Focused tests for public JSON Schema enforcement."""

from __future__ import annotations

import copy
import json
import unittest
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


class SchemaValidationTests(unittest.TestCase):
    def assert_rejected(
        self, validator: Draft202012Validator, instance: object, keyword: str
    ) -> None:
        errors = list(validator.iter_errors(instance))
        self.assertTrue(errors, "the deliberately invalid instance was accepted")
        self.assertIn(keyword, {error.validator for error in errors})

    def test_missing_required_report_field_is_rejected(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        del instance["status_reason"]
        self.assert_rejected(validator, instance, "required")

    def test_invalid_report_status_is_rejected(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["status"] = "synthetic-unknown-status"
        self.assert_rejected(validator, instance, "enum")

    def test_complete_report_with_stale_freshness_is_rejected(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["status"] = "complete"
        instance["coverage"] = {
            "universe": "one fictional candidate",
            "expected": 1,
            "observed": 1,
            "percent": 100.0,
            "gaps": [],
        }
        instance["freshness"]["status"] = "stale"
        instance["artifact"] = {
            "status": "persisted",
            "note": "Synthetic persistence outcome only.",
        }
        self.assert_rejected(validator, instance, "const")

    def test_invalid_idea_timestamp_is_rejected(self) -> None:
        validator = validator_for("schemas/v1/investment-idea.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/investment-idea.json"))
        instance["last_seen_at"] = "not-a-date-time"
        self.assert_rejected(validator, instance, "format")

    def test_extra_decision_property_is_rejected(self) -> None:
        validator = validator_for("schemas/v1/decision-record.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/decision-record.json"))
        instance["synthetic_extra"] = True
        self.assert_rejected(validator, instance, "additionalProperties")


if __name__ == "__main__":
    unittest.main()

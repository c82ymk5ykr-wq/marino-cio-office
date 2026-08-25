"""Focused tests for public JSON Schema enforcement."""

from __future__ import annotations

import copy
import unittest

from jsonschema import Draft202012Validator

from schema_helpers import load_json, validator_for


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

    def test_report_v11_requires_gate_inputs(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        del instance["gate_inputs"]
        self.assert_rejected(validator, instance, "required")

    def test_persisted_report_v11_requires_receipt(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["artifact"] = {
            "status": "persisted",
            "note": "Deliberately incomplete fictional persistence claim.",
        }
        self.assert_rejected(validator, instance, "required")

    def test_url_or_path_is_not_a_v11_receipt(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        references = [
            " ",
            "/tmp/report.pdf",
            "../reports/output.pdf",
            "C:\\temp\\report.pdf",
            "s3://private-bucket/report",
            " HTTPS://example.invalid/temporary",
            "ABCDEFGH\n",
        ]
        for reference in references:
            instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
            instance["artifact"] = {
                "status": "persisted",
                "durable_reference": reference,
                "persisted_at": "2026-01-15T14:06:00Z",
                "note": "Deliberately invalid fictional reference.",
            }
            with self.subTest(reference=reference):
                self.assert_rejected(validator, instance, "pattern")

    def test_unknown_required_period_lag_omits_count(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["gate_inputs"]["required_period_lag_known"] = False
        del instance["gate_inputs"]["required_period_lag"]
        self.assertEqual([], list(validator.iter_errors(instance)))

        instance["gate_inputs"]["required_period_lag"] = 0
        self.assert_rejected(validator, instance, "not")

    def test_v11_timestamp_requires_utc_z(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        invalid_times = [
            "2026-01-15T14:05:00+00:00",
            "2026-01-15T14:05:00Z\n",
        ]
        for value in invalid_times:
            instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
            instance["generated_at"] = value
            with self.subTest(value=value):
                self.assert_rejected(validator, instance, "pattern")

    def test_unknown_denominator_uses_zero_sentinel_and_omits_known_fields(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["gate_inputs"]["denominator_known"] = False

        keywords = {error.validator for error in validator.iter_errors(instance)}
        self.assertIn("not", keywords)
        self.assertIn("const", keywords)

        instance["status"] = "provisional"
        instance["coverage"] = {
            "universe": "unknown fictional population",
            "expected": 0,
            "observed": 0,
            "percent": 0.0,
            "gaps": [],
        }
        del instance["gate_inputs"]["membership_as_of"]
        del instance["gate_inputs"]["gap_count"]
        instance["quality_flags"] = ["COVERAGE_DENOMINATOR_UNKNOWN"]
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_v11_gap_count_requires_coherent_public_descriptions(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))

        zero_with_descriptions = copy.deepcopy(instance)
        zero_with_descriptions["gate_inputs"]["gap_count"] = 0
        self.assert_rejected(validator, zero_with_descriptions, "maxItems")

        positive_without_descriptions = copy.deepcopy(instance)
        positive_without_descriptions["coverage"]["gaps"] = []
        self.assert_rejected(validator, positive_without_descriptions, "minItems")

    def test_complete_v11_rejects_blocking_flag_and_zero_observed(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        corpus = load_json("tests/compatibility/v1-fixtures.json")
        fixture = next(
            fixture["instance"]
            for fixture in corpus["contracts"]["report-manifest"]["fixtures"]
            if fixture["fixture_id"] == "report-manifest-1.1.0-complete"
        )

        blocking_flag = copy.deepcopy(fixture)
        blocking_flag["quality_flags"] = ["INCOMPLETE_COVERAGE"]
        self.assert_rejected(validator, blocking_flag, "not")

        zero_observed = copy.deepcopy(fixture)
        zero_observed["coverage"]["observed"] = 0
        self.assert_rejected(validator, zero_observed, "minimum")

    def test_v11_gate_identifiers_and_notes_are_not_whitespace(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        corpus = load_json("tests/compatibility/v1-fixtures.json")
        fixture = next(
            fixture["instance"]
            for fixture in corpus["contracts"]["report-manifest"]["fixtures"]
            if fixture["fixture_id"] == "report-manifest-1.1.0-complete"
        )

        cases = []
        required_period = copy.deepcopy(fixture)
        required_period["gate_inputs"]["required_period"] = " "
        cases.append(required_period)

        source_identifier = copy.deepcopy(fixture)
        source_identifier["sources"][0]["source_id"] = " "
        for role in source_identifier["gate_inputs"]["source_roles"]:
            role["source_ids"] = [" "]
        cases.append(source_identifier)

        disclosure_note = copy.deepcopy(fixture)
        disclosure_note["gate_inputs"]["source_roles"][0]["note"] = "\t"
        cases.append(disclosure_note)

        status_reason = copy.deepcopy(fixture)
        status_reason["status_reason"] = "\n"
        cases.append(status_reason)

        gap_description = copy.deepcopy(
            load_json("examples/synthetic/report-manifest.json")
        )
        gap_description["coverage"]["gaps"] = [" "]
        cases.append(gap_description)

        for index, instance in enumerate(cases):
            with self.subTest(case=index):
                self.assert_rejected(validator, instance, "pattern")

    def test_unavailable_report_v11_source_omits_evidence_times(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["sources"][0]["status"] = "unavailable"
        self.assert_rejected(validator, instance, "not")

    def test_unknown_report_v11_freshness_omits_material_time(self) -> None:
        validator = validator_for("schemas/v1/report-manifest.schema.json")
        instance = copy.deepcopy(load_json("examples/synthetic/report-manifest.json"))
        instance["freshness"]["status"] = "unknown"
        self.assert_rejected(validator, instance, "not")

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

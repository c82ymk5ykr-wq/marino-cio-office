"""Tests for deterministic public report-acceptance status derivation."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from schema_helpers import load_json, validator_for
from scripts.validate import (
    derive_report_acceptance_status,
    materialize_report_acceptance_case,
    validate_report_acceptance_cases,
    validate_report_acceptance_input_shape,
    validate_report_manifest_acceptance,
)


class ReportAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.truth_table = load_json(
            "examples/synthetic/report-acceptance-cases.json"
        )
        corpus = load_json("tests/compatibility/v1-fixtures.json")
        fixtures = corpus["contracts"]["report-manifest"]["fixtures"]
        cls.complete_manifest = next(
            fixture["instance"]
            for fixture in fixtures
            if fixture["fixture_id"] == "report-manifest-1.1.0-complete"
        )
        cls.manifest_validator = validator_for(
            "schemas/v1/report-manifest.schema.json"
        )

    def assert_manifest_valid(self, report: object) -> None:
        self.assertEqual([], list(self.manifest_validator.iter_errors(report)))
        errors: list[str] = []
        validate_report_manifest_acceptance(
            report, Path("synthetic-full-manifest.json"), errors
        )
        self.assertEqual([], errors)

    def manifest_errors(self, report: object) -> list[str]:
        errors: list[str] = []
        validate_report_manifest_acceptance(
            report, Path("synthetic-full-manifest.json"), errors
        )
        return errors

    def test_truth_table_is_self_consistent(self) -> None:
        errors: list[str] = []
        validate_report_acceptance_cases(self.truth_table, errors)
        self.assertEqual([], errors)

    def test_valid_cases_cover_every_report_status(self) -> None:
        defaults = self.truth_table["defaults"]
        statuses = set()
        for case in self.truth_table["cases"]:
            if case["expect_valid"]:
                inputs = materialize_report_acceptance_case(defaults, case)
                status, _ = derive_report_acceptance_status(inputs)
                statuses.add(status)
        self.assertEqual({"complete", "provisional", "degraded", "failed"}, statuses)

    def test_no_reliable_product_has_highest_precedence(self) -> None:
        inputs = copy.deepcopy(self.truth_table["defaults"])
        inputs.update(
            {
                "reliable_product": False,
                "required_source_states": [
                    "unavailable",
                    "non_equivalent_fallback",
                    "stale",
                ],
                "artifact_status": "failed",
                "durable_receipt_present": False,
            }
        )
        status, flags = derive_report_acceptance_status(inputs)
        self.assertEqual("failed", status)
        self.assertIn("NO_RELIABLE_DECISION_PRODUCT", flags)
        self.assertIn("DURABLE_PERSISTENCE_FAILED", flags)

    def test_optional_source_failure_does_not_change_status(self) -> None:
        inputs = copy.deepcopy(self.truth_table["defaults"])
        inputs["optional_source_state"] = "unavailable"
        status, flags = derive_report_acceptance_status(inputs)
        self.assertEqual("complete", status)
        self.assertIn("OPTIONAL_SOURCE_UNAVAILABLE", flags)

    def test_unknown_required_period_lag_is_provisional(self) -> None:
        inputs = copy.deepcopy(self.truth_table["defaults"])
        inputs["required_period_lag_known"] = False
        inputs["required_period_lag"] = None
        status, flags = derive_report_acceptance_status(inputs)
        self.assertEqual("provisional", status)
        self.assertIn("REQUIRED_PERIOD_UNKNOWN", flags)

    def test_non_finite_numbers_are_contract_invalid(self) -> None:
        cases = [
            ("percent", float("nan")),
            ("freshness_age_hours", float("nan")),
            ("freshness_threshold_hours", float("inf")),
        ]
        for field, value in cases:
            inputs = copy.deepcopy(self.truth_table["defaults"])
            inputs[field] = value
            errors: list[str] = []
            validate_report_acceptance_input_shape(inputs, "synthetic", errors)
            with self.subTest(field=field):
                self.assertTrue(errors)

    def test_extreme_legal_integers_do_not_crash_validation(self) -> None:
        huge = 10**4000
        cases = [
            ("percent", huge),
            ("freshness_threshold_hours", huge),
            ("observed", huge),
        ]
        for field, value in cases:
            inputs = copy.deepcopy(self.truth_table["defaults"])
            inputs[field] = value
            errors: list[str] = []
            validate_report_acceptance_input_shape(inputs, "synthetic", errors)
            with self.subTest(field=field):
                self.assertIsInstance(errors, list)

    def test_full_manifests_cover_status_and_gate_branches(self) -> None:
        complete = copy.deepcopy(self.complete_manifest)

        equivalent_fallback = copy.deepcopy(complete)
        equivalent_fallback["sources"][0]["status"] = "fallback"
        for role in equivalent_fallback["gate_inputs"]["source_roles"]:
            role["state"] = "equivalent_fallback"
        equivalent_fallback["quality_flags"] = ["EQUIVALENT_FALLBACK_USED"]

        unknown_lag = copy.deepcopy(complete)
        unknown_lag["status"] = "provisional"
        unknown_lag["status_reason"] = "Fictional required-period lag is unknown."
        unknown_lag["gate_inputs"]["required_period_lag_known"] = False
        del unknown_lag["gate_inputs"]["required_period_lag"]
        unknown_lag["quality_flags"] = ["REQUIRED_PERIOD_UNKNOWN"]

        unknown_denominator = copy.deepcopy(complete)
        unknown_denominator["status"] = "provisional"
        unknown_denominator["status_reason"] = "Fictional denominator is unknown."
        unknown_denominator["coverage"] = {
            "universe": "unknown fictional population",
            "expected": 0,
            "observed": 0,
            "percent": 0.0,
            "gaps": [],
        }
        unknown_denominator["gate_inputs"]["denominator_known"] = False
        del unknown_denominator["gate_inputs"]["membership_as_of"]
        del unknown_denominator["gate_inputs"]["gap_count"]
        unknown_denominator["quality_flags"] = ["COVERAGE_DENOMINATOR_UNKNOWN"]

        not_attempted = copy.deepcopy(complete)
        not_attempted["status"] = "provisional"
        not_attempted["status_reason"] = "Fictional persistence was not attempted."
        not_attempted["artifact"] = {
            "status": "not_attempted",
            "note": "Fictional not-attempted persistence branch.",
        }
        not_attempted["quality_flags"] = ["DURABLE_PERSISTENCE_NOT_ATTEMPTED"]

        unavailable_freshness = copy.deepcopy(complete)
        unavailable_freshness["sources"].append(
            {
                "source_id": "SYNTH-COMPAT-UNAVAILABLE-110",
                "category": "market",
                "provenance": "INLINE",
                "checked_at": "2026-01-15T14:02:00Z",
                "status": "unavailable",
                "note": "Fictional unavailable freshness source only.",
            }
        )
        freshness_role = next(
            role
            for role in unavailable_freshness["gate_inputs"]["source_roles"]
            if role["role"] == "freshness_reference"
        )
        freshness_role["state"] = "unavailable"
        freshness_role["source_ids"] = ["SYNTH-COMPAT-UNAVAILABLE-110"]
        unavailable_freshness["freshness"] = {
            "status": "unknown",
            "threshold_hours": 24,
        }
        unavailable_freshness["status"] = "degraded"
        unavailable_freshness["status_reason"] = (
            "Fictional freshness reference is unavailable."
        )
        unavailable_freshness["quality_flags"] = [
            "FRESHNESS_UNKNOWN",
            "REQUIRED_SOURCE_UNAVAILABLE",
        ]

        unavailable_freshness_with_stale_role = copy.deepcopy(
            unavailable_freshness
        )
        unavailable_freshness_with_stale_role["sources"][0]["status"] = "stale"
        for role in unavailable_freshness_with_stale_role["gate_inputs"][
            "source_roles"
        ][:2]:
            role["state"] = "stale"
        unavailable_freshness_with_stale_role["quality_flags"].append(
            "REQUIRED_SOURCE_STALE"
        )

        persistence_failed = copy.deepcopy(complete)
        persistence_failed["status"] = "degraded"
        persistence_failed["status_reason"] = "Fictional persistence failed."
        persistence_failed["artifact"] = {
            "status": "failed",
            "note": "Fictional failed-persistence branch.",
        }
        persistence_failed["quality_flags"] = ["DURABLE_PERSISTENCE_FAILED"]

        failed = copy.deepcopy(complete)
        failed["status"] = "failed"
        failed["status_reason"] = "No reliable fictional decision product exists."
        failed["gate_inputs"]["reliable_product"] = False
        failed["quality_flags"] = ["NO_RELIABLE_DECISION_PRODUCT"]

        cases = {
            "complete": complete,
            "equivalent_fallback": equivalent_fallback,
            "unknown_lag": unknown_lag,
            "unknown_denominator": unknown_denominator,
            "not_attempted": not_attempted,
            "unavailable_freshness": unavailable_freshness,
            "unavailable_freshness_with_stale_role": unavailable_freshness_with_stale_role,
            "persistence_failed": persistence_failed,
            "failed": failed,
        }
        for name, report in cases.items():
            with self.subTest(case=name):
                self.assert_manifest_valid(report)

    def test_manifest_rejects_dangling_required_source_join(self) -> None:
        report = copy.deepcopy(
            load_json("examples/synthetic/report-manifest.json")
        )
        report["gate_inputs"]["source_roles"][0]["source_ids"] = [
            "SYNTHETIC-MISSING-SOURCE"
        ]
        errors: list[str] = []
        validate_report_manifest_acceptance(
            report, Path("examples/synthetic/report-manifest.json"), errors
        )
        self.assertTrue(any("dangling source_id" in error for error in errors))

    def test_manifest_rejects_duplicate_source_ids(self) -> None:
        report = copy.deepcopy(self.complete_manifest)
        report["sources"].append(copy.deepcopy(report["sources"][0]))
        errors = self.manifest_errors(report)
        self.assertTrue(any("duplicate source ID" in error for error in errors))

    def test_manifest_rejects_mixed_statuses_linked_to_one_role(self) -> None:
        report = copy.deepcopy(self.complete_manifest)
        report["sources"].append(
            {
                "source_id": "SYNTH-MIXED-UNAVAILABLE",
                "category": "market",
                "provenance": "INLINE",
                "checked_at": "2026-01-15T14:02:00Z",
                "status": "unavailable",
                "note": "Fictional conflicting role evidence.",
            }
        )
        report["gate_inputs"]["source_roles"][0]["source_ids"].append(
            "SYNTH-MIXED-UNAVAILABLE"
        )
        errors = self.manifest_errors(report)
        self.assertTrue(any("every linked source" in error for error in errors))

    def test_manifest_reconciles_gap_count_and_public_descriptions(self) -> None:
        zero_with_description = copy.deepcopy(self.complete_manifest)
        zero_with_description["coverage"]["gaps"] = [
            "Contradictory fictional gap description."
        ]
        self.assertTrue(
            any(
                "zero gap_count requires" in error
                for error in self.manifest_errors(zero_with_description)
            )
        )

        positive_without_description = copy.deepcopy(self.complete_manifest)
        positive_without_description["status"] = "provisional"
        positive_without_description["coverage"].update(
            {"expected": 2, "observed": 1, "percent": 50.0, "gaps": []}
        )
        positive_without_description["gate_inputs"]["gap_count"] = 1
        positive_without_description["quality_flags"] = ["INCOMPLETE_COVERAGE"]
        self.assertTrue(
            any(
                "positive gap_count requires" in error
                for error in self.manifest_errors(positive_without_description)
            )
        )

        whitespace_description = copy.deepcopy(positive_without_description)
        whitespace_description["coverage"]["gaps"] = [" "]
        self.assertTrue(
            any(
                "descriptions must contain" in error
                for error in self.manifest_errors(whitespace_description)
            )
        )

    def test_manifest_rejects_unreconciled_material_freshness(self) -> None:
        report = copy.deepcopy(self.complete_manifest)
        report["sources"][0]["data_as_of"] = "2026-01-10T14:00:00Z"
        errors = self.manifest_errors(report)
        self.assertTrue(any("earliest required-role source" in error for error in errors))

    def test_manifest_rejects_future_source_clocks(self) -> None:
        cases = {
            "source cutoff": ("data_as_of", "2026-01-15T14:03:00Z"),
            "retrieval": ("retrieved_at", "2026-01-15T14:06:00Z"),
            "check": ("checked_at", "2026-01-15T14:06:00Z"),
        }
        for name, (field, value) in cases.items():
            report = copy.deepcopy(self.complete_manifest)
            report["sources"][0][field] = value
            errors = self.manifest_errors(report)
            with self.subTest(case=name):
                self.assertTrue(any("cannot be after" in error for error in errors))

    def test_manifest_rejects_path_like_receipts(self) -> None:
        references = [
            " ",
            "/tmp/report.pdf",
            "../reports/output.pdf",
            "C:\\temp\\report.pdf",
            "s3://private-bucket/report",
            " HTTPS://example.invalid/report",
        ]
        for reference in references:
            report = copy.deepcopy(self.complete_manifest)
            report["artifact"]["durable_reference"] = reference
            errors = self.manifest_errors(report)
            with self.subTest(reference=reference):
                self.assertTrue(any("opaque receipt" in error for error in errors))

    def test_malformed_manifest_is_rejected_without_crashing(self) -> None:
        malformed_status = copy.deepcopy(self.complete_manifest)
        malformed_status["sources"][0]["status"] = {"not": "a status"}
        self.assertTrue(
            any("invalid status" in error for error in self.manifest_errors(malformed_status))
        )

        malformed_time = copy.deepcopy(self.complete_manifest)
        malformed_time["generated_at"] = "2026-01-15Z"
        self.assertTrue(
            any("invalid UTC timestamp" in error for error in self.manifest_errors(malformed_time))
        )

        malformed_freshness = copy.deepcopy(self.complete_manifest)
        malformed_freshness["freshness"]["status"] = {"not": "freshness"}
        self.assertTrue(
            any("freshness_status: invalid" in error for error in self.manifest_errors(malformed_freshness))
        )

        malformed_artifact = copy.deepcopy(self.complete_manifest)
        malformed_artifact["artifact"]["status"] = {"not": "persistence"}
        self.assertTrue(
            any("artifact_status: invalid" in error for error in self.manifest_errors(malformed_artifact))
        )

        whitespace_gate = copy.deepcopy(self.complete_manifest)
        whitespace_gate["gate_inputs"]["required_period"] = " "
        self.assertTrue(
            any("required_period" in error for error in self.manifest_errors(whitespace_gate))
        )

        whitespace_reason = copy.deepcopy(self.complete_manifest)
        whitespace_reason["status_reason"] = "\t"
        self.assertTrue(
            any("status_reason" in error for error in self.manifest_errors(whitespace_reason))
        )

        whitespace_source = copy.deepcopy(self.complete_manifest)
        whitespace_source["sources"][0]["source_id"] = " "
        for role in whitespace_source["gate_inputs"]["source_roles"]:
            role["source_ids"] = [" "]
        self.assertTrue(
            any("non-whitespace" in error for error in self.manifest_errors(whitespace_source))
        )

    def test_complete_v11_compatibility_manifest_passes_semantic_gate(self) -> None:
        corpus = load_json("tests/compatibility/v1-fixtures.json")
        fixtures = corpus["contracts"]["report-manifest"]["fixtures"]
        report = next(
            fixture["instance"]
            for fixture in fixtures
            if fixture["fixture_id"] == "report-manifest-1.1.0-complete"
        )
        errors: list[str] = []
        validate_report_manifest_acceptance(
            report, Path("tests/compatibility/v1-fixtures.json"), errors
        )
        self.assertEqual([], errors)

    def test_manifest_rejects_fresh_label_beyond_threshold(self) -> None:
        report = copy.deepcopy(
            load_json("examples/synthetic/report-manifest.json")
        )
        report["freshness"]["status"] = "fresh"
        errors: list[str] = []
        validate_report_manifest_acceptance(
            report, Path("examples/synthetic/report-manifest.json"), errors
        )
        self.assertTrue(
            any("fresh label exceeds its declared threshold" in error for error in errors)
        )

    def test_integer_and_float_thresholds_have_identical_exact_boundary(self) -> None:
        boundary_time = "2026-01-14T14:05:00Z"
        for threshold in (24, 24.0):
            report = copy.deepcopy(self.complete_manifest)
            report["sources"][0]["data_as_of"] = boundary_time
            report["freshness"]["oldest_material_source_as_of"] = boundary_time
            report["freshness"]["threshold_hours"] = threshold
            with self.subTest(threshold=threshold):
                self.assert_manifest_valid(report)

        over_boundary = copy.deepcopy(self.complete_manifest)
        over_boundary_time = "2026-01-14T14:04:59.999999Z"
        over_boundary["sources"][0]["data_as_of"] = over_boundary_time
        over_boundary["freshness"]["oldest_material_source_as_of"] = (
            over_boundary_time
        )
        errors = self.manifest_errors(over_boundary)
        self.assertTrue(
            any("fresh label exceeds its declared threshold" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()

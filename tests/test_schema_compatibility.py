"""Executable backward-compatibility gate for the public v1 contracts."""

from __future__ import annotations

import copy
import unittest

from schema_helpers import load_json, validator_for, validator_for_schema


CORPUS_PATH = "tests/compatibility/v1-fixtures.json"

ENUM_CASES = [
    (
        "report-manifest",
        "report-manifest-1.0.0-complete",
        ("report_type",),
        ["daily_decision_report", "ad_hoc_decision_report", "system_quality_report"],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-complete",
        ("status",),
        ["complete", "provisional", "degraded", "failed"],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-provisional",
        ("freshness", "status"),
        ["fresh", "stale", "unknown"],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-provisional",
        ("sources", 0, "category"),
        [
            "market",
            "macro",
            "fundamental",
            "technical",
            "positioning",
            "news",
            "risk",
            "internal",
        ],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-provisional",
        ("sources", 0, "provenance"),
        ["PASTED", "INLINE", "CIO_LEVEL_INFERENCE"],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-provisional",
        ("sources", 0, "status"),
        ["available", "fallback", "stale", "unavailable"],
    ),
    (
        "report-manifest",
        "report-manifest-1.0.0-provisional",
        ("artifact", "status"),
        ["persisted", "failed", "not_attempted"],
    ),
    (
        "investment-idea",
        "investment-idea-1.0.0",
        ("board",),
        [
            "FRESH_IDEA_DISCOVERY",
            "CORE_CONVICTION_MONITOR",
            "REJECTED_IDEA_BOARD",
        ],
    ),
    (
        "investment-idea",
        "investment-idea-1.0.0",
        ("research_state",),
        ["candidate", "advance", "monitor", "hold", "reject", "archive"],
    ),
    (
        "investment-idea",
        "investment-idea-1.0.0",
        ("asset", "asset_type"),
        [
            "equity",
            "etf",
            "closed_end_fund",
            "fixed_income",
            "commodity",
            "currency",
            "other",
        ],
    ),
    (
        "investment-idea",
        "investment-idea-1.0.0",
        ("confidence",),
        ["low", "medium", "high"],
    ),
    (
        "investment-idea",
        "investment-idea-1.0.0",
        ("evidence", 0, "provenance"),
        ["PASTED", "INLINE", "CIO_LEVEL_INFERENCE"],
    ),
    (
        "investment-idea",
        "investment-idea-1.1.0-materially-updated",
        ("lineage", "changed_dimensions"),
        [
            ["thesis"],
            ["evidence"],
            ["catalysts"],
            ["risks"],
            ["invalidation_conditions"],
            ["research_state"],
        ],
    ),
    (
        "decision-record",
        "decision-record-1.0.0",
        ("research_disposition",),
        ["advance", "monitor", "hold", "reject"],
    ),
    (
        "decision-record",
        "decision-record-1.0.0",
        ("deployment", "readiness"),
        ["not_ready", "ready", "blocked"],
    ),
    (
        "decision-record",
        "decision-record-1.0.0",
        ("deployment", "action"),
        ["no_action", "initiate", "add", "trim", "exit"],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("research_outcome",),
        ["favorable", "mixed", "adverse", "indeterminate", "not_applicable"],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("decision_quality",),
        ["well_supported", "mixed_support", "weakly_supported"],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("process_quality",),
        ["disciplined", "mixed", "undisciplined"],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("timing_discipline",),
        [
            "followed",
            "partially_followed",
            "not_followed",
            "not_applicable",
        ],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("attribution", 0, "category"),
        [
            "thesis",
            "evidence",
            "catalyst",
            "regime",
            "timing",
            "risk",
            "invalidation",
            "process",
            "other",
        ],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("attribution", 0, "direction"),
        ["supporting", "detracting", "mixed", "neutral", "unknown"],
    ),
    (
        "outcome-review",
        "outcome-review-1.0.0-assessable",
        ("attribution", 0, "confidence"),
        ["low", "medium", "high"],
    ),
]


def set_path(instance: object, path: tuple[object, ...], value: object) -> None:
    current = instance
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


class SchemaCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_json(CORPUS_PATH)
        cls.contracts = cls.corpus["contracts"]

    def fixture(self, contract_name: str, fixture_id: str) -> object:
        fixtures = self.contracts[contract_name]["fixtures"]
        for fixture in fixtures:
            if fixture["fixture_id"] == fixture_id:
                return fixture["instance"]
        self.fail(f"unknown compatibility fixture {fixture_id}")

    def test_frozen_v1_corpus_validates(self) -> None:
        seen_ids: set[str] = set()
        for contract_name, contract in self.contracts.items():
            validator = validator_for(contract["schema_path"])
            for fixture in contract["fixtures"]:
                fixture_id = fixture["fixture_id"]
                self.assertNotIn(fixture_id, seen_ids)
                seen_ids.add(fixture_id)
                self.assertEqual(
                    fixture["schema_version"], fixture["instance"]["schema_version"]
                )
                with self.subTest(contract=contract_name, fixture=fixture_id):
                    self.assertEqual([], list(validator.iter_errors(fixture["instance"])))

    def test_every_published_revision_is_declared_and_frozen(self) -> None:
        for contract_name, contract in self.contracts.items():
            schema = load_json(contract["schema_path"])
            version_rule = schema["properties"]["schema_version"]
            declared = (
                {version_rule["const"]}
                if "const" in version_rule
                else set(version_rule["enum"])
            )
            published = set(contract["published_versions"])
            frozen = {
                fixture["schema_version"] for fixture in contract["fixtures"]
            }
            with self.subTest(contract=contract_name):
                self.assertEqual(published, declared)
                self.assertEqual(published, frozen)

    def test_every_idea_lineage_classification_is_frozen(self) -> None:
        fixtures = self.contracts["investment-idea"]["fixtures"]
        classifications = {
            fixture["instance"]["lineage"]["classification"]
            for fixture in fixtures
            if fixture["schema_version"] == "1.1.0"
        }
        self.assertEqual(
            {
                "new",
                "repeat_unchanged",
                "materially_updated",
                "reintroduced",
                "stale_repeat",
                "unverified",
            },
            classifications,
        )

    def test_historical_enum_values_remain_accepted(self) -> None:
        for contract_name, fixture_id, path, values in ENUM_CASES:
            validator = validator_for(self.contracts[contract_name]["schema_path"])
            for value in values:
                instance = copy.deepcopy(self.fixture(contract_name, fixture_id))
                set_path(instance, path, value)
                with self.subTest(contract=contract_name, path=path, value=value):
                    self.assertEqual([], list(validator.iter_errors(instance)))

    def test_outcome_review_v1_assessability_states_are_frozen(self) -> None:
        fixtures = self.contracts["outcome-review"]["fixtures"]
        states = {
            (
                fixture["instance"]["assessability"],
                fixture["instance"]["ex_ante_basis"],
                fixture["instance"]["evidence_quality"],
            )
            for fixture in fixtures
        }
        self.assertEqual(
            {
                ("assessable", "verified", "sufficient"),
                ("partial", "unverified", "unverified"),
                ("unavailable", "verified", "unavailable"),
            },
            states,
        )

    def test_outcome_review_v1_intermediate_evidence_states_are_frozen(self) -> None:
        validator = validator_for(
            self.contracts["outcome-review"]["schema_path"]
        )
        for evidence_quality in ("limited", "conflicting"):
            instance = copy.deepcopy(
                self.fixture("outcome-review", "outcome-review-1.0.0-assessable")
            )
            instance["assessability"] = "partial"
            instance["evidence_quality"] = evidence_quality
            instance["limitations"] = [
                "Fictional compatibility limitation for an incomplete review."
            ]
            with self.subTest(evidence_quality=evidence_quality):
                self.assertEqual([], list(validator.iter_errors(instance)))

        partial_basis = copy.deepcopy(
            self.fixture("outcome-review", "outcome-review-1.0.0-assessable")
        )
        partial_basis["assessability"] = "partial"
        partial_basis["ex_ante_basis"] = "partial"
        partial_basis["limitations"] = [
            "Fictional compatibility limitation for a partial ex-ante basis."
        ]
        self.assertEqual([], list(validator.iter_errors(partial_basis)))

    def test_outcome_review_v1_invalidation_matrix_is_frozen(self) -> None:
        validator = validator_for(
            self.contracts["outcome-review"]["schema_path"]
        )
        cases = [
            ("not_triggered", "not_required", False),
            ("triggered", "followed", True),
            ("triggered", "delayed", True),
            ("triggered", "not_followed", True),
            ("triggered", "unknown", True),
            ("ambiguous", "unknown", False),
            ("unknown", "unknown", False),
            ("not_applicable", "not_applicable", False),
        ]
        for trigger_state, response_state, needs_evidence in cases:
            instance = copy.deepcopy(
                self.fixture("outcome-review", "outcome-review-1.0.0-assessable")
            )
            if trigger_state in {"ambiguous", "unknown"} or response_state == "unknown":
                instance["assessability"] = "partial"
                instance["limitations"] = [
                    "Fictional compatibility limitation for an unresolved state."
                ]
            instance["invalidation"] = {
                "trigger_state": trigger_state,
                "response_state": response_state,
                "evidence_ids": (
                    [instance["evidence_ids"][0]] if needs_evidence else []
                ),
                "note": "Fictional compatibility invalidation state.",
            }
            with self.subTest(trigger=trigger_state, response=response_state):
                self.assertEqual([], list(validator.iter_errors(instance)))

    def test_outcome_review_v1_unassessable_axes_are_frozen(self) -> None:
        validator = validator_for(
            self.contracts["outcome-review"]["schema_path"]
        )
        instance = copy.deepcopy(
            self.fixture("outcome-review", "outcome-review-1.0.0-partial")
        )
        self.assertEqual("unassessable", instance["decision_quality"])
        self.assertEqual("unassessable", instance["process_quality"])
        self.assertEqual("unassessable", instance["timing_discipline"])
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_outcome_review_v1_supersession_link_is_frozen(self) -> None:
        validator = validator_for(
            self.contracts["outcome-review"]["schema_path"]
        )
        instance = copy.deepcopy(
            self.fixture("outcome-review", "outcome-review-1.0.0-assessable")
        )
        instance["supersedes_review_id"] = "synthetic-prior-review"
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_historical_length_boundaries_remain_accepted(self) -> None:
        cases = [
            ("report-manifest", "report-manifest-1.0.0-complete", ("report_id",), "R" * 160),
            ("investment-idea", "investment-idea-1.0.0", ("idea_id",), "I" * 160),
            ("investment-idea", "investment-idea-1.0.0", ("asset", "symbol"), "S" * 32),
            ("decision-record", "decision-record-1.0.0", ("decision_id",), "D" * 160),
            ("outcome-review", "outcome-review-1.0.0-assessable", ("review_id",), "O" * 160),
        ]
        for contract_name, fixture_id, path, value in cases:
            validator = validator_for(self.contracts[contract_name]["schema_path"])
            instance = copy.deepcopy(self.fixture(contract_name, fixture_id))
            set_path(instance, path, value)
            with self.subTest(contract=contract_name, path=path):
                self.assertEqual([], list(validator.iter_errors(instance)))

    def test_legacy_complete_empty_universe_shape_remains_accepted(self) -> None:
        validator = validator_for(
            self.contracts["report-manifest"]["schema_path"]
        )
        instance = copy.deepcopy(
            self.fixture("report-manifest", "report-manifest-1.0.0-complete")
        )
        instance["coverage"].update(
            {"expected": 0, "observed": 0, "percent": 0.0, "gaps": []}
        )
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_legacy_v10_min_length_strings_remain_unchanged(self) -> None:
        validator = validator_for(
            self.contracts["report-manifest"]["schema_path"]
        )
        instance = copy.deepcopy(
            self.fixture("report-manifest", "report-manifest-1.0.0-complete")
        )
        instance["sources"][0]["source_id"] = " "
        instance["sources"][0]["note"] = " "
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_version_removal_is_detected(self) -> None:
        schema = copy.deepcopy(
            load_json(self.contracts["investment-idea"]["schema_path"])
        )
        schema["properties"]["schema_version"]["enum"] = ["1.1.0"]
        validator = validator_for_schema(schema)
        legacy = self.fixture("investment-idea", "investment-idea-1.0.0")
        self.assertTrue(list(validator.iter_errors(legacy)))

    def test_unconditional_required_field_is_detected(self) -> None:
        schema = copy.deepcopy(
            load_json(self.contracts["report-manifest"]["schema_path"])
        )
        schema["properties"]["synthetic_new_required"] = {"type": "string"}
        schema["required"].append("synthetic_new_required")
        validator = validator_for_schema(schema)
        legacy = self.fixture("report-manifest", "report-manifest-1.0.0-complete")
        self.assertTrue(list(validator.iter_errors(legacy)))

    def test_historical_enum_removal_is_detected(self) -> None:
        schema = copy.deepcopy(
            load_json(self.contracts["decision-record"]["schema_path"])
        )
        actions = schema["properties"]["deployment"]["properties"]["action"]["enum"]
        actions.remove("trim")
        validator = validator_for_schema(schema)
        legacy = copy.deepcopy(self.fixture("decision-record", "decision-record-1.0.0"))
        legacy["deployment"]["action"] = "trim"
        self.assertTrue(list(validator.iter_errors(legacy)))

    def test_malformed_legacy_instance_remains_rejected(self) -> None:
        validator = validator_for(self.contracts["investment-idea"]["schema_path"])
        legacy = copy.deepcopy(self.fixture("investment-idea", "investment-idea-1.0.0"))
        legacy["lineage"] = {
            "status": "verified",
            "classification": "new",
            "last_material_change_at": legacy["last_seen_at"],
            "repeat_count": 0,
            "changed_dimensions": [],
        }
        self.assertTrue(list(validator.iter_errors(legacy)))


if __name__ == "__main__":
    unittest.main()

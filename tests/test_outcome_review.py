"""Tests for the public-safe outcome-review contract and semantic joins."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from schema_helpers import load_json, validator_for
from scripts.validate import (
    validate_outcome_review_cohort,
    validate_outcome_review_fixture,
)


class OutcomeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = validator_for("schemas/v1/outcome-review.schema.json")
        cls.decision = load_json("examples/synthetic/decision-record.json")
        cls.idea = load_json("examples/synthetic/investment-idea.json")
        cls.review = load_json(
            "examples/synthetic/outcome-review-adverse-disciplined.json"
        )
        cls.review_paths = [
            "examples/synthetic/outcome-review-adverse-disciplined.json",
            "examples/synthetic/outcome-review-correction.json",
            "examples/synthetic/outcome-review-favorable-undisciplined.json",
            "examples/synthetic/outcome-review-invalidation-followed.json",
            "examples/synthetic/outcome-review-invalidation-delayed.json",
            "examples/synthetic/outcome-review-partial-unverified.json",
            "examples/synthetic/outcome-review-unavailable.json",
        ]
        cls.decisions = {cls.decision["decision_id"]: cls.decision}
        cls.idea_ids = {cls.idea["idea_id"]}

    def assert_schema_rejected(
        self, instance: object, keyword: str | None = None
    ) -> None:
        errors = list(self.validator.iter_errors(instance))
        self.assertTrue(errors, "the deliberately invalid review was accepted")
        if keyword is not None:
            self.assertIn(keyword, {error.validator for error in errors})

    def semantic_errors(self, instance: object) -> list[str]:
        errors: list[str] = []
        validate_outcome_review_fixture(
            Path("synthetic-outcome-review.json"),
            instance,
            self.decisions,
            self.idea_ids,
            errors,
        )
        return errors

    def test_all_public_fixtures_validate(self) -> None:
        cohort = []
        for path in self.review_paths:
            instance = load_json(path)
            cohort.append((Path(path), instance))
            with self.subTest(path=path):
                self.assertEqual([], list(self.validator.iter_errors(instance)))
                self.assertEqual([], self.semantic_errors(instance))
        errors: list[str] = []
        validate_outcome_review_cohort(cohort, errors)
        self.assertEqual([], errors)

    def test_review_links_resolve_to_decision_and_idea(self) -> None:
        missing_decision = copy.deepcopy(self.review)
        missing_decision["decision_id"] = "synthetic-missing-decision"
        self.assertTrue(
            any(
                "linked decision does not exist" in error
                for error in self.semantic_errors(missing_decision)
            )
        )

        mismatched_idea = copy.deepcopy(self.review)
        mismatched_idea["idea_id"] = "synthetic-missing-idea"
        errors = self.semantic_errors(mismatched_idea)
        self.assertTrue(any("linked idea does not exist" in error for error in errors))
        self.assertTrue(
            any("does not match the linked decision" in error for error in errors)
        )

    def test_review_clock_order_is_enforced(self) -> None:
        cases = {}

        before_decision = copy.deepcopy(self.review)
        before_decision["evaluation_window"]["started_at"] = "2026-01-15T14:04:00Z"
        cases["before decision"] = before_decision

        zero_window = copy.deepcopy(self.review)
        zero_window["evaluation_window"]["ended_at"] = zero_window[
            "evaluation_window"
        ]["started_at"]
        cases["zero window"] = zero_window

        cutoff_before_end = copy.deepcopy(self.review)
        cutoff_before_end["evidence_cutoff_at"] = "2026-02-15T14:04:00Z"
        cases["cutoff before end"] = cutoff_before_end

        review_before_cutoff = copy.deepcopy(self.review)
        review_before_cutoff["reviewed_at"] = "2026-02-16T13:59:00Z"
        cases["review before cutoff"] = review_before_cutoff

        for name, instance in cases.items():
            with self.subTest(case=name):
                self.assertTrue(self.semantic_errors(instance))

        partial_before_decision = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        partial_before_decision["reviewed_at"] = "2026-01-15T14:04:00Z"
        self.assertTrue(
            any(
                "recorded_at cannot be after reviewed_at" in error
                for error in self.semantic_errors(partial_before_decision)
            )
        )

    def test_nested_evidence_must_resolve_to_review_register(self) -> None:
        attribution = copy.deepcopy(self.review)
        attribution["attribution"][0]["evidence_ids"] = [
            "synthetic-unregistered-evidence"
        ]
        self.assertTrue(
            any(
                "dangling review evidence ID" in error
                for error in self.semantic_errors(attribution)
            )
        )

        invalidation = load_json(
            "examples/synthetic/outcome-review-invalidation-followed.json"
        )
        invalidation["invalidation"]["evidence_ids"] = [
            "synthetic-unregistered-evidence"
        ]
        self.assertTrue(
            any(
                "dangling review evidence IDs" in error
                for error in self.semantic_errors(invalidation)
            )
        )

        malformed = copy.deepcopy(invalidation)
        malformed["invalidation"]["evidence_ids"] = [
            1,
            "synthetic-unregistered-evidence",
        ]
        self.assertTrue(self.semantic_errors(malformed))

    def test_duplicate_attribution_factor_id_is_rejected_semantically(self) -> None:
        instance = copy.deepcopy(self.review)
        duplicate = copy.deepcopy(instance["attribution"][0])
        duplicate["note"] = "A different fictional note with the same factor ID."
        instance["attribution"].append(duplicate)
        self.assertEqual([], list(self.validator.iter_errors(instance)))
        self.assertTrue(
            any("duplicate factor ID" in error for error in self.semantic_errors(instance))
        )

    def test_review_cannot_supersede_itself(self) -> None:
        instance = copy.deepcopy(self.review)
        instance["supersedes_review_id"] = instance["review_id"]
        self.assertEqual([], list(self.validator.iter_errors(instance)))
        self.assertTrue(
            any(
                "cannot supersede itself" in error
                for error in self.semantic_errors(instance)
            )
        )

    def test_supersession_requires_prior_matching_acyclic_review(self) -> None:
        predecessor = copy.deepcopy(self.review)
        successor = load_json("examples/synthetic/outcome-review-correction.json")

        missing = copy.deepcopy(successor)
        missing["supersedes_review_id"] = "synthetic-missing-review"
        errors: list[str] = []
        validate_outcome_review_cohort(
            [
                (Path("predecessor.json"), predecessor),
                (Path("missing.json"), missing),
            ],
            errors,
        )
        self.assertTrue(
            any("prior review does not exist" in error for error in errors)
        )

        later_predecessor = copy.deepcopy(predecessor)
        later_predecessor["reviewed_at"] = successor["reviewed_at"]
        errors = []
        validate_outcome_review_cohort(
            [
                (Path("predecessor.json"), later_predecessor),
                (Path("successor.json"), successor),
            ],
            errors,
        )
        self.assertTrue(any("must have an earlier" in error for error in errors))

        wrong_lineage = copy.deepcopy(predecessor)
        wrong_lineage["decision_id"] = "synthetic-other-decision"
        wrong_lineage["idea_id"] = "synthetic-other-idea"
        errors = []
        validate_outcome_review_cohort(
            [
                (Path("predecessor.json"), wrong_lineage),
                (Path("successor.json"), successor),
            ],
            errors,
        )
        self.assertTrue(any("different decision_id" in error for error in errors))
        self.assertTrue(any("different idea_id" in error for error in errors))

        first = copy.deepcopy(predecessor)
        second = copy.deepcopy(successor)
        first["supersedes_review_id"] = second["review_id"]
        errors = []
        validate_outcome_review_cohort(
            [(Path("first.json"), first), (Path("second.json"), second)], errors
        )
        self.assertTrue(any("cycle detected" in error for error in errors))

    def test_impossible_invalidation_pairs_are_rejected(self) -> None:
        pairs = [
            ("not_triggered", "followed"),
            ("triggered", "not_required"),
            ("ambiguous", "followed"),
            ("unknown", "not_required"),
            ("not_applicable", "unknown"),
        ]
        for trigger, response in pairs:
            instance = copy.deepcopy(self.review)
            instance["invalidation"].update(
                {
                    "trigger_state": trigger,
                    "response_state": response,
                    "evidence_ids": (
                        [instance["evidence_ids"][0]] if trigger == "triggered" else []
                    ),
                }
            )
            with self.subTest(trigger=trigger, response=response):
                self.assert_schema_rejected(instance)

    def test_triggered_invalidation_requires_evidence(self) -> None:
        instance = load_json(
            "examples/synthetic/outcome-review-invalidation-followed.json"
        )
        instance["invalidation"]["evidence_ids"] = []
        self.assert_schema_rejected(instance, "minItems")

    def test_empty_evidence_cannot_support_categorical_claims(self) -> None:
        instance = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        instance["research_outcome"] = "favorable"
        self.assert_schema_rejected(instance, "enum")

    def test_incomplete_basis_and_evidence_require_limitations(self) -> None:
        instance = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        instance["limitations"] = []
        self.assert_schema_rejected(instance, "minItems")

    def test_unverified_history_cannot_support_reconstructed_assessments(self) -> None:
        decision_claim = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        decision_claim["decision_quality"] = "well_supported"
        self.assert_schema_rejected(decision_claim, "const")

        outcome_claim = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        outcome_claim["research_outcome"] = "favorable"
        self.assert_schema_rejected(outcome_claim, "enum")

        invalidation_claim = load_json(
            "examples/synthetic/outcome-review-partial-unverified.json"
        )
        invalidation_claim["invalidation"].update(
            {
                "trigger_state": "triggered",
                "response_state": "followed",
                "evidence_ids": ["synthetic-outcome-evidence-claim"],
            }
        )
        invalidation_claim["evidence_ids"] = [
            "synthetic-outcome-evidence-claim"
        ]
        self.assert_schema_rejected(invalidation_claim, "const")

    def test_assessable_review_requires_sufficient_resolved_evidence(self) -> None:
        for evidence_quality in ("limited", "conflicting"):
            instance = copy.deepcopy(self.review)
            instance["evidence_quality"] = evidence_quality
            instance["limitations"] = ["Fictional incomplete-evidence limitation."]
            with self.subTest(evidence_quality=evidence_quality):
                self.assert_schema_rejected(instance, "const")

        timing = copy.deepcopy(self.review)
        timing["timing_discipline"] = "unassessable"
        self.assert_schema_rejected(timing, "not")

        invalidation = copy.deepcopy(self.review)
        invalidation["invalidation"].update(
            {
                "trigger_state": "unknown",
                "response_state": "unknown",
                "evidence_ids": [],
            }
        )
        self.assert_schema_rejected(invalidation, "not")

    def test_existing_unicode_and_space_link_identifiers_are_accepted(self) -> None:
        instance = copy.deepcopy(self.review)
        decision = copy.deepcopy(self.decision)
        decision["decision_id"] = "Décision synthetic 001"
        decision["idea_id"] = "Idée synthetic 001"
        instance["decision_id"] = decision["decision_id"]
        instance["idea_id"] = decision["idea_id"]
        self.assertEqual([], list(self.validator.iter_errors(instance)))

        errors: list[str] = []
        validate_outcome_review_fixture(
            Path("synthetic-outcome-review.json"),
            instance,
            {decision["decision_id"]: decision},
            {decision["idea_id"]},
            errors,
        )
        self.assertEqual([], errors)

    def test_outcome_review_requires_utc_z_timestamps(self) -> None:
        instance = copy.deepcopy(self.review)
        instance["reviewed_at"] = "2026-02-17T14:00:00+00:00"
        self.assert_schema_rejected(instance, "pattern")

    def test_performance_account_and_deployment_fields_are_rejected(self) -> None:
        forbidden = {
            "return": 1.0,
            "returns": [],
            "P&L": 1,
            "pnl": 1,
            "profit_and_loss": 1,
            "price": 1,
            "prices": [],
            "performance": {},
            "alpha": 1,
            "benchmark": "synthetic",
            "holdings": [],
            "allocation": 1,
            "allocations": [],
            "position_size": 1,
            "position_sizes": [],
            "transactions": [],
            "client_id": "synthetic-client",
            "client": {},
            "account_id": "synthetic-account",
            "account": {},
            "client_data": {},
            "deployment": {},
            "deployment_action": "initiate",
            "deployment_actions": [],
        }
        for field, value in forbidden.items():
            instance = copy.deepcopy(self.review)
            instance[field] = value
            with self.subTest(field=field):
                self.assert_schema_rejected(instance, "additionalProperties")

    def test_numeric_attribution_fields_are_rejected(self) -> None:
        for field in (
            "weight",
            "contribution_weight",
            "return_contribution",
            "causal_contribution",
        ):
            instance = copy.deepcopy(self.review)
            instance["attribution"][0][field] = 0.5
            with self.subTest(field=field):
                self.assert_schema_rejected(instance, "additionalProperties")

    def test_every_nested_object_rejects_unknown_properties(self) -> None:
        cases = []

        evaluation = copy.deepcopy(self.review)
        evaluation["evaluation_window"]["synthetic_extra"] = True
        cases.append(evaluation)

        invalidation = copy.deepcopy(self.review)
        invalidation["invalidation"]["synthetic_extra"] = True
        cases.append(invalidation)

        attribution = copy.deepcopy(self.review)
        attribution["attribution"][0]["synthetic_extra"] = True
        cases.append(attribution)

        for index, instance in enumerate(cases):
            with self.subTest(case=index):
                self.assert_schema_rejected(instance, "additionalProperties")


if __name__ == "__main__":
    unittest.main()

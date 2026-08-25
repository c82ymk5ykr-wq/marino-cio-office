"""Tests for the public-safe append-only outcome-review contract."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from schema_helpers import load_json, validator_for
from scripts.validate import (
    OUTCOME_INVALIDATION_RESPONSES,
    validate_outcome_review,
    validate_outcome_review_fixture_coverage,
)


SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic"


class OutcomeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = validator_for("schemas/v1/outcome-review.schema.json")
        cls.examples = {
            path.stem: load_json(f"examples/synthetic/{path.name}")
            for path in sorted(SYNTHETIC_DIR.glob("outcome-review-*.json"))
        }
        cls.adverse = cls.examples["outcome-review-adverse-disciplined"]
        cls.favorable = cls.examples["outcome-review-favorable-undisciplined"]
        cls.followed = cls.examples["outcome-review-invalidation-followed"]
        cls.partial = cls.examples["outcome-review-partial"]
        cls.unknown = cls.examples["outcome-review-unknown-unverified"]
        cls.unavailable = cls.examples["outcome-review-unavailable"]

    def semantic_errors(self, review: object) -> list[str]:
        errors: list[str] = []
        validate_outcome_review(
            review, Path("examples/synthetic/test-outcome-review.json"), errors
        )
        return errors

    def assert_valid(self, review: object) -> None:
        self.assertEqual([], list(self.validator.iter_errors(review)))
        self.assertEqual([], self.semantic_errors(review))

    def configured_invalidation_pair(
        self, trigger_state: str, response_state: str
    ) -> object:
        review = copy.deepcopy(self.followed)
        evidence_ref = review["links"]["evidence_refs"][0]

        trigger = {
            "state": trigger_state,
            "evidence_refs": [],
            "note": "Fictional trigger state for exhaustive contract testing.",
        }
        if trigger_state == "triggered":
            trigger["triggered_at"] = "2099-03-06T09:00:00Z"
            trigger["evidence_refs"] = [evidence_ref]
        elif trigger_state in {"not_triggered", "ambiguous"}:
            trigger["evidence_refs"] = [evidence_ref]

        response = {
            "state": response_state,
            "evidence_refs": [],
            "note": "Fictional response state for exhaustive contract testing.",
        }
        if response_state in {"followed", "delayed"}:
            response["responded_at"] = "2099-03-06T10:00:00Z"
            response["evidence_refs"] = [evidence_ref]
        elif response_state in {"not_followed", "ambiguous"}:
            response["evidence_refs"] = [evidence_ref]

        review["invalidation_trigger"] = trigger
        review["invalidation_response"] = response

        uncertain = trigger_state in {"ambiguous", "unknown"} or response_state in {
            "ambiguous",
            "unknown",
        }
        if uncertain:
            review["review_assessability"] = "partial"
            review["evidence_quality"] = "partial"

        return review

    def test_all_synthetic_examples_pass_schema_and_semantic_validation(self) -> None:
        self.assertEqual(7, len(self.examples))
        for name, review in self.examples.items():
            with self.subTest(example=name):
                self.assert_valid(review)

    def test_scenario_fixtures_preserve_axis_independence(self) -> None:
        self.assertEqual("adverse", self.adverse["research_outcome"]["classification"])
        self.assertEqual("sound", self.adverse["decision_quality"]["classification"])
        self.assertEqual(
            "disciplined", self.adverse["process_quality"]["classification"]
        )
        self.assert_valid(self.adverse)

        self.assertEqual(
            "favorable", self.favorable["research_outcome"]["classification"]
        )
        self.assertEqual("unsound", self.favorable["decision_quality"]["classification"])
        self.assertEqual(
            "undisciplined", self.favorable["process_quality"]["classification"]
        )
        self.assert_valid(self.favorable)

    def test_fixture_coverage_gate_passes(self) -> None:
        errors: list[str] = []
        reviews = [
            (Path(f"examples/synthetic/{name}.json"), review)
            for name, review in self.examples.items()
        ]
        validate_outcome_review_fixture_coverage(reviews, errors)
        self.assertEqual([], errors)

    def test_lifecycle_adjacent_inversions_are_rejected(self) -> None:
        pairs = [
            ("decision_recorded_at", "evaluation_started_at"),
            ("evaluation_started_at", "evidence_cutoff_at"),
            ("evidence_cutoff_at", "reviewed_at"),
        ]
        for earlier, later in pairs:
            review = copy.deepcopy(self.adverse)
            review["clocks"][earlier] = "2099-01-12T09:00:00Z"
            review["clocks"][later] = "2099-01-11T09:00:00Z"
            with self.subTest(earlier=earlier, later=later):
                self.assertTrue(
                    any("cannot be after" in error for error in self.semantic_errors(review))
                )

    def test_invalidation_clocks_stay_inside_review_lifecycle(self) -> None:
        cases = {
            "trigger before decision": (
                ("invalidation_trigger", "triggered_at"),
                "2099-02-28T09:00:00Z",
                "cannot precede decision",
            ),
            "trigger after cutoff": (
                ("invalidation_trigger", "triggered_at"),
                "2099-03-10T09:00:01Z",
                "cannot exceed evidence cutoff",
            ),
            "response before trigger": (
                ("invalidation_response", "responded_at"),
                "2099-03-06T08:59:59Z",
                "cannot precede trigger",
            ),
            "response after cutoff": (
                ("invalidation_response", "responded_at"),
                "2099-03-10T09:00:01Z",
                "cannot exceed evidence cutoff",
            ),
        }
        for name, (path, value, expected) in cases.items():
            review = copy.deepcopy(self.followed)
            review[path[0]][path[1]] = value
            with self.subTest(case=name):
                self.assertTrue(
                    any(expected in error for error in self.semantic_errors(review))
                )

    def test_every_invalidation_pair_is_accepted_or_rejected_deterministically(
        self,
    ) -> None:
        trigger_states = list(OUTCOME_INVALIDATION_RESPONSES)
        response_states = [
            "followed",
            "delayed",
            "not_followed",
            "ambiguous",
            "unknown",
            "not_applicable",
        ]
        for trigger_state in trigger_states:
            for response_state in response_states:
                review = self.configured_invalidation_pair(
                    trigger_state, response_state
                )
                schema_errors = list(self.validator.iter_errors(review))
                semantic_errors = self.semantic_errors(review)
                allowed = response_state in OUTCOME_INVALIDATION_RESPONSES[trigger_state]
                with self.subTest(
                    trigger=trigger_state, response=response_state, allowed=allowed
                ):
                    if allowed:
                        self.assertEqual([], schema_errors)
                        self.assertEqual([], semantic_errors)
                    else:
                        self.assertTrue(schema_errors or semantic_errors)

    def test_dangling_evidence_is_rejected_from_every_nested_location(self) -> None:
        cases = []

        for axis_name in (
            "research_outcome",
            "decision_quality",
            "process_quality",
            "timing_discipline",
            "invalidation_trigger",
        ):
            review = copy.deepcopy(self.adverse)
            review[axis_name]["evidence_refs"] = ["ref_SYNTH999999999991"]
            cases.append((axis_name, review))

        response = copy.deepcopy(self.followed)
        response["invalidation_response"]["evidence_refs"] = [
            "ref_SYNTH999999999992"
        ]
        cases.append(("invalidation_response", response))

        factor = copy.deepcopy(self.adverse)
        factor["attribution"]["factors"][0]["evidence_refs"] = [
            "ref_SYNTH999999999993"
        ]
        cases.append(("attribution", factor))

        for name, review in cases:
            with self.subTest(location=name):
                self.assertTrue(
                    any("dangling reference" in error for error in self.semantic_errors(review))
                )

    def test_unused_declared_evidence_is_rejected(self) -> None:
        review = copy.deepcopy(self.adverse)
        review["links"]["evidence_refs"].append("ref_SYNTH999999999994")
        self.assertTrue(
            any("unused reference" in error for error in self.semantic_errors(review))
        )

    def test_intrinsic_axes_cannot_be_not_applicable(self) -> None:
        for axis_name in (
            "research_outcome",
            "decision_quality",
            "process_quality",
        ):
            review = copy.deepcopy(self.partial)
            review[axis_name] = {
                "assessment_state": "not_applicable",
                "evidence_refs": [],
                "note": "Fictional intrinsic axis mutation.",
            }
            with self.subTest(axis=axis_name):
                self.assertTrue(list(self.validator.iter_errors(review)))
                self.assertTrue(
                    any(
                        "intrinsic axis cannot be not_applicable" in error
                        for error in self.semantic_errors(review)
                    )
                )

    def test_partial_review_can_be_limited_only_by_invalidation(self) -> None:
        review = self.configured_invalidation_pair("triggered", "unknown")
        self.assertEqual("assessable", review["research_outcome"]["assessment_state"])
        self.assertEqual("partial", review["review_assessability"])
        self.assert_valid(review)

    def test_identity_and_append_only_references_are_distinct(self) -> None:
        self_reference = copy.deepcopy(self.adverse)
        self_reference["prior_review_ref"] = self_reference["review_id"]
        self.assertTrue(
            any("cannot refer to itself" in error for error in self.semantic_errors(self_reference))
        )

        same_identity = copy.deepcopy(self.adverse)
        same_identity["links"]["idea_ref"] = same_identity["links"]["decision_ref"]
        self.assertTrue(
            any("must be distinct" in error for error in self.semantic_errors(same_identity))
        )

        reused_evidence = copy.deepcopy(self.adverse)
        reused_evidence["links"]["evidence_refs"][0] = reused_evidence["links"][
            "decision_ref"
        ]
        reused_evidence["research_outcome"]["evidence_refs"][0] = reused_evidence[
            "links"
        ]["decision_ref"]
        self.assertTrue(
            any(
                "cannot also be an evidence reference" in error
                for error in self.semantic_errors(reused_evidence)
            )
        )

    def test_assessability_and_evidence_quality_are_coherent(self) -> None:
        pairs = [
            ("assessable", "verified"),
            ("partial", "partial"),
            ("unknown", "unverified"),
            ("unavailable", "unavailable"),
        ]
        fixtures = [self.adverse, self.partial, self.unknown, self.unavailable]
        for fixture, pair in zip(fixtures, pairs):
            with self.subTest(pair=pair):
                self.assertEqual(pair, (
                    fixture["review_assessability"],
                    fixture["evidence_quality"],
                ))
                self.assert_valid(fixture)

        contradiction = copy.deepcopy(self.adverse)
        contradiction["evidence_quality"] = "unverified"
        self.assertTrue(
            any("requires evidence_quality" in error for error in self.semantic_errors(contradiction))
        )

        empty_assessable = copy.deepcopy(self.adverse)
        empty_assessable["links"]["evidence_refs"] = []
        for axis_name in (
            "research_outcome",
            "decision_quality",
            "process_quality",
            "timing_discipline",
        ):
            empty_assessable[axis_name]["assessment_state"] = "not_applicable"
            empty_assessable[axis_name].pop("classification", None)
            empty_assessable[axis_name]["evidence_refs"] = []
        empty_assessable["invalidation_trigger"] = {
            "state": "not_applicable",
            "evidence_refs": [],
            "note": "Fictional non-applicable trigger.",
        }
        empty_assessable["invalidation_response"] = {
            "state": "not_applicable",
            "evidence_refs": [],
            "note": "Fictional non-applicable response.",
        }
        empty_assessable["attribution"] = {
            "assessment_state": "not_applicable",
            "factors": [],
            "note": "Fictional non-applicable attribution.",
        }
        self.assertTrue(list(self.validator.iter_errors(empty_assessable)))
        self.assertTrue(
            any("assessable review needs evidence" in error for error in self.semantic_errors(empty_assessable))
        )

    def test_unknown_properties_are_rejected_at_every_object_layer(self) -> None:
        mutations = []

        top = copy.deepcopy(self.adverse)
        top["unexpected"] = "fictional"
        mutations.append(top)

        links = copy.deepcopy(self.adverse)
        links["links"]["unexpected"] = "fictional"
        mutations.append(links)

        clocks = copy.deepcopy(self.adverse)
        clocks["clocks"]["unexpected"] = "fictional"
        mutations.append(clocks)

        axis = copy.deepcopy(self.adverse)
        axis["research_outcome"]["unexpected"] = "fictional"
        mutations.append(axis)

        trigger = copy.deepcopy(self.adverse)
        trigger["invalidation_trigger"]["unexpected"] = "fictional"
        mutations.append(trigger)

        response = copy.deepcopy(self.adverse)
        response["invalidation_response"]["unexpected"] = "fictional"
        mutations.append(response)

        attribution = copy.deepcopy(self.adverse)
        attribution["attribution"]["unexpected"] = "fictional"
        mutations.append(attribution)

        factor = copy.deepcopy(self.adverse)
        factor["attribution"]["factors"][0]["unexpected"] = "fictional"
        mutations.append(factor)

        for index, review in enumerate(mutations):
            with self.subTest(layer=index):
                keywords = {
                    error.validator for error in self.validator.iter_errors(review)
                }
                self.assertIn("additionalProperties", keywords)

    def test_performance_account_and_deployment_fields_are_rejected(self) -> None:
        prohibited = [
            "return",
            "returns",
            "return_pct",
            "P&L",
            "pnl",
            "profit_loss",
            "performance",
            "alpha",
            "price",
            "prices",
            "benchmark",
            "benchmarks",
            "holding",
            "holdings",
            "allocation",
            "allocations",
            "position_size",
            "position_sizes",
            "transaction",
            "transactions",
            "client",
            "client_id",
            "client_data",
            "account",
            "account_id",
            "account_data",
            "portfolio",
            "asset",
            "symbol",
            "ticker",
            "payload_hash",
            "deployment",
            "deployment_action",
            "action",
            "research_disposition",
        ]
        for field in prohibited:
            review = copy.deepcopy(self.adverse)
            review[field] = 1
            with self.subTest(field=field):
                self.assertTrue(list(self.validator.iter_errors(review)))
                self.assertTrue(
                    any("prohibited" in error for error in self.semantic_errors(review))
                )

    def test_numeric_and_causal_attribution_fields_are_rejected(self) -> None:
        fields = [
            "weight",
            "contribution_weight",
            "contribution",
            "percent",
            "score",
            "causal_status",
            "causal_probability",
        ]
        for field in fields:
            review = copy.deepcopy(self.adverse)
            review["attribution"]["factors"][0][field] = 0.5
            with self.subTest(field=field):
                self.assertTrue(list(self.validator.iter_errors(review)))
                errors = self.semantic_errors(review)
                self.assertTrue(any("attribution field is prohibited" in error for error in errors))
                self.assertTrue(any("numeric values are not permitted" in error for error in errors))

        confidence = copy.deepcopy(self.adverse)
        confidence["attribution"]["factors"][0]["confidence"] = 0.9
        self.assertTrue(list(self.validator.iter_errors(confidence)))
        self.assertTrue(
            any("numeric values are not permitted" in error for error in self.semantic_errors(confidence))
        )

    def test_contract_clocks_require_utc_z(self) -> None:
        for value in (
            "2099-01-01T09:00:00+00:00",
            "2099-01-01T09:00:00Z\n",
        ):
            review = copy.deepcopy(self.adverse)
            review["clocks"]["decision_recorded_at"] = value
            with self.subTest(value=value):
                self.assertTrue(list(self.validator.iter_errors(review)))
                self.assertTrue(
                    any("invalid UTC timestamp" in error for error in self.semantic_errors(review))
                )

    def test_malformed_review_is_rejected_without_crashing(self) -> None:
        malformed_states = copy.deepcopy(self.adverse)
        malformed_states["review_assessability"] = []
        malformed_states["research_outcome"]["assessment_state"] = {}
        malformed_states["invalidation_trigger"]["state"] = []
        malformed_states["invalidation_response"]["state"] = {}
        malformed_states["attribution"]["assessment_state"] = []

        malformed_factors = copy.deepcopy(self.adverse)
        malformed_factors["attribution"]["factors"] = [
            "not-an-object",
            {"evidence_refs": {}},
        ]
        cases = [
            None,
            [],
            {"schema_version": "1.0.0"},
            {**copy.deepcopy(self.adverse), "clocks": "not-an-object"},
            {**copy.deepcopy(self.adverse), "links": "not-an-object"},
            malformed_states,
            malformed_factors,
        ]
        for index, review in enumerate(cases):
            errors = self.semantic_errors(review)
            schema_errors = list(self.validator.iter_errors(review))
            with self.subTest(case=index):
                self.assertTrue(schema_errors or errors)

    def test_malformed_fixture_cohort_is_rejected_without_crashing(self) -> None:
        malformed = copy.deepcopy(self.adverse)
        malformed["research_outcome"] = "not-an-object"
        malformed["process_quality"] = []
        malformed["invalidation_trigger"] = "not-an-object"
        malformed["invalidation_response"]["state"] = {}
        malformed["review_assessability"] = {}
        errors: list[str] = []
        validate_outcome_review_fixture_coverage(
            [(Path("examples/synthetic/malformed.json"), malformed)], errors
        )
        self.assertTrue(errors)

    def test_compatibility_outcome_reviews_pass_semantic_gate(self) -> None:
        corpus = load_json("tests/compatibility/v1-fixtures.json")
        fixtures = corpus["contracts"]["outcome-review"]["fixtures"]
        for fixture in fixtures:
            review = fixture["instance"]
            with self.subTest(fixture=fixture["fixture_id"]):
                self.assert_valid(review)


if __name__ == "__main__":
    unittest.main()

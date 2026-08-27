"""Tests for deterministic public-safe learning-loop measurement."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from typing import Any

from schema_helpers import load_json, validator_for
from scripts.learning_metrics import (
    NOT_AVAILABLE,
    LearningMetricError,
    assert_metric_claim,
    measure_idea_cohort,
    measure_outcome_review_cohort,
    rate,
)
from scripts.validate import validate_idea_fixture, validate_outcome_review


SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic"


def synthetic_idea(
    suffix: str,
    *,
    status: str,
    classification: str,
    first_seen_at: str = "2099-01-01T00:00:00Z",
    last_seen_at: str = "2099-01-01T00:00:00Z",
    repeat_reason: str | None = None,
) -> dict[str, Any]:
    fixture_name = {
        "new": "investment-idea.json",
        "repeat_unchanged": "investment-idea-repeat-unchanged.json",
        "unverified": "investment-idea-unverified-lineage.json",
    }.get(classification, "investment-idea-unverified-lineage.json")
    idea = copy.deepcopy(load_json(f"examples/synthetic/{fixture_name}"))
    idea["idea_id"] = f"synthetic-metric-idea-{suffix}"
    idea["first_seen_at"] = first_seen_at
    idea["last_seen_at"] = last_seen_at
    idea["lineage"]["status"] = status
    idea["lineage"]["classification"] = classification
    if classification == "new":
        idea["lineage"]["last_material_change_at"] = first_seen_at
    elif classification == "repeat_unchanged":
        idea["lineage"]["last_material_change_at"] = first_seen_at
    if repeat_reason is not None:
        idea["repeat_reason"] = repeat_reason
    else:
        idea.pop("repeat_reason", None)
    return idea


def synthetic_review(
    suffix: str,
    decision_ref: str,
    idea_ref: str,
    *,
    prior_review_ref: str | None = None,
    timing_state: str = "assessable",
    timing_classification: str | None = "disciplined",
    trigger_state: str | None = None,
    response_state: str | None = None,
    research_outcome: str = "mixed",
) -> dict[str, Any]:
    if timing_state == "unknown":
        fixture_name = "outcome-review-unknown-unverified.json"
    elif timing_state == "unavailable":
        fixture_name = "outcome-review-unavailable.json"
    elif timing_state == "not_applicable":
        fixture_name = "outcome-review-partial.json"
    elif trigger_state == "triggered" and response_state == "delayed":
        fixture_name = "outcome-review-invalidation-delayed.json"
    elif trigger_state == "triggered":
        fixture_name = "outcome-review-invalidation-followed.json"
    else:
        fixture_name = "outcome-review-adverse-disciplined.json"

    review = copy.deepcopy(load_json(f"examples/synthetic/{fixture_name}"))
    review["review_id"] = f"orv_SYNTHMETRIC{suffix}"
    review["links"]["decision_ref"] = decision_ref
    review["links"]["idea_ref"] = idea_ref
    review.pop("prior_review_ref", None)

    if timing_state in {"assessable", "partial"}:
        review["timing_discipline"]["assessment_state"] = timing_state
        review["timing_discipline"]["classification"] = timing_classification
        if timing_state == "partial":
            review["review_assessability"] = "partial"
            review["evidence_quality"] = "partial"

    if trigger_state in {"ambiguous", "unknown", "not_applicable"}:
        evidence_refs = (
            [review["links"]["evidence_refs"][0]]
            if trigger_state == "ambiguous"
            else []
        )
        review["invalidation_trigger"] = {
            "state": trigger_state,
            "evidence_refs": evidence_refs,
            "note": "Visibly fictional trigger state for metric testing.",
        }
        if trigger_state in {"ambiguous", "unknown"}:
            review["review_assessability"] = (
                "partial" if trigger_state == "ambiguous" else "unknown"
            )
            review["evidence_quality"] = (
                "partial" if trigger_state == "ambiguous" else "unverified"
            )
    if response_state in {"ambiguous", "unknown", "not_applicable"}:
        evidence_refs = (
            [review["links"]["evidence_refs"][0]]
            if response_state == "ambiguous"
            else []
        )
        review["invalidation_response"] = {
            "state": response_state,
            "evidence_refs": evidence_refs,
            "note": "Visibly fictional response state for metric testing.",
        }

    # The measurement helper deliberately ignores this independent axis.
    if "classification" in review["research_outcome"]:
        review["research_outcome"]["classification"] = research_outcome
    if prior_review_ref is not None:
        review["prior_review_ref"] = prior_review_ref
    return review


class LearningMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_json("examples/synthetic/learning-metrics-cases.json")
        cls.idea_validator = validator_for("schemas/v1/investment-idea.schema.json")
        cls.review_validator = validator_for("schemas/v1/outcome-review.schema.json")
        report = load_json("examples/synthetic/report-manifest.json")
        cls.source_statuses = {
            source["source_id"]: source["status"] for source in report["sources"]
        }

    def full_idea_is_valid(self, idea: dict[str, Any]) -> bool:
        semantic_errors: list[str] = []
        validate_idea_fixture(
            Path("examples/synthetic/learning-metrics-generated-idea.json"),
            idea,
            self.source_statuses,
            semantic_errors,
        )
        return not list(self.idea_validator.iter_errors(idea)) and not semantic_errors

    def full_review_is_valid(self, review: dict[str, Any]) -> bool:
        semantic_errors: list[str] = []
        validate_outcome_review(
            review,
            Path("examples/synthetic/learning-metrics-generated-review.json"),
            semantic_errors,
        )
        return not list(self.review_validator.iter_errors(review)) and not semantic_errors

    def measure_ideas(self, ideas: list[dict[str, Any]]) -> dict[str, Any]:
        return measure_idea_cohort(ideas, idea_validator=self.full_idea_is_valid)

    def measure_reviews(
        self,
        targets: list[dict[str, str]],
        reviews: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return measure_outcome_review_cohort(
            targets, reviews, review_validator=self.full_review_is_valid
        )

    def balanced_ideas(self) -> list[dict[str, Any]]:
        return [
            load_json(f"examples/synthetic/{name}")
            for name in self.cases["idea_balanced"]["fixture_refs"]
        ]

    def balanced_reviews(
        self,
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        case = self.cases["review_balanced"]
        reviews = [
            load_json(f"examples/synthetic/{name}") for name in case["fixture_refs"]
        ]
        recipe = case["predecessor"]
        predecessor = copy.deepcopy(
            load_json(
                f"examples/synthetic/{recipe['clone_fixture_ref']}"
            )
        )
        predecessor["review_id"] = recipe["review_id"]
        if recipe["remove_prior_review_ref"]:
            predecessor.pop("prior_review_ref", None)
        reviews.append(predecessor)

        targets: list[dict[str, str]] = []
        seen: set[str] = set()
        for review in reviews:
            decision_ref = review["links"]["decision_ref"]
            if decision_ref in seen:
                continue
            seen.add(decision_ref)
            targets.append(
                {
                    "decision_ref": decision_ref,
                    "idea_ref": review["links"]["idea_ref"],
                }
            )
        return targets, reviews

    def chain_reviews(self) -> list[dict[str, Any]]:
        reviews: list[dict[str, Any]] = []
        for fragment in self.cases["chain_exclusions"]["topology_fragments"]:
            timing = fragment["timing_discipline"]
            review = synthetic_review(
                fragment["review_id"].removeprefix("orv_SYNTHMETRIC"),
                fragment["links"]["decision_ref"],
                fragment["links"]["idea_ref"],
                prior_review_ref=fragment.get("prior_review_ref"),
                timing_state=timing["assessment_state"],
                timing_classification=timing.get("classification"),
                trigger_state=fragment["invalidation_trigger"]["state"],
                response_state=fragment["invalidation_response"]["state"],
            )
            self.assertTrue(self.full_review_is_valid(review))
            reviews.append(review)
        return reviews

    def test_balanced_idea_truth_table_matches_exactly(self) -> None:
        ideas = self.balanced_ideas()
        for idea in ideas:
            self.assertEqual([], list(self.idea_validator.iter_errors(idea)))
        measured = self.measure_ideas(ideas)
        self.assertEqual(self.cases["idea_balanced"]["expected"], measured)

    def test_balanced_review_truth_table_matches_exactly(self) -> None:
        targets, reviews = self.balanced_reviews()
        for review in reviews:
            self.assertTrue(self.full_review_is_valid(review))
        measured = self.measure_reviews(targets, reviews)
        self.assertEqual(self.cases["review_balanced"]["expected"], measured)

    def test_balanced_rates_have_expected_display_percentages(self) -> None:
        idea = self.measure_ideas(self.balanced_ideas())
        review = self.measure_reviews(*self.balanced_reviews())
        self.assertEqual("1/5", idea["rates"]["new_idea"]["value"])
        self.assertEqual("4/5", idea["rates"]["repeat"]["value"])
        self.assertEqual("1/6", idea["rates"]["unverified_lineage"]["value"])
        self.assertEqual(
            "2/3", review["timing"]["rates"]["classification_coverage"]["value"]
        )
        self.assertEqual(
            "4/7",
            review["invalidations"]["rates"]["trigger_ascertainment"]["value"],
        )

    def test_all_unverified_baseline_does_not_invent_new_ideas(self) -> None:
        ideas = [
            synthetic_idea("baseline-1", status="unverified", classification="unverified"),
            synthetic_idea("baseline-2", status="unverified", classification="unverified"),
        ]
        measured = self.measure_ideas(ideas)
        self.assertEqual(0, measured["cohort"]["verified_count"])
        self.assertEqual(2, measured["cohort"]["unverified_count"])
        self.assertEqual(NOT_AVAILABLE, measured["rates"]["new_idea"]["value"])
        self.assertEqual(NOT_AVAILABLE, measured["rates"]["repeat"]["value"])
        self.assertEqual("1", measured["rates"]["unverified_lineage"]["value"])

    def test_verified_cohort_with_no_repeats_has_only_legitimate_zero(self) -> None:
        ideas = [
            synthetic_idea("new-1", status="verified", classification="new"),
            synthetic_idea("new-2", status="verified", classification="new"),
        ]
        measured = self.measure_ideas(ideas)
        self.assertEqual(
            {"numerator": 0, "denominator": 2, "value": "0"},
            measured["rates"]["repeat"],
        )
        for name in (
            "explained_repeat",
            "strict_material_update",
            "decision_changing_repeat",
            "stale_repeat",
        ):
            with self.subTest(rate=name):
                self.assertEqual(NOT_AVAILABLE, measured["rates"][name]["value"])
        self.assertEqual(
            {"count": 0, "median": NOT_AVAILABLE, "maximum": NOT_AVAILABLE},
            measured["repeat_age_hours"],
        )

    def test_legacy_only_cohort_is_excluded_and_not_reclassified(self) -> None:
        measured = self.measure_ideas(
            [load_json("examples/synthetic/investment-idea-legacy-1.0.json")]
        )
        self.assertEqual(0, measured["cohort"]["current_idea_count"])
        self.assertEqual(
            {"legacy_1_0_0_count": 1, "total_count": 1},
            measured["cohort"]["exclusions"],
        )
        self.assertEqual(
            NOT_AVAILABLE, measured["rates"]["unverified_lineage"]["value"]
        )

    def test_duplicate_eligible_idea_id_fails_frozen_cohort(self) -> None:
        idea = synthetic_idea("duplicate", status="verified", classification="new")
        with self.assertRaisesRegex(LearningMetricError, "more than one"):
            self.measure_ideas([idea, copy.deepcopy(idea)])

    def test_truncated_idea_cannot_be_measured(self) -> None:
        truncated = synthetic_idea(
            "truncated", status="verified", classification="new"
        )
        truncated.pop("thesis")
        self.assertFalse(self.full_idea_is_valid(truncated))
        with self.assertRaisesRegex(LearningMetricError, "full schema"):
            self.measure_ideas([truncated])

    def test_unexplained_repeat_fails_instead_of_flattering_quality(self) -> None:
        repeat = synthetic_idea(
            "unexplained",
            status="verified",
            classification="repeat_unchanged",
            last_seen_at="2099-01-02T00:00:00Z",
        )
        with self.assertRaisesRegex(LearningMetricError, "full schema"):
            self.measure_ideas([repeat])

    def test_inconsistent_lineage_partition_fails(self) -> None:
        inconsistent = synthetic_idea(
            "inconsistent", status="verified", classification="unverified"
        )
        with self.assertRaisesRegex(LearningMetricError, "full schema"):
            self.measure_ideas([inconsistent])

    def test_exact_repeat_age_supports_fractional_hours(self) -> None:
        repeat = synthetic_idea(
            "fractional-age",
            status="verified",
            classification="repeat_unchanged",
            first_seen_at="2099-01-01T00:00:00Z",
            last_seen_at="2099-01-01T00:30:00Z",
            repeat_reason="A fictional pending review remains decision-useful.",
        )
        measured = self.measure_ideas([repeat])
        self.assertEqual("1/2", measured["repeat_age_hours"]["median"])
        self.assertEqual("1/2", measured["repeat_age_hours"]["maximum"])

    def test_exact_repeat_age_preserves_subsecond_precision(self) -> None:
        tenth_second = synthetic_idea(
            "tenth-second-age",
            status="verified",
            classification="repeat_unchanged",
            first_seen_at="2099-01-01T00:00:00.1Z",
            last_seen_at="2099-01-01T00:00:00.2Z",
            repeat_reason="A fictional pending review remains decision-useful.",
        )
        measured = self.measure_ideas([tenth_second])
        self.assertEqual("1/36000", measured["repeat_age_hours"]["median"])

        beyond_microseconds = synthetic_idea(
            "sub-microsecond-age",
            status="verified",
            classification="repeat_unchanged",
            first_seen_at="2099-01-01T00:00:00.1234567Z",
            last_seen_at="2099-01-01T00:00:00.1234568Z",
            repeat_reason="A fictional pending review remains decision-useful.",
        )
        measured = self.measure_ideas([beyond_microseconds])
        self.assertEqual(
            "1/36000000000", measured["repeat_age_hours"]["median"]
        )

    def test_six_decision_chain_truth_table_counts_all_exclusions(self) -> None:
        case = self.cases["chain_exclusions"]
        measured = self.measure_reviews(case["targets"], self.chain_reviews())
        self.assertEqual(case["expected_review_cohort"], measured["review_cohort"])

    def test_each_ambiguous_topology_is_unresolved_independently(self) -> None:
        case = self.cases["chain_exclusions"]
        for target in case["targets"]:
            if target["case"] not in {
                "dangling_predecessor",
                "cycle",
                "fork",
                "multiple_unlinked_heads",
            }:
                continue
            measured = self.measure_reviews([target], self.chain_reviews())
            with self.subTest(case=target["case"]):
                self.assertEqual(
                    1, measured["review_cohort"]["exclusions"]["unresolved"]
                )

    def test_predecessor_and_successor_count_once_using_terminal_only(self) -> None:
        decision_ref = "ref_SYNTHMETRICTERMINALDECISION"
        idea_ref = "ref_SYNTHMETRICTERMINALIDEA0001"
        predecessor = synthetic_review(
            "TERMINALROOT0001",
            decision_ref,
            idea_ref,
            timing_classification="undisciplined",
        )
        successor = synthetic_review(
            "TERMINALNEXT0001",
            decision_ref,
            idea_ref,
            prior_review_ref=predecessor["review_id"],
            timing_classification="disciplined",
            trigger_state="triggered",
            response_state="followed",
        )
        measured = self.measure_reviews(
            [{"decision_ref": decision_ref, "idea_ref": idea_ref}],
            [successor, predecessor],
        )
        self.assertEqual(1, measured["review_cohort"]["measured_decision_count"])
        self.assertEqual(1, measured["timing"]["classification_counts"]["disciplined"])
        self.assertEqual(
            0, measured["timing"]["classification_counts"]["undisciplined"]
        )
        self.assertEqual(1, measured["invalidations"]["triggered_count"])

    def test_latest_timestamp_cannot_override_terminal_topology(self) -> None:
        decision_ref = "ref_SYNTHMETRICTIMESTAMPDECISION"
        idea_ref = "ref_SYNTHMETRICTIMESTAMPIDEA0001"
        predecessor = synthetic_review("TIMESTAMPROOT01", decision_ref, idea_ref)
        predecessor["clocks"]["evidence_cutoff_at"] = "2099-12-30T00:00:00Z"
        predecessor["clocks"]["reviewed_at"] = "2099-12-31T00:00:00Z"
        successor = synthetic_review(
            "TIMESTAMPNEXT01",
            decision_ref,
            idea_ref,
            prior_review_ref=predecessor["review_id"],
            timing_classification="undisciplined",
        )
        self.assertGreater(
            predecessor["clocks"]["reviewed_at"], successor["clocks"]["reviewed_at"]
        )
        measured = self.measure_reviews(
            [{"decision_ref": decision_ref, "idea_ref": idea_ref}],
            [predecessor, successor],
        )
        self.assertEqual(
            1, measured["timing"]["classification_counts"]["undisciplined"]
        )
        self.assertEqual(0, measured["timing"]["classification_counts"]["disciplined"])

    def test_cross_identity_predecessor_is_unresolved(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICCROSSDECISION01",
            "idea_ref": "ref_SYNTHMETRICCROSSIDEA00001",
        }
        predecessor = synthetic_review(
            "CROSSROOT000001",
            "ref_SYNTHMETRICOTHERDECISION1",
            "ref_SYNTHMETRICOTHERIDEA00001",
        )
        successor = synthetic_review(
            "CROSSNEXT000001",
            target["decision_ref"],
            target["idea_ref"],
            prior_review_ref=predecessor["review_id"],
        )
        measured = self.measure_reviews([target], [predecessor, successor])
        self.assertEqual(0, measured["review_cohort"]["measured_decision_count"])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["unresolved"])

    def test_cross_identity_successor_pointing_into_chain_is_unresolved(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICOUTGOINGDECISION",
            "idea_ref": "ref_SYNTHMETRICOUTGOINGIDEA001",
        }
        target_review = synthetic_review(
            "OUTGOINGROOT0001", target["decision_ref"], target["idea_ref"]
        )
        cross_successor = synthetic_review(
            "OUTGOINGCROSS001",
            "ref_SYNTHMETRICOTHEROUTGOINGDEC",
            "ref_SYNTHMETRICOTHEROUTGOINGIDEA",
            prior_review_ref=target_review["review_id"],
        )
        self.assertTrue(self.full_review_is_valid(target_review))
        self.assertTrue(self.full_review_is_valid(cross_successor))
        measured = self.measure_reviews([target], [target_review, cross_successor])
        self.assertEqual(0, measured["review_cohort"]["measured_decision_count"])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["unresolved"])

    def test_malformed_successor_pointing_into_chain_is_invalid(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICBADOUTDECISION01",
            "idea_ref": "ref_SYNTHMETRICBADOUTIDEA00001",
        }
        target_review = synthetic_review(
            "BADOUTROOT000001", target["decision_ref"], target["idea_ref"]
        )
        malformed_successor = synthetic_review(
            "BADOUTCHILD00001",
            "ref_SYNTHMETRICBADOUTOTHERDEC",
            "ref_SYNTHMETRICBADOUTOTHERIDEA",
            prior_review_ref=target_review["review_id"],
        )
        malformed_successor["links"].pop("decision_ref")
        self.assertFalse(self.full_review_is_valid(malformed_successor))
        measured = self.measure_reviews(
            [target], [target_review, malformed_successor]
        )
        self.assertEqual(0, measured["review_cohort"]["measured_decision_count"])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["invalid"])

    def test_duplicate_review_id_is_unresolved(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICDUPDECISION001",
            "idea_ref": "ref_SYNTHMETRICDUPIDEA000001",
        }
        review = synthetic_review(
            "DUPLICATE0000001", target["decision_ref"], target["idea_ref"]
        )
        duplicate = copy.deepcopy(review)
        duplicate["timing_discipline"]["classification"] = "undisciplined"
        measured = self.measure_reviews([target], [review, duplicate])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["unresolved"])

    def test_attributable_malformed_review_is_invalid(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICINVALIDDECISION1",
            "idea_ref": "ref_SYNTHMETRICINVALIDIDEA0001",
        }
        review = synthetic_review(
            "INVALID000000001", target["decision_ref"], target["idea_ref"]
        )
        review["timing_discipline"]["assessment_state"] = "malformed"
        measured = self.measure_reviews([target], [review])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["invalid"])
        self.assertEqual(0, measured["review_cohort"]["exclusions"]["unresolved"])

    def test_truncated_review_cannot_be_measured(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICTRUNCATEDDECISION",
            "idea_ref": "ref_SYNTHMETRICTRUNCATEDIDEA01",
        }
        truncated = {
            "schema_version": "1.0.0",
            "review_id": "orv_SYNTHMETRICTRUNCATED0001",
            "links": dict(target),
            "timing_discipline": {
                "assessment_state": "assessable",
                "classification": "disciplined",
            },
            "invalidation_trigger": {"state": "not_triggered"},
            "invalidation_response": {"state": "not_applicable"},
        }
        self.assertFalse(self.full_review_is_valid(truncated))
        measured = self.measure_reviews([target], [truncated])
        self.assertEqual(0, measured["review_cohort"]["measured_decision_count"])
        self.assertEqual(1, measured["review_cohort"]["exclusions"]["invalid"])

    def test_empty_decision_cohort_makes_every_denominator_unavailable(self) -> None:
        measured = self.measure_reviews([], [])
        self.assertEqual(
            NOT_AVAILABLE,
            measured["review_cohort"]["measurement_coverage"]["value"],
        )
        self.assertEqual(
            NOT_AVAILABLE,
            measured["timing"]["rates"]["classification_coverage"]["value"],
        )
        self.assertEqual(
            NOT_AVAILABLE,
            measured["invalidations"]["rates"]["trigger_ascertainment"]["value"],
        )
        for response_rate in measured["invalidations"]["rates"][
            "triggered_response_shares"
        ].values():
            self.assertEqual(NOT_AVAILABLE, response_rate["value"])

    def test_limited_timing_states_never_become_classifications(self) -> None:
        states = ("unknown", "unavailable", "not_applicable")
        targets = []
        reviews = []
        for index, state in enumerate(states, start=1):
            decision_ref = f"ref_SYNTHMETRICLIMITDECISION{index}"
            idea_ref = f"ref_SYNTHMETRICLIMITIDEA000{index}"
            targets.append({"decision_ref": decision_ref, "idea_ref": idea_ref})
            reviews.append(
                synthetic_review(
                    f"LIMITED0000000{index}",
                    decision_ref,
                    idea_ref,
                    timing_state=state,
                    timing_classification=None,
                )
            )
        measured = self.measure_reviews(targets, reviews)
        self.assertEqual(2, measured["timing"]["applicable_count"])
        self.assertEqual(0, measured["timing"]["classified_count"])
        self.assertEqual(
            {"disciplined": 0, "mixed": 0, "undisciplined": 0},
            measured["timing"]["classification_counts"],
        )
        self.assertEqual(
            "0", measured["timing"]["rates"]["classification_coverage"]["value"]
        )

    def test_partial_timing_is_classified_and_visible_in_cross_tab(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICPARTIALDECISION",
            "idea_ref": "ref_SYNTHMETRICPARTIALIDEA001",
        }
        review = synthetic_review(
            "PARTIAL000000001",
            target["decision_ref"],
            target["idea_ref"],
            timing_state="partial",
            timing_classification="mixed",
        )
        measured = self.measure_reviews([target], [review])
        self.assertEqual(1, measured["timing"]["assessment_state_counts"]["partial"])
        self.assertEqual(
            1, measured["timing"]["state_by_classification"]["partial"]["mixed"]
        )

    def test_no_definitive_trigger_makes_incidence_unavailable(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICAMBIGDECISION01",
            "idea_ref": "ref_SYNTHMETRICAMBIGIDEA00001",
        }
        review = synthetic_review(
            "AMBIGUOUS0000001",
            target["decision_ref"],
            target["idea_ref"],
            trigger_state="ambiguous",
            response_state="ambiguous",
        )
        measured = self.measure_reviews([target], [review])
        self.assertEqual(
            {"numerator": 0, "denominator": 1, "value": "0"},
            measured["invalidations"]["rates"]["trigger_ascertainment"],
        )
        self.assertEqual(
            NOT_AVAILABLE,
            measured["invalidations"]["rates"]["trigger_incidence"]["value"],
        )

    def test_no_triggered_review_makes_response_shares_unavailable(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICNOTRIGGERDECISION",
            "idea_ref": "ref_SYNTHMETRICNOTRIGGERIDEA01",
        }
        review = synthetic_review(
            "NOTRIGGER0000001", target["decision_ref"], target["idea_ref"]
        )
        measured = self.measure_reviews([target], [review])
        self.assertEqual(
            {"numerator": 0, "denominator": 1, "value": "0"},
            measured["invalidations"]["rates"]["trigger_incidence"],
        )
        for response_rate in measured["invalidations"]["rates"][
            "triggered_response_shares"
        ].values():
            self.assertEqual(NOT_AVAILABLE, response_rate["value"])

    def test_research_outcome_cannot_change_timing_or_invalidation_metrics(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICINDEPENDENTDEC",
            "idea_ref": "ref_SYNTHMETRICINDEPENDENTIDEA",
        }
        favorable = synthetic_review(
            "INDEPENDENT00001",
            target["decision_ref"],
            target["idea_ref"],
            trigger_state="triggered",
            response_state="delayed",
            research_outcome="favorable",
        )
        adverse = copy.deepcopy(favorable)
        adverse["research_outcome"]["classification"] = "adverse"
        favorable_result = self.measure_reviews([target], [favorable])
        adverse_result = self.measure_reviews([target], [adverse])
        self.assertEqual(favorable_result["timing"], adverse_result["timing"])
        self.assertEqual(
            favorable_result["invalidations"], adverse_result["invalidations"]
        )

    def test_wrong_rate_or_hidden_exclusion_claim_fails(self) -> None:
        measured = self.measure_ideas(self.balanced_ideas())
        wrong_rate = copy.deepcopy(measured)
        wrong_rate["rates"]["new_idea"]["value"] = "1/4"
        with self.assertRaisesRegex(LearningMetricError, "do not exactly match"):
            assert_metric_claim(measured, wrong_rate)

        hidden_exclusion = copy.deepcopy(measured)
        hidden_exclusion["cohort"].pop("exclusions")
        with self.assertRaisesRegex(LearningMetricError, "do not exactly match"):
            assert_metric_claim(measured, hidden_exclusion)

    def test_rate_rejects_impossible_counts(self) -> None:
        for numerator, denominator in ((-1, 1), (1, -1), (2, 1)):
            with self.subTest(numerator=numerator, denominator=denominator):
                with self.assertRaises(LearningMetricError):
                    rate(numerator, denominator)

    def test_duplicate_decision_target_fails_frozen_cohort(self) -> None:
        target = {
            "decision_ref": "ref_SYNTHMETRICDUPTARGETDECISION",
            "idea_ref": "ref_SYNTHMETRICDUPTARGETIDEA01",
        }
        with self.assertRaisesRegex(LearningMetricError, "repeats decision_ref"):
            self.measure_reviews([target, copy.deepcopy(target)], [])

    def test_validator_execution_failure_aborts_measurement_consistently(self) -> None:
        idea = synthetic_idea("validator-error", status="verified", classification="new")

        def broken_idea_validator(_idea: object) -> bool:
            raise RuntimeError("synthetic validator outage")

        with self.assertRaisesRegex(LearningMetricError, "validation could not complete"):
            measure_idea_cohort([idea], idea_validator=broken_idea_validator)

        target = {
            "decision_ref": "ref_SYNTHMETRICVALIDATORDECISION",
            "idea_ref": "ref_SYNTHMETRICVALIDATORIDEA01",
        }
        review = synthetic_review(
            "VALIDATORERROR001", target["decision_ref"], target["idea_ref"]
        )

        def broken_review_validator(_review: object) -> bool:
            raise RuntimeError("synthetic validator outage")

        with self.assertRaisesRegex(LearningMetricError, "validation could not complete"):
            measure_outcome_review_cohort(
                [target], [review], review_validator=broken_review_validator
            )

    def test_truth_table_identifiers_are_visibly_synthetic(self) -> None:
        identifier_keys = {
            "decision_ref",
            "idea_ref",
            "review_id",
            "prior_review_ref",
        }

        def walk(value: object, key: str | None = None) -> None:
            if isinstance(value, dict):
                for child_key, child in value.items():
                    walk(child, child_key)
            elif isinstance(value, list):
                for child in value:
                    walk(child, key)
            elif key in identifier_keys:
                self.assertIsInstance(value, str)
                self.assertIn("SYNTH", value)

        walk(self.cases)

    def test_truth_table_contains_no_private_or_performance_fields(self) -> None:
        prohibited = {
            "account",
            "allocation",
            "asset",
            "benchmark",
            "client",
            "deployment_action",
            "holding",
            "performance",
            "pnl",
            "portfolio",
            "price",
            "return",
            "symbol",
            "ticker",
            "transaction",
        }
        discovered: set[str] = set()

        def walk(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    discovered.add(key.lower())
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.cases)
        self.assertTrue(prohibited.isdisjoint(discovered))


if __name__ == "__main__":
    unittest.main()

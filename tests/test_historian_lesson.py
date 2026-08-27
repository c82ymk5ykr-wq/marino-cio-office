"""Tests for human-approved, versioned Chief Historian lesson controls."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from schema_helpers import load_json, validator_for
from scripts.validate import (
    validate_decision_historian_lesson_refs,
    validate_historian_lesson,
    validate_historian_lesson_chain,
)


SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic"


class HistorianLessonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lesson_validator = validator_for(
            "schemas/v1/historian-lesson.schema.json"
        )
        cls.decision_validator = validator_for(
            "schemas/v1/decision-record.schema.json"
        )
        cls.initial = load_json(
            "examples/synthetic/historian-lesson-initial.json"
        )
        cls.revised = load_json(
            "examples/synthetic/historian-lesson-revised.json"
        )
        cls.retired = load_json(
            "examples/synthetic/historian-lesson-retired.json"
        )
        cls.decision = load_json(
            "examples/synthetic/decision-record-historian-lesson.json"
        )
        cls.legacy_decision = load_json("examples/synthetic/decision-record.json")

    def lesson_errors(self, lesson: object) -> list[str]:
        errors: list[str] = []
        validate_historian_lesson(
            lesson, Path("examples/synthetic/test-historian-lesson.json"), errors
        )
        return errors

    def lesson_items(self, *lessons: object) -> list[tuple[Path, object]]:
        return [
            (Path(f"examples/synthetic/test-historian-lesson-{index}.json"), lesson)
            for index, lesson in enumerate(lessons, start=1)
        ]

    def chain_errors(self, *lessons: object) -> list[str]:
        errors: list[str] = []
        validate_historian_lesson_chain(self.lesson_items(*lessons), errors)
        return errors

    def selection_errors(
        self, decision: object, *lessons: object
    ) -> list[str]:
        errors: list[str] = []
        validate_decision_historian_lesson_refs(
            decision,
            self.lesson_items(*lessons),
            Path("examples/synthetic/test-decision-record.json"),
            errors,
        )
        return errors

    def assert_schema_valid(self, validator: object, instance: object) -> None:
        self.assertEqual([], list(validator.iter_errors(instance)))

    def test_initial_revised_and_retired_fixtures_are_valid(self) -> None:
        for name, lesson in (
            ("initial", self.initial),
            ("revised", self.revised),
            ("retired", self.retired),
        ):
            with self.subTest(fixture=name):
                self.assert_schema_valid(self.lesson_validator, lesson)
                self.assertEqual([], self.lesson_errors(lesson))

        self.assertEqual([], self.chain_errors(self.initial, self.revised, self.retired))
        self.assertEqual(1, self.initial["revision"])
        self.assertNotIn("prior_version_ref", self.initial)
        self.assertEqual(
            self.initial["lesson_version_ref"], self.revised["prior_version_ref"]
        )
        self.assertEqual(
            self.revised["lesson_version_ref"], self.retired["prior_version_ref"]
        )
        self.assertEqual("retired", self.retired["state"])
        self.assertNotIn("content_ref", self.retired)

    def test_human_approval_and_successful_advisory_ingestion_are_required(
        self,
    ) -> None:
        cases = []

        missing_approval = copy.deepcopy(self.initial)
        del missing_approval["approval"]
        cases.append(missing_approval)

        non_human = copy.deepcopy(self.initial)
        non_human["approval"]["authority_type"] = "machine"
        cases.append(non_human)

        unapproved = copy.deepcopy(self.initial)
        unapproved["approval"]["status"] = "pending"
        cases.append(unapproved)

        missing_ingestion = copy.deepcopy(self.initial)
        del missing_ingestion["ingestion"]
        cases.append(missing_ingestion)

        failed_ingestion = copy.deepcopy(self.initial)
        failed_ingestion["ingestion"]["status"] = "failed"
        cases.append(failed_ingestion)

        executable_ingestion = copy.deepcopy(self.initial)
        executable_ingestion["ingestion"]["mode"] = "execute"
        cases.append(executable_ingestion)

        for index, lesson in enumerate(cases):
            with self.subTest(case=index):
                self.assertTrue(list(self.lesson_validator.iter_errors(lesson)))

    def test_revision_state_and_content_shape_is_closed(self) -> None:
        cases = []

        initial_with_predecessor = copy.deepcopy(self.initial)
        initial_with_predecessor["prior_version_ref"] = self.initial[
            "lesson_version_ref"
        ]
        cases.append(initial_with_predecessor)

        initial_retired = copy.deepcopy(self.initial)
        initial_retired["state"] = "retired"
        del initial_retired["content_ref"]
        cases.append(initial_retired)

        active_without_content = copy.deepcopy(self.revised)
        del active_without_content["content_ref"]
        cases.append(active_without_content)

        retired_with_content = copy.deepcopy(self.retired)
        retired_with_content["content_ref"] = "ref_SYNTH000000000299"
        cases.append(retired_with_content)

        successor_without_predecessor = copy.deepcopy(self.revised)
        del successor_without_predecessor["prior_version_ref"]
        cases.append(successor_without_predecessor)

        for index, lesson in enumerate(cases):
            with self.subTest(case=index):
                self.assertTrue(list(self.lesson_validator.iter_errors(lesson)))

    def test_receipt_and_reference_tokens_reject_paths_urls_and_latest_aliases(
        self,
    ) -> None:
        mutations = []
        for field_path, value in (
            (("approval", "receipt"), "/private/approval.json"),
            (("ingestion", "receipt"), "https://example.invalid/receipt"),
            (("content_ref",), "sha256:synthetic"),
            (("prior_version_ref",), "hlv_latest"),
        ):
            lesson = copy.deepcopy(self.revised)
            container = lesson
            for part in field_path[:-1]:
                container = container[part]
            container[field_path[-1]] = value
            mutations.append(lesson)

        for index, lesson in enumerate(mutations):
            with self.subTest(case=index):
                self.assertTrue(list(self.lesson_validator.iter_errors(lesson)))

    def test_reused_receipts_and_content_are_rejected_across_revisions(self) -> None:
        cases = []

        reused_approval = copy.deepcopy(self.revised)
        reused_approval["approval"]["receipt"] = self.initial["approval"]["receipt"]
        cases.append(reused_approval)

        reused_ingestion = copy.deepcopy(self.revised)
        reused_ingestion["ingestion"]["receipt"] = self.initial["ingestion"][
            "receipt"
        ]
        cases.append(reused_ingestion)

        reused_content = copy.deepcopy(self.revised)
        reused_content["content_ref"] = self.initial["content_ref"]
        cases.append(reused_content)

        for index, successor in enumerate(cases):
            with self.subTest(case=index):
                self.assertTrue(self.chain_errors(self.initial, successor))

    def test_gaps_branches_cycles_and_cross_series_links_are_rejected(self) -> None:
        gap = copy.deepcopy(self.revised)
        gap["revision"] = 3

        branch = copy.deepcopy(self.revised)
        branch["lesson_version_ref"] = "hlv_SYNTH000000000199"
        branch["approval"]["receipt"] = "apr_SYNTH000000000199"
        branch["ingestion"]["receipt"] = "ing_SYNTH000000000199"
        branch["content_ref"] = "ref_SYNTH000000000299"

        cycle = copy.deepcopy(self.revised)
        cycle["prior_version_ref"] = cycle["lesson_version_ref"]

        cross_series = copy.deepcopy(self.revised)
        cross_series["lesson_series_id"] = "hls_SYNTH000000000099"

        duplicate_version = copy.deepcopy(self.revised)
        duplicate_version["lesson_version_ref"] = self.initial["lesson_version_ref"]

        after_retirement = copy.deepcopy(self.retired)
        after_retirement["lesson_version_ref"] = "hlv_SYNTH000000000104"
        after_retirement["revision"] = 4
        after_retirement["state"] = "active"
        after_retirement["prior_version_ref"] = self.retired["lesson_version_ref"]
        after_retirement["approval"]["receipt"] = "apr_SYNTH000000000104"
        after_retirement["ingestion"]["receipt"] = "ing_SYNTH000000000104"
        after_retirement["content_ref"] = "ref_SYNTH000000000204"
        after_retirement["clocks"] = {
            "data_as_of": "2099-04-01T09:00:00Z",
            "approved_at": "2099-04-01T11:00:00Z",
            "ingested_at": "2099-04-01T12:00:00Z",
            "generated_at": "2099-04-01T13:00:00Z",
        }

        non_increasing_ingestion = copy.deepcopy(self.revised)
        non_increasing_ingestion["clocks"]["ingested_at"] = self.initial[
            "clocks"
        ]["ingested_at"]

        cases = (
            (self.initial, gap),
            (self.initial, self.revised, branch),
            (self.initial, cycle),
            (self.initial, cross_series),
            (self.initial, duplicate_version),
            (self.initial, self.revised, self.retired, after_retirement),
            (self.initial, non_increasing_ingestion),
        )
        for index, lessons in enumerate(cases):
            with self.subTest(case=index):
                self.assertTrue(self.chain_errors(*lessons))

    def test_clock_inversions_and_late_review_finalization_are_rejected(self) -> None:
        cases = []
        adjacent = (
            ("data_as_of", "approved_at"),
            ("approved_at", "ingested_at"),
            ("ingested_at", "generated_at"),
        )
        for earlier, later in adjacent:
            lesson = copy.deepcopy(self.initial)
            lesson["clocks"][earlier] = "2099-01-02T00:00:00Z"
            lesson["clocks"][later] = "2099-01-01T00:00:00Z"
            cases.append(lesson)

        late_review = copy.deepcopy(self.initial)
        late_review["source_reviews"][0]["finalized_at"] = (
            "2099-01-01T11:00:01Z"
        )
        cases.append(late_review)

        evidence_after_every_review = copy.deepcopy(self.initial)
        evidence_after_every_review["source_reviews"][0]["finalized_at"] = (
            "2099-01-01T08:59:59Z"
        )
        cases.append(evidence_after_every_review)

        duplicate_review_ref = copy.deepcopy(self.initial)
        duplicate_review_ref["source_reviews"].append(
            {
                "review_ref": duplicate_review_ref["source_reviews"][0][
                    "review_ref"
                ],
                "finalized_at": "2099-01-01T10:00:01Z",
            }
        )
        cases.append(duplicate_review_ref)

        for index, lesson in enumerate(cases):
            with self.subTest(case=index):
                self.assertTrue(self.lesson_errors(lesson))

        multiple_reviews = copy.deepcopy(self.initial)
        multiple_reviews["source_reviews"].append(
            {
                "review_ref": "orv_SYNTH000000000099",
                "finalized_at": "2098-12-01T10:00:00Z",
            }
        )
        self.assertEqual([], self.lesson_errors(multiple_reviews))

    def test_decision_record_versions_preserve_1_0_and_require_exact_1_1_refs(
        self,
    ) -> None:
        self.assert_schema_valid(self.decision_validator, self.legacy_decision)

        legacy_with_refs = copy.deepcopy(self.legacy_decision)
        legacy_with_refs["historian_lesson_version_refs"] = []
        self.assertTrue(list(self.decision_validator.iter_errors(legacy_with_refs)))

        missing_refs = copy.deepcopy(self.decision)
        del missing_refs["historian_lesson_version_refs"]
        self.assertTrue(list(self.decision_validator.iter_errors(missing_refs)))

        duplicate_refs = copy.deepcopy(self.decision)
        duplicate_refs["historian_lesson_version_refs"].append(
            duplicate_refs["historian_lesson_version_refs"][0]
        )
        self.assertTrue(list(self.decision_validator.iter_errors(duplicate_refs)))

        for invalid_ref in (
            "hls_SYNTH000000000001",
            "ref_SYNTH000000000202",
            "hlv_latest",
            "https://example.invalid/lesson",
        ):
            invalid = copy.deepcopy(self.decision)
            invalid["historian_lesson_version_refs"] = [invalid_ref]
            with self.subTest(reference=invalid_ref):
                self.assertTrue(list(self.decision_validator.iter_errors(invalid)))

        no_lesson = copy.deepcopy(self.decision)
        no_lesson["historian_lesson_version_refs"] = []
        self.assert_schema_valid(self.decision_validator, no_lesson)
        self.assertEqual([], self.selection_errors(no_lesson, self.initial))

        for clock in ("recorded_at", "review_by"):
            non_utc = copy.deepcopy(no_lesson)
            non_utc[clock] = non_utc[clock].replace("Z", "+00:00")
            with self.subTest(clock=clock):
                self.assertTrue(list(self.decision_validator.iter_errors(non_utc)))
                self.assertTrue(self.selection_errors(non_utc, self.initial))

    def test_exact_version_selection_uses_the_decision_timestamp(self) -> None:
        self.assert_schema_valid(self.decision_validator, self.decision)
        self.assertEqual(
            [],
            self.selection_errors(
                self.decision, self.initial, self.revised, self.retired
            ),
        )

        stale = copy.deepcopy(self.decision)
        stale["historian_lesson_version_refs"] = [
            self.initial["lesson_version_ref"]
        ]
        self.assertTrue(self.selection_errors(stale, self.initial, self.revised))

        future = copy.deepcopy(self.decision)
        future["recorded_at"] = "2099-01-15T14:00:00Z"
        self.assertTrue(self.selection_errors(future, self.initial, self.revised))

        retired = copy.deepcopy(self.decision)
        retired["recorded_at"] = "2099-03-01T14:00:00Z"
        retired["historian_lesson_version_refs"] = [
            self.retired["lesson_version_ref"]
        ]
        self.assertTrue(
            self.selection_errors(retired, self.initial, self.revised, self.retired)
        )

    def test_later_retirement_does_not_rewrite_an_earlier_decision(self) -> None:
        earlier_decision = copy.deepcopy(self.decision)
        preserved = copy.deepcopy(earlier_decision)

        self.assertEqual(
            [],
            self.selection_errors(
                earlier_decision, self.initial, self.revised, self.retired
            ),
        )
        self.assertEqual(preserved, earlier_decision)
        self.assertEqual(
            [self.revised["lesson_version_ref"]],
            earlier_decision["historian_lesson_version_refs"],
        )

    def test_prohibited_private_and_executable_fields_are_rejected(self) -> None:
        prohibited = (
            "lesson_body",
            "prompt",
            "code",
            "configuration",
            "threshold",
            "weight",
            "deployment_action",
            "performance",
            "account_id",
            "client_id",
            "storage_path",
            "content_url",
            "payload_hash",
            "approval_identity",
            "provider",
            "usage_count",
            "aggregate",
        )
        for field in prohibited:
            lesson = copy.deepcopy(self.initial)
            lesson[field] = "invented but prohibited"
            with self.subTest(field=field):
                self.assertTrue(list(self.lesson_validator.iter_errors(lesson)))

        nested_locations = ("clocks", "approval", "ingestion")
        for location in nested_locations:
            lesson = copy.deepcopy(self.initial)
            lesson[location]["prompt"] = "invented but prohibited"
            with self.subTest(location=location):
                self.assertTrue(list(self.lesson_validator.iter_errors(lesson)))


if __name__ == "__main__":
    unittest.main()

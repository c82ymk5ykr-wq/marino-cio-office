#!/usr/bin/env python3
"""Validation for the public Marino CIO Office contract repository."""

from __future__ import annotations

import copy
import json
import math
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from statistics import median
from urllib.parse import unquote

try:
    from scripts.learning_metrics import (
        LearningMetricError,
        assert_metric_claim,
        measure_idea_cohort,
        measure_outcome_review_cohort,
    )
except ModuleNotFoundError:  # Direct execution uses the sibling module path.
    from learning_metrics import (  # type: ignore[no-redef]
        LearningMetricError,
        assert_metric_claim,
        measure_idea_cohort,
        measure_outcome_review_cohort,
    )

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError as exc:  # Reported as one actionable repository error in main().
    Draft202012Validator = None
    FormatChecker = None
    SchemaError = Exception
    JSONSCHEMA_IMPORT_ERROR: ImportError | None = exc
else:
    JSONSCHEMA_IMPORT_ERROR = None


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    ".gitattributes",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/quality.yml",
    ".gitignore",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "docs/decisions/0001-public-operating-foundation.md",
    "docs/decisions/0002-canonical-contract-vocabulary.md",
    "docs/decisions/0003-deterministic-universe-completion-gates.md",
    "docs/decisions/0004-verifiable-idea-lineage.md",
    "docs/decisions/0005-v1-schema-compatibility-gate.md",
    "docs/decisions/0006-deterministic-report-acceptance.md",
    "docs/decisions/0007-private-contract-adoption-attestation.md",
    "docs/decisions/0008-append-only-outcome-review.md",
    "docs/decisions/0009-deterministic-learning-loop-measurement.md",
    "docs/decisions/0010-human-approved-versioned-historian-lessons.md",
    "docs/decisions/README.md",
    "docs/contract-vocabulary.md",
    "docs/historian-lesson-contract.md",
    "docs/idea-lineage-metrics.md",
    "docs/learning-loop-metrics.md",
    "docs/operating-model.md",
    "docs/outcome-review-contract.md",
    "docs/public-private-boundary.md",
    "docs/report-acceptance-gates.md",
    "docs/schema-compatibility-policy.md",
    "docs/specification-inventory.md",
    "docs/universe-completion-gates.md",
    "examples/synthetic/decision-record-historian-lesson.json",
    "examples/synthetic/decision-record.json",
    "examples/synthetic/historian-lesson-initial.json",
    "examples/synthetic/historian-lesson-retired.json",
    "examples/synthetic/historian-lesson-revised.json",
    "examples/synthetic/investment-idea.json",
    "examples/synthetic/investment-idea-legacy-1.0.json",
    "examples/synthetic/investment-idea-materially-updated.json",
    "examples/synthetic/investment-idea-reintroduced.json",
    "examples/synthetic/investment-idea-repeat-unchanged.json",
    "examples/synthetic/investment-idea-stale-repeat.json",
    "examples/synthetic/investment-idea-unverified-lineage.json",
    "examples/synthetic/learning-metrics-cases.json",
    "examples/synthetic/outcome-review-adverse-disciplined.json",
    "examples/synthetic/outcome-review-favorable-undisciplined.json",
    "examples/synthetic/outcome-review-invalidation-delayed.json",
    "examples/synthetic/outcome-review-invalidation-followed.json",
    "examples/synthetic/outcome-review-partial.json",
    "examples/synthetic/outcome-review-unknown-unverified.json",
    "examples/synthetic/outcome-review-unavailable.json",
    "examples/synthetic/report-acceptance-cases.json",
    "examples/synthetic/report-manifest-legacy-1.0.json",
    "examples/synthetic/report-manifest.json",
    "examples/synthetic/universe-completion-cases.json",
    "requirements-validation.txt",
    "schemas/v1/decision-record.schema.json",
    "schemas/v1/historian-lesson.schema.json",
    "schemas/v1/investment-idea.schema.json",
    "schemas/v1/outcome-review.schema.json",
    "schemas/v1/report-manifest.schema.json",
    "scripts/validate.py",
    "scripts/learning_metrics.py",
    "templates/architecture-decision.md",
    "templates/daily-decision-report.md",
    "templates/decision-record.md",
    "templates/historian-lesson.md",
    "templates/outcome-review.md",
    "tests/compatibility/v1-fixtures.json",
    "tests/schema_helpers.py",
    "tests/test_report_acceptance.py",
    "tests/test_schema_compatibility.py",
    "tests/test_schema_validation.py",
    "tests/test_historian_lesson.py",
    "tests/test_learning_metrics.py",
    "tests/test_outcome_review.py",
}

SCHEMA_FIXTURE_FAMILIES = {
    Path("schemas/v1/report-manifest.schema.json"): "report-manifest",
    Path("schemas/v1/investment-idea.schema.json"): "investment-idea",
    Path("schemas/v1/decision-record.schema.json"): "decision-record",
    Path("schemas/v1/outcome-review.schema.json"): "outcome-review",
    Path("schemas/v1/historian-lesson.schema.json"): "historian-lesson",
}

FORBIDDEN_DIRECTORIES = {
    "artifacts",
    "exports",
    "logs",
    "private",
    "snapshots",
}

FORBIDDEN_SUFFIXES = {
    ".arrow",
    ".csv",
    ".db",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".pdf",
    ".pkl",
    ".sqlite",
    ".sqlite3",
    ".tsv",
    ".xls",
    ".xlsx",
}

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
UTC_TIMESTAMP_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z"
)


def tracked_files() -> list[Path]:
    """Return tracked paths, with a filesystem fallback before local git init."""

    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return sorted(
            path.relative_to(ROOT)
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )

    names = output.decode("utf-8").split("\0")
    return [Path(name) for name in names if name]


def parse_utc_timestamp(value: object, location: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_TEXT.fullmatch(value):
        errors.append(f"{location}: timestamp must be a UTC string ending in Z")
        return

    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{location}: invalid ISO-8601 timestamp {value!r}")
        return
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        errors.append(f"{location}: timestamp must use UTC")


def walk_timestamps(value: object, location: str, errors: list[str]) -> None:
    timestamp_keys = {
        "checked_at",
        "approved_at",
        "data_as_of",
        "decision_recorded_at",
        "evaluation_started_at",
        "evidence_cutoff_at",
        "first_seen_at",
        "finalized_at",
        "generated_at",
        "ingested_at",
        "last_seen_at",
        "last_material_change_at",
        "membership_as_of",
        "oldest_material_source_as_of",
        "persisted_at",
        "recorded_at",
        "responded_at",
        "retrieved_at",
        "review_by",
        "reviewed_at",
        "triggered_at",
    }

    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key in timestamp_keys:
                parse_utc_timestamp(child, child_location, errors)
            else:
                walk_timestamps(child, child_location, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_timestamps(child, f"{location}[{index}]", errors)


def validate_relative_links(path: Path, text: str, errors: list[str]) -> None:
    for match in MARKDOWN_LINK.finditer(text):
        raw_target = match.group(1).strip().strip("<>")
        if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:")):
            continue

        target_without_fragment = raw_target.split("#", 1)[0].split("?", 1)[0]
        target_without_title = target_without_fragment.split(maxsplit=1)[0]
        target = (ROOT / path.parent / unquote(target_without_title)).resolve()

        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{path}: relative link escapes repository: {raw_target}")
            continue

        if not target.exists():
            errors.append(f"{path}: broken relative link: {raw_target}")


def validate_public_path(path: Path, errors: list[str]) -> None:
    lower = path.as_posix().lower()
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()

    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        errors.append(f"{path}: environment file must not be tracked")

    if name.startswith(".secrets") and name != ".secrets.example":
        errors.append(f"{path}: secrets file must not be tracked")

    if any(part in FORBIDDEN_DIRECTORIES for part in parts):
        errors.append(f"{path}: private/generated directory must not be tracked")

    if lower.startswith(("data/raw/", "data/client/", "reports/generated/")):
        errors.append(f"{path}: private/generated path must not be tracked")

    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        errors.append(f"{path}: binary, export, or provider-data format is forbidden")

    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        errors.append(f"{path}: credential-like file is forbidden")

    if name.startswith("credentials") and name.endswith(".json"):
        errors.append(f"{path}: credential-like file is forbidden")

    if "service-account" in name and name.endswith(".json"):
        errors.append(f"{path}: service-account file is forbidden")


def load_json(path: Path, errors: list[str]) -> object | None:
    def reject_non_finite_constant(value: str) -> object:
        raise ValueError(f"non-finite numeric constant {value}")

    try:
        return json.loads(
            (ROOT / path).read_text(encoding="utf-8"),
            parse_constant=reject_non_finite_constant,
        )
    except json.JSONDecodeError as exc:
        errors.append(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}")
    except ValueError as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
    return None


def render_json_path(parts: object) -> str:
    """Render a jsonschema path deque as a stable JSONPath-like location."""

    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        elif isinstance(part, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            result += f".{part}"
        else:
            result += f"[{json.dumps(part)}]"
    return result


def validate_json_schema_examples(
    parsed: dict[Path, object], errors: list[str]
) -> None:
    """Validate public artifact fixtures against their canonical Draft 2020-12 schemas."""

    if JSONSCHEMA_IMPORT_ERROR is not None:
        errors.append(
            "JSON Schema validation dependency is missing; install "
            "requirements-validation.txt before running scripts/validate.py"
        )
        return

    assert Draft202012Validator is not None
    assert FormatChecker is not None

    fixture_root = Path("examples/synthetic")
    format_checker = FormatChecker()
    fixture_mapping_counts: dict[Path, int] = {}

    for schema_path, fixture_prefix in SCHEMA_FIXTURE_FAMILIES.items():
        schema = parsed.get(schema_path)
        if not isinstance(schema, dict):
            errors.append(f"{schema_path}: schema could not be loaded")
            continue

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            schema_location = render_json_path(exc.absolute_schema_path)
            errors.append(
                f"{schema_path}:{schema_location}: invalid Draft 2020-12 schema: "
                f"{exc.message}"
            )
            continue

        validator = Draft202012Validator(schema, format_checker=format_checker)
        fixture_paths = sorted(
            path
            for path in parsed
            if path.parent == fixture_root
            and path.name.startswith(fixture_prefix)
            and path.suffix == ".json"
        )
        if not fixture_paths:
            errors.append(f"{schema_path}: no synthetic fixtures found")
            continue

        for fixture_path in fixture_paths:
            fixture_mapping_counts[fixture_path] = (
                fixture_mapping_counts.get(fixture_path, 0) + 1
            )
            instance = parsed[fixture_path]
            schema_errors = sorted(
                validator.iter_errors(instance),
                key=lambda exc: (
                    tuple(str(part) for part in exc.absolute_path),
                    tuple(str(part) for part in exc.absolute_schema_path),
                    str(exc.validator),
                    exc.message,
                ),
            )
            for exc in schema_errors:
                instance_location = render_json_path(exc.absolute_path)
                errors.append(
                    f"{fixture_path}:{instance_location}: schema violation: "
                    f"{exc.message}"
                )

    exempt_fixture_paths = {
        Path("examples/synthetic/learning-metrics-cases.json"),
        Path("examples/synthetic/report-acceptance-cases.json"),
        Path("examples/synthetic/universe-completion-cases.json"),
    }
    all_synthetic_json = {
        path
        for path in parsed
        if path.parent == fixture_root and path.suffix == ".json"
    }
    unmapped = sorted(
        all_synthetic_json - fixture_mapping_counts.keys() - exempt_fixture_paths
    )
    for fixture_path in unmapped:
        errors.append(f"{fixture_path}: synthetic JSON fixture is not schema-mapped or exempt")
    for fixture_path, count in sorted(fixture_mapping_counts.items()):
        if count != 1:
            errors.append(f"{fixture_path}: synthetic fixture maps to {count} schemas")


def require_keys(
    value: object, keys: set[str], location: str, errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{location}: expected a JSON object")
        return

    missing = sorted(keys - value.keys())
    if missing:
        errors.append(f"{location}: missing required keys: {', '.join(missing)}")


COMPLETION_PROFILE_IDS = {
    "broad_equity_daily",
    "curated_etf_daily",
    "declared_bounded_set",
}

COMPLETION_SOURCE_STATES = {
    "available",
    "equivalent_fallback",
    "stale",
    "non_equivalent_fallback",
    "unavailable",
}

COMPLETION_STATUSES = {"complete", "provisional", "degraded", "failed"}

COMPLETION_CASE_KEYS = {
    "artifact_status",
    "case_id",
    "claimed_status",
    "conflicting_duplicate_count",
    "current_retained",
    "denominator_known",
    "exact_duplicate_count",
    "expect_valid",
    "expected",
    "expected_status",
    "gap_count",
    "observed",
    "percent",
    "profile_id",
    "refreshed_this_cycle",
    "reliable_product",
    "required_period_lag",
    "required_source_state",
    "reviews_complete",
    "stale_retained",
}


def is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def is_percentage(value: object) -> bool:
    return is_finite_number(value) and 0 <= value <= 100


def exceeds_threshold(value: float, threshold: object) -> bool:
    return is_finite_number(threshold) and value > threshold


ACCEPTANCE_SOURCE_STATES = {
    "available",
    "equivalent_fallback",
    "stale",
    "non_equivalent_fallback",
    "unavailable",
}

ACCEPTANCE_OPTIONAL_SOURCE_STATES = {
    "available",
    "fallback",
    "stale",
    "unavailable",
}

ACCEPTANCE_FRESHNESS_STATES = {"fresh", "stale", "unknown"}
ACCEPTANCE_ARTIFACT_STATES = {"persisted", "failed", "not_attempted"}
OPAQUE_DURABLE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}\Z")

ACCEPTANCE_INPUT_KEYS = {
    "artifact_status",
    "denominator_known",
    "durable_receipt_present",
    "expected",
    "freshness_age_hours",
    "freshness_status",
    "freshness_threshold_hours",
    "gap_count",
    "observed",
    "optional_source_state",
    "percent",
    "reliable_product",
    "required_period_lag",
    "required_period_lag_known",
    "required_reviews_complete",
    "required_source_states",
}

ACCEPTANCE_QUALITY_FLAGS = {
    "COVERAGE_DENOMINATOR_UNKNOWN",
    "DURABLE_PERSISTENCE_FAILED",
    "DURABLE_PERSISTENCE_NOT_ATTEMPTED",
    "EMPTY_ELIGIBLE_UNIVERSE",
    "EQUIVALENT_FALLBACK_USED",
    "FRESHNESS_STALE",
    "FRESHNESS_UNKNOWN",
    "INCOMPLETE_COVERAGE",
    "NON_EQUIVALENT_FALLBACK",
    "NO_RELIABLE_DECISION_PRODUCT",
    "OPTIONAL_SOURCE_UNAVAILABLE",
    "REQUIRED_PERIOD_LAG",
    "REQUIRED_PERIOD_UNKNOWN",
    "REQUIRED_REVIEWS_INCOMPLETE",
    "REQUIRED_SOURCE_STALE",
    "REQUIRED_SOURCE_UNAVAILABLE",
}


def materialize_report_acceptance_case(
    defaults: dict[str, object], case: dict[str, object]
) -> dict[str, object]:
    """Apply one synthetic case's explicit overrides to the public defaults."""

    effective = dict(defaults)
    overrides = case.get("overrides")
    if isinstance(overrides, dict):
        effective.update(overrides)
    return effective


def derive_report_acceptance_status(
    inputs: dict[str, object],
) -> tuple[str, set[str]]:
    """Derive report status and required quality flags using safety-first precedence."""

    flags: set[str] = set()
    required_source_states = inputs.get("required_source_states")
    states = (
        {state for state in required_source_states if isinstance(state, str)}
        if isinstance(required_source_states, list)
        else set()
    )

    reliable_product = inputs.get("reliable_product") is True
    denominator_known = inputs.get("denominator_known") is True
    expected = inputs.get("expected")
    observed = inputs.get("observed")
    percent = inputs.get("percent")
    gap_count = inputs.get("gap_count")
    required_period_lag = inputs.get("required_period_lag")
    required_period_lag_known = inputs.get("required_period_lag_known") is True
    freshness_status = inputs.get("freshness_status")
    required_reviews_complete = inputs.get("required_reviews_complete") is True
    artifact_status = inputs.get("artifact_status")

    if not reliable_product:
        flags.add("NO_RELIABLE_DECISION_PRODUCT")

    if "unavailable" in states:
        flags.add("REQUIRED_SOURCE_UNAVAILABLE")
    if "non_equivalent_fallback" in states:
        flags.add("NON_EQUIVALENT_FALLBACK")
    if "stale" in states:
        flags.add("REQUIRED_SOURCE_STALE")
    if "equivalent_fallback" in states:
        flags.add("EQUIVALENT_FALLBACK_USED")

    coverage_passes = False
    if not denominator_known:
        flags.add("COVERAGE_DENOMINATOR_UNKNOWN")
    elif expected == 0:
        flags.add("EMPTY_ELIGIBLE_UNIVERSE")
    elif (
        is_non_negative_int(expected)
        and is_non_negative_int(observed)
        and observed == expected
        and is_percentage(percent)
        and abs(float(percent) - 100.0) <= 0.01
        and gap_count == 0
    ):
        coverage_passes = True
    else:
        flags.add("INCOMPLETE_COVERAGE")

    if not required_period_lag_known:
        flags.add("REQUIRED_PERIOD_UNKNOWN")
    elif required_period_lag != 0:
        flags.add("REQUIRED_PERIOD_LAG")

    if freshness_status == "stale":
        flags.add("FRESHNESS_STALE")
    elif freshness_status == "unknown":
        flags.add("FRESHNESS_UNKNOWN")

    if not required_reviews_complete:
        flags.add("REQUIRED_REVIEWS_INCOMPLETE")

    if artifact_status == "failed":
        flags.add("DURABLE_PERSISTENCE_FAILED")
    elif artifact_status == "not_attempted":
        flags.add("DURABLE_PERSISTENCE_NOT_ATTEMPTED")

    if inputs.get("optional_source_state") == "unavailable":
        flags.add("OPTIONAL_SOURCE_UNAVAILABLE")

    if not reliable_product:
        status = "failed"
    elif (
        "unavailable" in states
        or "non_equivalent_fallback" in states
        or artifact_status == "failed"
    ):
        status = "degraded"
    elif (
        not coverage_passes
        or not required_period_lag_known
        or required_period_lag != 0
        or freshness_status != "fresh"
        or "stale" in states
        or not required_reviews_complete
        or artifact_status != "persisted"
    ):
        status = "provisional"
    else:
        status = "complete"

    return status, flags


def validate_report_acceptance_input_shape(
    value: object, location: str, errors: list[str]
) -> None:
    require_keys(value, ACCEPTANCE_INPUT_KEYS, location, errors)
    if not isinstance(value, dict):
        return

    for key in (
        "denominator_known",
        "durable_receipt_present",
        "reliable_product",
        "required_period_lag_known",
        "required_reviews_complete",
    ):
        if not isinstance(value.get(key), bool):
            errors.append(f"{location}.{key}: expected a boolean")

    for key in ("expected", "observed"):
        if not is_non_negative_int(value.get(key)):
            errors.append(f"{location}.{key}: expected a non-negative integer")

    denominator_known = value.get("denominator_known")
    gap_count = value.get("gap_count")
    if denominator_known is True:
        if not is_non_negative_int(gap_count):
            errors.append(f"{location}.gap_count: expected a non-negative integer when known")
    elif denominator_known is False and gap_count is not None:
        errors.append(f"{location}.gap_count: expected null when denominator is unknown")

    required_period_lag_known = value.get("required_period_lag_known")
    required_period_lag = value.get("required_period_lag")
    if required_period_lag_known is True:
        if not is_non_negative_int(required_period_lag):
            errors.append(
                f"{location}.required_period_lag: expected a non-negative integer when known"
            )
    elif required_period_lag_known is False:
        if required_period_lag is not None:
            errors.append(
                f"{location}.required_period_lag: expected null when lag is unknown"
            )

    percent = value.get("percent")
    if not is_percentage(percent):
        errors.append(f"{location}.percent: expected a finite number from 0 to 100")

    threshold = value.get("freshness_threshold_hours")
    if (
        not is_finite_number(threshold)
        or threshold <= 0
    ):
        errors.append(
            f"{location}.freshness_threshold_hours: expected a positive number"
        )

    freshness_status = value.get("freshness_status")
    freshness_age = value.get("freshness_age_hours")
    if (
        not isinstance(freshness_status, str)
        or freshness_status not in ACCEPTANCE_FRESHNESS_STATES
    ):
        errors.append(f"{location}.freshness_status: invalid state")
    elif freshness_status == "unknown":
        if freshness_age is not None:
            errors.append(
                f"{location}.freshness_age_hours: unknown freshness requires null age"
            )
    elif (
        not is_finite_number(freshness_age)
        or freshness_age < 0
    ):
        errors.append(
            f"{location}.freshness_age_hours: expected a non-negative number"
        )
    elif (
        freshness_status == "fresh"
        and isinstance(threshold, (int, float))
        and not isinstance(threshold, bool)
        and exceeds_threshold(freshness_age, threshold)
    ):
        errors.append(f"{location}: fresh label exceeds its declared threshold")

    source_states = value.get("required_source_states")
    if (
        not isinstance(source_states, list)
        or len(source_states) != 3
        or any(
            not isinstance(state, str) or state not in ACCEPTANCE_SOURCE_STATES
            for state in source_states
        )
    ):
        errors.append(
            f"{location}.required_source_states: expected three valid role states"
        )

    optional_source_state = value.get("optional_source_state")
    if (
        not isinstance(optional_source_state, str)
        or optional_source_state not in ACCEPTANCE_OPTIONAL_SOURCE_STATES
    ):
        errors.append(f"{location}.optional_source_state: invalid state")
    artifact_status = value.get("artifact_status")
    if (
        not isinstance(artifact_status, str)
        or artifact_status not in ACCEPTANCE_ARTIFACT_STATES
    ):
        errors.append(f"{location}.artifact_status: invalid state")

    expected = value.get("expected")
    observed = value.get("observed")
    gap_count = value.get("gap_count")
    if is_non_negative_int(expected) and is_non_negative_int(observed):
        counts_are_ordered = observed <= expected
        if not counts_are_ordered:
            errors.append(f"{location}: observed exceeds expected")
        calculated = (
            0.0
            if expected == 0
            else observed / expected * 100
            if counts_are_ordered
            else None
        )
        if (
            calculated is not None
            and is_percentage(percent)
            and abs(float(percent) - calculated) > 0.01
        ):
            errors.append(f"{location}: percent does not match coverage counts")
        if (
            denominator_known is True
            and is_non_negative_int(gap_count)
            and gap_count != expected - observed
        ):
            errors.append(f"{location}: gap_count does not match coverage counts")

    receipt_present = value.get("durable_receipt_present")
    if artifact_status == "persisted" and receipt_present is not True:
        errors.append(f"{location}: persisted requires a durable receipt")
    if artifact_status in ("failed", "not_attempted") and receipt_present is not False:
        errors.append(f"{location}: non-persisted outcomes cannot claim a receipt")


def validate_report_acceptance_cases(value: object, errors: list[str]) -> None:
    path = Path("examples/synthetic/report-acceptance-cases.json")
    location = str(path)
    require_keys(value, {"spec_version", "defaults", "cases"}, location, errors)
    if not isinstance(value, dict):
        return

    if value.get("spec_version") != "1.0.0":
        errors.append(f"{location}.spec_version: expected 1.0.0")

    defaults = value.get("defaults")
    validate_report_acceptance_input_shape(
        defaults, f"{location}.defaults", errors
    )
    if not isinstance(defaults, dict):
        return

    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{location}.cases: expected a non-empty array")
        return

    seen_ids: set[str] = set()
    covered_statuses: set[str] = set()
    for index, case in enumerate(cases):
        case_location = f"{location}.cases[{index}]"
        require_keys(
            case,
            {
                "case_id",
                "claimed_status",
                "expect_valid",
                "expected_quality_flags",
                "expected_status",
                "overrides",
            },
            case_location,
            errors,
        )
        if not isinstance(case, dict):
            continue

        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{case_location}.case_id: expected a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{case_location}.case_id: duplicate case ID {case_id}")
        else:
            seen_ids.add(case_id)

        overrides = case.get("overrides")
        if not isinstance(overrides, dict):
            errors.append(f"{case_location}.overrides: expected an object")
            continue
        unknown_overrides = sorted(overrides.keys() - ACCEPTANCE_INPUT_KEYS)
        if unknown_overrides:
            errors.append(
                f"{case_location}.overrides: unknown keys {', '.join(unknown_overrides)}"
            )

        effective = materialize_report_acceptance_case(defaults, case)
        before_shape_errors = len(errors)
        validate_report_acceptance_input_shape(
            effective, f"{case_location}.effective", errors
        )
        if len(errors) != before_shape_errors:
            continue

        derived_status, derived_flags = derive_report_acceptance_status(effective)
        covered_statuses.add(derived_status)
        if case.get("expected_status") != derived_status:
            errors.append(
                f"{case_location}.expected_status: expected derived {derived_status}"
            )

        expected_flags = case.get("expected_quality_flags")
        if (
            not isinstance(expected_flags, list)
            or any(
                not isinstance(flag, str) or flag not in ACCEPTANCE_QUALITY_FLAGS
                for flag in expected_flags
            )
            or len(set(expected_flags)) != len(expected_flags)
        ):
            errors.append(
                f"{case_location}.expected_quality_flags: invalid or duplicate flags"
            )
        elif set(expected_flags) != derived_flags:
            errors.append(
                f"{case_location}.expected_quality_flags: does not match derived flags"
            )

        claimed_status = case.get("claimed_status")
        if (
            not isinstance(claimed_status, str)
            or claimed_status not in COMPLETION_STATUSES
        ):
            errors.append(f"{case_location}.claimed_status: invalid status")
            continue
        claim_mismatch = claimed_status != derived_status
        if case.get("expect_valid") is True and claim_mismatch:
            errors.append(f"{case_location}: valid case contradicts derived status")
        elif case.get("expect_valid") is False:
            if not claim_mismatch:
                errors.append(
                    f"{case_location}: negative case must contradict derived status"
                )
            if case.get("expected_error") != "CLAIMED_STATUS_MISMATCH":
                errors.append(
                    f"{case_location}.expected_error: expected CLAIMED_STATUS_MISMATCH"
                )
        elif not isinstance(case.get("expect_valid"), bool):
            errors.append(f"{case_location}.expect_valid: expected a boolean")

    if covered_statuses != COMPLETION_STATUSES:
        errors.append(f"{location}: truth table must derive all four report statuses")


def derive_completion_status(case: dict[str, object]) -> str:
    """Derive the public report status from one synthetic gate case."""

    if case.get("reliable_product") is not True:
        return "failed"

    if case.get("required_source_state") in {
        "non_equivalent_fallback",
        "unavailable",
    } or case.get("artifact_status") == "failed":
        return "degraded"

    if case.get("denominator_known") is not True:
        return "provisional"

    expected = case.get("expected")
    observed = case.get("observed")
    percent = case.get("percent")
    gap_count = case.get("gap_count")
    required_period_lag = case.get("required_period_lag")
    conflicting_duplicates = case.get("conflicting_duplicate_count")

    if (
        not is_non_negative_int(expected)
        or expected == 0
        or not is_non_negative_int(observed)
        or observed != expected
        or not isinstance(percent, (int, float))
        or isinstance(percent, bool)
        or abs(float(percent) - 100.0) > 0.01
        or gap_count != 0
        or required_period_lag != 0
        or conflicting_duplicates != 0
        or case.get("required_source_state") == "stale"
        or case.get("reviews_complete") is not True
        or case.get("artifact_status") != "persisted"
    ):
        return "provisional"

    return "complete"


def validate_universe_completion_cases(value: object, errors: list[str]) -> None:
    path = Path("examples/synthetic/universe-completion-cases.json")
    location = str(path)
    require_keys(value, {"spec_version", "profiles", "cases"}, location, errors)
    if not isinstance(value, dict):
        return

    if value.get("spec_version") != "1.0.0":
        errors.append(f"{location}: spec_version must be 1.0.0")

    profiles = value.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != COMPLETION_PROFILE_IDS:
        errors.append(f"{location}: profiles must match the supported profile IDs")
    else:
        expected_profile = {
            "minimum_percent": 100.0,
            "maximum_gap_count": 0,
            "maximum_required_period_lag": 0,
        }
        for profile_id, profile in profiles.items():
            if profile != expected_profile:
                errors.append(
                    f"{location}.profiles.{profile_id}: profile must require "
                    "100 percent, zero gaps, and zero required-period lag"
                )

    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{location}.cases: expected a non-empty array")
        return

    seen_ids: set[str] = set()
    integer_fields = {
        "conflicting_duplicate_count",
        "current_retained",
        "exact_duplicate_count",
        "expected",
        "gap_count",
        "observed",
        "refreshed_this_cycle",
        "required_period_lag",
        "stale_retained",
    }

    for index, case in enumerate(cases):
        case_location = f"{location}.cases[{index}]"
        require_keys(case, COMPLETION_CASE_KEYS, case_location, errors)
        if not isinstance(case, dict):
            continue

        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{case_location}.case_id: expected a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{case_location}.case_id: duplicate case ID {case_id}")
        else:
            seen_ids.add(case_id)

        if case.get("profile_id") not in COMPLETION_PROFILE_IDS:
            errors.append(f"{case_location}.profile_id: unsupported profile")
        if case.get("required_source_state") not in COMPLETION_SOURCE_STATES:
            errors.append(f"{case_location}.required_source_state: invalid state")
        if case.get("artifact_status") not in {"persisted", "failed", "not_attempted"}:
            errors.append(f"{case_location}.artifact_status: invalid state")
        if case.get("claimed_status") not in COMPLETION_STATUSES:
            errors.append(f"{case_location}.claimed_status: invalid status")
        if case.get("expected_status") not in COMPLETION_STATUSES:
            errors.append(f"{case_location}.expected_status: invalid status")

        for key in ("denominator_known", "expect_valid", "reliable_product", "reviews_complete"):
            if not isinstance(case.get(key), bool):
                errors.append(f"{case_location}.{key}: expected a boolean")

        for key in integer_fields:
            if not is_non_negative_int(case.get(key)):
                errors.append(f"{case_location}.{key}: expected a non-negative integer")

        expected = case.get("expected")
        observed = case.get("observed")
        gap_count = case.get("gap_count")
        percent = case.get("percent")
        refreshed = case.get("refreshed_this_cycle")
        retained = case.get("current_retained")

        if is_non_negative_int(expected) and is_non_negative_int(observed):
            if observed > expected:
                errors.append(f"{case_location}: observed exceeds expected")
            calculated = 0.0 if expected == 0 else observed / expected * 100
            if (
                not isinstance(percent, (int, float))
                or isinstance(percent, bool)
                or abs(float(percent) - calculated) > 0.01
            ):
                errors.append(f"{case_location}: percent does not match counts")
            if is_non_negative_int(gap_count) and gap_count != expected - observed:
                errors.append(f"{case_location}: gap_count does not match counts")

        if (
            is_non_negative_int(observed)
            and is_non_negative_int(refreshed)
            and is_non_negative_int(retained)
            and observed != refreshed + retained
        ):
            errors.append(
                f"{case_location}: observed must equal refreshed_this_cycle plus "
                "current_retained after deduplication"
            )

        derived = derive_completion_status(case)
        if case.get("expected_status") != derived:
            errors.append(
                f"{case_location}: expected_status {case.get('expected_status')!r} "
                f"does not match derived status {derived!r}"
            )

        claim_mismatch = case.get("claimed_status") != derived
        if case.get("expect_valid") is True and claim_mismatch:
            errors.append(f"{case_location}: valid case contradicts its derived status")
        if case.get("expect_valid") is False:
            if not claim_mismatch:
                errors.append(f"{case_location}: negative case must contradict its derived status")
            if case.get("expected_error") != "CLAIMED_STATUS_MISMATCH":
                errors.append(
                    f"{case_location}.expected_error: expected CLAIMED_STATUS_MISMATCH"
                )


IDEA_REQUIRED_KEYS = {
    "asset",
    "board",
    "catalysts",
    "confidence",
    "evidence",
    "first_seen_at",
    "idea_id",
    "invalidation_conditions",
    "last_seen_at",
    "regime_fit",
    "research_state",
    "risks",
    "schema_version",
    "thesis",
    "time_horizon",
    "timing_notes",
}

VERIFIED_REPEAT_CLASSES = {
    "repeat_unchanged",
    "materially_updated",
    "reintroduced",
    "stale_repeat",
}

LINEAGE_CLASSES = VERIFIED_REPEAT_CLASSES | {"new", "unverified"}

LINEAGE_DIMENSIONS = {
    "thesis",
    "evidence",
    "catalysts",
    "risks",
    "invalidation_conditions",
    "research_state",
}


def timestamp_value(value: object) -> datetime | None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_TEXT.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed


def exact_timestamp_value(value: object) -> Fraction | None:
    """Return an exact UTC instant without truncating fractional seconds."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z",
        value,
    )
    if match is None:
        return None
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    fraction_digits = match.group(7) or ""
    try:
        whole = datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
    epoch = datetime(1970, 1, 1)
    delta = whole - epoch
    whole_seconds = delta.days * 86_400 + delta.seconds
    scale = 10 ** len(fraction_digits)
    fractional = int(fraction_digits) if fraction_digits else 0
    return Fraction(whole_seconds * scale + fractional, scale)


def percent_or_none(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator * 100


def validate_report_manifest_acceptance(
    report: object, path: Path, errors: list[str]
) -> None:
    """Validate report-manifest 1.1 gate joins, clocks, flags, and derived status."""

    location = str(path)
    if not isinstance(report, dict) or report.get("schema_version") != "1.1.0":
        return

    coverage = report.get("coverage")
    freshness = report.get("freshness")
    sources = report.get("sources")
    artifact = report.get("artifact")
    gate_inputs = report.get("gate_inputs")
    if not all(
        isinstance(value, dict)
        for value in (coverage, freshness, artifact, gate_inputs)
    ) or not isinstance(sources, list):
        return

    status_reason = report.get("status_reason")
    if not isinstance(status_reason, str) or not status_reason.strip():
        errors.append(f"{location}.status_reason: expected non-whitespace text")
    coverage_universe = coverage.get("universe")
    if not isinstance(coverage_universe, str) or not coverage_universe.strip():
        errors.append(f"{location}.coverage.universe: expected non-whitespace text")

    generated_at = timestamp_value(report.get("generated_at"))
    data_as_of = timestamp_value(report.get("data_as_of"))
    if generated_at is None:
        errors.append(f"{location}.generated_at: invalid UTC timestamp")
    if data_as_of is None:
        errors.append(f"{location}.data_as_of: invalid UTC timestamp")
    if generated_at and data_as_of and data_as_of > generated_at:
        errors.append(f"{location}: data_as_of cannot be after generated_at")

    denominator_known = gate_inputs.get("denominator_known")
    required_period = gate_inputs.get("required_period")
    if not isinstance(required_period, str) or not required_period.strip():
        errors.append(f"{location}.gate_inputs.required_period: expected non-whitespace text")
    membership_as_of = timestamp_value(gate_inputs.get("membership_as_of"))
    if "membership_as_of" in gate_inputs and membership_as_of is None:
        errors.append(f"{location}.gate_inputs.membership_as_of: invalid UTC timestamp")
    if generated_at and membership_as_of and membership_as_of > generated_at:
        errors.append(f"{location}: membership_as_of cannot be after generated_at")
    if data_as_of and membership_as_of and membership_as_of > data_as_of:
        errors.append(f"{location}: membership_as_of cannot be after data_as_of")

    gap_count = gate_inputs.get("gap_count")
    coverage_gaps = coverage.get("gaps")
    nonblank_gap_descriptions: list[str] = []
    if isinstance(coverage_gaps, list):
        nonblank_gap_descriptions = [
            gap for gap in coverage_gaps if isinstance(gap, str) and gap.strip()
        ]
        if len(nonblank_gap_descriptions) != len(coverage_gaps):
            errors.append(
                f"{location}.coverage.gaps: descriptions must contain non-whitespace text"
            )
    if denominator_known is False:
        for field_name in ("membership_as_of", "gap_count"):
            if field_name in gate_inputs:
                errors.append(
                    f"{location}.gate_inputs.{field_name}: omit when denominator is unknown"
                )
        if any(
            coverage.get(field_name) != 0
            for field_name in ("expected", "observed", "percent")
        ) or coverage_gaps != []:
            errors.append(
                f"{location}.coverage: unknown denominator requires the zero sentinel and no gap descriptions"
            )
    elif denominator_known is True and is_non_negative_int(gap_count):
        if gap_count == 0 and isinstance(coverage_gaps, list) and coverage_gaps:
            errors.append(
                f"{location}.coverage.gaps: zero gap_count requires an empty array"
            )
        if (
            gap_count > 0
            and isinstance(coverage_gaps, list)
            and not nonblank_gap_descriptions
        ):
            errors.append(
                f"{location}.coverage.gaps: positive gap_count requires a public-safe gap description"
            )

    source_by_id: dict[str, dict[str, object]] = {}
    for index, source in enumerate(sources):
        source_location = f"{location}.sources[{index}]"
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if isinstance(source_id, str):
            if not source_id.strip():
                errors.append(f"{source_location}.source_id: expected non-whitespace text")
            if source_id in source_by_id:
                errors.append(f"{source_location}.source_id: duplicate source ID")
            else:
                source_by_id[source_id] = source
        source_note = source.get("note")
        if not isinstance(source_note, str) or not source_note.strip():
            errors.append(f"{source_location}.note: expected non-whitespace text")

        source_data_as_of = timestamp_value(source.get("data_as_of"))
        retrieved_at = timestamp_value(source.get("retrieved_at"))
        checked_at = timestamp_value(source.get("checked_at"))
        for field_name, field_value in (
            ("data_as_of", source_data_as_of),
            ("retrieved_at", retrieved_at),
            ("checked_at", checked_at),
        ):
            if field_name in source and field_value is None:
                errors.append(
                    f"{source_location}.{field_name}: invalid UTC timestamp"
                )
        if source_data_as_of and retrieved_at and source_data_as_of > retrieved_at:
            errors.append(
                f"{source_location}: data_as_of cannot be after retrieved_at"
            )
        if retrieved_at and checked_at and retrieved_at > checked_at:
            errors.append(f"{source_location}: retrieved_at cannot be after checked_at")
        if data_as_of and source_data_as_of and source_data_as_of > data_as_of:
            errors.append(f"{source_location}: data_as_of cannot be after report data_as_of")
        if generated_at and retrieved_at and retrieved_at > generated_at:
            errors.append(f"{source_location}: retrieved_at cannot be after generated_at")
        if generated_at and checked_at and checked_at > generated_at:
            errors.append(f"{source_location}: checked_at cannot be after generated_at")

    freshness_status = freshness.get("status")
    threshold = freshness.get("threshold_hours")
    oldest_material = timestamp_value(freshness.get("oldest_material_source_as_of"))
    if (
        "oldest_material_source_as_of" in freshness
        and oldest_material is None
    ):
        errors.append(
            f"{location}.freshness.oldest_material_source_as_of: invalid UTC timestamp"
        )
    freshness_age_hours: float | None = None
    if generated_at and oldest_material:
        freshness_age_hours = (
            generated_at - oldest_material
        ).total_seconds() / 3600
        if freshness_age_hours < 0:
            errors.append(
                f"{location}: oldest material source cannot be after generated_at"
            )
        if (
            freshness_status == "fresh"
            and is_finite_number(threshold)
            and exceeds_threshold(freshness_age_hours, threshold)
        ):
            errors.append(f"{location}: fresh label exceeds its declared threshold")

    artifact_status = artifact.get("status")
    artifact_note = artifact.get("note")
    if not isinstance(artifact_note, str) or not artifact_note.strip():
        errors.append(f"{location}.artifact.note: expected non-whitespace text")
    persisted_at = timestamp_value(artifact.get("persisted_at"))
    if "persisted_at" in artifact and persisted_at is None:
        errors.append(f"{location}.artifact.persisted_at: invalid UTC timestamp")
    if generated_at and persisted_at and persisted_at < generated_at:
        errors.append(f"{location}: persisted_at cannot be before generated_at")
    durable_reference = artifact.get("durable_reference")
    durable_reference_is_opaque = bool(
        isinstance(durable_reference, str)
        and OPAQUE_DURABLE_REFERENCE.fullmatch(durable_reference)
    )
    if isinstance(durable_reference, str) and not durable_reference_is_opaque:
        errors.append(
            f"{location}.artifact.durable_reference: expected an opaque receipt, not a URL or path"
        )

    roles = gate_inputs.get("source_roles")
    required_states: list[object] = []
    referenced_source_ids: set[str] = set()
    role_states: dict[str, object] = {}
    raw_status_for_role_state = {
        "available": "available",
        "equivalent_fallback": "fallback",
        "stale": "stale",
        "non_equivalent_fallback": "fallback",
        "unavailable": "unavailable",
    }
    if isinstance(roles, list):
        for index, role in enumerate(roles):
            role_location = f"{location}.gate_inputs.source_roles[{index}]"
            if not isinstance(role, dict):
                continue
            role_name = role.get("role")
            state = role.get("state")
            role_note = role.get("note")
            if not isinstance(role_note, str) or not role_note.strip():
                errors.append(f"{role_location}.note: expected non-whitespace text")
            required_states.append(state)
            if isinstance(role_name, str):
                if role_name in role_states:
                    errors.append(f"{role_location}.role: duplicate required role")
                else:
                    role_states[role_name] = state
            source_ids = role.get("source_ids")
            if not isinstance(source_ids, list):
                continue

            linked_statuses: list[str] = []
            for source_id in source_ids:
                if isinstance(source_id, str) and not source_id.strip():
                    errors.append(
                        f"{role_location}.source_ids: expected non-whitespace text"
                    )
                if not isinstance(source_id, str) or source_id not in source_by_id:
                    errors.append(f"{role_location}: dangling source_id {source_id!r}")
                    continue
                referenced_source_ids.add(source_id)
                linked_status = source_by_id[source_id].get("status")
                if not isinstance(linked_status, str):
                    errors.append(
                        f"{role_location}: linked source {source_id!r} has an invalid status"
                    )
                    continue
                linked_statuses.append(linked_status)

            expected_raw_status = (
                raw_status_for_role_state.get(state)
                if isinstance(state, str)
                else None
            )
            if expected_raw_status and (
                not linked_statuses
                or any(status != expected_raw_status for status in linked_statuses)
            ):
                errors.append(
                    f"{role_location}: every linked source must match role state {state!r}"
                )

    freshness_role_state = role_states.get("freshness_reference")
    if freshness_role_state == "unavailable" and freshness_status != "unknown":
        errors.append(
            f"{location}: unavailable freshness reference requires unknown aggregate freshness"
        )
    elif freshness_role_state != "unavailable" and freshness_status == "unknown":
        errors.append(
            f"{location}: unknown aggregate freshness requires an unavailable freshness reference"
        )

    if (
        freshness_role_state != "unavailable"
        and "stale" in required_states
        and freshness_status != "stale"
    ):
        errors.append(
            f"{location}: required stale source role requires stale aggregate freshness"
        )

    material_times: list[datetime] = []
    for source_id in referenced_source_ids:
        source = source_by_id.get(source_id)
        if not isinstance(source, dict):
            continue
        source_status = source.get("status")
        if not isinstance(source_status, str) or source_status not in {
            "available",
            "fallback",
            "stale",
        }:
            continue
        source_time = timestamp_value(source.get("data_as_of"))
        if source_time is not None:
            material_times.append(source_time)
    if isinstance(freshness_status, str) and freshness_status in ("fresh", "stale"):
        if not material_times:
            errors.append(f"{location}: known freshness requires material source times")
        elif oldest_material != min(material_times):
            errors.append(
                f"{location}.freshness.oldest_material_source_as_of: must equal the earliest required-role source time"
            )
    elif freshness_status == "unknown" and oldest_material is not None:
        errors.append(
            f"{location}: unknown aggregate freshness cannot claim a material source time"
        )

    optional_source_state = "available"
    if any(
        source.get("status") == "unavailable"
        for source_id, source in source_by_id.items()
        if source_id not in referenced_source_ids
    ):
        optional_source_state = "unavailable"

    normalized = {
        "artifact_status": artifact_status,
        "denominator_known": denominator_known,
        "durable_receipt_present": bool(
            durable_reference_is_opaque and persisted_at
        ),
        "expected": coverage.get("expected"),
        "freshness_age_hours": freshness_age_hours,
        "freshness_status": freshness_status,
        "freshness_threshold_hours": threshold,
        "gap_count": gap_count,
        "observed": coverage.get("observed"),
        "optional_source_state": optional_source_state,
        "percent": coverage.get("percent"),
        "reliable_product": gate_inputs.get("reliable_product"),
        "required_period_lag": gate_inputs.get("required_period_lag"),
        "required_period_lag_known": gate_inputs.get("required_period_lag_known"),
        "required_reviews_complete": gate_inputs.get("required_reviews_complete"),
        "required_source_states": required_states,
    }
    validate_report_acceptance_input_shape(
        normalized, f"{location}.derived_gate_inputs", errors
    )

    derived_status, derived_flags = derive_report_acceptance_status(normalized)
    if report.get("status") != derived_status:
        errors.append(
            f"{location}.status: claimed {report.get('status')!r}, derived {derived_status!r}"
        )

    quality_flags = report.get("quality_flags")
    if isinstance(quality_flags, list):
        known_flags = {
            flag
            for flag in quality_flags
            if isinstance(flag, str) and flag in ACCEPTANCE_QUALITY_FLAGS
        }
        missing_flags = sorted(derived_flags - known_flags)
        contradictory_flags = sorted(known_flags - derived_flags)
        if missing_flags:
            errors.append(
                f"{location}.quality_flags: missing derived flags {', '.join(missing_flags)}"
            )
        if contradictory_flags:
            errors.append(
                f"{location}.quality_flags: contradictory flags {', '.join(contradictory_flags)}"
            )


def validate_idea_fixture(
    path: Path,
    value: object,
    source_statuses: dict[str, str],
    errors: list[str],
) -> str | None:
    location = str(path)
    require_keys(value, IDEA_REQUIRED_KEYS, location, errors)
    if not isinstance(value, dict):
        return None

    version = value.get("schema_version")
    if version not in {"1.0.0", "1.1.0"}:
        errors.append(f"{location}.schema_version: expected 1.0.0 or 1.1.0")

    first_seen = timestamp_value(value.get("first_seen_at"))
    last_seen = timestamp_value(value.get("last_seen_at"))
    if first_seen and last_seen and first_seen > last_seen:
        errors.append(f"{location}: first_seen_at is after last_seen_at")

    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{location}.evidence: expected a non-empty array")
        evidence = []

    for index, item in enumerate(evidence):
        evidence_location = f"{location}.evidence[{index}]"
        require_keys(item, {"source_id", "provenance", "claim"}, evidence_location, errors)
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or source_id not in source_statuses:
            errors.append(f"{evidence_location}.source_id: source is not in the report register")

    lineage = value.get("lineage")
    if version == "1.0.0":
        if lineage is not None:
            errors.append(f"{location}: schema 1.0.0 must not contain lineage")
        return None

    require_keys(lineage, {"status", "classification", "changed_dimensions"}, f"{location}.lineage", errors)
    if not isinstance(lineage, dict):
        return None

    status = lineage.get("status")
    classification = lineage.get("classification")
    dimensions = lineage.get("changed_dimensions")
    if status not in {"verified", "unverified"}:
        errors.append(f"{location}.lineage.status: invalid status")
    if classification not in LINEAGE_CLASSES:
        errors.append(f"{location}.lineage.classification: invalid classification")
        return None
    if (
        not isinstance(dimensions, list)
        or any(dimension not in LINEAGE_DIMENSIONS for dimension in dimensions)
        or len(set(dimensions)) != len(dimensions)
    ):
        errors.append(f"{location}.lineage.changed_dimensions: invalid dimensions")
        dimensions = []

    if status == "unverified":
        if classification != "unverified":
            errors.append(f"{location}: unverified status requires unverified classification")
        if dimensions:
            errors.append(f"{location}: unverified lineage cannot claim changed dimensions")
        if not isinstance(lineage.get("verification_note"), str) or not lineage.get("verification_note"):
            errors.append(f"{location}: unverified lineage requires verification_note")
        if "last_material_change_at" in lineage or "repeat_count" in lineage:
            errors.append(f"{location}: unverified lineage cannot reconstruct material time or count")
        return classification

    if status != "verified":
        return classification

    if classification == "unverified":
        errors.append(f"{location}: verified lineage cannot use unverified classification")

    repeat_count = lineage.get("repeat_count")
    if not is_non_negative_int(repeat_count):
        errors.append(f"{location}.lineage.repeat_count: expected a non-negative integer")

    material_time = timestamp_value(lineage.get("last_material_change_at"))
    if material_time is None:
        errors.append(f"{location}.lineage.last_material_change_at: invalid or missing UTC time")
    elif first_seen and last_seen and not (first_seen <= material_time <= last_seen):
        errors.append(f"{location}: material-change time must fall within retained lineage")

    reason = value.get("repeat_reason")
    if classification in VERIFIED_REPEAT_CLASSES and (
        not isinstance(reason, str) or not reason.strip()
    ):
        errors.append(f"{location}: verified repeats require repeat_reason")

    if classification == "new":
        if repeat_count != 0 or dimensions:
            errors.append(f"{location}: new lineage requires count zero and no changed dimensions")
        if first_seen and last_seen and material_time and not (
            first_seen == last_seen == material_time
        ):
            errors.append(f"{location}: new lineage timestamps must be equal")
    elif classification in {"repeat_unchanged", "stale_repeat"}:
        if not is_non_negative_int(repeat_count) or repeat_count < 1 or dimensions:
            errors.append(f"{location}: unchanged repeats require a positive count and no changed dimensions")
    elif classification == "materially_updated":
        if not is_non_negative_int(repeat_count) or repeat_count < 1 or not dimensions:
            errors.append(f"{location}: material updates require a positive count and changed dimensions")
    elif classification == "reintroduced":
        if (
            not is_non_negative_int(repeat_count)
            or repeat_count < 1
            or "research_state" not in dimensions
        ):
            errors.append(f"{location}: reintroduction requires a positive count and research_state change")

    if classification == "stale_repeat":
        evidence_statuses = {
            source_statuses.get(item.get("source_id"))
            for item in evidence
            if isinstance(item, dict)
        }
        if "stale" not in evidence_statuses:
            errors.append(f"{location}: stale_repeat requires mapped stale evidence")

    return classification


OUTCOME_REVIEW_AXES = (
    "research_outcome",
    "decision_quality",
    "process_quality",
    "timing_discipline",
)

OUTCOME_INVALIDATION_RESPONSES = {
    "not_triggered": {"not_applicable"},
    "triggered": {
        "followed",
        "delayed",
        "not_followed",
        "ambiguous",
        "unknown",
    },
    "ambiguous": {"ambiguous", "unknown"},
    "unknown": {"unknown"},
    "not_applicable": {"not_applicable"},
}

OUTCOME_REVIEW_FORBIDDEN_KEYS = {
    "account",
    "accountdata",
    "accountid",
    "action",
    "alpha",
    "allocation",
    "allocations",
    "asset",
    "benchmark",
    "benchmarks",
    "client",
    "clientdata",
    "clientid",
    "deployment",
    "deploymentaction",
    "deploymentactions",
    "holding",
    "holdings",
    "pandl",
    "payloadhash",
    "performance",
    "pnl",
    "position",
    "positions",
    "positionsize",
    "positionsizes",
    "price",
    "prices",
    "profitloss",
    "portfolio",
    "researchdisposition",
    "return",
    "returnpct",
    "returns",
    "symbol",
    "ticker",
    "trade",
    "trades",
    "transaction",
    "transactions",
}

OUTCOME_ATTRIBUTION_FORBIDDEN_KEYS = {
    "causalprobability",
    "causalstatus",
    "contribution",
    "contributionweight",
    "percent",
    "score",
    "weight",
}


def normalize_outcome_review_key(value: str) -> str:
    """Normalize a JSON key for defensive public-boundary checks."""

    return re.sub(r"[^a-z0-9]+", "", value.lower().replace("&", "and"))


def validate_outcome_review_payload_boundary(
    value: object,
    location: str,
    errors: list[str],
    *,
    inside_attribution: bool = False,
) -> None:
    """Reject performance, account, deployment, causal, and numeric payload data."""

    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            normalized = normalize_outcome_review_key(key)
            if normalized in OUTCOME_REVIEW_FORBIDDEN_KEYS:
                errors.append(
                    f"{child_location}: prohibited private, performance, or "
                    "deployment field"
                )
            child_inside_attribution = inside_attribution or key == "attribution"
            if (
                child_inside_attribution
                and normalized in OUTCOME_ATTRIBUTION_FORBIDDEN_KEYS
            ):
                errors.append(
                    f"{child_location}: numeric or causal attribution field is prohibited"
                )
            validate_outcome_review_payload_boundary(
                child,
                child_location,
                errors,
                inside_attribution=child_inside_attribution,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_outcome_review_payload_boundary(
                child,
                f"{location}[{index}]",
                errors,
                inside_attribution=inside_attribution,
            )
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        errors.append(
            f"{location}: numeric values are not permitted in outcome-review artifacts"
        )


def validate_outcome_review(
    review: object, path: Path, errors: list[str]
) -> None:
    """Validate cross-field semantics for one public-safe outcome review."""

    location = str(path)
    require_keys(
        review,
        {
            "schema_version",
            "review_id",
            "links",
            "clocks",
            "review_assessability",
            "evidence_quality",
            *OUTCOME_REVIEW_AXES,
            "invalidation_trigger",
            "invalidation_response",
            "attribution",
        },
        location,
        errors,
    )
    if not isinstance(review, dict):
        return

    validate_outcome_review_payload_boundary(review, location, errors)

    if review.get("schema_version") != "1.0.0":
        errors.append(f"{location}.schema_version: expected 1.0.0")

    review_id = review.get("review_id")
    prior_review_ref = review.get("prior_review_ref")
    if (
        isinstance(review_id, str)
        and isinstance(prior_review_ref, str)
        and review_id == prior_review_ref
    ):
        errors.append(f"{location}.prior_review_ref: review cannot refer to itself")

    links = review.get("links")
    declared_refs: list[object] = []
    if isinstance(links, dict):
        raw_refs = links.get("evidence_refs")
        if isinstance(raw_refs, list):
            declared_refs = raw_refs
            string_refs = [value for value in raw_refs if isinstance(value, str)]
            if len(string_refs) != len(set(string_refs)):
                errors.append(f"{location}.links.evidence_refs: duplicate reference")
    declared_ref_set = {
        value for value in declared_refs if isinstance(value, str)
    }
    if isinstance(links, dict):
        decision_ref = links.get("decision_ref")
        idea_ref = links.get("idea_ref")
        if (
            isinstance(decision_ref, str)
            and isinstance(idea_ref, str)
            and decision_ref == idea_ref
        ):
            errors.append(
                f"{location}.links: decision_ref and idea_ref must be distinct"
            )
        for field_name, value in (
            ("decision_ref", decision_ref),
            ("idea_ref", idea_ref),
        ):
            if isinstance(value, str) and value in declared_ref_set:
                errors.append(
                    f"{location}.links.{field_name}: identity reference cannot "
                    "also be an evidence reference"
                )

    public_fixture = (
        "examples/synthetic/" in location
        or "tests/compatibility/" in location
    )
    if public_fixture:
        if not isinstance(review_id, str) or not review_id.startswith("orv_SYNTH"):
            errors.append(f"{location}.review_id: public fixture must be visibly synthetic")
        if isinstance(prior_review_ref, str) and not prior_review_ref.startswith(
            "orv_SYNTH"
        ):
            errors.append(
                f"{location}.prior_review_ref: public fixture must be visibly synthetic"
            )
        if isinstance(links, dict):
            link_values = [links.get("decision_ref"), links.get("idea_ref")]
            link_values.extend(declared_refs)
            for value in link_values:
                if not isinstance(value, str) or not value.startswith("ref_SYNTH"):
                    errors.append(
                        f"{location}.links: public references must be visibly synthetic"
                    )

    clocks = review.get("clocks")
    clock_names = (
        "decision_recorded_at",
        "evaluation_started_at",
        "evidence_cutoff_at",
        "reviewed_at",
    )
    parsed_clocks: dict[str, datetime] = {}
    if isinstance(clocks, dict):
        for name in clock_names:
            parsed = timestamp_value(clocks.get(name))
            if parsed is None:
                errors.append(f"{location}.clocks.{name}: invalid UTC timestamp")
            else:
                parsed_clocks[name] = parsed
        for earlier_name, later_name in zip(clock_names, clock_names[1:]):
            earlier = parsed_clocks.get(earlier_name)
            later = parsed_clocks.get(later_name)
            if earlier is not None and later is not None and earlier > later:
                errors.append(
                    f"{location}.clocks: {earlier_name} cannot be after {later_name}"
                )
    else:
        errors.append(f"{location}.clocks: expected an object")

    trigger = review.get("invalidation_trigger")
    response = review.get("invalidation_response")
    raw_trigger_state = trigger.get("state") if isinstance(trigger, dict) else None
    raw_response_state = response.get("state") if isinstance(response, dict) else None
    trigger_state = raw_trigger_state if isinstance(raw_trigger_state, str) else None
    response_state = (
        raw_response_state if isinstance(raw_response_state, str) else None
    )
    allowed_responses = (
        OUTCOME_INVALIDATION_RESPONSES.get(trigger_state)
        if isinstance(trigger_state, str)
        else None
    )
    if allowed_responses is None:
        errors.append(f"{location}.invalidation_trigger.state: invalid state")
    elif response_state not in allowed_responses:
        errors.append(
            f"{location}: invalid invalidation combination "
            f"{trigger_state!r} -> {response_state!r}"
        )

    triggered_at = (
        timestamp_value(trigger.get("triggered_at"))
        if isinstance(trigger, dict) and "triggered_at" in trigger
        else None
    )
    if isinstance(trigger, dict) and "triggered_at" in trigger and triggered_at is None:
        errors.append(
            f"{location}.invalidation_trigger.triggered_at: invalid UTC timestamp"
        )
    if trigger_state == "triggered" and triggered_at is None:
        errors.append(
            f"{location}.invalidation_trigger.triggered_at: required when triggered"
        )

    responded_at = (
        timestamp_value(response.get("responded_at"))
        if isinstance(response, dict) and "responded_at" in response
        else None
    )
    if isinstance(response, dict) and "responded_at" in response and responded_at is None:
        errors.append(
            f"{location}.invalidation_response.responded_at: invalid UTC timestamp"
        )
    if response_state in {"followed", "delayed"} and responded_at is None:
        errors.append(
            f"{location}.invalidation_response.responded_at: required for "
            f"{response_state}"
        )

    decision_time = parsed_clocks.get("decision_recorded_at")
    cutoff_time = parsed_clocks.get("evidence_cutoff_at")
    if triggered_at is not None:
        if decision_time is not None and triggered_at < decision_time:
            errors.append(
                f"{location}.invalidation_trigger.triggered_at: cannot precede decision"
            )
        if cutoff_time is not None and triggered_at > cutoff_time:
            errors.append(
                f"{location}.invalidation_trigger.triggered_at: cannot exceed evidence cutoff"
            )
    if responded_at is not None:
        if triggered_at is not None and responded_at < triggered_at:
            errors.append(
                f"{location}.invalidation_response.responded_at: cannot precede trigger"
            )
        if cutoff_time is not None and responded_at > cutoff_time:
            errors.append(
                f"{location}.invalidation_response.responded_at: cannot exceed evidence cutoff"
            )

    used_ref_set: set[str] = set()

    def validate_nested_refs(container: object, nested_location: str) -> None:
        if not isinstance(container, dict):
            return
        refs = container.get("evidence_refs")
        if not isinstance(refs, list):
            return
        strings = [value for value in refs if isinstance(value, str)]
        used_ref_set.update(strings)
        if len(strings) != len(set(strings)):
            errors.append(f"{nested_location}.evidence_refs: duplicate reference")
        for value in strings:
            if value not in declared_ref_set:
                errors.append(
                    f"{nested_location}.evidence_refs: dangling reference {value!r}"
                )

    for axis_name in OUTCOME_REVIEW_AXES:
        validate_nested_refs(review.get(axis_name), f"{location}.{axis_name}")
    validate_nested_refs(trigger, f"{location}.invalidation_trigger")
    validate_nested_refs(response, f"{location}.invalidation_response")

    attribution = review.get("attribution")
    factors = attribution.get("factors") if isinstance(attribution, dict) else None
    if isinstance(factors, list):
        for index, factor in enumerate(factors):
            validate_nested_refs(
                factor, f"{location}.attribution.factors[{index}]"
            )

    for orphan_ref in sorted(declared_ref_set - used_ref_set):
        errors.append(
            f"{location}.links.evidence_refs: unused reference {orphan_ref!r}"
        )

    raw_assessability = review.get("review_assessability")
    assessability = raw_assessability if isinstance(raw_assessability, str) else None
    evidence_quality = review.get("evidence_quality")
    expected_quality = {
        "assessable": "verified",
        "partial": "partial",
        "unknown": "unverified",
        "unavailable": "unavailable",
    }.get(assessability)
    if expected_quality is None:
        errors.append(f"{location}.review_assessability: invalid state")
    elif evidence_quality != expected_quality:
        errors.append(
            f"{location}: {assessability!r} review requires "
            f"evidence_quality {expected_quality!r}"
        )

    axis_states: dict[str, str | None] = {}
    for name in OUTCOME_REVIEW_AXES:
        value = review.get(name)
        raw_state = value.get("assessment_state") if isinstance(value, dict) else None
        axis_states[name] = raw_state if isinstance(raw_state, str) else None
    raw_attribution_state = (
        attribution.get("assessment_state")
        if isinstance(attribution, dict)
        else None
    )
    attribution_state = (
        raw_attribution_state if isinstance(raw_attribution_state, str) else None
    )

    for name in ("research_outcome", "decision_quality", "process_quality"):
        if axis_states.get(name) == "not_applicable":
            errors.append(
                f"{location}.{name}.assessment_state: intrinsic axis cannot be "
                "not_applicable"
            )

    if assessability == "assessable":
        if not declared_ref_set:
            errors.append(
                f"{location}.links.evidence_refs: assessable review needs evidence"
            )
        for name in ("research_outcome", "decision_quality", "process_quality"):
            if axis_states.get(name) != "assessable":
                errors.append(
                    f"{location}.{name}.assessment_state: assessable review "
                    "requires an assessable intrinsic axis"
                )
        if axis_states.get("timing_discipline") not in {
            "assessable",
            "not_applicable",
        }:
            errors.append(
                f"{location}.timing_discipline.assessment_state: assessable "
                "review cannot contain a limited applicable timing axis"
            )
        if attribution_state not in {"assessable", "not_applicable"}:
            errors.append(
                f"{location}.attribution.assessment_state: assessable review "
                "cannot contain a limited attribution axis"
            )
        if trigger_state in {"ambiguous", "unknown"} or response_state in {
            "ambiguous",
            "unknown",
        }:
            errors.append(
                f"{location}: assessable review cannot contain uncertain "
                "invalidation handling"
            )

    elif assessability == "partial":
        if not declared_ref_set:
            errors.append(f"{location}.links.evidence_refs: partial review needs evidence")
        states = set(axis_states.values()) | {attribution_state}
        limited_invalidation = trigger_state in {"ambiguous", "unknown"} or (
            response_state in {"ambiguous", "unknown"}
        )
        if not states.intersection({"partial", "unavailable", "unknown"}) and not (
            limited_invalidation
        ):
            errors.append(f"{location}: partial review must expose a limited axis")
        if not states.intersection({"assessable", "partial"}):
            errors.append(f"{location}: partial review needs one useful assessment")

    elif assessability == "unknown":
        if declared_ref_set:
            errors.append(
                f"{location}.links.evidence_refs: unknown review cannot claim "
                "supporting evidence"
            )
        for name in OUTCOME_REVIEW_AXES:
            if axis_states.get(name) not in {"unknown", "not_applicable"}:
                errors.append(
                    f"{location}.{name}.assessment_state: unknown review cannot "
                    "make a substantive assessment"
                )
        if attribution_state not in {"unknown", "not_applicable"}:
            errors.append(
                f"{location}.attribution.assessment_state: unknown review cannot "
                "claim attribution"
            )
        if (trigger_state, response_state) not in {
            ("unknown", "unknown"),
            ("not_applicable", "not_applicable"),
        }:
            errors.append(
                f"{location}: unknown review cannot claim invalidation handling"
            )

    elif assessability == "unavailable":
        if declared_ref_set:
            errors.append(
                f"{location}.links.evidence_refs: unavailable review must omit evidence"
            )
        for name in OUTCOME_REVIEW_AXES:
            if axis_states.get(name) != "unavailable":
                errors.append(
                    f"{location}.{name}.assessment_state: unavailable review "
                    "requires unavailable axes"
                )
        if (trigger_state, response_state) != ("unknown", "unknown"):
            errors.append(
                f"{location}: unavailable review requires unknown invalidation history"
            )
        if attribution_state != "unavailable" or (
            isinstance(factors, list) and factors
        ):
            errors.append(
                f"{location}.attribution: unavailable review cannot claim factors"
            )


def validate_outcome_review_fixture_coverage(
    reviews: list[tuple[Path, object]], errors: list[str]
) -> None:
    """Require invented fixtures for the issue's independent-axis scenarios."""

    usable = [review for _, review in reviews if isinstance(review, dict)]
    review_ids = [
        review.get("review_id")
        for review in usable
        if isinstance(review.get("review_id"), str)
    ]
    if len(review_ids) != len(set(review_ids)):
        errors.append("synthetic outcome reviews must use unique review IDs")

    def nested_text(review: dict[str, object], section: str, field: str) -> str | None:
        container = review.get(section)
        if not isinstance(container, dict):
            return None
        value = container.get(field)
        return value if isinstance(value, str) else None

    scenarios = {
        "adverse outcome with disciplined process": any(
            nested_text(review, "research_outcome", "classification") == "adverse"
            and nested_text(review, "process_quality", "classification") == "disciplined"
            for review in usable
        ),
        "favorable outcome with undisciplined process": any(
            nested_text(review, "research_outcome", "classification") == "favorable"
            and nested_text(review, "process_quality", "classification") == "undisciplined"
            for review in usable
        ),
        "triggered invalidation followed": any(
            nested_text(review, "invalidation_trigger", "state") == "triggered"
            and nested_text(review, "invalidation_response", "state") == "followed"
            for review in usable
        ),
        "triggered invalidation delayed or not followed": any(
            nested_text(review, "invalidation_trigger", "state") == "triggered"
            and nested_text(review, "invalidation_response", "state")
            in ("delayed", "not_followed")
            for review in usable
        ),
        "partial or unverified review": any(
            review.get("review_assessability") == "partial"
            or review.get("evidence_quality") == "unverified"
            for review in usable
        ),
    }
    for name, covered in scenarios.items():
        if not covered:
            errors.append(f"synthetic outcome-review fixtures must cover {name}")

    required_assessability = {"assessable", "partial", "unknown", "unavailable"}
    actual_assessability = {
        value
        for review in usable
        if isinstance((value := review.get("review_assessability")), str)
    }
    if not required_assessability.issubset(actual_assessability):
        errors.append(
            "synthetic outcome reviews must cover assessable, partial, unknown, "
            "and unavailable review states"
        )


HISTORIAN_LESSON_FORBIDDEN_KEYS = {
    "account",
    "accountdata",
    "accountid",
    "aggregate",
    "aggregates",
    "allocation",
    "allocations",
    "approvalidentity",
    "client",
    "clientdata",
    "clientid",
    "code",
    "configuration",
    "contenthash",
    "contenturl",
    "deployment",
    "deploymentaction",
    "deploymentactions",
    "endpoint",
    "filesystempath",
    "hash",
    "holding",
    "holdings",
    "lessonbody",
    "mapping",
    "mappings",
    "pandl",
    "path",
    "payloadhash",
    "performance",
    "pnl",
    "portfolio",
    "price",
    "prices",
    "prompt",
    "provider",
    "providers",
    "return",
    "returns",
    "schema",
    "sourcecode",
    "storagepath",
    "threshold",
    "thresholds",
    "transaction",
    "transactions",
    "uri",
    "url",
    "usage",
    "usagecount",
    "weight",
    "weights",
}


def normalize_historian_lesson_key(value: str) -> str:
    """Normalize a JSON key for defensive historian-lesson boundary checks."""

    return re.sub(r"[^a-z0-9]+", "", value.lower().replace("&", "and"))


def validate_historian_lesson_payload_boundary(
    value: object, location: str, errors: list[str]
) -> None:
    """Reject executable, private, performance, identity, and location fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if normalize_historian_lesson_key(key) in HISTORIAN_LESSON_FORBIDDEN_KEYS:
                errors.append(
                    f"{child_location}: prohibited private, executable, identity, "
                    "performance, location, hash, or usage field"
                )
            validate_historian_lesson_payload_boundary(child, child_location, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_historian_lesson_payload_boundary(
                child, f"{location}[{index}]", errors
            )


def validate_historian_lesson(
    lesson: object, path: Path, errors: list[str]
) -> None:
    """Validate cross-field semantics for one metadata-only lesson revision."""

    location = str(path)
    require_keys(
        lesson,
        {
            "schema_version",
            "lesson_series_id",
            "lesson_version_ref",
            "revision",
            "state",
            "source_reviews",
            "clocks",
            "approval",
            "ingestion",
        },
        location,
        errors,
    )
    if not isinstance(lesson, dict):
        return

    validate_historian_lesson_payload_boundary(lesson, location, errors)

    if lesson.get("schema_version") != "1.0.0":
        errors.append(f"{location}.schema_version: expected 1.0.0")

    revision = lesson.get("revision")
    state = lesson.get("state")
    prior_ref = lesson.get("prior_version_ref")
    content_ref = lesson.get("content_ref")
    version_ref = lesson.get("lesson_version_ref")

    if revision == 1:
        if prior_ref is not None:
            errors.append(f"{location}.prior_version_ref: revision 1 has no predecessor")
        if state != "active" or not isinstance(content_ref, str):
            errors.append(f"{location}: revision 1 must be active with content")
    elif isinstance(revision, int) and not isinstance(revision, bool) and revision > 1:
        if not isinstance(prior_ref, str):
            errors.append(
                f"{location}.prior_version_ref: revision {revision} needs a predecessor"
            )

    if isinstance(version_ref, str) and version_ref == prior_ref:
        errors.append(f"{location}.prior_version_ref: revision cannot refer to itself")
    if state == "active" and not isinstance(content_ref, str):
        errors.append(f"{location}.content_ref: active revision requires content")
    if state == "retired":
        if content_ref is not None:
            errors.append(f"{location}.content_ref: retired tombstone cannot have content")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 2:
            errors.append(f"{location}.revision: retirement requires revision N > 1")

    source_reviews = lesson.get("source_reviews")
    review_refs: list[str] = []
    review_finalized_times: list[tuple[int, datetime]] = []
    if isinstance(source_reviews, list):
        for index, review in enumerate(source_reviews):
            if not isinstance(review, dict):
                continue
            review_ref = review.get("review_ref")
            if isinstance(review_ref, str):
                review_refs.append(review_ref)
            finalized_at = exact_timestamp_value(review.get("finalized_at"))
            if finalized_at is None:
                errors.append(
                    f"{location}.source_reviews[{index}].finalized_at: "
                    "invalid UTC timestamp"
                )
            else:
                review_finalized_times.append((index, finalized_at))
    if len(review_refs) != len(set(review_refs)):
        errors.append(f"{location}.source_reviews: duplicate review reference")

    clocks = lesson.get("clocks")
    clock_names = ("data_as_of", "approved_at", "ingested_at", "generated_at")
    parsed_clocks: dict[str, Fraction] = {}
    if isinstance(clocks, dict):
        for name in clock_names:
            parsed = exact_timestamp_value(clocks.get(name))
            if parsed is None:
                errors.append(f"{location}.clocks.{name}: invalid UTC timestamp")
            else:
                parsed_clocks[name] = parsed
        for earlier_name, later_name in zip(clock_names, clock_names[1:]):
            earlier = parsed_clocks.get(earlier_name)
            later = parsed_clocks.get(later_name)
            if earlier is not None and later is not None and earlier > later:
                errors.append(
                    f"{location}.clocks: {earlier_name} cannot be after {later_name}"
                )
    else:
        errors.append(f"{location}.clocks: expected an object")

    data_as_of = parsed_clocks.get("data_as_of")
    approved_at = parsed_clocks.get("approved_at")
    if (
        data_as_of is not None
        and review_finalized_times
        and data_as_of > max(value for _, value in review_finalized_times)
    ):
        errors.append(
            f"{location}.clocks.data_as_of: cannot exceed every linked review's "
            "finalized_at"
        )
    for index, finalized_at in review_finalized_times:
        if approved_at is not None and finalized_at > approved_at:
            errors.append(
                f"{location}.source_reviews[{index}].finalized_at: linked review "
                "must be finalized before approval"
            )

    public_fixture = (
        "examples/synthetic/" in location or "tests/compatibility/" in location
    )
    if public_fixture:
        expected_prefixes = (
            (lesson.get("lesson_series_id"), "hls_SYNTH", "lesson_series_id"),
            (version_ref, "hlv_SYNTH", "lesson_version_ref"),
            (prior_ref, "hlv_SYNTH", "prior_version_ref"),
            (content_ref, "ref_SYNTH", "content_ref"),
        )
        for value, prefix, field in expected_prefixes:
            if value is not None and (
                not isinstance(value, str) or not value.startswith(prefix)
            ):
                errors.append(f"{location}.{field}: public fixture must be visibly synthetic")
        for review_ref in review_refs:
            if not review_ref.startswith("orv_SYNTH"):
                errors.append(
                    f"{location}.source_reviews: public references must be visibly synthetic"
                )
        approval = lesson.get("approval")
        ingestion = lesson.get("ingestion")
        approval_receipt = approval.get("receipt") if isinstance(approval, dict) else None
        ingestion_receipt = (
            ingestion.get("receipt") if isinstance(ingestion, dict) else None
        )
        if not isinstance(approval_receipt, str) or not approval_receipt.startswith(
            "apr_SYNTH"
        ):
            errors.append(
                f"{location}.approval.receipt: public fixture must be visibly synthetic"
            )
        if not isinstance(ingestion_receipt, str) or not ingestion_receipt.startswith(
            "ing_SYNTH"
        ):
            errors.append(
                f"{location}.ingestion.receipt: public fixture must be visibly synthetic"
            )


def validate_historian_lesson_chain(
    lessons: list[tuple[Path, object]], errors: list[str]
) -> None:
    """Validate an append-only, linear, receipt-unique lesson revision corpus."""

    usable = [(path, lesson) for path, lesson in lessons if isinstance(lesson, dict)]
    by_version: dict[str, tuple[Path, dict[str, object]]] = {}
    approval_receipts: dict[str, Path] = {}
    ingestion_receipts: dict[str, Path] = {}
    all_receipts: dict[str, Path] = {}
    content_refs: dict[str, Path] = {}

    def register_unique(
        value: object,
        location: Path,
        field: str,
        registry: dict[str, Path],
    ) -> None:
        if not isinstance(value, str):
            return
        prior_path = registry.get(value)
        if prior_path is not None:
            errors.append(
                f"{location}.{field}: reused value also present in {prior_path}"
            )
        else:
            registry[value] = location

    for path, lesson in usable:
        version_ref = lesson.get("lesson_version_ref")
        if isinstance(version_ref, str):
            if version_ref in by_version:
                errors.append(
                    f"{path}.lesson_version_ref: duplicate version reference"
                )
            else:
                by_version[version_ref] = (path, lesson)

        approval = lesson.get("approval")
        approval_receipt = approval.get("receipt") if isinstance(approval, dict) else None
        ingestion = lesson.get("ingestion")
        ingestion_receipt = (
            ingestion.get("receipt") if isinstance(ingestion, dict) else None
        )
        register_unique(approval_receipt, path, "approval.receipt", approval_receipts)
        register_unique(
            ingestion_receipt, path, "ingestion.receipt", ingestion_receipts
        )
        register_unique(approval_receipt, path, "approval.receipt", all_receipts)
        register_unique(ingestion_receipt, path, "ingestion.receipt", all_receipts)
        if lesson.get("state") == "active":
            register_unique(lesson.get("content_ref"), path, "content_ref", content_refs)

    children: dict[str, list[str]] = {}
    series_records: dict[str, list[tuple[Path, dict[str, object]]]] = {}
    for path, lesson in usable:
        series_id = lesson.get("lesson_series_id")
        version_ref = lesson.get("lesson_version_ref")
        prior_ref = lesson.get("prior_version_ref")
        revision = lesson.get("revision")
        if isinstance(series_id, str):
            series_records.setdefault(series_id, []).append((path, lesson))
        if not isinstance(prior_ref, str) or not isinstance(version_ref, str):
            continue
        children.setdefault(prior_ref, []).append(version_ref)
        predecessor = by_version.get(prior_ref)
        if predecessor is None:
            errors.append(f"{path}.prior_version_ref: predecessor does not resolve")
            continue
        predecessor_path, predecessor_lesson = predecessor
        if predecessor_lesson.get("lesson_series_id") != series_id:
            errors.append(f"{path}.prior_version_ref: cross-series predecessor")
        predecessor_revision = predecessor_lesson.get("revision")
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or not isinstance(predecessor_revision, int)
            or isinstance(predecessor_revision, bool)
            or predecessor_revision != revision - 1
        ):
            errors.append(
                f"{path}.prior_version_ref: predecessor must be exact revision N-1"
            )
        if predecessor_lesson.get("state") == "retired":
            errors.append(
                f"{path}.prior_version_ref: retired terminal cannot have a successor"
            )

        predecessor_clocks = predecessor_lesson.get("clocks")
        current_clocks = lesson.get("clocks")
        if isinstance(predecessor_clocks, dict) and isinstance(current_clocks, dict):
            predecessor_ingested = exact_timestamp_value(
                predecessor_clocks.get("ingested_at")
            )
            current_ingested = exact_timestamp_value(current_clocks.get("ingested_at"))
            if (
                predecessor_ingested is not None
                and current_ingested is not None
                and current_ingested <= predecessor_ingested
            ):
                errors.append(
                    f"{path}.clocks.ingested_at: successor must be ingested after "
                    f"{predecessor_path}"
                )

    for prior_ref, child_refs in children.items():
        if len(child_refs) > 1:
            errors.append(f"historian lesson chain branches after {prior_ref}")

    for series_id, records in series_records.items():
        revisions = [
            lesson.get("revision")
            for _, lesson in records
            if isinstance(lesson.get("revision"), int)
            and not isinstance(lesson.get("revision"), bool)
        ]
        if revisions:
            expected = set(range(1, max(revisions) + 1))
            actual = set(revisions)
            if actual != expected or len(revisions) != len(actual):
                errors.append(f"historian lesson series {series_id}: revision gap or duplicate")

        series_version_refs = {
            lesson.get("lesson_version_ref")
            for _, lesson in records
            if isinstance(lesson.get("lesson_version_ref"), str)
        }
        referenced = {
            lesson.get("prior_version_ref")
            for _, lesson in records
            if isinstance(lesson.get("prior_version_ref"), str)
            and lesson.get("prior_version_ref") in series_version_refs
        }
        terminals = series_version_refs - referenced
        if len(terminals) != 1:
            errors.append(
                f"historian lesson series {series_id}: expected exactly one terminal revision"
            )
        for path, lesson in records:
            if (
                lesson.get("state") == "retired"
                and lesson.get("lesson_version_ref") not in terminals
            ):
                errors.append(f"{path}.state: retired revision must be terminal")

    reported_cycles: set[str] = set()
    for start_ref in by_version:
        current_ref = start_ref
        visited: set[str] = set()
        while current_ref in by_version:
            if current_ref in visited:
                if current_ref not in reported_cycles:
                    errors.append(
                        f"historian lesson chain contains a cycle at {current_ref}"
                    )
                    reported_cycles.add(current_ref)
                break
            visited.add(current_ref)
            current_lesson = by_version[current_ref][1]
            prior_ref = current_lesson.get("prior_version_ref")
            if not isinstance(prior_ref, str):
                break
            current_ref = prior_ref


def validate_decision_historian_lesson_refs(
    decision: object,
    lessons: list[tuple[Path, object]],
    path: Path,
    errors: list[str],
) -> None:
    """Validate exact lesson selection at an immutable decision timestamp."""

    location = str(path)
    if not isinstance(decision, dict):
        errors.append(f"{location}: expected a JSON object")
        return

    schema_version = decision.get("schema_version")
    refs = decision.get("historian_lesson_version_refs")
    if schema_version == "1.0.0":
        if "historian_lesson_version_refs" in decision:
            errors.append(
                f"{location}.historian_lesson_version_refs: forbidden in "
                "decision-record 1.0.0"
            )
        return
    if schema_version != "1.1.0":
        return
    if not isinstance(refs, list):
        errors.append(
            f"{location}.historian_lesson_version_refs: required array for "
            "decision-record 1.1.0"
        )
        return

    string_refs = [value for value in refs if isinstance(value, str)]
    if len(string_refs) != len(set(string_refs)):
        errors.append(
            f"{location}.historian_lesson_version_refs: duplicate exact version reference"
        )
    decision_time = exact_timestamp_value(decision.get("recorded_at"))
    review_time = exact_timestamp_value(decision.get("review_by"))
    if decision_time is None:
        errors.append(f"{location}.recorded_at: invalid UTC timestamp")
    if review_time is None:
        errors.append(f"{location}.review_by: invalid UTC timestamp")
    if (
        decision_time is not None
        and review_time is not None
        and review_time < decision_time
    ):
        errors.append(f"{location}.review_by: cannot precede recorded_at")
    if not string_refs:
        return
    if decision_time is None:
        return

    usable = [lesson for _, lesson in lessons if isinstance(lesson, dict)]
    by_version = {
        lesson.get("lesson_version_ref"): lesson
        for lesson in usable
        if isinstance(lesson.get("lesson_version_ref"), str)
    }
    for selected_ref in string_refs:
        selected = by_version.get(selected_ref)
        if selected is None:
            errors.append(
                f"{location}.historian_lesson_version_refs: unresolved exact "
                f"version {selected_ref!r}"
            )
            continue

        selected_clocks = selected.get("clocks")
        selected_ingested = (
            exact_timestamp_value(selected_clocks.get("ingested_at"))
            if isinstance(selected_clocks, dict)
            else None
        )
        if selected_ingested is None or selected_ingested > decision_time:
            errors.append(
                f"{location}.historian_lesson_version_refs: {selected_ref!r} "
                "was not ingested by the decision time"
            )
            continue

        series_id = selected.get("lesson_series_id")
        available = []
        for lesson in usable:
            if lesson.get("lesson_series_id") != series_id:
                continue
            clocks = lesson.get("clocks")
            ingested_at = (
                exact_timestamp_value(clocks.get("ingested_at"))
                if isinstance(clocks, dict)
                else None
            )
            revision = lesson.get("revision")
            if (
                ingested_at is not None
                and ingested_at <= decision_time
                and isinstance(revision, int)
                and not isinstance(revision, bool)
            ):
                available.append(lesson)
        if not available:
            errors.append(
                f"{location}.historian_lesson_version_refs: no eligible revision "
                f"for series {series_id!r}"
            )
            continue
        terminal = max(available, key=lambda lesson: lesson["revision"])
        if terminal.get("lesson_version_ref") != selected_ref:
            errors.append(
                f"{location}.historian_lesson_version_refs: {selected_ref!r} is a "
                "stale version at the decision time"
            )
            continue
        if terminal.get("state") != "active":
            errors.append(
                f"{location}.historian_lesson_version_refs: retired lesson "
                f"{selected_ref!r} is not selectable"
            )


LEARNING_METRIC_IDENTIFIER_KEYS = {
    "decision_ref",
    "idea_ref",
    "prior_review_ref",
    "review_id",
}

LEARNING_METRIC_FORBIDDEN_KEYS = {
    "account",
    "allocation",
    "asset",
    "benchmark",
    "client",
    "deploymentaction",
    "holding",
    "performance",
    "pnl",
    "portfolio",
    "price",
    "return",
    "symbol",
    "ticker",
    "transaction",
    "weight",
}


def validate_learning_metric_fixture_boundary(
    value: object, location: str, errors: list[str], key: str | None = None
) -> None:
    """Keep the derived-metric truth table visibly synthetic and public-safe."""

    if isinstance(value, dict):
        for child_key, child in value.items():
            normalized_key = re.sub(r"[^a-z0-9]+", "", child_key.lower())
            child_location = f"{location}.{child_key}"
            if normalized_key in LEARNING_METRIC_FORBIDDEN_KEYS:
                errors.append(
                    f"{child_location}: prohibited private, performance, "
                    "deployment, or weighted-score field"
                )
            validate_learning_metric_fixture_boundary(
                child, child_location, errors, child_key
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_learning_metric_fixture_boundary(
                child, f"{location}[{index}]", errors, key
            )
        return
    if key in LEARNING_METRIC_IDENTIFIER_KEYS and (
        not isinstance(value, str) or "SYNTH" not in value
    ):
        errors.append(f"{location}: public metric identifier must be visibly synthetic")


def validate_learning_metric_cases(
    parsed: dict[Path, object],
    source_statuses: dict[str, str],
    errors: list[str],
) -> None:
    """Reproduce exact learning-loop truth tables with full input validation."""

    path = Path("examples/synthetic/learning-metrics-cases.json")
    cases = parsed.get(path)
    require_keys(
        cases,
        {"spec_version", "idea_balanced", "review_balanced", "chain_exclusions"},
        str(path),
        errors,
    )
    if not isinstance(cases, dict):
        return
    if cases.get("spec_version") != "1.0.0":
        errors.append(f"{path}.spec_version: expected 1.0.0")
    validate_learning_metric_fixture_boundary(cases, str(path), errors)

    if Draft202012Validator is None or FormatChecker is None:
        return
    idea_schema = parsed.get(Path("schemas/v1/investment-idea.schema.json"))
    review_schema = parsed.get(Path("schemas/v1/outcome-review.schema.json"))
    if not isinstance(idea_schema, dict) or not isinstance(review_schema, dict):
        errors.append(f"{path}: metric input schemas could not be loaded")
        return
    idea_schema_validator = Draft202012Validator(
        idea_schema, format_checker=FormatChecker()
    )
    review_schema_validator = Draft202012Validator(
        review_schema, format_checker=FormatChecker()
    )

    def idea_is_valid(idea: Mapping[str, object]) -> bool:
        semantic_errors: list[str] = []
        validate_idea_fixture(
            Path(f"{path}::generated-idea"),
            idea,
            source_statuses,
            semantic_errors,
        )
        return not list(idea_schema_validator.iter_errors(idea)) and not semantic_errors

    def review_is_valid(review: Mapping[str, object]) -> bool:
        semantic_errors: list[str] = []
        validate_outcome_review(
            review,
            Path(f"{path}::generated-review"),
            semantic_errors,
        )
        return not list(review_schema_validator.iter_errors(review)) and not semantic_errors

    def referenced_fixtures(section: object, section_name: str) -> list[dict[str, object]]:
        if not isinstance(section, dict):
            errors.append(f"{path}.{section_name}: expected an object")
            return []
        references = section.get("fixture_refs")
        if not isinstance(references, list) or not references:
            errors.append(f"{path}.{section_name}.fixture_refs: expected a non-empty array")
            return []
        resolved: list[dict[str, object]] = []
        for index, name in enumerate(references):
            location = f"{path}.{section_name}.fixture_refs[{index}]"
            if (
                not isinstance(name, str)
                or not name
                or Path(name).name != name
                or Path(name).suffix != ".json"
            ):
                errors.append(f"{location}: expected one local synthetic JSON filename")
                continue
            fixture = parsed.get(Path("examples/synthetic") / name)
            if not isinstance(fixture, dict):
                errors.append(f"{location}: referenced fixture could not be loaded")
                continue
            resolved.append(fixture)
        return resolved

    idea_case = cases.get("idea_balanced")
    ideas = referenced_fixtures(idea_case, "idea_balanced")
    if ideas and isinstance(idea_case, dict):
        try:
            measured_ideas = measure_idea_cohort(
                ideas, idea_validator=idea_is_valid
            )
            expected_ideas = idea_case.get("expected")
            if not isinstance(expected_ideas, dict):
                raise LearningMetricError("idea truth table expected result is missing")
            assert_metric_claim(measured_ideas, expected_ideas)
        except LearningMetricError as exc:
            errors.append(f"{path}.idea_balanced: {exc}")

    review_case = cases.get("review_balanced")
    reviews = referenced_fixtures(review_case, "review_balanced")
    if reviews and isinstance(review_case, dict):
        predecessor_recipe = review_case.get("predecessor")
        if not isinstance(predecessor_recipe, dict):
            errors.append(f"{path}.review_balanced.predecessor: expected an object")
        else:
            clone_name = predecessor_recipe.get("clone_fixture_ref")
            clone = (
                parsed.get(Path("examples/synthetic") / clone_name)
                if isinstance(clone_name, str) and Path(clone_name).name == clone_name
                else None
            )
            if not isinstance(clone, dict):
                errors.append(
                    f"{path}.review_balanced.predecessor: clone fixture could not be loaded"
                )
            else:
                predecessor = copy.deepcopy(clone)
                predecessor["review_id"] = predecessor_recipe.get("review_id")
                if predecessor_recipe.get("remove_prior_review_ref") is True:
                    predecessor.pop("prior_review_ref", None)
                reviews.append(predecessor)

        targets: list[dict[str, str]] = []
        seen_decisions: set[str] = set()
        for review in reviews:
            links = review.get("links")
            if not isinstance(links, dict):
                continue
            decision_ref = links.get("decision_ref")
            idea_ref = links.get("idea_ref")
            if (
                isinstance(decision_ref, str)
                and isinstance(idea_ref, str)
                and decision_ref not in seen_decisions
            ):
                seen_decisions.add(decision_ref)
                targets.append(
                    {"decision_ref": decision_ref, "idea_ref": idea_ref}
                )
        try:
            measured_reviews = measure_outcome_review_cohort(
                targets, reviews, review_validator=review_is_valid
            )
            expected_reviews = review_case.get("expected")
            if not isinstance(expected_reviews, dict):
                raise LearningMetricError("review truth table expected result is missing")
            assert_metric_claim(measured_reviews, expected_reviews)
        except LearningMetricError as exc:
            errors.append(f"{path}.review_balanced: {exc}")

    chain_case = cases.get("chain_exclusions")
    if not isinstance(chain_case, dict):
        errors.append(f"{path}.chain_exclusions: expected an object")
        return
    chain_targets = chain_case.get("targets")
    fragments = chain_case.get("topology_fragments")
    expected_cohort = chain_case.get("expected_review_cohort")
    if (
        not isinstance(chain_targets, list)
        or not isinstance(fragments, list)
        or not isinstance(expected_cohort, dict)
    ):
        errors.append(f"{path}.chain_exclusions: incomplete topology truth table")
        return

    adverse_base = parsed.get(
        Path("examples/synthetic/outcome-review-adverse-disciplined.json")
    )
    followed_base = parsed.get(
        Path("examples/synthetic/outcome-review-invalidation-followed.json")
    )
    if not isinstance(adverse_base, dict) or not isinstance(followed_base, dict):
        errors.append(f"{path}.chain_exclusions: base review fixtures could not be loaded")
        return

    chain_reviews: list[dict[str, object]] = []
    for index, fragment in enumerate(fragments):
        location = f"{path}.chain_exclusions.topology_fragments[{index}]"
        if not isinstance(fragment, dict):
            errors.append(f"{location}: expected an object")
            continue
        trigger = fragment.get("invalidation_trigger")
        response = fragment.get("invalidation_response")
        timing = fragment.get("timing_discipline")
        links = fragment.get("links")
        if not all(isinstance(value, dict) for value in (trigger, response, timing, links)):
            errors.append(f"{location}: incomplete measurement-relevant fields")
            continue
        assert isinstance(trigger, dict)
        assert isinstance(response, dict)
        assert isinstance(timing, dict)
        assert isinstance(links, dict)
        base = followed_base if trigger.get("state") == "triggered" else adverse_base
        review = copy.deepcopy(base)
        review["review_id"] = fragment.get("review_id")
        review["links"]["decision_ref"] = links.get("decision_ref")
        review["links"]["idea_ref"] = links.get("idea_ref")
        review["timing_discipline"]["assessment_state"] = timing.get(
            "assessment_state"
        )
        review["timing_discipline"]["classification"] = timing.get(
            "classification"
        )
        review.pop("prior_review_ref", None)
        if "prior_review_ref" in fragment:
            review["prior_review_ref"] = fragment.get("prior_review_ref")
        if review_is_valid(review) is not True:
            errors.append(f"{location}: materialized review must fully validate")
        chain_reviews.append(review)

    try:
        measured_chain = measure_outcome_review_cohort(
            chain_targets,
            chain_reviews,
            review_validator=review_is_valid,
        )
        assert_metric_claim(measured_chain["review_cohort"], expected_cohort)
    except LearningMetricError as exc:
        errors.append(f"{path}.chain_exclusions: {exc}")


def validate_examples(parsed: dict[Path, object], errors: list[str]) -> None:
    report_path = Path("examples/synthetic/report-manifest.json")
    legacy_report_path = Path("examples/synthetic/report-manifest-legacy-1.0.json")
    acceptance_path = Path("examples/synthetic/report-acceptance-cases.json")
    primary_idea_path = Path("examples/synthetic/investment-idea.json")
    legacy_idea_path = Path("examples/synthetic/investment-idea-legacy-1.0.json")
    decision_path = Path("examples/synthetic/decision-record.json")
    historian_decision_path = Path(
        "examples/synthetic/decision-record-historian-lesson.json"
    )
    completion_path = Path("examples/synthetic/universe-completion-cases.json")
    compatibility_path = Path("tests/compatibility/v1-fixtures.json")

    report = parsed.get(report_path)
    legacy_report = parsed.get(legacy_report_path)
    acceptance = parsed.get(acceptance_path)
    decision = parsed.get(decision_path)
    historian_decision = parsed.get(historian_decision_path)
    completion = parsed.get(completion_path)
    decision_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("decision-record")
        and path.suffix == ".json"
    )
    decisions = [(path, parsed.get(path)) for path in decision_paths]
    idea_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("investment-idea")
        and path.suffix == ".json"
    )
    ideas = [(path, parsed.get(path)) for path in idea_paths]
    outcome_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("outcome-review")
        and path.suffix == ".json"
    )
    outcome_reviews = [(path, parsed.get(path)) for path in outcome_paths]
    historian_lesson_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("historian-lesson")
        and path.suffix == ".json"
    )
    historian_lessons = [
        (path, parsed.get(path)) for path in historian_lesson_paths
    ]

    require_keys(
        report,
        {
            "artifact",
            "coverage",
            "data_as_of",
            "decision_ids",
            "freshness",
            "gate_inputs",
            "generated_at",
            "idea_ids",
            "quality_flags",
            "report_id",
            "report_type",
            "schema_version",
            "sources",
            "status",
            "status_reason",
        },
        str(report_path),
        errors,
    )
    require_keys(
        decision,
        {
            "alternatives_considered",
            "decision_id",
            "deployment",
            "evidence_ids",
            "historian_note",
            "idea_id",
            "invalidation_conditions",
            "rationale",
            "recorded_at",
            "research_disposition",
            "review_by",
            "schema_version",
            "skeptic_countercase",
        },
        str(decision_path),
        errors,
    )

    for path, value in [
        (report_path, report),
        (legacy_report_path, legacy_report),
        *decisions,
        *ideas,
        *outcome_reviews,
        *historian_lessons,
    ]:
        walk_timestamps(value, str(path), errors)

    if isinstance(report, dict) and report.get("schema_version") != "1.1.0":
        errors.append(f"{report_path}: synthetic report must use schema version 1.1.0")
    if (
        not isinstance(legacy_report, dict)
        or legacy_report.get("schema_version") != "1.0.0"
    ):
        errors.append(
            f"{legacy_report_path}: legacy report fixture must preserve schema 1.0.0"
        )
    if isinstance(decision, dict) and decision.get("schema_version") != "1.0.0":
        errors.append(f"{decision_path}: synthetic decision must use schema version 1.0.0")
    if (
        not isinstance(historian_decision, dict)
        or historian_decision.get("schema_version") != "1.1.0"
    ):
        errors.append(
            f"{historian_decision_path}: historian decision must use schema "
            "version 1.1.0"
        )

    for path, review in outcome_reviews:
        validate_outcome_review(review, path, errors)
    validate_outcome_review_fixture_coverage(outcome_reviews, errors)
    for path, lesson in historian_lessons:
        validate_historian_lesson(lesson, path, errors)
    validate_historian_lesson_chain(historian_lessons, errors)
    for path, candidate_decision in decisions:
        validate_decision_historian_lesson_refs(
            candidate_decision, historian_lessons, path, errors
        )

    source_statuses: dict[str, str] = {}
    if isinstance(report, dict):
        coverage = report.get("coverage")
        if isinstance(coverage, dict):
            expected = coverage.get("expected")
            observed = coverage.get("observed")
            percent = coverage.get("percent")
            if isinstance(expected, int) and isinstance(observed, int):
                if observed > expected:
                    errors.append(f"{report_path}: observed coverage exceeds expected")
                calculated = 0.0 if expected == 0 else observed / expected * 100
                if not isinstance(percent, (int, float)) or abs(percent - calculated) > 0.01:
                    errors.append(f"{report_path}: coverage percent does not match counts")

            if report.get("status") == "complete" and (
                expected != observed
                or not isinstance(expected, int)
                or isinstance(expected, bool)
                or expected <= 0
                or percent != 100
                or coverage.get("gaps")
            ):
                errors.append(f"{report_path}: complete status requires full coverage")

        freshness = report.get("freshness")
        artifact = report.get("artifact")
        if report.get("status") == "complete":
            if not isinstance(freshness, dict) or freshness.get("status") != "fresh":
                errors.append(f"{report_path}: complete status requires fresh inputs")
            if not isinstance(artifact, dict) or artifact.get("status") != "persisted":
                errors.append(f"{report_path}: complete status requires durable persistence")

        sources = report.get("sources")
        if isinstance(sources, list):
            for index, source in enumerate(sources):
                source_location = f"{report_path}.sources[{index}]"
                if not isinstance(source, dict):
                    errors.append(f"{source_location}: expected an object")
                    continue
                source_id = source.get("source_id")
                status = source.get("status")
                if not isinstance(source_id, str) or not source_id:
                    errors.append(f"{source_location}.source_id: expected a non-empty string")
                elif source_id in source_statuses:
                    errors.append(f"{source_location}.source_id: duplicate source ID")
                elif isinstance(status, str):
                    source_statuses[source_id] = status

    classifications: dict[Path, str | None] = {}
    idea_ids: dict[str, Path] = {}
    for path, idea in ideas:
        classification = validate_idea_fixture(path, idea, source_statuses, errors)
        classifications[path] = classification
        if not isinstance(idea, dict):
            continue
        idea_id = idea.get("idea_id")
        if not isinstance(idea_id, str) or not idea_id:
            errors.append(f"{path}.idea_id: expected a non-empty string")
        elif idea_id in idea_ids:
            errors.append(f"{path}.idea_id: duplicate idea ID also used by {idea_ids[idea_id]}")
        else:
            idea_ids[idea_id] = path

    expected_classes = {
        "new",
        "repeat_unchanged",
        "materially_updated",
        "reintroduced",
        "stale_repeat",
        "unverified",
    }
    version_11_ideas = [
        idea
        for _, idea in ideas
        if isinstance(idea, dict) and idea.get("schema_version") == "1.1.0"
    ]
    actual_classes = {
        classification for classification in classifications.values() if classification
    }
    if actual_classes != expected_classes:
        errors.append("synthetic idea fixtures must cover every lineage classification exactly")
    if len(version_11_ideas) != len(expected_classes):
        errors.append("synthetic cohort must contain exactly six version 1.1.0 ideas")

    legacy = parsed.get(legacy_idea_path)
    if not isinstance(legacy, dict) or legacy.get("schema_version") != "1.0.0":
        errors.append(f"{legacy_idea_path}: legacy fixture must preserve schema 1.0.0")

    if isinstance(report, dict):
        linked_ids = report.get("idea_ids")
        if not isinstance(linked_ids, list):
            errors.append(f"{report_path}.idea_ids: expected an array")
            linked_ids = []
        current_ids = {
            idea.get("idea_id")
            for idea in version_11_ideas
            if isinstance(idea.get("idea_id"), str)
        }
        if set(linked_ids) != current_ids:
            errors.append(f"{report_path}: idea_ids must link the full version 1.1.0 cohort")

    primary_idea = parsed.get(primary_idea_path)
    if isinstance(report, dict) and isinstance(decision, dict):
        if decision.get("decision_id") not in report.get("decision_ids", []):
            errors.append(f"{report_path}: synthetic decision ID is not linked")
    if isinstance(primary_idea, dict) and isinstance(decision, dict):
        if decision.get("idea_id") != primary_idea.get("idea_id"):
            errors.append(f"{decision_path}: idea link does not match primary synthetic idea")

    verified = [
        idea
        for idea in version_11_ideas
        if isinstance(idea.get("lineage"), dict)
        and idea["lineage"].get("status") == "verified"
    ]
    repeats = [
        idea
        for idea in verified
        if idea["lineage"].get("classification") in VERIFIED_REPEAT_CLASSES
    ]
    new_ideas = [idea for idea in verified if idea["lineage"].get("classification") == "new"]
    material_updates = [
        idea for idea in repeats if idea["lineage"].get("classification") == "materially_updated"
    ]
    reintroduced = [
        idea for idea in repeats if idea["lineage"].get("classification") == "reintroduced"
    ]
    stale_repeats = [
        idea for idea in repeats if idea["lineage"].get("classification") == "stale_repeat"
    ]
    explained = [idea for idea in repeats if isinstance(idea.get("repeat_reason"), str)]
    unverified_count = len(version_11_ideas) - len(verified)

    expected_rates = {
        "new": 20.0,
        "repeat": 80.0,
        "explained": 100.0,
        "material": 25.0,
        "decision_changing": 50.0,
        "stale": 25.0,
        "unverified": 100 / 6,
    }
    actual_rates = {
        "new": percent_or_none(len(new_ideas), len(verified)),
        "repeat": percent_or_none(len(repeats), len(verified)),
        "explained": percent_or_none(len(explained), len(repeats)),
        "material": percent_or_none(len(material_updates), len(repeats)),
        "decision_changing": percent_or_none(
            len(material_updates) + len(reintroduced), len(repeats)
        ),
        "stale": percent_or_none(len(stale_repeats), len(repeats)),
        "unverified": percent_or_none(unverified_count, len(version_11_ideas)),
    }
    for name, expected_rate in expected_rates.items():
        actual = actual_rates.get(name)
        if actual is None or abs(actual - expected_rate) > 0.01:
            errors.append(f"synthetic lineage metric {name} does not match expected rate")

    repeat_ages: list[float] = []
    for idea in repeats:
        first_seen = timestamp_value(idea.get("first_seen_at"))
        last_seen = timestamp_value(idea.get("last_seen_at"))
        if first_seen and last_seen:
            repeat_ages.append((last_seen - first_seen).total_seconds() / 3600)
    if (
        len(repeat_ages) != 4
        or median(repeat_ages) != 252.0
        or max(repeat_ages, default=0) != 744.0
    ):
        errors.append("synthetic repeat-age metrics do not match expected values")

    evidence_entries = [
        evidence
        for idea in version_11_ideas
        for evidence in idea.get("evidence", [])
        if isinstance(evidence, dict)
    ]
    known_recency = [
        evidence
        for evidence in evidence_entries
        if source_statuses.get(evidence.get("source_id")) in {"available", "fallback", "stale"}
    ]
    stale_evidence = [
        evidence
        for evidence in known_recency
        if source_statuses.get(evidence.get("source_id")) == "stale"
    ]
    unknown_evidence = len(evidence_entries) - len(known_recency)
    if (
        percent_or_none(len(stale_evidence), len(known_recency)) is None
        or abs(percent_or_none(len(stale_evidence), len(known_recency)) - 100 / 6) > 0.01
        or unknown_evidence != 0
    ):
        errors.append("synthetic stale-evidence metrics do not match expected values")

    if percent_or_none(0, 0) is not None or percent_or_none(0, 5) != 0.0:
        errors.append("metric zero-denominator behavior is inconsistent")

    for candidate_path, candidate in sorted(parsed.items()):
        if (
            candidate_path.parent == Path("examples/synthetic")
            and candidate_path.name.startswith("report-manifest")
        ):
            validate_report_manifest_acceptance(candidate, candidate_path, errors)

    compatibility = parsed.get(compatibility_path)
    if isinstance(compatibility, dict):
        contracts = compatibility.get("contracts")
        report_contract = (
            contracts.get("report-manifest") if isinstance(contracts, dict) else None
        )
        fixtures = (
            report_contract.get("fixtures")
            if isinstance(report_contract, dict)
            else None
        )
        if isinstance(fixtures, list):
            for index, fixture in enumerate(fixtures):
                if not isinstance(fixture, dict):
                    continue
                validate_report_manifest_acceptance(
                    fixture.get("instance"),
                    Path(f"{compatibility_path}::report-manifest[{index}]"),
                    errors,
                )
        outcome_contract = (
            contracts.get("outcome-review") if isinstance(contracts, dict) else None
        )
        outcome_fixtures = (
            outcome_contract.get("fixtures")
            if isinstance(outcome_contract, dict)
            else None
        )
        if isinstance(outcome_fixtures, list):
            for index, fixture in enumerate(outcome_fixtures):
                if not isinstance(fixture, dict):
                    continue
                validate_outcome_review(
                    fixture.get("instance"),
                    Path(f"{compatibility_path}::outcome-review[{index}]"),
                    errors,
                )
        historian_contract = (
            contracts.get("historian-lesson") if isinstance(contracts, dict) else None
        )
        historian_fixtures = (
            historian_contract.get("fixtures")
            if isinstance(historian_contract, dict)
            else None
        )
        compatibility_lessons: list[tuple[Path, object]] = []
        if isinstance(historian_fixtures, list):
            for index, fixture in enumerate(historian_fixtures):
                if not isinstance(fixture, dict):
                    continue
                fixture_path = Path(
                    f"{compatibility_path}::historian-lesson[{index}]"
                )
                instance = fixture.get("instance")
                compatibility_lessons.append((fixture_path, instance))
                validate_historian_lesson(instance, fixture_path, errors)
            validate_historian_lesson_chain(compatibility_lessons, errors)
        decision_contract = (
            contracts.get("decision-record") if isinstance(contracts, dict) else None
        )
        decision_fixtures = (
            decision_contract.get("fixtures")
            if isinstance(decision_contract, dict)
            else None
        )
        if isinstance(decision_fixtures, list):
            for index, fixture in enumerate(decision_fixtures):
                if not isinstance(fixture, dict):
                    continue
                validate_decision_historian_lesson_refs(
                    fixture.get("instance"),
                    compatibility_lessons,
                    Path(f"{compatibility_path}::decision-record[{index}]"),
                    errors,
                )
    validate_learning_metric_cases(parsed, source_statuses, errors)
    validate_report_acceptance_cases(acceptance, errors)
    validate_universe_completion_cases(completion, errors)


def main() -> int:
    errors: list[str] = []
    paths = tracked_files()
    tracked = {path.as_posix() for path in paths}

    missing = sorted(REQUIRED_FILES - tracked)
    if missing:
        errors.append("Missing required tracked files: " + ", ".join(missing))

    parsed_json: dict[Path, object] = {}

    for path in paths:
        validate_public_path(path, errors)
        absolute = ROOT / path

        try:
            raw = absolute.read_bytes()
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{path}: public baseline files must be UTF-8: {exc}")
            continue

        if b"\r\n" in raw:
            errors.append(f"{path}: use LF rather than CRLF")
        if raw and not raw.endswith(b"\n"):
            errors.append(f"{path}: missing final newline")

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                errors.append(f"{path}:{line_number}: trailing whitespace")
            if line.startswith(CONFLICT_MARKERS):
                errors.append(f"{path}:{line_number}: unresolved conflict marker")

        if path.suffix.lower() == ".md":
            validate_relative_links(path, text, errors)

        if path.suffix.lower() == ".json":
            parsed = load_json(path, errors)
            if parsed is not None:
                parsed_json[path] = parsed

        if path.as_posix().startswith("schemas/") and path.suffix == ".json":
            parsed = parsed_json.get(path)
            if isinstance(parsed, dict):
                if parsed.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                    errors.append(f"{path}: schema must declare JSON Schema 2020-12")
                if parsed.get("type") != "object":
                    errors.append(f"{path}: top-level schema type must be object")

    validate_json_schema_examples(parsed_json, errors)
    validate_examples(parsed_json, errors)

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Repository validation passed for {len(paths)} tracked public-safe files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

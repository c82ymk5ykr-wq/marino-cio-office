#!/usr/bin/env python3
"""Validation for the public Marino CIO Office contract repository."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from urllib.parse import unquote

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
    "docs/decisions/README.md",
    "docs/contract-vocabulary.md",
    "docs/idea-lineage-metrics.md",
    "docs/operating-model.md",
    "docs/outcome-review-contract.md",
    "docs/public-private-boundary.md",
    "docs/report-acceptance-gates.md",
    "docs/schema-compatibility-policy.md",
    "docs/specification-inventory.md",
    "docs/universe-completion-gates.md",
    "examples/synthetic/decision-record.json",
    "examples/synthetic/investment-idea.json",
    "examples/synthetic/investment-idea-legacy-1.0.json",
    "examples/synthetic/investment-idea-materially-updated.json",
    "examples/synthetic/investment-idea-reintroduced.json",
    "examples/synthetic/investment-idea-repeat-unchanged.json",
    "examples/synthetic/investment-idea-stale-repeat.json",
    "examples/synthetic/investment-idea-unverified-lineage.json",
    "examples/synthetic/outcome-review-adverse-disciplined.json",
    "examples/synthetic/outcome-review-correction.json",
    "examples/synthetic/outcome-review-favorable-undisciplined.json",
    "examples/synthetic/outcome-review-invalidation-delayed.json",
    "examples/synthetic/outcome-review-invalidation-followed.json",
    "examples/synthetic/outcome-review-partial-unverified.json",
    "examples/synthetic/outcome-review-unavailable.json",
    "examples/synthetic/report-acceptance-cases.json",
    "examples/synthetic/report-manifest-legacy-1.0.json",
    "examples/synthetic/report-manifest.json",
    "examples/synthetic/universe-completion-cases.json",
    "requirements-validation.txt",
    "schemas/v1/decision-record.schema.json",
    "schemas/v1/investment-idea.schema.json",
    "schemas/v1/outcome-review.schema.json",
    "schemas/v1/report-manifest.schema.json",
    "scripts/validate.py",
    "templates/architecture-decision.md",
    "templates/daily-decision-report.md",
    "templates/decision-record.md",
    "templates/outcome-review.md",
    "tests/compatibility/v1-fixtures.json",
    "tests/schema_helpers.py",
    "tests/test_report_acceptance.py",
    "tests/test_outcome_review.py",
    "tests/test_schema_compatibility.py",
    "tests/test_schema_validation.py",
}

SCHEMA_FIXTURE_FAMILIES = {
    Path("schemas/v1/report-manifest.schema.json"): "report-manifest",
    Path("schemas/v1/investment-idea.schema.json"): "investment-idea",
    Path("schemas/v1/decision-record.schema.json"): "decision-record",
    Path("schemas/v1/outcome-review.schema.json"): "outcome-review",
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
        "data_as_of",
        "evidence_cutoff_at",
        "ended_at",
        "first_seen_at",
        "generated_at",
        "last_seen_at",
        "last_material_change_at",
        "membership_as_of",
        "oldest_material_source_as_of",
        "persisted_at",
        "recorded_at",
        "retrieved_at",
        "review_by",
        "reviewed_at",
        "started_at",
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


def validate_outcome_review_fixture(
    path: Path,
    value: object,
    decisions_by_id: dict[str, dict[str, object]],
    idea_ids: set[str],
    errors: list[str],
) -> None:
    """Validate outcome-review joins, evidence references, and clock order."""

    location = str(path)
    if not isinstance(value, dict):
        errors.append(f"{location}: expected a JSON object")
        return

    review_id = value.get("review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        errors.append(f"{location}.review_id: expected a non-whitespace opaque ID")

    supersedes_review_id = value.get("supersedes_review_id")
    if isinstance(review_id, str) and supersedes_review_id == review_id:
        errors.append(
            f"{location}.supersedes_review_id: a review cannot supersede itself"
        )

    decision_id = value.get("decision_id")
    decision = (
        decisions_by_id.get(decision_id) if isinstance(decision_id, str) else None
    )
    if decision is None:
        errors.append(f"{location}.decision_id: linked decision does not exist")

    idea_id = value.get("idea_id")
    if not isinstance(idea_id, str) or idea_id not in idea_ids:
        errors.append(f"{location}.idea_id: linked idea does not exist")
    if decision is not None and idea_id != decision.get("idea_id"):
        errors.append(f"{location}: idea_id does not match the linked decision")

    recorded_at = timestamp_value(decision.get("recorded_at")) if decision else None
    reviewed_at = timestamp_value(value.get("reviewed_at"))
    evidence_cutoff_at = timestamp_value(value.get("evidence_cutoff_at"))
    if "reviewed_at" in value and reviewed_at is None:
        errors.append(f"{location}.reviewed_at: invalid UTC timestamp")
    if "evidence_cutoff_at" in value and evidence_cutoff_at is None:
        errors.append(f"{location}.evidence_cutoff_at: invalid UTC timestamp")
    evaluation_window = value.get("evaluation_window")
    started_at: datetime | None = None
    ended_at: datetime | None = None
    if isinstance(evaluation_window, dict):
        started_at = timestamp_value(evaluation_window.get("started_at"))
        ended_at = timestamp_value(evaluation_window.get("ended_at"))
        if "started_at" in evaluation_window and started_at is None:
            errors.append(
                f"{location}.evaluation_window.started_at: invalid UTC timestamp"
            )
        if "ended_at" in evaluation_window and ended_at is None:
            errors.append(
                f"{location}.evaluation_window.ended_at: invalid UTC timestamp"
            )

    if recorded_at and reviewed_at and recorded_at > reviewed_at:
        errors.append(f"{location}: decision recorded_at cannot be after reviewed_at")
    if recorded_at and started_at and recorded_at > started_at:
        errors.append(
            f"{location}: decision recorded_at cannot be after evaluation start"
        )
    if started_at and ended_at and started_at >= ended_at:
        errors.append(f"{location}: evaluation start must be before evaluation end")
    if ended_at and evidence_cutoff_at and ended_at > evidence_cutoff_at:
        errors.append(f"{location}: evaluation end cannot be after evidence cutoff")
    if evidence_cutoff_at and reviewed_at and evidence_cutoff_at > reviewed_at:
        errors.append(f"{location}: evidence cutoff cannot be after reviewed_at")
    if ended_at and reviewed_at and ended_at > reviewed_at:
        errors.append(f"{location}: evaluation end cannot be after reviewed_at")
    if recorded_at and evidence_cutoff_at and recorded_at > evidence_cutoff_at:
        errors.append(f"{location}: decision recorded_at cannot be after evidence cutoff")

    evidence = value.get("evidence_ids")
    root_evidence = (
        {evidence_id for evidence_id in evidence if isinstance(evidence_id, str)}
        if isinstance(evidence, list)
        else set()
    )

    invalidation = value.get("invalidation")
    if isinstance(invalidation, dict):
        invalidation_evidence = invalidation.get("evidence_ids")
        if isinstance(invalidation_evidence, list):
            if any(
                not isinstance(evidence_id, str) or evidence_id not in root_evidence
                for evidence_id in invalidation_evidence
            ):
                errors.append(
                    f"{location}.invalidation.evidence_ids: dangling review evidence IDs"
                )

    factors = value.get("attribution")
    factor_ids: set[str] = set()
    if isinstance(factors, list):
        for index, factor in enumerate(factors):
            factor_location = f"{location}.attribution[{index}]"
            if not isinstance(factor, dict):
                continue
            factor_id = factor.get("factor_id")
            if isinstance(factor_id, str):
                if factor_id in factor_ids:
                    errors.append(f"{factor_location}.factor_id: duplicate factor ID")
                factor_ids.add(factor_id)
            factor_evidence = factor.get("evidence_ids")
            if isinstance(factor_evidence, list) and any(
                not isinstance(evidence_id, str) or evidence_id not in root_evidence
                for evidence_id in factor_evidence
            ):
                errors.append(
                    f"{factor_location}.evidence_ids: dangling review evidence ID"
                )


def validate_outcome_review_cohort(
    reviews: list[tuple[Path, object]], errors: list[str]
) -> None:
    """Validate append-only supersession links across an outcome-review cohort."""

    reviews_by_id: dict[str, tuple[Path, dict[str, object]]] = {}
    for path, review in reviews:
        if not isinstance(review, dict):
            continue
        review_id = review.get("review_id")
        if isinstance(review_id, str) and review_id not in reviews_by_id:
            reviews_by_id[review_id] = (path, review)

    for review_id, (path, review) in reviews_by_id.items():
        predecessor_id = review.get("supersedes_review_id")
        if not isinstance(predecessor_id, str) or predecessor_id == review_id:
            continue

        predecessor_entry = reviews_by_id.get(predecessor_id)
        if predecessor_entry is None:
            errors.append(
                f"{path}.supersedes_review_id: linked prior review does not exist"
            )
            continue

        predecessor_path, predecessor = predecessor_entry
        if predecessor.get("decision_id") != review.get("decision_id"):
            errors.append(
                f"{path}.supersedes_review_id: prior review {predecessor_path} "
                "has a different decision_id"
            )
        if predecessor.get("idea_id") != review.get("idea_id"):
            errors.append(
                f"{path}.supersedes_review_id: prior review {predecessor_path} "
                "has a different idea_id"
            )

        predecessor_reviewed_at = timestamp_value(predecessor.get("reviewed_at"))
        reviewed_at = timestamp_value(review.get("reviewed_at"))
        if (
            predecessor_reviewed_at is not None
            and reviewed_at is not None
            and predecessor_reviewed_at >= reviewed_at
        ):
            errors.append(
                f"{path}.supersedes_review_id: prior review must have an earlier "
                "reviewed_at"
            )

    reported_cycles: set[frozenset[str]] = set()
    for start_id, (start_path, _) in reviews_by_id.items():
        chain: list[str] = []
        positions: dict[str, int] = {}
        current_id = start_id
        while current_id in reviews_by_id:
            if current_id in positions:
                cycle = frozenset(chain[positions[current_id] :])
                if cycle and cycle not in reported_cycles:
                    reported_cycles.add(cycle)
                    errors.append(
                        f"{start_path}.supersedes_review_id: supersession cycle detected"
                    )
                break
            positions[current_id] = len(chain)
            chain.append(current_id)
            current_review = reviews_by_id[current_id][1]
            predecessor_id = current_review.get("supersedes_review_id")
            if not isinstance(predecessor_id, str):
                break
            current_id = predecessor_id


def validate_examples(parsed: dict[Path, object], errors: list[str]) -> None:
    report_path = Path("examples/synthetic/report-manifest.json")
    legacy_report_path = Path("examples/synthetic/report-manifest-legacy-1.0.json")
    acceptance_path = Path("examples/synthetic/report-acceptance-cases.json")
    primary_idea_path = Path("examples/synthetic/investment-idea.json")
    legacy_idea_path = Path("examples/synthetic/investment-idea-legacy-1.0.json")
    decision_path = Path("examples/synthetic/decision-record.json")
    completion_path = Path("examples/synthetic/universe-completion-cases.json")
    compatibility_path = Path("tests/compatibility/v1-fixtures.json")

    report = parsed.get(report_path)
    legacy_report = parsed.get(legacy_report_path)
    acceptance = parsed.get(acceptance_path)
    decision = parsed.get(decision_path)
    completion = parsed.get(completion_path)
    idea_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("investment-idea")
        and path.suffix == ".json"
    )
    ideas = [(path, parsed.get(path)) for path in idea_paths]
    outcome_review_paths = sorted(
        path
        for path in parsed
        if path.parent == Path("examples/synthetic")
        and path.name.startswith("outcome-review")
        and path.suffix == ".json"
    )
    outcome_reviews = [(path, parsed.get(path)) for path in outcome_review_paths]

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
        (decision_path, decision),
        *ideas,
        *outcome_reviews,
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

    decisions_by_id: dict[str, dict[str, object]] = {}
    if isinstance(decision, dict) and isinstance(decision.get("decision_id"), str):
        decisions_by_id[decision["decision_id"]] = decision

    review_ids: dict[str, Path] = {}
    review_values: list[dict[str, object]] = []
    for path, review in outcome_reviews:
        validate_outcome_review_fixture(
            path, review, decisions_by_id, set(idea_ids), errors
        )
        if not isinstance(review, dict):
            continue
        if review.get("schema_version") != "1.0.0":
            errors.append(f"{path}: synthetic outcome review must use version 1.0.0")
        review_id = review.get("review_id")
        if isinstance(review_id, str):
            if review_id in review_ids:
                errors.append(
                    f"{path}.review_id: duplicate review ID also used by {review_ids[review_id]}"
                )
            else:
                review_ids[review_id] = path
        review_values.append(review)

    validate_outcome_review_cohort(outcome_reviews, errors)

    outcome_case_coverage = {
        "adverse_with_disciplined_process": any(
            review.get("research_outcome") == "adverse"
            and review.get("process_quality") == "disciplined"
            for review in review_values
        ),
        "favorable_with_undisciplined_process": any(
            review.get("research_outcome") == "favorable"
            and review.get("process_quality") == "undisciplined"
            for review in review_values
        ),
        "triggered_invalidation_followed": any(
            isinstance(review.get("invalidation"), dict)
            and review["invalidation"].get("trigger_state") == "triggered"
            and review["invalidation"].get("response_state") == "followed"
            for review in review_values
        ),
        "triggered_invalidation_delayed_or_not_followed": any(
            isinstance(review.get("invalidation"), dict)
            and review["invalidation"].get("trigger_state") == "triggered"
            and review["invalidation"].get("response_state")
            in {"delayed", "not_followed"}
            for review in review_values
        ),
        "partial_or_unverified": any(
            review.get("assessability") == "partial"
            or review.get("ex_ante_basis") == "unverified"
            or review.get("evidence_quality") == "unverified"
            for review in review_values
        ),
    }
    missing_outcome_cases = sorted(
        name for name, present in outcome_case_coverage.items() if not present
    )
    if missing_outcome_cases:
        errors.append(
            "synthetic outcome reviews do not cover: "
            + ", ".join(missing_outcome_cases)
        )

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
        if isinstance(contracts, dict):
            decision_contract = contracts.get("decision-record")
            idea_contract = contracts.get("investment-idea")
            outcome_contract = contracts.get("outcome-review")
            decision_fixtures = (
                decision_contract.get("fixtures")
                if isinstance(decision_contract, dict)
                else []
            )
            idea_fixtures = (
                idea_contract.get("fixtures")
                if isinstance(idea_contract, dict)
                else []
            )
            outcome_fixtures = (
                outcome_contract.get("fixtures")
                if isinstance(outcome_contract, dict)
                else []
            )
            compatibility_decisions: dict[str, dict[str, object]] = {}
            if isinstance(decision_fixtures, list):
                for fixture in decision_fixtures:
                    instance = fixture.get("instance") if isinstance(fixture, dict) else None
                    if isinstance(instance, dict) and isinstance(
                        instance.get("decision_id"), str
                    ):
                        compatibility_decisions[instance["decision_id"]] = instance
            compatibility_idea_ids: set[str] = set()
            if isinstance(idea_fixtures, list):
                for fixture in idea_fixtures:
                    instance = fixture.get("instance") if isinstance(fixture, dict) else None
                    if isinstance(instance, dict) and isinstance(
                        instance.get("idea_id"), str
                    ):
                        compatibility_idea_ids.add(instance["idea_id"])
            if isinstance(outcome_fixtures, list):
                compatibility_reviews: list[tuple[Path, object]] = []
                for index, fixture in enumerate(outcome_fixtures):
                    if not isinstance(fixture, dict):
                        continue
                    fixture_path = Path(
                        f"{compatibility_path}::outcome-review[{index}]"
                    )
                    compatibility_reviews.append(
                        (fixture_path, fixture.get("instance"))
                    )
                    validate_outcome_review_fixture(
                        fixture_path,
                        fixture.get("instance"),
                        compatibility_decisions,
                        compatibility_idea_ids,
                        errors,
                    )
                validate_outcome_review_cohort(compatibility_reviews, errors)
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

#!/usr/bin/env python3
"""Dependency-free validation for the public Marino CIO Office baseline."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


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
    "docs/decisions/README.md",
    "docs/contract-vocabulary.md",
    "docs/operating-model.md",
    "docs/public-private-boundary.md",
    "docs/universe-completion-gates.md",
    "examples/synthetic/decision-record.json",
    "examples/synthetic/investment-idea.json",
    "examples/synthetic/report-manifest.json",
    "examples/synthetic/universe-completion-cases.json",
    "schemas/v1/decision-record.schema.json",
    "schemas/v1/investment-idea.schema.json",
    "schemas/v1/report-manifest.schema.json",
    "scripts/validate.py",
    "templates/architecture-decision.md",
    "templates/daily-decision-report.md",
    "templates/decision-record.md",
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
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{location}: timestamp must be a UTC string ending in Z")
        return

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{location}: invalid ISO-8601 timestamp {value!r}")


def walk_timestamps(value: object, location: str, errors: list[str]) -> None:
    timestamp_keys = {
        "data_as_of",
        "first_seen_at",
        "generated_at",
        "last_seen_at",
        "oldest_material_source_as_of",
        "recorded_at",
        "retrieved_at",
        "review_by",
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
    try:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}")
    return None


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


def validate_examples(parsed: dict[Path, object], errors: list[str]) -> None:
    report_path = Path("examples/synthetic/report-manifest.json")
    idea_path = Path("examples/synthetic/investment-idea.json")
    decision_path = Path("examples/synthetic/decision-record.json")
    completion_path = Path("examples/synthetic/universe-completion-cases.json")

    report = parsed.get(report_path)
    idea = parsed.get(idea_path)
    decision = parsed.get(decision_path)
    completion = parsed.get(completion_path)

    require_keys(
        report,
        {
            "artifact",
            "coverage",
            "data_as_of",
            "decision_ids",
            "freshness",
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
        idea,
        {
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
        },
        str(idea_path),
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

    for path, value in ((report_path, report), (idea_path, idea), (decision_path, decision)):
        if isinstance(value, dict) and value.get("schema_version") != "1.0.0":
            errors.append(f"{path}: synthetic example must use schema version 1.0.0")
        walk_timestamps(value, str(path), errors)

    if isinstance(report, dict):
        coverage = report.get("coverage")
        if isinstance(coverage, dict):
            expected = coverage.get("expected")
            observed = coverage.get("observed")
            percent = coverage.get("percent")
            if isinstance(expected, int) and isinstance(observed, int):
                if observed > expected:
                    errors.append(f"{report_path}: observed coverage exceeds expected")
                calculated = 100.0 if expected == 0 else observed / expected * 100
                if not isinstance(percent, (int, float)) or abs(percent - calculated) > 0.01:
                    errors.append(f"{report_path}: coverage percent does not match counts")

        if report.get("status") == "complete":
                if (
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

    if isinstance(report, dict) and isinstance(idea, dict):
        if idea.get("idea_id") not in report.get("idea_ids", []):
            errors.append(f"{report_path}: synthetic idea ID is not linked")

    if isinstance(report, dict) and isinstance(decision, dict):
        if decision.get("decision_id") not in report.get("decision_ids", []):
            errors.append(f"{report_path}: synthetic decision ID is not linked")

    if isinstance(idea, dict) and isinstance(decision, dict):
        if decision.get("idea_id") != idea.get("idea_id"):
            errors.append(f"{decision_path}: idea link does not match synthetic idea")

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

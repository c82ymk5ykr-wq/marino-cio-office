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
    "docs/decisions/README.md",
    "docs/operating-model.md",
    "docs/public-private-boundary.md",
    "examples/synthetic/decision-record.json",
    "examples/synthetic/investment-idea.json",
    "examples/synthetic/report-manifest.json",
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


def validate_examples(parsed: dict[Path, object], errors: list[str]) -> None:
    report_path = Path("examples/synthetic/report-manifest.json")
    idea_path = Path("examples/synthetic/investment-idea.json")
    decision_path = Path("examples/synthetic/decision-record.json")

    report = parsed.get(report_path)
    idea = parsed.get(idea_path)
    decision = parsed.get(decision_path)

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
                if expected != observed or coverage.get("gaps"):
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

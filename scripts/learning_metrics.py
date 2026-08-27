#!/usr/bin/env python3
"""Pure helpers for deterministic, public-safe learning-loop measurements.

The helpers require callers to supply full schema-and-semantic validators for
both input families before any artifact can be measured. Returned rates use
reduced rational strings so calculation is exact and display rounding remains
a separate concern.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from fractions import Fraction
import re
from statistics import median
from typing import Any


NOT_AVAILABLE = "not_available"

VERIFIED_REPEAT_CLASSES = (
    "repeat_unchanged",
    "materially_updated",
    "reintroduced",
    "stale_repeat",
)
TIMING_STATES = (
    "assessable",
    "partial",
    "unavailable",
    "unknown",
    "not_applicable",
)
TIMING_CLASSIFICATIONS = ("disciplined", "mixed", "undisciplined")
TRIGGER_STATES = (
    "triggered",
    "not_triggered",
    "ambiguous",
    "unknown",
    "not_applicable",
)
TRIGGERED_RESPONSE_STATES = (
    "followed",
    "delayed",
    "not_followed",
    "ambiguous",
    "unknown",
)
class LearningMetricError(ValueError):
    """Raised when a frozen cohort cannot support deterministic measurement."""


def assert_metric_claim(measured: Mapping[str, Any], claimed: Mapping[str, Any]) -> None:
    """Reject a claimed snapshot that changes a result or hides an output field."""

    if measured != claimed:
        raise LearningMetricError(
            "claimed learning metrics do not exactly match deterministic measurement"
        )


def _fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def rate(numerator: int, denominator: int) -> dict[str, int | str]:
    """Return a rate with raw counts and an exact reduced-rational value."""

    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise LearningMetricError(
            f"invalid rate counts: numerator={numerator}, denominator={denominator}"
        )
    value = (
        NOT_AVAILABLE
        if denominator == 0
        else _fraction_text(Fraction(numerator, denominator))
    )
    return {"numerator": numerator, "denominator": denominator, "value": value}


def _utc_instant(value: object, field: str) -> Fraction:
    """Parse a UTC RFC 3339 instant without truncating fractional seconds."""

    if not isinstance(value, str):
        raise LearningMetricError(f"{field} must be a UTC timestamp ending in Z")
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z",
        value,
    )
    if match is None:
        raise LearningMetricError(f"{field} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(match.group(1) + "+00:00")
    except ValueError as exc:
        raise LearningMetricError(f"{field} is not a valid timestamp") from exc
    epoch = datetime(1970, 1, 1, tzinfo=parsed.tzinfo)
    elapsed = parsed - epoch
    whole_seconds = elapsed.days * 86_400 + elapsed.seconds
    fraction_digits = match.group(2)
    fractional_seconds = (
        Fraction(int(fraction_digits), 10 ** len(fraction_digits))
        if fraction_digits is not None
        else Fraction(0)
    )
    return Fraction(whole_seconds) + fractional_seconds


def _age_hours(idea: Mapping[str, Any]) -> Fraction:
    first_seen = _utc_instant(idea.get("first_seen_at"), "first_seen_at")
    last_seen = _utc_instant(idea.get("last_seen_at"), "last_seen_at")
    elapsed_seconds = last_seen - first_seen
    if elapsed_seconds < 0:
        raise LearningMetricError("last_seen_at cannot precede first_seen_at")
    return elapsed_seconds / 3_600


def measure_idea_cohort(
    ideas: Sequence[Mapping[str, Any]],
    *,
    idea_validator: Callable[[Mapping[str, Any]], bool],
) -> dict[str, Any]:
    """Measure novelty and repeat quality for one frozen idea cohort.

    ``idea_validator`` must apply the complete schema and semantic contract;
    validation runs before version eligibility or lineage classification.
    Only investment-idea ``1.1.0`` records are metric eligible.  Valid legacy
    ``1.0.0`` records are explicitly counted as exclusions and never relabeled.
    """

    eligible: list[Mapping[str, Any]] = []
    legacy_count = 0
    seen_eligible_ids: set[str] = set()

    for index, idea in enumerate(ideas):
        if not isinstance(idea, Mapping):
            raise LearningMetricError(f"ideas[{index}] must be an object")
        try:
            valid = idea_validator(idea)
        except Exception as exc:
            raise LearningMetricError(
                f"ideas[{index}] validation could not complete"
            ) from exc
        if valid is not True:
            raise LearningMetricError(
                f"ideas[{index}] fails the full schema and semantic contract"
            )
        version = idea.get("schema_version")
        if version == "1.0.0":
            legacy_count += 1
            continue
        if version != "1.1.0":
            raise LearningMetricError(
                f"ideas[{index}].schema_version is not metric eligible or legacy"
            )
        idea_id = idea.get("idea_id")
        if not isinstance(idea_id, str) or not idea_id:
            raise LearningMetricError(f"ideas[{index}].idea_id must be non-empty")
        if idea_id in seen_eligible_ids:
            raise LearningMetricError(
                "frozen idea cohort contains more than one 1.1.0 record for "
                f"idea_id {idea_id!r}"
            )
        seen_eligible_ids.add(idea_id)
        eligible.append(idea)

    class_counts = Counter(
        {
            "new": 0,
            "repeat_unchanged": 0,
            "materially_updated": 0,
            "reintroduced": 0,
            "stale_repeat": 0,
            "unverified": 0,
        }
    )
    repeat_ages: list[Fraction] = []
    explained_repeats = 0

    for idea in eligible:
        lineage = idea.get("lineage")
        if not isinstance(lineage, Mapping):
            raise LearningMetricError("eligible idea is missing lineage")
        status = lineage.get("status")
        classification = lineage.get("classification")

        if status == "unverified":
            if classification != "unverified":
                raise LearningMetricError(
                    "unverified lineage must use classification unverified"
                )
            class_counts["unverified"] += 1
            continue
        if status != "verified":
            raise LearningMetricError("lineage status must be verified or unverified")
        if classification == "new":
            class_counts["new"] += 1
            continue
        if classification not in VERIFIED_REPEAT_CLASSES:
            raise LearningMetricError(
                "verified lineage must classify as new or one repeat class"
            )

        class_counts[classification] += 1
        repeat_reason = idea.get("repeat_reason")
        if isinstance(repeat_reason, str) and repeat_reason.strip():
            explained_repeats += 1
        repeat_ages.append(_age_hours(idea))

    current_count = len(eligible)
    unverified_count = class_counts["unverified"]
    verified_count = current_count - unverified_count
    new_count = class_counts["new"]
    repeat_count = sum(class_counts[name] for name in VERIFIED_REPEAT_CLASSES)

    if new_count + repeat_count != verified_count:
        raise LearningMetricError("verified new and repeat counts do not partition V")
    if explained_repeats != repeat_count:
        raise LearningMetricError("every verified repeat must have a repeat reason")

    if repeat_count == 0:
        repeat_age_metrics: dict[str, int | str] = {
            "count": 0,
            "median": NOT_AVAILABLE,
            "maximum": NOT_AVAILABLE,
        }
    else:
        repeat_age_metrics = {
            "count": repeat_count,
            "median": _fraction_text(median(repeat_ages)),
            "maximum": _fraction_text(max(repeat_ages)),
        }

    return {
        "cohort": {
            "current_idea_count": current_count,
            "verified_count": verified_count,
            "unverified_count": unverified_count,
            "exclusions": {
                "legacy_1_0_0_count": legacy_count,
                "total_count": legacy_count,
            },
        },
        "counts": {
            "new": new_count,
            "repeats": repeat_count,
            "explained_repeats": explained_repeats,
            "repeat_unchanged": class_counts["repeat_unchanged"],
            "materially_updated": class_counts["materially_updated"],
            "reintroduced": class_counts["reintroduced"],
            "stale_repeat": class_counts["stale_repeat"],
        },
        "rates": {
            "new_idea": rate(new_count, verified_count),
            "repeat": rate(repeat_count, verified_count),
            "explained_repeat": rate(explained_repeats, repeat_count),
            "strict_material_update": rate(
                class_counts["materially_updated"], repeat_count
            ),
            "decision_changing_repeat": rate(
                class_counts["materially_updated"]
                + class_counts["reintroduced"],
                repeat_count,
            ),
            "stale_repeat": rate(class_counts["stale_repeat"], repeat_count),
            "unverified_lineage": rate(unverified_count, current_count),
        },
        "repeat_age_hours": repeat_age_metrics,
    }


def _review_identity(review: Mapping[str, Any]) -> tuple[object, object]:
    links = review.get("links")
    if not isinstance(links, Mapping):
        return None, None
    return links.get("decision_ref"), links.get("idea_ref")


def _resolve_terminal_review(
    target: Mapping[str, str],
    reviews: Sequence[Mapping[str, Any]],
    reviews_by_id: Mapping[str, Sequence[Mapping[str, Any]]],
    review_is_valid: Callable[[Mapping[str, Any]], bool],
) -> tuple[str, Mapping[str, Any] | None]:
    """Resolve one chain to ``eligible``, ``missing``, ``invalid``, or ``unresolved``."""

    decision_ref = target["decision_ref"]
    idea_ref = target["idea_ref"]
    direct = [
        review for review in reviews if _review_identity(review)[0] == decision_ref
    ]
    if not direct:
        return "missing", None

    # Invalid has deterministic precedence over topology failures whenever the
    # malformed record can be attributed to this target decision.
    if any(not review_is_valid(review) for review in direct):
        return "invalid", None

    nodes: dict[str, Mapping[str, Any]] = {}
    pending = list(direct)
    while pending:
        review = pending.pop()
        review_id = review["review_id"]
        matches = reviews_by_id.get(review_id, ())
        if len(matches) != 1:
            return "unresolved", None
        if review_id in nodes:
            continue
        nodes[review_id] = review

        prior_ref = review.get("prior_review_ref")
        if prior_ref is None:
            continue
        predecessors = reviews_by_id.get(prior_ref, ())
        if len(predecessors) != 1:
            return "unresolved", None
        predecessor = predecessors[0]
        if not review_is_valid(predecessor):
            return "invalid", None
        if _review_identity(predecessor) != (decision_ref, idea_ref):
            return "unresolved", None
        pending.append(predecessor)

    # A cross-identity or malformed successor can point into an otherwise
    # valid target chain.  Inspect every outgoing prior-review edge globally;
    # otherwise the referenced predecessor could be falsely accepted as the
    # terminal review merely because the corrupt child carries another (or no)
    # decision identity.
    node_ids = set(nodes)
    for candidate in reviews:
        if candidate.get("prior_review_ref") not in node_ids:
            continue
        candidate_valid = review_is_valid(candidate)
        if candidate_valid is not True:
            return "invalid", None
        if _review_identity(candidate) != (decision_ref, idea_ref):
            return "unresolved", None

    if any(_review_identity(node) != (decision_ref, idea_ref) for node in nodes.values()):
        return "unresolved", None

    child_counts: Counter[str] = Counter()
    for node in nodes.values():
        prior_ref = node.get("prior_review_ref")
        if prior_ref is not None:
            if prior_ref not in nodes:
                return "unresolved", None
            child_counts[prior_ref] += 1
    if any(count > 1 for count in child_counts.values()):
        return "unresolved", None

    roots = [node for node in nodes.values() if node.get("prior_review_ref") is None]
    terminals = [
        node for review_id, node in nodes.items() if child_counts[review_id] == 0
    ]
    if len(roots) != 1 or len(terminals) != 1:
        return "unresolved", None

    # A single root and terminal plus an in-degree of at most one excludes
    # forks, but explicitly walk the predecessor pointers to detect a detached
    # cycle or any other disconnected component.
    visited: set[str] = set()
    current: Mapping[str, Any] | None = terminals[0]
    while current is not None:
        current_id = current["review_id"]
        if current_id in visited:
            return "unresolved", None
        visited.add(current_id)
        prior_ref = current.get("prior_review_ref")
        current = nodes.get(prior_ref) if prior_ref is not None else None
    if len(visited) != len(nodes):
        return "unresolved", None

    return "eligible", terminals[0]


def measure_outcome_review_cohort(
    targets: Sequence[Mapping[str, str]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    review_validator: Callable[[Mapping[str, Any]], bool],
) -> dict[str, Any]:
    """Measure terminal outcome reviews for a frozen decision cohort.

    The complete retained chain through the cutoff must be supplied.  A
    timestamp is never used to choose a review.  Only the uniquely resolved
    terminal of one valid append-only chain contributes to timing and
    invalidation measurements. ``review_validator`` must apply the complete
    schema and semantic contract before chain resolution begins.
    """

    normalized_targets: list[dict[str, str]] = []
    seen_decisions: set[str] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, Mapping):
            raise LearningMetricError(f"targets[{index}] must be an object")
        decision_ref = target.get("decision_ref")
        idea_ref = target.get("idea_ref")
        if not isinstance(decision_ref, str) or not decision_ref:
            raise LearningMetricError(f"targets[{index}].decision_ref is required")
        if not isinstance(idea_ref, str) or not idea_ref:
            raise LearningMetricError(f"targets[{index}].idea_ref is required")
        if decision_ref in seen_decisions:
            raise LearningMetricError(
                f"frozen decision cohort repeats decision_ref {decision_ref!r}"
            )
        seen_decisions.add(decision_ref)
        normalized_targets.append(
            {"decision_ref": decision_ref, "idea_ref": idea_ref}
        )

    normalized_reviews: list[Mapping[str, Any]] = []
    reviews_by_id: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    validation_results: dict[int, bool] = {}
    for index, review in enumerate(reviews):
        if not isinstance(review, Mapping):
            raise LearningMetricError(f"reviews[{index}] must be an object")
        try:
            validation_results[id(review)] = review_validator(review) is True
        except Exception as exc:
            raise LearningMetricError(
                f"reviews[{index}] validation could not complete"
            ) from exc
        normalized_reviews.append(review)
        review_id = review.get("review_id")
        if isinstance(review_id, str):
            reviews_by_id[review_id].append(review)

    def validator(review: Mapping[str, Any]) -> bool:
        return validation_results[id(review)]

    terminal_reviews: list[Mapping[str, Any]] = []
    exclusion_counts = Counter({"missing": 0, "invalid": 0, "unresolved": 0})
    for target in normalized_targets:
        status, terminal = _resolve_terminal_review(
            target, normalized_reviews, reviews_by_id, validator
        )
        if status == "eligible":
            assert terminal is not None
            terminal_reviews.append(terminal)
        else:
            exclusion_counts[status] += 1

    target_count = len(normalized_targets)
    measured_count = len(terminal_reviews)
    if measured_count + sum(exclusion_counts.values()) != target_count:
        raise LearningMetricError("review exclusions do not partition target decisions")

    timing_state_counts = Counter({state: 0 for state in TIMING_STATES})
    timing_class_counts = Counter(
        {classification: 0 for classification in TIMING_CLASSIFICATIONS}
    )
    timing_cross_tab = {
        state: {classification: 0 for classification in TIMING_CLASSIFICATIONS}
        for state in ("assessable", "partial")
    }
    trigger_state_counts = Counter({state: 0 for state in TRIGGER_STATES})
    triggered_response_counts = Counter(
        {state: 0 for state in TRIGGERED_RESPONSE_STATES}
    )

    for review in terminal_reviews:
        timing = review["timing_discipline"]
        timing_state = timing["assessment_state"]
        timing_state_counts[timing_state] += 1
        if timing_state in {"assessable", "partial"}:
            classification = timing["classification"]
            timing_class_counts[classification] += 1
            timing_cross_tab[timing_state][classification] += 1

        trigger_state = review["invalidation_trigger"]["state"]
        trigger_state_counts[trigger_state] += 1
        if trigger_state == "triggered":
            response_state = review["invalidation_response"]["state"]
            triggered_response_counts[response_state] += 1

    timing_applicable = measured_count - timing_state_counts["not_applicable"]
    timing_classified = sum(timing_class_counts.values())
    invalidation_applicable = measured_count - trigger_state_counts["not_applicable"]
    trigger_ascertained = (
        trigger_state_counts["triggered"]
        + trigger_state_counts["not_triggered"]
    )
    triggered_count = trigger_state_counts["triggered"]
    if sum(triggered_response_counts.values()) != triggered_count:
        raise LearningMetricError(
            "triggered-response counts do not partition triggered reviews"
        )

    return {
        "review_cohort": {
            "target_decision_count": target_count,
            "measured_decision_count": measured_count,
            "exclusions": {
                "missing": exclusion_counts["missing"],
                "invalid": exclusion_counts["invalid"],
                "unresolved": exclusion_counts["unresolved"],
                "total_count": sum(exclusion_counts.values()),
            },
            "measurement_coverage": rate(measured_count, target_count),
        },
        "timing": {
            "applicable_count": timing_applicable,
            "classified_count": timing_classified,
            "assessment_state_counts": dict(timing_state_counts),
            "classification_counts": dict(timing_class_counts),
            "state_by_classification": timing_cross_tab,
            "rates": {
                "classification_coverage": rate(
                    timing_classified, timing_applicable
                ),
                "disciplined_share": rate(
                    timing_class_counts["disciplined"], timing_classified
                ),
                "mixed_share": rate(
                    timing_class_counts["mixed"], timing_classified
                ),
                "undisciplined_share": rate(
                    timing_class_counts["undisciplined"], timing_classified
                ),
            },
        },
        "invalidations": {
            "applicable_count": invalidation_applicable,
            "ascertained_count": trigger_ascertained,
            "triggered_count": triggered_count,
            "trigger_state_counts": dict(trigger_state_counts),
            "triggered_response_counts": dict(triggered_response_counts),
            "rates": {
                "trigger_ascertainment": rate(
                    trigger_ascertained, invalidation_applicable
                ),
                "trigger_incidence": rate(triggered_count, trigger_ascertained),
                "triggered_response_shares": {
                    state: rate(triggered_response_counts[state], triggered_count)
                    for state in TRIGGERED_RESPONSE_STATES
                },
            },
        },
    }

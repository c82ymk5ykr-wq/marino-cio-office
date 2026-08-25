# Outcome-review and decision-attribution contract

- Contract version: `outcome-review 1.0.0`
- Status: Accepted public interface; private conformance pending

This contract defines how a private Marino CIO Office implementation records a
post-decision review without changing the original decision or publishing the
review's populated contents. It separates what happened from whether the
decision and process were sound at the time.

## Public and private boundary

The public repository contains only the schema, terminology, template,
fictional fixtures, and deterministic validation rules. Every real populated
outcome review, evidence record, attribution entry, aggregate, review date, and
private identifier remains in approved private storage.

The contract contains no returns, P&L, prices, benchmarks, holdings,
allocations, position sizes, transactions, client or account data, or copied
deployment actions. Redacted, hashed, relabeled, or anonymized production
records are not acceptable public fixtures.

## Artifact boundary

An outcome review is a new append-only artifact. It links to the immutable
ex-ante `decision-record` and stable `investment-idea` lineage through opaque
identifiers. Hindsight never rewrites the original rationale, evidence,
invalidation conditions, timing prerequisites, or decision timestamp.

A later review horizon creates another review artifact. A correction to a
finalized private review is represented as a new review whose optional
`supersedes_review_id` points to the prior artifact. The prior review remains
unchanged, and the correction does not mutate the public contract or the
ex-ante decision.

## Separate assessment axes

| Axis | Values | Meaning |
| --- | --- | --- |
| Assessability | `assessable`, `partial`, `unavailable` | Whether retained evidence supports the review |
| Ex-ante basis | `verified`, `partial`, `unverified` | Whether the original decision basis is available without reconstruction |
| Evidence quality | `sufficient`, `limited`, `conflicting`, `unavailable`, `unverified` | Quality of the evidence admitted to the review |
| Research outcome | `favorable`, `mixed`, `adverse`, `indeterminate`, `not_applicable` | Qualitative result of the research case, never investment performance |
| Decision quality | `well_supported`, `mixed_support`, `weakly_supported`, `unassessable` | Whether the ex-ante decision was supported by evidence then available |
| Process quality | `disciplined`, `mixed`, `undisciplined`, `unassessable` | Whether the declared process was followed |
| Timing discipline | `followed`, `partially_followed`, `not_followed`, `unassessable`, `not_applicable` | Whether declared timing and confirmation prerequisites were followed |

No value on one axis proves a value on another. A favorable result does not
prove a sound decision or disciplined process. An adverse result does not prove
the decision or process was unsound.

An `assessable` review requires a verified ex-ante basis, sufficient evidence,
a complete evaluation window, an evidence cutoff, admitted evidence, at least
one qualitative attribution entry, and resolved applicable timing and
invalidation states. Limited or conflicting evidence makes the review
`partial`, and every partial or otherwise non-sufficient review discloses
limitations. An `unavailable` review contains no attribution or evidence claims
and marks decision and process quality unassessable.

An unverified ex-ante basis cannot support a reconstructed decision, process,
or timing assessment. Unverified outcome evidence cannot support a favorable,
mixed, or adverse research outcome, attribution factor, or resolved
invalidation trigger.

## Clock order

All clocks are RFC 3339 UTC timestamps ending in `Z`. When the applicable
fields are present, private producers and public synthetic validation enforce:

`decision-record.recorded_at <= evaluation_window.started_at <
evaluation_window.ended_at <= evidence_cutoff_at <= reviewed_at`

Unknown clocks are omitted only where the schema permits them. They are never
estimated or reconstructed. The evaluation window describes the declared
review horizon; `evidence_cutoff_at` describes the last evidence admitted; and
`reviewed_at` records finalization of the review.

## Invalidation states

Trigger and response are separate axes. These are the only valid combinations:

| Trigger state | Allowed response state |
| --- | --- |
| `not_triggered` | `not_required` |
| `triggered` | `followed`, `delayed`, `not_followed`, `unknown` |
| `ambiguous` | `unknown` |
| `unknown` | `unknown` |
| `not_applicable` | `not_applicable` |

A triggered state requires evidence. `not_triggered` is not counted as a
successful response, and an ambiguous or unknown trigger is not silently
resolved.

## Qualitative attribution

Attribution entries contain an opaque factor ID, a public category, a
categorical direction, qualitative confidence, evidence IDs, and a note.
Directions are `supporting`, `detracting`, `mixed`, `neutral`, or `unknown`.
They describe an evidence-linked association only.

The contract forbids numeric contribution weights, causal certainty, return
attribution, and outcome-based inference of process quality. Every attribution
evidence ID and invalidation evidence ID must appear in the review's root
evidence register, and factor IDs must be unique within a review.

## Cross-artifact invariants

Private consumers and public synthetic validation enforce that:

- `review_id` is unique and opaque;
- `supersedes_review_id`, when present, differs from `review_id`, resolves to an
  earlier review of the same decision and idea, and cannot form a cycle;
- `decision_id` resolves to one immutable decision record;
- the review and decision resolve to the same `idea_id`;
- evaluation and review clocks follow the declared order;
- attribution factor IDs do not repeat;
- nested evidence references resolve to the review's evidence register; and
- missing or incomplete history yields an explicit partial, unavailable, or
  unverified state.

## Compatibility and adoption

`outcome-review 1.0.0` is a new additive v1 contract family. It does not change
the meaning or validity of report-manifest, investment-idea, or decision-record
artifacts. Breaking changes require a new major schema directory and a
superseding Architecture Decision Record.

Private adoption is verified outside this repository. A public closeout may
name the adopted contract version and categorical conformance result only. It
must not publish mappings, real fixtures, counts, dates, evidence, review
contents, storage references, or performance history. Phase 4 outcome 1 remains
open until that private conformance check passes.

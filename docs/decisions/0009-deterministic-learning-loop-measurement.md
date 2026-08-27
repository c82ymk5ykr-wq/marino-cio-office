# 0009 — Measure the learning loop with deterministic cohorts and exclusions

- Status: Accepted
- Date: 2026-08-27
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

Phase 4 introduced append-only outcome reviews, while the existing idea-lineage
contract defined report-level novelty arithmetic. The system still needs one
durable rule for measuring novelty, repeat quality, timing discipline, and
invalidations without rewarding missing history, silently dropping uncertain
reviews, or selecting a convenient hindsight record.

A new public metrics artifact would invite publication of private counts,
windows, identifiers, decisions, and review history. A composite learning score
would hide denominators and embed unsupported weights. Selecting the review
with the newest timestamp would also violate the append-only chain whenever a
predecessor is missing, forked, cyclic, or cross-linked.

## Decision

Adopt [`docs/learning-loop-metrics.md`](../learning-loop-metrics.md) as a
versioned derived-measurement specification. It consumes validated
`investment-idea 1.1.0` and `outcome-review 1.0.0` inputs and creates a new
immutable snapshot only in approved private storage. No schema or template is
changed.

For ideas, freeze a current cohort with at most one eligible `1.1.0` record per
stable idea ID. Count legacy `1.0.0` inputs as metric-ineligible exclusions,
keep missing history unverified, require all verified repeats to be explained,
and report novelty and repeat quality as exact counts, rates, and repeat ages.
Do not create a weighted repeat-quality score.

For decisions, freeze distinct targets and load every retained review through
the cutoff, including predecessors outside the reporting window. Count only
the unique terminal of a fully valid, single append-only chain. Count a target
as missing, invalid, or unresolved when it cannot contribute. Never use a
latest timestamp to resolve ambiguous topology.

Measure timing assessment coverage and classifications separately from
invalidation-trigger ascertainment, incidence, and response. Preserve raw
partial and uncertain states. Neither axis derives from research outcome,
performance, or the other axis.

Every rate retains its numerator and denominator. Zero denominators are
`not_available`; zero numerators with positive denominators are zero.
Calculation uses exact values and rounds only for display.

All populated snapshots, cohorts, windows, target IDs, review chains, counts,
rates, exclusions, mappings, and evidence remain private. Public verification
uses invented fixtures and categorical conformance only.

## Alternatives considered

- **Add a public learning-metrics schema.** Rejected because the result is a
  private operational snapshot, not a portable public artifact, and publishing
  populated aggregates would cross the data boundary.
- **Use a single weighted learning score.** Rejected because weighting would
  hide the independent axes and private policy choices.
- **Treat the first observed cohort as new.** Rejected because absence of
  retained history is unverified, not evidence of first occurrence.
- **Select the latest review timestamp.** Rejected because chronology cannot
  repair dangling, cyclic, branched, duplicate, or cross-identity lineage.
- **Drop uncertain or unavailable rows.** Rejected because hidden exclusions
  can flatter coverage and quality rates.

## Consequences

- novelty and repeat quality reuse the adopted lineage vocabulary;
- terminal-review selection is deterministic and append-only;
- missing, invalid, unresolved, partial, unknown, unavailable, and not
  applicable states remain visible in their proper denominators;
- calculations can be reproduced exactly without exposing private values;
- implementation must retain review predecessors beyond a reporting window;
- recalculation appends a snapshot rather than mutating decisions or reviews;
  and
- completion still requires categorical private conformance.

## Verification

Public tests reproduce the invented balanced cohort and exact rational results,
exercise zero denominators, reject unexplained repeats and inconsistent claims,
and prove that predecessor/successor chains count once while malformed or
ambiguous histories become explicit exclusions.

Before the roadmap outcome is checked complete, an authorized private check
must confirm adopted input validation, frozen cohorts, unverified missing
history, unique terminal selection, exclusion accounting, exact arithmetic,
immutable snapshot creation, prohibited-field exclusion, and the public/private
boundary. Only the categorical conformance result may be recorded publicly.

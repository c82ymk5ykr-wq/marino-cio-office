# 0004 — Verifiable idea lineage and anti-staleness metrics

- Status: Accepted
- Date: 2026-08-25
- Owners: Marino CIO Office

## Context

The original idea contract records first seen, last seen, and an optional repeat
reason. That preserves useful timestamps but cannot distinguish a new idea from
an unchanged repeat, a material update, a reintroduction, stale evidence, or
missing lineage.

Counting every refreshed row as fresh would reward churn and repeated tickers.
Reconstructing missing history would create false precision. Publishing private
identity-matching methods would expose proprietary implementation logic.

## Decision

Adopt [`docs/idea-lineage-metrics.md`](../idea-lineage-metrics.md) and add a
backward-compatible `1.1.0` revision to the v1 investment-idea schema.

- Preserve stable idea lineage while keeping identity matching private.
- Require explicit verified or unverified lineage status.
- Use mutually exclusive classifications for new, unchanged repeat, material
  update, reintroduction, stale repeat, and unverified history.
- Require a repeat reason for every verified repeat, without treating the reason
  itself as proof of freshness.
- Advance the material-change timestamp only for named decision-changing
  dimensions.
- Publish counts, denominators, zero-case behavior, and unknown exclusions for
  each report-level metric.
- Never reconstruct unavailable history.

## Consequences

Positive:

- fresh-idea discovery becomes measurable without rewarding repeated wording;
- durable core ideas may repeat honestly with a reason;
- material updates and reintroductions receive credit without being mislabeled
  new;
- missing lineage and unknown evidence recency remain visible;
- legacy `1.0.0` idea artifacts remain valid.

Costs and constraints:

- producers claiming metrics must emit `1.1.0` lineage metadata;
- private systems must retain stable lineage and material-change history;
- semantic identity and materiality still require private implementation and
  governance;
- report-level metric fields may be added only after compatibility review.

## Verification

- Validate all fictional lineage fixtures and the legacy fixture.
- Check classification-specific counts, timestamps, changed dimensions, and
  repeat reasons.
- Join stale-repeat evidence to a visibly fictional stale source.
- Compute the synthetic cohort metrics and zero-denominator cases.
- Keep live ideas, actual rates, targets, alerts, weights, identity techniques,
  and performance out of the repository.

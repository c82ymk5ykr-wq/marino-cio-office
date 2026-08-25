# Universe completion gates

- Specification version: `1.0.0`
- Status: Accepted

This specification defines when a bounded research universe may be called
complete. It governs public status semantics; it does not disclose constituent
lists, provider identities, scan mechanics, ranking methods, or live results.

## Core rule

`complete` means the entire declared eligible universe was successfully
evaluated for the required period and every required freshness, source, review,
and persistence gate passed.

A page load, successful job, non-empty result, minimum usable sample, or 100%
refresh of only a subset is not universe completion.

## Supported gate profiles

Membership is frozen before evaluation and held privately. The public contract
records the profile identifier and membership as-of time, not the members.

| Profile | Membership basis | Minimum coverage | Maximum gaps | Maximum required-period lag |
| --- | --- | ---: | ---: | ---: |
| `broad_equity_daily` | Versioned broad-equity membership snapshot | 100% | 0 | 0 |
| `curated_etf_daily` | Versioned curated-ETF membership snapshot | 100% | 0 | 0 |
| `declared_bounded_set` | Finite set declared and frozen before evaluation | 100% | 0 | 0 |

All profiles also require known non-zero membership, passing required source
roles, complete report-type reviews, and `artifact.status: persisted`.

The daily profiles require evidence current for the latest required market or
source period. `freshness.threshold_hours` remains a disclosed secondary bound;
an elapsed-hours test alone cannot prove current-period completion across
weekends, holidays, or source schedules.

## Membership and coverage accounting

- `membership_as_of` identifies the frozen membership snapshot. Completion
  never carries across a changed snapshot.
- `expected` is the count of unique eligible members after normalization of the
  frozen snapshot.
- `observed` counts unique expected members that have every required
  observation and were successfully evaluated for the required period.
- `percent` equals `observed / expected * 100`.
- When `expected` is zero or unknown, `percent` is `0.0` and `complete` is
  forbidden.
- `gaps` are expected members that were not successfully evaluated. The public
  artifact may use safe gap descriptions rather than publishing members.
- No exclusion may be invented after the snapshot is frozen. Missing data,
  unresolved symbol identity, corporate actions, or compute failures are gaps.
- A resolved corporate action counts once under the snapshot identity. An
  unresolved action remains a gap.
- Exact duplicate observations are deduplicated and disclosed without
  increasing `observed`. Conflicting duplicates make the affected member a gap.

## Current and retained observations

`refreshed_this_cycle` is informational and is not the completion numerator.

A retained observation from a prior cycle may count only when it remains:

1. valid for the current snapshot identity;
2. complete for the required evaluation; and
3. current for the latest required period.

Stale retained observations never count. Less than 100% refreshed this cycle can
still be complete when retained observations satisfy all three rules; 100%
refreshed this cycle cannot overcome a coverage gap.

Recency remains visible through the report and source `data_as_of` fields and
`oldest_material_source_as_of`.

## Required sources and fallbacks

Profiles use provider-neutral source roles:

- membership definition;
- eligible observations; and
- freshness reference.

For a required role:

- `available` passes;
- `fallback` passes only if declared completion-equivalent before the run and
  held to identical membership, coverage, and freshness rules;
- `stale` fails the freshness gate;
- `unavailable` is a material source failure; and
- a non-equivalent fallback is a material source failure.

Optional-source problems remain disclosed. They block completion only when a
required report review depends on them.

In report-manifest 1.1, a source with no knowable evidence time omits evidence
and retrieval timestamps, retains `checked_at`, and contributes `unknown`
freshness unless a required-source failure controls status. A time is never
fabricated. Version 1.0 remains unchanged for compatibility.

## Review and persistence

Every review required by the report type must be complete. For the daily
decision product this includes the Chief Historian, Chief Skeptic, CIO research
disposition, and the separate deployment review.

Persistence outcomes affect status as follows:

- `persisted` passes;
- `not_attempted` leaves the product `provisional`; and
- `failed` makes a usable product `degraded`.

A temporary URL or download never satisfies persistence.

## Deterministic status precedence

Evaluate the gates in this order:

1. `failed` if no reliable decision product exists.
2. `degraded` if a usable product exists with a material required-source,
   non-equivalent-fallback, or persistence failure.
3. `provisional` if any denominator, coverage, freshness, review, or persistence
   gate is unknown or unmet without a material operational failure.
4. `complete` only when every declared gate passes.

The full cross-gate derivation and report-manifest 1.1 evidence fields are
defined in [report acceptance gates](report-acceptance-gates.md).

An unknown denominator is `provisional` when the system otherwise ran. It is
`degraded` when the denominator is unknown because its required source failed,
and `failed` when no reliable product remains.

## Runtime readiness is separate

Runtime readiness answers whether a system has enough usable material to render
or continue safely. Universe completion answers whether the declared population
passed its full gate. Neither state implies the other, and runtime thresholds
must never be presented as completion thresholds.

## Verification fixtures

[`examples/synthetic/universe-completion-cases.json`](../examples/synthetic/universe-completion-cases.json)
contains fictional boundary cases. The repository validator derives each case's
status from this specification and rejects contradictory completion claims.

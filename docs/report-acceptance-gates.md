# Report acceptance gates

- Specification version: `1.0.0`
- Report-manifest revision: `1.1.0`
- Status: Accepted

This specification defines the deterministic decision that assigns a public
report outcome. It uses provider-neutral gate evidence and does not publish
source identities, constituent lists, review implementation, storage locations,
ranking logic, live results, or client information.

## Contract validity comes first

A malformed manifest is rejected as contract-invalid. Its claimed `status` is
not trusted and is not automatically converted to `failed`.

For a valid report-manifest 1.1 artifact, derive status in this order:

1. `failed` when no reliable decision product exists.
2. `degraded` when a reliable product remains but a required source role uses a
   non-equivalent fallback, is unavailable, or durable persistence failed.
3. `provisional` when any remaining coverage, required-period, freshness,
   required-source recency, review, or persistence gate is unknown or unmet.
4. `complete` only when every gate passes.

The claimed status must exactly equal the derived status.

## Gate decision table

| Gate | Pass | Provisional | Degraded or failed |
| --- | --- | --- | --- |
| Reliable product | A decision-useful product exists | Not applicable | `false` always yields `failed` |
| Coverage | Known non-zero denominator; observed equals expected; 100%; zero gaps | Unknown or zero denominator, incomplete coverage, or gaps | A required-source failure is handled by the source gate |
| Required period | Zero required-period lag | Positive or unknown lag | A required-source failure is handled by the source gate |
| Freshness | `fresh` and within the declared threshold | `stale` | `unknown` accompanies an unavailable freshness-reference role and is handled by the source gate |
| Required source roles | `available` or predeclared `equivalent_fallback` | `stale` | `non_equivalent_fallback` or `unavailable` yields `degraded` when the product remains reliable |
| Required reviews | Every report-type review completed | One or more incomplete | Not applicable |
| Persistence | `persisted` with an opaque receipt and persistence time | `not_attempted` | `failed` yields `degraded` when the product remains reliable |
| Optional sources | Disclosed but do not control acceptance | No effect | No effect unless promoted to a required role before the run |

Universe completion and minimum runtime readiness remain different decisions.
A usable subset may support a reliable provisional or degraded product, but it
does not establish full-universe completion.

## Report-manifest 1.1 gate evidence

`gate_inputs` is required for report-manifest `1.1.0` and contains:

- `reliable_product`;
- `completion_profile_id`;
- `denominator_known` and, when known, `membership_as_of` and `gap_count`;
- `required_period`, `required_period_lag_known`, and `required_period_lag` only
  when that lag is known;
- `required_reviews_complete`; and
- exactly one gate record for each required role: membership definition,
  eligible observations, and freshness reference.

Each source-role record has a provider-neutral role, a gate state, public-safe
source IDs, and a disclosure note. Every linked raw source must have the status
implied by the role state; failed preferred-source attempts that did not fulfill
the role remain unlinked, disclosed source records. `equivalent_fallback` is
completion-eligible
only when equivalence was declared before the run. `non_equivalent_fallback`
never passes a required role.

When `denominator_known` is false, `membership_as_of` and `gap_count` are
omitted and coverage uses the explicit unknown sentinel `expected: 0`,
`observed: 0`, `percent: 0`, with no gap descriptions. When the denominator is
known, zero gaps requires an empty descriptions array and a positive gap count
requires at least one public-safe description; descriptions need not enumerate
every missing member.

The raw source register retains `status: fallback`; the source-role gate records
whether that fallback is completion-equivalent. This prevents a preferred-source
failure from blocking completion when a declared equivalent source actually
fulfilled the role, while keeping both conditions visible.

## Time and persistence evidence

All serialized times are UTC and end in `Z`.

- Source 1.1 records add `checked_at`.
- `available`, `fallback`, and `stale` sources require evidence and retrieval
  times.
- `unavailable` sources omit evidence and retrieval times rather than inventing
  them; `checked_at` records when unavailability was established.
- `fresh` and `stale` aggregate states require
  `oldest_material_source_as_of`; `unknown` omits it.
- For known aggregate freshness, `oldest_material_source_as_of` equals the
  earliest `data_as_of` among all sources linked to required roles. A stale
  required role makes aggregate freshness stale; an unavailable
  `freshness_reference` makes it unknown.
- Freshness age is measured from `generated_at`, not validator wall-clock time.
  Exactly at the declared threshold passes.
- Required-source clocks obey `data_as_of <= report.data_as_of` and
  `data_as_of <= retrieved_at <= checked_at <= generated_at`.
- `persisted` requires an opaque `durable_reference` receipt and `persisted_at`.
  The receipt is an 8-128 character non-sensitive token made only from letters,
  digits, dots, underscores, and hyphens. URIs, whitespace, and filesystem
  paths never qualify.
- `failed` and `not_attempted` persistence outcomes cannot claim a receipt.

The public validator can validate the attestation and receipt shape. Confirming
that a private object still exists belongs to private integration verification.

## Required quality flags

Every active acceptance condition must be represented in `quality_flags`:

- product: `NO_RELIABLE_DECISION_PRODUCT`;
- source failures: `REQUIRED_SOURCE_UNAVAILABLE`,
  `NON_EQUIVALENT_FALLBACK`, `REQUIRED_SOURCE_STALE`;
- coverage: `COVERAGE_DENOMINATOR_UNKNOWN`, `EMPTY_ELIGIBLE_UNIVERSE`,
  `INCOMPLETE_COVERAGE`, `REQUIRED_PERIOD_LAG`, `REQUIRED_PERIOD_UNKNOWN`;
- freshness and reviews: `FRESHNESS_STALE`, `FRESHNESS_UNKNOWN`,
  `REQUIRED_REVIEWS_INCOMPLETE`;
- persistence: `DURABLE_PERSISTENCE_FAILED`,
  `DURABLE_PERSISTENCE_NOT_ATTEMPTED`; and
- non-blocking disclosures: `EQUIVALENT_FALLBACK_USED`,
  `OPTIONAL_SOURCE_UNAVAILABLE`.

A complete report may contain a non-blocking disclosure flag. It may not contain
an active blocking flag.

## Upstream evidence boundary

Acceptance assumes coverage counts were produced under the Phase 1 identity,
retained-observation, and conflicting-duplicate rules. Report-manifest 1.1
attests those resulting counts and gaps; it does not publish constituents or
re-serialize private deduplication evidence.

## Verification

[`examples/synthetic/report-acceptance-cases.json`](../examples/synthetic/report-acceptance-cases.json)
covers every status, exact freshness-threshold behavior, required and optional
source conditions, persistence outcomes, precedence, and contradictory claims.
The validator derives the expected status and flags rather than trusting the
fixture labels. Unit tests also exercise complete, provisional, degraded,
failed, equivalent-fallback, unavailable-source, and persistence branches as
full report-manifest 1.1 instances.

Report-manifest `1.0.0` remains accepted as a legacy public contract. New
artifacts should use `1.1.0` when deterministic acceptance evidence is required.

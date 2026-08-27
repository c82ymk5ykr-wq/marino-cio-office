# Deterministic learning-loop metrics

- Specification version: `1.0.0`
- Status: Accepted
- Inputs: `investment-idea 1.1.0` and `outcome-review 1.0.0`

This specification defines deterministic private measurement of idea novelty,
repeat quality, timing discipline, and invalidation handling. It adds no public
artifact family and does not alter either input contract. The implementation
must calculate a new immutable private snapshot from a frozen cohort; it must
not write a result back into an idea, decision, or outcome review.

The public repository contains only formulas, invented truth tables, and tests.
Actual windows, targets, identifiers, review chains, counts, rates, exclusions,
evidence, and snapshots remain private. Public conformance records only one of
`conforms`, `public_contract_gap`, or `private_migration_needed`.

## Common calculation rules

- Validate every named input against its adopted schema and semantic rules
  before measuring it.
- Freeze the idea and decision cohorts, the measurement cutoff, and the full
  retained review histories before classification.
- Record every rate's raw numerator and denominator.
- Calculate from integer counts or exact rational values. Round only for
  display; never feed a rounded value into another metric.
- A zero denominator produces `not_available`, not zero. A zero numerator with
  a positive denominator produces the exact value zero.
- Record exclusions beside the affected denominator. An unavailable value or
  excluded record may not be omitted to improve a rate.
- Do not combine the metrics into a weighted score, grade, target, causal
  attribution, recommendation, or deployment signal.

The repository helper represents an exact available ratio as a reduced
rational string such as `1/6` and an unavailable ratio as `not_available`.
Private implementations may use an equivalent exact numeric representation.
Percentages such as `16.666…%` are presentation only.

## Idea measurement cohort

The frozen current cohort contains at most one `investment-idea 1.1.0` record
per stable `idea_id`. Version `1.1.0` is metric eligible because it carries the
verified-lineage interface. Valid `1.0.0` records remain valid artifacts but
are metric-ineligible exclusions; count them and never relabel them.

Let:

- `C` be distinct metric-eligible current idea IDs;
- `V` be current ideas with verified lineage;
- `U = C - V` be current ideas with unverified lineage;
- `N` be verified ideas classified `new`;
- `R` be verified ideas in one of the four repeat classes;
- `X` be repeats with a non-empty `repeat_reason`;
- `M` be repeats classified `materially_updated`;
- `RI` be repeats classified `reintroduced`; and
- `S` be repeats classified `stale_repeat`.

The four repeat classes are `repeat_unchanged`, `materially_updated`,
`reintroduced`, and `stale_repeat`. Valid measurement requires:

`N + R = V`, `U + V = C`, and `X = R`.

An unexplained repeat or inconsistent partition fails measurement. It is not
silently excluded.

### Idea rates

| Metric | Numerator | Denominator |
| --- | ---: | ---: |
| New-idea rate | `N` | `V` |
| Repeat rate | `R` | `V` |
| Explained-repeat rate | `X` | `R` |
| Strict material-update rate | `M` | `R` |
| Decision-changing-repeat rate | `M + RI` | `R` |
| Stale-repeat rate | `S` | `R` |
| Unverified-lineage share | `U` | `C` |

Repeat quality is the profile of the four repeat-class counts, all repeat
rates, repeat count, median repeat age, and maximum repeat age. It is not a
weighted score. For each verified repeat, age is
`last_seen_at - first_seen_at` in exact hours.

If `V = 0`, new-idea and repeat rates are `not_available`. If `V > 0` and
`R = 0`, repeat rate is legitimately zero; repeat subrates and repeat-age
aggregates are `not_available` because there are no repeats.

### Baseline and missing history

The first measurement run establishes a baseline; it does not prove that every
observed idea is new. Missing pre-adoption or retained history requires
`status: unverified` and `classification: unverified`. Never reconstruct or
reset `first_seen_at`, `last_material_change_at`, or `repeat_count` to make a
lineage measurable.

The classifications and material-change rules in
[`idea-lineage-metrics.md`](idea-lineage-metrics.md) remain canonical. A routine
refresh, changed score, changed price, regenerated explanation, or technical
gate movement cannot establish novelty on its own.

## Decision-review measurement cohort

Let `D` be distinct target decision references in the frozen private cohort.
For each target, load the complete retained outcome-review sequence through the
cutoff, including every predecessor outside the reporting window.

A decision has one measurable terminal review only when:

1. every attributable or resolved review validates as `outcome-review 1.0.0`;
2. review IDs resolve uniquely;
3. every `prior_review_ref` resolves to the same decision and idea identity;
4. the graph contains no dangling link, self-link, cycle, fork, cross-identity
   link, multiple unlinked chain, or disconnected component; and
5. exactly one terminal review remains.

The terminal review is the unique review not referenced as a predecessor by
another review in that chain. Never choose a review by `reviewed_at`, file
order, retrieval order, or another latest-looking timestamp when topology is
unresolved.

Classify each target exactly once:

| Class | Meaning |
| --- | --- |
| Measured | One valid, uniquely resolved terminal review contributes to the metrics |
| Missing | No review is retained for the target decision |
| Invalid | An attributable or resolved review fails its schema or semantic contract |
| Unresolved | Records exist, but identity or append-only chain topology is not unique |

Missing applies only when no target review exists. Invalid takes precedence
when a malformed record can be attributed to the target or resolved in its
chain. Otherwise, a linkage or topology failure is unresolved.

Let `Q` be measured decisions. The exclusion partition must satisfy:

`Q = D - missing - invalid - unresolved`.

Review measurement coverage is `Q / D`. When `D = 0`, it is
`not_available`. Only the `Q` terminal reviews enter the timing and invalidation
denominators.

## Timing discipline

Over the `Q` terminal reviews, let:

- `A_t` be reviews whose timing `assessment_state` is not `not_applicable`;
- `K_t` be timing states `assessable` or `partial`, which therefore carry a
  qualitative classification;
- `D_t` be classifications `disciplined`;
- `M_t` be classifications `mixed`; and
- `U_t` be classifications `undisciplined`.

| Metric | Numerator | Denominator |
| --- | ---: | ---: |
| Timing-classification coverage | `K_t` | `A_t` |
| Disciplined timing share | `D_t` | `K_t` |
| Mixed timing share | `M_t` | `K_t` |
| Undisciplined timing share | `U_t` | `K_t` |

Every private snapshot also records the assessment-state counts, including raw
`partial`, `unavailable`, `unknown`, and `not_applicable` counts, plus the
`assessable`/`partial` by classification cross-tab. This prevents limited
evidence from disappearing inside an aggregate.

`unavailable`, `unknown`, and `not_applicable` never become disciplined, mixed,
or undisciplined. `partial` may carry a classification under the adopted
outcome-review contract and therefore belongs in `K_t`.

## Invalidation trigger and response

Over the same `Q` terminal reviews, let:

- `A_i` be trigger states other than `not_applicable`;
- `K_i` be definitive trigger states `triggered` or `not_triggered`; and
- `T_i` be reviews whose trigger state is `triggered`.

| Metric | Numerator | Denominator |
| --- | ---: | ---: |
| Trigger ascertainment | `K_i` | `A_i` |
| Trigger incidence | `T_i` | `K_i` |

For triggered reviews, record separate response counts and shares for
`followed`, `delayed`, `not_followed`, `ambiguous`, and `unknown`, each divided
by `T_i`. The five response counts must sum to `T_i`.

If no trigger is definitive, trigger incidence is `not_available`. If no
review is triggered, every triggered-response share is `not_available`, even
when trigger incidence is legitimately zero.

Invalidation response does not determine timing discipline. Neither timing nor
invalidation classification is derived from research outcome, decision
quality, process quality, performance, or deployment action.

## Synthetic verification baseline

The invented balanced cohort deterministically produces:

- ideas: `C=6`, `V=5`, `U=1`, `N=1`, `R=4`, `M=1`, `RI=1`, `S=1`;
- idea rates: `1/5`, `4/5`, `1`, `1/4`, `1/2`, `1/4`, and `1/6` in table order;
- repeat ages: median `252` hours and maximum `744` hours;
- reviews: `D=Q=7`;
- timing: `A_t=6`, `K_t=4`, `D_t=2`, `M_t=0`, `U_t=2`;
- invalidations: `A_i=7`, `K_i=4`, `T_i=2`; and
- triggered responses: one followed, one delayed, and zero in the other three
  response classes.

Tests also cover all-unverified and no-repeat cohorts, every zero denominator,
a resolved predecessor/successor counted once, missing/invalid/unresolved
exclusions, dangling links, cycles, forks, multiple heads, cross-identity
links, duplicate IDs, outcome-axis independence, and rejected claimed results
that hide exclusions or alter exact rates.

## Private conformance gate

Before the Phase 4 measurement outcome is marked complete, authorized private
verification must categorically confirm:

- input versions and semantic validation conform;
- both cohorts and the cutoff are frozen before classification;
- missing lineage remains unverified;
- the full retained chain resolves to exactly one counted terminal review;
- missing, invalid, and unresolved histories are excluded and counted;
- private counts, exact rates, and zero-denominator behavior match this
  specification;
- recalculation creates a new private snapshot and never mutates an input;
- metric values, targets, IDs, windows, mappings, and evidence remain private;
  and
- no performance, account, client, deployment, causal, weighting, or composite
  score field is introduced.

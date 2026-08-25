# Idea lineage and anti-staleness metrics

- Specification version: `1.1.0`
- Status: Accepted

This specification defines observable idea-lineage metadata and report-level
novelty metrics. It is designed to reward decision-useful change without
rewarding churn or relabeling old ideas as fresh.

The stable `idea_id` lineage is public contract behavior. Identity matching,
semantic deduplication, fingerprints, embeddings, similarity thresholds,
prompts, ranking weights, targets, alerts, live results, and performance remain
private.

## Distinct concepts

| Concept | Meaning |
| --- | --- |
| Data recency | Age or required-period currency of a source or observation |
| Refreshed-this-cycle coverage | Eligible universe members successfully re-evaluated during the current cycle |
| Newly covered security | A security with verified coverage now and no prior verified coverage |
| Genuinely fresh idea | An idea with verified lineage classification `new` |
| Materially updated idea | A prior lineage with a decision-changing change in a named dimension |
| Reintroduced idea | A prior rejected or archived lineage returned to active research with a named state change |

None of these states implies another. A fresh data pull does not make an old
thesis a fresh idea, and a fresh idea does not establish complete universe
coverage.

## Lineage fields

Version `1.1.0` of the investment-idea contract adds `lineage`.

| Field | Meaning |
| --- | --- |
| `status` | `verified` when retained history supports the classification; otherwise `unverified` |
| `classification` | Mutually exclusive current lineage classification |
| `last_material_change_at` | Most recent verified decision-changing change; it does not advance for routine refreshes |
| `repeat_count` | Cumulative verified appearances after the first, including the current repeat; it never resets |
| `changed_dimensions` | Material dimensions changed in the current appearance only |
| `verification_note` | Required explanation when history is insufficient to classify the lineage |
| `repeat_reason` | Why a verified repeat remains decision-useful; it does not prove material change by itself |

`first_seen_at` and `last_seen_at` are the earliest and latest retained verified
appearances of the stable idea. For unverified lineage, they describe only the
accessible record and must not be presented as reconstructed history.

## Classifications and precedence

Apply the first supported classification in this order:

1. `unverified`: retained history cannot support a new-or-repeat claim.
2. `new`: first verified occurrence; `repeat_count` is zero and first seen,
   last seen, and last material change are equal.
3. `reintroduced`: a prior rejected or archived case becomes active again.
4. `materially_updated`: a prior idea has one or more decision-changing changed
   dimensions.
5. `stale_repeat`: no material dimension changed and current material evidence
   fails the applicable recency gate.
6. `repeat_unchanged`: no material dimension changed, evidence is current, and
   repetition remains decision-useful.

Every verified repeat requires `repeat_reason`. Reappearance, regenerated
wording, or a new reason alone never qualifies an idea as new or materially
updated.

## Material-change test

Allowed changed dimensions are:

- `thesis`;
- `evidence`;
- `catalysts`;
- `risks`;
- `invalidation_conditions`; and
- `research_state`.

A material change must be capable of changing research disposition, timing
prerequisites, risk assessment, invalidation, or continued decision usefulness.

These do not qualify on their own:

- routine timestamp or source refreshes;
- refreshed prices that do not change the decision case;
- regenerated wording or reordered bullets;
- repetition by another feeder capability; or
- a newly written `repeat_reason` without changed decision evidence.

When history is missing, use `status: unverified` and `classification:
unverified`. Do not guess timestamps, counts, or a new-or-repeat label.

## Report-level metrics

Let:

- `C` be distinct idea IDs in the current report;
- `V` be current ideas with verified lineage;
- `U` be `C - V`;
- `N` be verified ideas classified `new`;
- `R` be verified ideas in any of the four repeat classifications;
- `X` be repeats with a non-empty `repeat_reason`;
- `M` be repeats classified `materially_updated`;
- `RI` be repeats classified `reintroduced`; and
- `S` be repeats classified `stale_repeat`.

Publish raw counts with every rate. Round only for display.

| Metric | Formula |
| --- | --- |
| New-idea rate | `N / V * 100` |
| Repeat rate | `R / V * 100` |
| Explained-repeat rate | `X / R * 100` |
| Strict material-update rate | `M / R * 100` |
| Decision-changing-repeat rate | `(M + RI) / R * 100` |
| Stale-repeat rate | `S / R * 100` |
| Unverified-lineage share | `U / C * 100` |

For each verified repeat, idea age is `last_seen_at - first_seen_at` in hours.
Report repeat count, median age, and maximum age.

If a denominator is zero, the rate is `not_available`, never zero. The one
exception is repeat rate: when `V` is positive and `R` is zero, repeat rate is
legitimately zero. When `R` is zero, all repeat subrates and repeat-age
aggregates are `not_available`.

## Stale-evidence share

The unit is each current-report idea evidence entry. Join `evidence[].source_id`
to the report source register.

- Known recency entries `K` have source status `available`, `fallback`, or
  `stale` under the v1 safety-first status precedence.
- Stale entries `E` have source status `stale`.
- Unavailable sources and missing joins are unknown and are not silently counted
  as current.

Stale-evidence share is `E / K * 100`. Publish the unknown count and unknown
share against all evidence entries so exclusions cannot flatter the rate. When
`K` is zero, stale-evidence share is `not_available`.

A fallback that is also stale is serialized as `stale`, with fallback detail in
the source note and quality flags.

## Contract compatibility

The v1 schema file accepts both artifact revisions:

- `1.0.0` preserves the original idea shape and forbids `lineage`;
- `1.1.0` requires `lineage` and enforces classification-specific fields.

Existing `1.0.0` artifacts remain valid. Producers claiming lineage metrics
emit `1.1.0`. Breaking identity or classification changes require a new major
schema directory and a superseding Architecture Decision Record.

## Verification fixtures

The fictional investment-idea examples cover new, unchanged repeat, material
update, reintroduction, stale repeat, unverified lineage, and legacy `1.0.0`
compatibility. The repository validator checks their timestamps,
classifications, evidence joins, required repeat reasons, and aggregate metric
arithmetic.

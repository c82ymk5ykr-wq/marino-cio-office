# Outcome-review contract

- Artifact family: `outcome-review`
- Current version: `1.0.0`
- Scope: private post-decision review through a public, implementation-neutral interface

## Core invariant

An outcome review is an immutable hindsight artifact appended to an existing
ex-ante decision. It does not alter, replace, or reinterpret the linked
`decision-record`. A later correction or evaluation horizon creates another
review with a new `review_id`; the optional `prior_review_ref` links the
append-only sequence without deleting or rewriting either artifact.

A favorable research outcome does not establish sound decision or process
quality. An adverse research outcome does not establish unsound decision or
process quality. Outcome, decision quality, process quality, timing discipline,
invalidation handling, and attribution are independent axes.

## Public/private boundary

This repository publishes only the schema, vocabulary, template, invented
fixtures, and deterministic validation rules. Every populated review,
attribution entry, evidence record, real identifier, review date or window,
aggregate, and private producer/consumer mapping remains private.

Public examples are invented from scratch and visibly fictional. A redacted,
hashed, anonymized, relabeled, or sampled production record is not a synthetic
fixture and must not enter a public branch, pull request, test log, Actions
artifact, or issue.

The contract contains no asset, account, client, portfolio, transaction,
deployment, price, benchmark, return, alpha, or P&L field. It is not an
investment-performance or performance-attribution interface.

## Identity and linkage

| Field | Meaning |
| --- | --- |
| `review_id` | Stable opaque identifier for this finalized review |
| `prior_review_ref` | Optional opaque reference to the immediately prior review |
| `links.decision_ref` | Opaque private reconciliation token for the immutable ex-ante decision |
| `links.idea_ref` | Opaque private reconciliation token for the linked idea lineage |
| `links.evidence_refs` | Complete set of opaque evidence tokens used anywhere in the review |

Identifiers use contract prefixes and base64url-safe opaque bodies. Their bodies
must not encode symbols, clients, accounts, providers, decisions, content,
payload hashes, or other semantic aliases. Decision, idea, and evidence
references are distinct tokens. Private systems own the mapping and
referential-integrity check. Public validation deliberately does not require
any linked record to exist in this repository.

Every axis-level or attribution `evidence_refs` entry must occur in
`links.evidence_refs`. Missing evidence is omitted and represented by the
applicable state; it is never reconstructed.

## Clocks and lifecycle

All clocks are RFC 3339 UTC date-times ending in `Z`.

| Field | Named meaning |
| --- | --- |
| `clocks.decision_recorded_at` | Creation time of the immutable ex-ante decision |
| `clocks.evaluation_started_at` | Start of the outcome-observation interval; invalidation surveillance may already have begun at decision time |
| `clocks.evidence_cutoff_at` | Latest effective evidence time considered |
| `clocks.reviewed_at` | Time the append-only review was finalized |
| `invalidation_trigger.triggered_at` | Observed trigger time when the trigger state is `triggered` |
| `invalidation_response.responded_at` | Observed response time when the response was `followed` or `delayed` |

The required order is:

`decision_recorded_at <= evaluation_started_at <= evidence_cutoff_at <= reviewed_at`

Invalidation surveillance is independent of the outcome-observation interval. A
trigger may therefore be observed at or after `decision_recorded_at`, including
before `evaluation_started_at`.

A trigger time must fall between the decision and evidence cutoff. A response
time must not precede its trigger or exceed the evidence cutoff. Equal clocks
are permitted when the events genuinely share an effective instant.

## Assessability and evidence quality

`review_assessability` describes whether the review as a whole can make
supported qualitative assessments:

| Value | Meaning |
| --- | --- |
| `assessable` | Every applicable axis can be assessed from verified retained evidence |
| `partial` | At least one useful axis can be assessed from partial retained evidence |
| `unavailable` | Retained evidence is absent; no substantive assessment is inferred |
| `unknown` | Available history cannot establish whether a substantive assessment is supportable |

`evidence_quality` is a separate axis:

| Value | Meaning |
| --- | --- |
| `verified` | Retained evidence links support verification under the private policy |
| `partial` | Some required evidence is retained and some is missing |
| `unverified` | Evidence may exist, but retained history cannot verify it |
| `unavailable` | No usable evidence is retained |

An assessable review requires verified evidence. A partial review requires
partial evidence, at least one useful assessment, and at least one limited
qualitative or invalidation assessment. A limited invalidation axis does not
downgrade an otherwise assessable research, decision, process, timing, or
attribution axis. An unknown review uses unverified evidence quality and makes no qualitative
classification. An unavailable review requires unavailable evidence, empty
evidence links, and no qualitative classification or attribution factor. Every
limited review discloses its constraints rather than backfilling history.

Each qualitative axis has its own `assessment_state`:
`assessable`, `partial`, `unavailable`, `unknown`, or
`not_applicable`. Research outcome, decision quality, and process quality are
intrinsic to a linked decision review and cannot be `not_applicable`; timing
may be not applicable. A classification and evidence link are present only for
an assessable or partial axis.

## Independent review axes

| Axis | Allowed qualitative classification |
| --- | --- |
| `research_outcome` | `favorable`, `mixed`, `adverse` |
| `decision_quality` | `sound`, `mixed`, `unsound` |
| `process_quality` | `disciplined`, `mixed`, `undisciplined` |
| `timing_discipline` | `disciplined`, `mixed`, `undisciplined` |

The research-outcome classification describes thesis-relevant qualitative
observations at the evidence cutoff. It does not serialize prices, returns,
benchmarks, or investment performance. Decision quality is evaluated against
the evidence available ex ante, not the realized outcome. Process and timing
remain distinct from both.

## Invalidation trigger and response

Trigger and response are serialized separately. The following matrix is
exhaustive:

| Trigger state | Allowed response state |
| --- | --- |
| `not_triggered` | `not_applicable` |
| `triggered` | `followed`, `delayed`, `not_followed`, `ambiguous`, `unknown` |
| `ambiguous` | `ambiguous`, `unknown` |
| `unknown` | `unknown` |
| `not_applicable` | `not_applicable` |

`triggered_at` exists only for a triggered condition. `responded_at` exists
only for a followed or delayed response. `ambiguous` means conflicting
retained evidence; `unknown` means the retained history cannot establish a
state. Whether a response is followed or delayed is determined by the private
policy; no private threshold, rule text, or deployment action is published by
this contract.

## Qualitative attribution

`attribution.factors[]` records plausible qualitative associations. Each
factor has:

- a public factor category;
- categorical `direction`: `supporting`, `detracting`, `mixed`, or
  `unclear`;
- qualitative `confidence`: `low`, `medium`, or `high`;
- one or more opaque evidence references; and
- a qualification note.

Attribution is uncertainty-aware and evidence-linked. It is not causal proof,
performance attribution, or a numeric allocation of contribution. Numeric
weights, contribution percentages, and performance fields are not part of this
artifact.

## Compatibility

`outcome-review` is a new additive artifact family at version `1.0.0`. It
does not change the meaning or validity of `report-manifest`,
`investment-idea`, or `decision-record`.

Compatible revisions may be published as later `1.x` versions while retaining
the v1 compatibility corpus. A breaking change requires a new schema directory,
an ADR, migration notes, and private producer/consumer conformance review.

## Private conformance gate

Before Phase 4 outcome 1 is marked complete, authorized private checks must
categorically confirm:

- producer serialization and consumer parsing for `outcome-review 1.0.0`;
- opaque decision, idea, evidence, and prior-review reconciliation;
- append-only storage without mutation of the ex-ante decision or earlier
  finalized reviews;
- assessability, evidence, state, and clock enforcement; and
- exclusion of every prohibited private or performance field.

Only the adopted version and categorical conformance classes may be recorded
publicly. Mappings, real fixtures, counts, logs, screenshots, storage
references, and detailed evidence remain private.

## Downstream learning controls

Outcome reviews are eligible inputs to the private derived measurements in
[`learning-loop-metrics.md`](learning-loop-metrics.md), but only through a
valid, uniquely resolved append-only chain. A favorable or adverse outcome can
never determine timing, invalidation, process quality, or lesson approval.

An outcome review does not itself contain a lesson or approval. A lesson may
enter future Chief Historian review only through the separate, human-approved
and versioned [`historian-lesson` contract](historian-lesson-contract.md).

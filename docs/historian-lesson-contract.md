# Chief Historian lesson contract

- Artifact family: `historian-lesson`
- Current version: `1.0.0`
- Decision trace: `decision-record 1.1.0`
- Scope: human-approved, advisory lessons consumed privately through a public,
  metadata-only control interface

## Core invariant

A Chief Historian lesson is eligible for review only after a human approves an
exact immutable lesson revision and the private consumer acknowledges successful
advisory ingestion of that same revision. Approval and ingestion create new
opaque receipts for every revision. They do not execute the lesson or authorize
any investment or system action.

The lesson body is never serialized in this artifact. An active revision points
to its immutable body through `content_ref`; a retired revision is a tombstone
with no content reference. The real body and every real/private populated
control artifact remain in approved private storage.

## Control envelope

The artifact proves only that an exact revision passed the following controls:

1. every linked `outcome-review` was finalized;
2. a human authority approved the exact revision;
3. the private Chief Historian consumer acknowledged advisory ingestion; and
4. immutable metadata identifies the series, revision, predecessor, lifecycle
   state, clocks, receipts, and—only while active—the private content reference.

`approval.authority_type` is always `human`; no person, team, account, provider,
or credential is named. `approval.status` is always `approved` and
`ingestion.status` is always `ingested`. A proposed, rejected, pending, failed,
or machine-approved lesson is not a `historian-lesson` artifact.

`ingestion.mode` is always `advisory_only`. Ingestion makes guidance eligible
for a future Chief Historian review. It never executes content and never edits a
prompt, code, configuration, schema, threshold, weight, historical artifact,
research disposition, deployment readiness, sizing plan, or deployment action.
Any operating change requires its own separately authorized control.

## Identity and opaque references

| Field | Meaning |
| --- | --- |
| `lesson_series_id` | Stable opaque identity shared by every revision in one lesson series |
| `lesson_version_ref` | Exact immutable identity of one approved and ingested revision |
| `prior_version_ref` | Exact reference to revision N-1 in the same series |
| `source_reviews[].review_ref` | Opaque reference to one finalized private outcome review |
| `approval.receipt` | Immutable acknowledgement of human approval for this exact revision |
| `ingestion.receipt` | Immutable acknowledgement of successful advisory ingestion for this exact revision |
| `content_ref` | Opaque reference to the exact immutable private body of an active revision |

Token prefixes distinguish reference classes, and token bodies are
base64url-safe. Bodies do not encode lesson text, symbols, clients, accounts,
providers, decision semantics, identities, paths, URIs, or payload hashes.
Private systems own receipt resolution, content-version reconciliation, and
referential-integrity checks. Public validation uses only invented tokens.

Every lesson revision has a unique `lesson_version_ref`, approval receipt, and
ingestion receipt. Approval and ingestion receipts are different token classes
and may never be reused by another revision. Every active revision has a new
immutable content reference; a body cannot be silently relabeled as a new
revision.

## Append-only lifecycle

The lifecycle is a single linear chain within one `lesson_series_id`:

| Revision | Required state | Predecessor | Content |
| --- | --- | --- | --- |
| `1` | `active` | omitted | required |
| `N > 1`, revised guidance | `active` | exact revision `N-1` | required and new |
| `N > 1`, retirement | `retired` | exact revision `N-1` | forbidden |

Revision N points to exactly N-1 in the same series. Gaps, branches, cycles,
self-links, cross-series links, duplicate identities, and multiple terminal
revisions are invalid. A retirement is a newly human-approved and ingested
tombstone. It never mutates or deletes an earlier active revision. A retired
terminal ends the series unless a future contract explicitly defines a new
lifecycle operation.

Only the terminal active revision available at a decision's `recorded_at` may be
selected for a new Chief Historian review. “Latest” aliases and series-level
references are not selection mechanisms. A revision is available only after its
`ingested_at` clock; a later generated metadata copy does not change the
revision's control meaning.

## Clocks

Every clock is an RFC 3339 UTC date-time ending in `Z`.

| Field | Named meaning |
| --- | --- |
| `source_reviews[].finalized_at` | Finalization time of a linked private outcome review |
| `clocks.data_as_of` | Latest effective evidence time represented by this lesson revision |
| `clocks.approved_at` | Human approval time for this exact revision |
| `clocks.ingested_at` | Successful advisory-ingestion acknowledgement time |
| `clocks.generated_at` | Assembly time of this metadata control artifact |

The required order is:

`data_as_of <= approved_at <= ingested_at <= generated_at`

Every linked review must be finalized no later than `approved_at`. Private
reconciliation additionally verifies that each serialized `finalized_at` equals
the linked finalized review's actual `clocks.reviewed_at` and that the lesson's
`data_as_of` does not exceed the evidence available from those reviews. Within
one revision, equal clocks are permitted when events share an effective
instant. Across revisions, a successor's `ingested_at` must be strictly later
than its predecessor's `ingested_at`; equal ingestion clocks cannot establish
an append-only revision order.

## Exact decision trace

`decision-record 1.1.0` requires
`historian_lesson_version_refs`. The array contains only the exact terminal
active lesson revisions materially used in that decision's Chief Historian
review. References are unique. An empty array is correct when no approved lesson
applied; missing history is never reconstructed.

Eligibility is evaluated as of the decision's `recorded_at`:

- the referenced revision must have been approved and ingested by that time;
- it must have been the terminal active revision of its series at that time;
- a predecessor is stale once its active successor or retirement tombstone is
  ingested; and
- a successor or retirement ingested later never changes an earlier decision.

The decision remains an immutable ex-ante record. A later lesson revision
requires a later decision to cite the new exact version if it is materially
used. `decision-record 1.0.0` remains valid and explicitly forbids the new
field; it carries no implied lesson history.

## Public/private boundary

This repository publishes only the schema, template, contract semantics,
architecture decision, deterministic validation behavior, and visibly invented
fixtures. It never publishes or reconstructs:

- a real lesson body, outcome review, decision, chain, or usage record;
- approval identities, receipt mappings, content mappings, or storage details;
- prompts, code, configurations, schemas, thresholds, weights, or change logs;
- provider identities, logs, counts, aggregates, or adoption metrics; or
- client, account, portfolio, transaction, deployment, performance, price,
  return, benchmark, alpha, P&L, path, URI, or payload-hash data.

Redacted, anonymized, relabeled, sampled, or hashed production material is not
synthetic and does not belong in public Git history, issues, test logs, or CI
artifacts.

## Compatibility

`historian-lesson 1.0.0` is a new additive v1 artifact family.
`decision-record 1.1.0` is a backward-compatible revision: it requires exact
lesson-version references while the retained `decision-record 1.0.0` branch
keeps its original shape and forbids the new field. Compatible later `1.x`
revisions must preserve the v1 corpus. A breaking change requires a new schema
directory, migration notes, an ADR, and renewed private conformance review.

## Private conformance gate

Before the lesson-control outcome or Phase 4 is marked complete, authorized
private checks must categorically confirm:

- exact approval- and ingestion-receipt resolution for every revision;
- exact content-version linkage for active revisions;
- finalized-review reconciliation and clock ordering;
- linear append-only supersession and retirement with no mutation or deletion;
- terminal-active selection as of each `decision-record 1.1.0` timestamp;
- immutable exact-version traces on earlier decisions; and
- advisory-only ingestion with no prompt, code, configuration, schema,
  threshold, weight, historical-decision, or deployment side effect.

Only adopted public versions and categorical conformance classes may be
recorded publicly. Real artifacts, mappings, evidence, counts, logs, and usage
history remain private.

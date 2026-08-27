# ADR 0010: Admit only human-approved, versioned lessons to Chief Historian review

- Status: Accepted
- Date: 2026-08-27
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

Outcome reviews and deterministic learning-loop measurements can identify
possible operating lessons, but neither should automatically change future
research. Phase 4 needs a controlled way to make a lesson eligible for Chief
Historian review without publishing lesson content, rewriting prior decisions,
or allowing an ingestion mechanism to modify production behavior.

A mutable “current lesson” would erase what guidance existed when a decision
was made. Automatic extraction or prompt editing would also collapse evidence,
approval, ingestion, and execution into one unsafe action. Publishing redacted
lessons, receipts, or usage history would cross the public/private boundary.

## Decision

Create a metadata-only `historian-lesson` artifact family at version `1.0.0`.
Only finalized revisions that have a categorical human approval, a unique
immutable approval receipt, successful advisory ingestion, and a unique
immutable ingestion receipt enter this family. Lesson bodies stay in approved
private storage behind an active revision's opaque `content_ref`.

Represent each lesson as a linear append-only revision series. Revision 1 is
active, has no predecessor, and has content. Revision N points to exact revision
N-1 in the same series. A revised active lesson has new immutable content. A
retirement is a new approved and ingested tombstone with a predecessor and no
content; it does not mutate or delete prior revisions. Reject gaps, branches,
cycles, cross-series links, reused identities or receipts, and multiple terminal
revisions.

Serialize finalized source-review references and their finalization clocks.
Require UTC clock order
`data_as_of <= approved_at <= ingested_at <= generated_at` and require every
linked review to have finalized no later than approval. Private conformance
resolves the opaque reviews, receipts, and content references to their exact
private records.

Set `ingestion.mode` to `advisory_only`. Ingestion only admits guidance for
consideration in a later Chief Historian review. It never executes lesson
content or edits prompts, code, configuration, schemas, thresholds, weights,
historical records, research decisions, sizing, or deployment actions.

Add backward-compatible `decision-record 1.1.0` with required
`historian_lesson_version_refs`. A decision cites only unique exact lesson
versions materially used. Empty references are valid when no approved lesson
applies. Preserve `decision-record 1.0.0` unchanged in meaning and explicitly
forbid the new field on that version.

Evaluate lesson selection at the decision's `recorded_at`. Only a terminal
active revision approved and ingested by that instant is selectable. A later
successor or retirement does not invalidate, reinterpret, or update the exact
reference stored on an earlier decision.

Keep all real/private populated lesson controls and their bodies, reviews,
decisions, receipts, mappings, chains, identities, storage details, usage
records, counts, aggregates, logs, prompts, production changes, and conformance
evidence private. Public validation uses invented fixtures only.

## Alternatives considered

- **Automatically turn outcome reviews into lessons.** Rejected because review
  completion does not establish human approval or operating suitability.
- **Maintain one mutable current lesson.** Rejected because it destroys the
  exact historical guidance available to an earlier decision.
- **Reference only a lesson series from decisions.** Rejected because resolving
  “latest” later would rewrite historical meaning.
- **Encode retirement by deleting or disabling the prior record.** Rejected
  because deletion breaks the append-only audit trail.
- **Let ingestion edit a prompt or configuration.** Rejected because advisory
  admission and production change authorization are separate controls.
- **Publish redacted lesson bodies or usage aggregates.** Rejected because
  redaction, hashing, relabeling, or aggregation does not make private learning
  history synthetic.

## Consequences

- human judgment remains the admission authority for institutional lessons;
- every revision and decision trace has stable point-in-time meaning;
- supersession and retirement preserve history without making stale guidance
  eligible for new decisions;
- a no-lesson decision is explicit and missing history is not reconstructed;
- private consumers must resolve receipts, content, reviews, and exact versions
  while preserving append-only storage; and
- public contracts can validate lifecycle and trace semantics without
  disclosing the proprietary lesson or production implementation.

## Verification

Public verification requires the historian-lesson schema, contract, template,
invented initial/revised/retired fixtures, decision-record 1.1 fixture, v1
compatibility entries, deterministic validator, and focused unit tests to pass
together while retaining decision-record 1.0 compatibility.

Before Phase 4 is checked complete, authorized private verification must
categorically confirm receipt resolution, exact content-version linkage,
finalized-review linkage, append-only supersession and retirement,
terminal-active selection at decision time, immutable earlier decisions,
decision-record 1.1 tracing, advisory-only ingestion, and boundary exclusion.
Phase 4 closes only when the separate private learning-measurement gate is also
accepted. Detailed evidence never enters this repository.

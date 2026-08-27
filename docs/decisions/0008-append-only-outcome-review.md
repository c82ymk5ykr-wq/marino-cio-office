# ADR 0008: Append hindsight in a separate qualitative outcome-review artifact

- Status: Accepted
- Date: 2026-08-25
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

Phase 4 needs a durable way to learn from decisions without allowing hindsight
to rewrite the original record. The public interface must distinguish what was
observed from whether the decision, process, timing, or invalidation response
was disciplined. It must support private reconciliation while keeping real
decisions, outcomes, evidence, dates, performance, and history out of this
public repository.

Adding hindsight fields to `decision-record` would change an immutable ex-ante
artifact's meaning. Publishing a performance-attribution model or populated
reviews would cross the public/private boundary.

## Decision

Create a new additive `outcome-review` artifact family at version `1.0.0`.
Each finalized review is append-only and has its own opaque `review_id`. A
later correction or evaluation horizon creates another review; the optional
`prior_review_ref` links the sequence without mutating the prior review or the
linked decision.

Embed qualitative attribution entries within the review. Keep research outcome,
decision quality, process quality, timing discipline, invalidation trigger,
invalidation response, and attribution as independent fields. Outcome never
derives decision or process quality.

Use opaque private reconciliation tokens for the linked decision, idea, prior
review, and evidence. Token bodies carry no semantic private aliases. The
public validator verifies token shape and internal evidence-reference closure
but deliberately does not require linked records to be published.

Use four required, single-purpose clocks in UTC ending in `Z`:

`decision_recorded_at <= evaluation_started_at <= evidence_cutoff_at <= reviewed_at`

When present, invalidation trigger and response clocks must fall within that
lifecycle and the response cannot precede the trigger.

Represent missing or uncertain history explicitly through review
assessability, evidence quality, per-axis assessment states, and invalidation
states. Do not infer or reconstruct missing records.

Attribution uses categorical direction and qualitative confidence, retains
opaque evidence links, and makes no causal or numeric contribution claim.

Existing `report-manifest`, `investment-idea`, and `decision-record`
schemas are unchanged. Compatible outcome-review revisions remain in
`schemas/v1/`; breaking changes require a new schema directory and a
superseding ADR.

All populated reviews, attribution entries, supporting evidence, real
identifiers, review dates and windows, aggregates, private mappings, storage
references, and conformance evidence remain private. Public CI uses invented
fixtures only.

## Alternatives considered

- **Add hindsight to `decision-record`.** Rejected because it would erase the
  distinction between ex-ante judgment and later knowledge.
- **Create a separate attribution artifact.** Rejected for version 1 because
  attribution has meaning only in the context of one review and embedding keeps
  its evidence and uncertainty boundary atomic.
- **Use numeric contribution or performance attribution.** Rejected because it
  would imply causal precision, introduce prohibited investment-performance
  data, and conflate outcome with process quality.
- **Publish redacted production reviews or aggregates.** Rejected because
  anonymization, hashing, or relabeling does not make private history synthetic.

## Consequences

- outcome learning can be appended without weakening the decision record;
- favorable and adverse outcomes can coexist with independent process-quality
  assessments;
- missing history remains visible as partial, unavailable, unknown, unverified,
  or not applicable;
- private systems must maintain opaque-reference reconciliation and append-only
  storage;
- public validation can enforce shape, state coherence, clocks, qualitative
  attribution, and prohibited fields without production data; and
- idea novelty metrics and Chief Historian lesson approval or ingestion are
  governed by the later Phase 4 decisions that adopt those contracts.

## Verification

Public verification requires the outcome-review schema, contract documentation,
template, invented fixtures, v1 compatibility fixture, deterministic validator,
and focused unit tests to pass together.

Before the first Phase 4 roadmap outcome is checked complete, an authorized
private review must categorically verify producer serialization, consumer
parsing, opaque-link reconciliation, append-only behavior, unchanged ex-ante
decisions, state and clock handling, and boundary exclusion. Only the adopted
contract version and categorical conformance classes may be recorded publicly;
the mappings and evidence never enter this repository.

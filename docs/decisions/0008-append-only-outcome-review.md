# 0008 — Add an append-only outcome-review contract

- Status: Accepted
- Date: 2026-08-25
- Owners: Marino CIO Office

## Context

Phase 4 requires private outcome review and decision attribution without moving
decisions or performance history into the public repository. Extending a
decision record after the outcome is known would mix ex-ante judgment with
hindsight, weaken auditability, and invite outcome bias. A documentation-only
interface would not provide executable compatibility or state validation.

## Decision

Add `outcome-review 1.0.0` as a separate additive v1 contract family. The
original decision record remains immutable. A review links to the decision,
idea, and evidence through opaque identifiers and records independent,
qualitative axes for research outcome, decision quality, process quality,
timing discipline, invalidation trigger and response, and attribution. A
correction is another append-only artifact with an optional opaque link to the
review it supersedes; no finalized review is overwritten.

The contract uses explicit assessable, partial, unavailable, unverified,
unknown, and not-applicable behavior. Attribution is evidence-linked and
qualitative; it has no numeric weights and makes no causal or investment-
performance claim. Ordered UTC clocks distinguish the decision time,
evaluation window, evidence cutoff, and review time.

All real populated reviews, attribution entries, identifiers, evidence,
aggregates, dates, and performance history remain private. The public
repository contains only the schema, template, invented fixtures, terminology,
and validation. Private adoption is attested categorically only after producer
and consumer conformance passes.

## Alternatives considered

- Extend `decision-record` with hindsight fields: rejected because it would
  mutate or reinterpret the ex-ante record and risk breaking v1 semantics.
- Publish numeric outcome or return attribution: rejected because performance,
  holdings, transactions, and causal contribution claims are outside the public
  boundary and would create false precision.
- Define the workflow in prose only: rejected because impossible invalidation
  states, dangling links, clock order, and compatibility would not be
  executable gates.
- Combine review, measurement, and Chief Historian lesson approval in one
  contract: rejected to keep evidence, metrics, and institutional-memory
  approval as distinct later Phase 4 outcomes.

## Consequences

- Existing report, idea, and decision artifacts remain valid without changes.
- Private producers must create append-only review artifacts rather than write
  hindsight into decisions.
- Private consumers must preserve every assessment axis and unknown state
  without deriving process quality from outcome.
- Later Phase 4 metrics can measure review records without redefining idea
  lineage or introducing a composite performance score.
- Phase 4 outcome 1 stays open until private conformance is verified; accepting
  the public interface alone is not a production-adoption claim.

## Verification

- Validate the Draft 2020-12 schema and freeze version 1.0.0 in the v1
  compatibility corpus.
- Exercise fictional adverse/disciplined, favorable/undisciplined, triggered
  and followed, triggered and delayed, partial/unverified, and append-only
  correction reviews.
- Reject impossible invalidation pairs, dangling links, duplicate factor IDs,
  unordered clocks, unknown properties, and performance- or account-like
  fields.
- Run the repository unit suite and `python3 scripts/validate.py`.
- Complete a separate categorical private producer/consumer conformance review
  before changing the Phase 4 roadmap checkbox.

# ADR 0007: Attest private contract adoption without publishing mappings

- Status: Accepted
- Date: 2026-08-25
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

Phase 2 established deterministic public contracts and report-acceptance gates.
Phase 3 requires the private production system to consume named contract
versions, make those versions and their status visible, and preserve an honest
decision product when required inputs or persistence degrade.

Closing that phase publicly creates two risks. Publishing production mappings or
verification evidence would breach the public/private boundary. Merely checking
roadmap boxes would not record which contract versions were adopted or what
behavior was verified.

## Decision

Record a provider-neutral adoption attestation for this contract set:

| Artifact | Public contract | Adopted version |
| --- | --- | --- |
| Report manifest | `report-manifest` | `1.1.0` |
| Investment idea | `investment-idea` | `1.1.0` |
| Decision record | `decision-record` | `1.0.0` |

Treat adoption as verified only when private conformance checks confirm that:

- emitted contract fields, enum values, clocks, and cross-artifact identifiers
  validate against the named versions;
- the private dashboard and generated artifacts surface the contract versions,
  contract-validation result, derived report outcome, artifact outcome, and
  quality flags;
- report outcome remains separate from runtime readiness, research disposition,
  deployment readiness, deployment action, and persistence outcome;
- report status follows the public `failed`, `degraded`, `provisional`,
  `complete` gate precedence rather than a job, page, or scan status;
- completion-equivalent fallbacks remain visible, while unavailable or stale
  required sources, non-equivalent fallbacks, and persistence failures prevent
  completion without hiding a reliable limited product;
- the absence of a reliable decision product yields `failed`; and
- durable persistence is claimed only with an opaque receipt and persistence
  time, never a path, URI, or temporary link.

This is a categorical conformance attestation, not a publication of the
implementation. Production mappings, adapter source, provider identities,
production source identifiers, runtime thresholds and values, reports, test
fixtures, receipts, and storage locations remain private.

## Alternatives considered

- **Publish the production mappings.** Rejected because the mappings could
  disclose proprietary implementation and provider details.
- **Maintain a public mirror of the private adapters.** Rejected because it
  would duplicate production code, create drift, and weaken the repository
  boundary.
- **Close the roadmap without naming the adopted versions.** Rejected because
  future compatibility work would have no durable adoption record.

## Consequences

- the public repository records which contracts private production consumes
  without describing how they are implemented;
- users can distinguish contract validation and report status from operational
  readiness or deployment decisions;
- degraded and failed outcomes remain valid, visible products of the contract
  rather than hidden execution errors;
- private verification evidence remains authoritative and is not reproduced in
  this repository; and
- adopting another contract version or changing acceptance semantics requires a
  renewed private verification review.

No public schema, vocabulary, or status semantic changes as a result of this
decision.

## Verification

Private verification confirmed the following provider-neutral classes:

- contract shape, enum, version, clock, and cross-artifact identifier
  conformance;
- contract-version and status reporting in the dashboard and generated
  artifacts;
- complete, provisional, degraded, and failed report outcomes;
- unavailable-source, stale-source, equivalent-fallback,
  non-equivalent-fallback, and persistence-failure behavior;
- continued usability when a reliable limited decision product exists; and
- public/private boundary compliance.

The public closeout must pass the repository unit tests and
`python3 scripts/validate.py`. Public review confirms only the named versions
and categorical results above; detailed evidence remains private.

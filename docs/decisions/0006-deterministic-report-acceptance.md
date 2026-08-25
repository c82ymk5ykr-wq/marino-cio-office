# ADR 0006: Add deterministic report acceptance and manifest 1.1

- Status: Accepted
- Date: 2026-08-25
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

Phase 1 established full-universe completion semantics and safety-first report
status precedence. Report-manifest 1.0 could not serialize required-source role
equivalence, review completion, reliable-product state, required-period lag, or
an auditable persistence receipt. Several contradictory status claims therefore
could not be rejected from one manifest.

## Decision

Add backward-compatible report-manifest `1.1.0` with explicit `gate_inputs`,
source checking times, explicit known/unknown required-period lag, honest
unavailable/unknown time representation, and a durable persistence receipt.
Derive the report outcome in repository validation
using `failed`, then `degraded`, then `provisional`, then `complete` precedence.

Preserve report-manifest `1.0.0` unchanged through the compatibility corpus.
Keep universe completion separate from runtime readiness, and keep report
completion separate from recommendation or deployment authorization.

## Consequences

- a 1.1 report cannot be called complete from a successful job, page load, or
  usable subset;
- required source roles and fallback equivalence become machine-readable without
  exposing provider implementation;
- unavailable or unknown time is omitted rather than fabricated;
- durable persistence requires a non-sensitive opaque receipt token and
  persistence time;
- role-linked source evidence, aggregate freshness, and report-generation clocks
  must reconcile;
- status claims, gate evidence, and required quality flags must agree; and
- private consumers may adopt 1.1 without invalidating retained 1.0 artifacts.

## Alternatives considered

- **Continue using narrative quality flags only.** Rejected because review,
  role, and persistence evidence could not be joined deterministically.
- **Make the new fields mandatory for 1.0.0.** Rejected as a breaking change.
- **Publish private source or storage mappings.** Rejected by the repository
  boundary and unnecessary for public contract conformance.

## Verification

- Validate both report-manifest 1.0 and 1.1 fixtures against the current schema.
- Derive all four statuses from the synthetic acceptance truth table.
- Reject contradictory claims, arithmetic errors, duplicate or inconsistent
  source joins, invalid time ordering, unreconciled freshness, and non-opaque
  persistence references.
- Run the append-only v1 compatibility suite.

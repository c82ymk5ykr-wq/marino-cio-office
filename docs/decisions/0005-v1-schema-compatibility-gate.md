# ADR 0005: Make v1 backward compatibility an executable gate

- Status: Accepted
- Date: 2026-08-25
- Decision owners: Marino CIO Office maintainers
- Supersedes: None
- Superseded by: None

## Context

The repository already required backward-compatible changes within
`schemas/v1/`, but that promise was review guidance rather than an executable
gate. Schema syntax checks and evolving examples could not reliably detect a
removed artifact version, a newly required field, or a narrowed historical
enum value.

## Decision

Maintain an append-only, public-safe compatibility corpus for every published
v1 artifact revision. Validate the corpus with the current Draft 2020-12
schemas in CI and exercise retained enum and boundary values through deterministic
tests.

The corpus defines a compatibility floor. It does not replace schema review,
prove compatibility for every theoretical instance, or describe private
consumer payloads.

## Consequences

- routine compatible additions remain possible within `schemas/v1/`;
- regressions affecting retained valid artifacts fail CI;
- breaking changes must use a new schema directory and explicit migration ADR;
- new published revisions require new frozen synthetic fixtures; and
- fixture content remains fictional and contains no private mapping or live data.

## Alternatives considered

- **Compare schema text.** Rejected because harmless formatting and compatible
  additions would create noise while semantic breakage could still be missed.
- **Attempt formal schema-subsumption proof.** Rejected as disproportionate and
  unreliable for the current conditional schemas.
- **Rely only on evolving examples.** Rejected because examples may legitimately
  change and therefore do not form an append-only compatibility record.

## Verification

- Validate every corpus entry against its current schema.
- Confirm the schema still declares every corpus version.
- Exercise historical enum values and representative length boundaries.
- Mutate schemas and instances in memory to prove breaking changes are detected.

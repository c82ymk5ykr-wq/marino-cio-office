# 0003 — Deterministic universe-completion gates

- Status: Accepted
- Date: 2026-08-25
- Owners: Marino CIO Office

## Context

The v1 report manifest records expected and observed coverage, freshness,
source health, reviews by implication, and persistence. It does not by itself
name the threshold profile that turns those facts into a universe-completion
claim.

Operational readiness checks may deliberately use smaller minimum samples so a
system can render or recover. Treating such a minimum as full completion would
make a broad-universe ranking look more reliable than its evidence.

## Decision

Adopt [`docs/universe-completion-gates.md`](../universe-completion-gates.md) as
the public universe-completion specification.

- Use provider-neutral named profiles.
- Require known non-zero membership, 100% unique eligible evaluation, zero gaps,
  and zero required-period lag for every supported profile.
- Keep current-period freshness distinct from elapsed wall-clock age.
- Permit retained observations only when they remain identity-valid,
  evaluation-complete, and current for the required period.
- Keep minimum runtime readiness separate from universe completion.
- Derive report status using the specified failure precedence.
- Validate the rules with entirely fictional truth-table cases.

The actual membership, providers, scheduling, batching, ranking logic, and live
coverage remain private.

## Consequences

Positive:

- `complete` becomes a reproducible evidence claim rather than a UI label;
- the S&P 500-style broad-equity use case cannot be complete on a small usable
  subset;
- ETF and other bounded universes use the same transparent accounting rules;
- weekends and source schedules do not create false freshness through a single
  wall-clock shortcut;
- duplicate or retained observations cannot silently inflate coverage.

Costs and constraints:

- one missing required member keeps a ranking provisional unless a material
  failure makes it degraded;
- membership snapshots and required-period calendars must be maintained
  privately;
- v1 cannot serialize every gate input, so Phase 2 quality gates may add a
  backward-compatible extension or a new schema version after compatibility
  review.

## Verification

- Validate all synthetic truth-table cases with `python3 scripts/validate.py`.
- Reject zero-denominator and contradictory `complete` claims.
- Confirm no constituent, provider, live count, schedule, batch, or ranking
  detail appears in the public repository.

# 0002 — Canonical public contract vocabulary

- Status: Accepted
- Date: 2026-08-25
- Owners: Marino CIO Office

## Context

The public contracts and the private production consumer describe several
different status, time, coverage, research, and deployment concepts. Reusing a
generic word such as `status`, `ready`, `fresh`, or `complete` across those axes
can create false equivalence even when each underlying system is functioning as
designed.

Publishing a private schema map would expose implementation detail and make the
public repository depend on private aliases. Leaving the terms implicit would
allow the public contract and the production consumer to drift.

## Decision

Adopt [`docs/contract-vocabulary.md`](../contract-vocabulary.md) as the
canonical semantic glossary for the public contracts.

- The public schema names and enum meanings are canonical.
- Repository baseline versions and serialized artifact schema versions remain
  distinct.
- Public Architecture Decision Records and operational CIO decision records
  remain distinct artifacts.
- Report outcome, source health, freshness, research disposition, deployment
  readiness, deployment action, persistence, and provenance remain separate
  axes.
- Generation, evidence, retrieval, persistence, universe-membership, and cycle
  completion remain separate clocks.
- `complete` and `ready` describe contract state only. They do not mean
  recommended, suitable, or authorized for deployment.
- Private consumers perform their mapping privately and expose only a public
  conformance disposition when coordination is necessary.
- Missing history or quality is disclosed as unknown or unverified; it is not
  reconstructed.

## Consequences

Positive:

- status and timestamp claims can be reviewed without inspecting production
  code;
- public contract changes have one semantic reference point;
- private implementations can migrate without publishing their aliases;
- completion and investment action cannot be conflated by vocabulary alone.

Costs and constraints:

- private consumers must maintain their own compatibility mapping;
- new public fields require both schema definitions and glossary semantics;
- a breaking semantic change requires a new contract version and superseding
  decision record.

## Verification

- Review every public schema field against the glossary.
- Record private comparison results only as `conforms`,
  `public_contract_gap`, or `private_migration_needed`.
- Keep private schemas, payloads, code paths, and migration details out of the
  public repository.

## Initial conformance disposition

- `conforms`: the existing public report, idea, and decision contracts preserve
  separate research, deployment, provenance, source, freshness, and persistence
  concepts.
- `public_contract_gap`: deterministic universe-completion profiles and
  repeat-idea metrics require separate public specifications; unknown source
  time must also become representable without fabrication.
- `private_migration_needed`: a private consumer must map any overloaded or
  legacy internal label to the correct public axis before claiming conformance.

The private comparison was performed outside this repository. No private alias,
payload, code path, or migration detail is recorded here.

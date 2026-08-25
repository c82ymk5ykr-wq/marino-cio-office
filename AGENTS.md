# Repository instructions for agents

These instructions apply to every file in this repository.

## Mission

Preserve a public-safe, implementation-neutral source of truth for the Marino
CIO Office operating model and artifact contracts. Do not turn this repository
into a duplicate of the private MarinoTerminal application.

## Non-negotiable boundary

Never commit or reconstruct:

- credentials, tokens, cookies, private endpoints, or environment values;
- client or household information of any kind;
- real holdings, allocations, transactions, performance, or investment reports;
- chat exports, private prompts, ranking weights, or proprietary decision logic;
- raw provider files, logs, or data without redistribution rights;
- production deployment configuration or durable-artifact URLs.

Examples must be visibly fictional and synthetic. Anonymized real data is not
synthetic.

## Contract rules

- Preserve separate `generated_at` and `data_as_of` timestamps in UTC.
- Treat the public schema names and `docs/contract-vocabulary.md` meanings as
  canonical; keep private aliases and mappings private.
- Do not collapse report outcome, source health, freshness, research state,
  deployment readiness, deployment action, or persistence into one status.
- A `complete` or `ready` state never implies a recommendation or deployment
  authorization.
- Record expected and observed coverage, source health, and persistence outcome.
- Apply `docs/universe-completion-gates.md` to supported bounded universes;
  minimum runtime readiness is never evidence of full universe completion.
- Apply `docs/report-acceptance-gates.md` to report-manifest 1.1 artifacts and
  derive status from serialized gate evidence rather than trusting a label.
- Use `complete` only when the contract's freshness and coverage gates pass.
- Disclose unavailable sources and fallbacks; never fabricate completeness.
- Preserve the provenance labels `PASTED`, `INLINE`, and
  `CIO_LEVEL_INFERENCE`.
- Track an idea's `first_seen_at` and `last_seen_at`; explain material repeats.
- Apply `docs/idea-lineage-metrics.md`: routine refreshes do not make an idea
  new, and missing lineage is unverified rather than reconstructed.
- Separate research disposition from deployment timing, sizing, and action.
- Apply `docs/outcome-review-contract.md`: preserve the ex-ante decision,
  append hindsight separately, and keep outcome, process, timing,
  invalidation, and qualitative attribution independent.
- Apply `docs/schema-compatibility-policy.md` and keep `schemas/v1/` backward
  compatible. Breaking changes require a new schema version directory and an
  Architecture Decision Record (ADR).
- Update affected schemas, templates, synthetic examples, and documentation in
  the same change.

Report generation should still produce an honest degraded or failed manifest
when an input or persistence step fails. A temporary download link is never a
durable storage outcome.

## Change workflow

1. Read `README.md`, `docs/operating-model.md`, and
   `docs/public-private-boundary.md`.
2. Keep the change as small as practical.
3. Add an ADR for architecture, scope, status semantics, or data
   boundary changes.
4. Run `python3 scripts/validate.py`.
5. Summarize contract and boundary effects in the pull request.

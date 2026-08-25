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
- Record expected and observed coverage, source health, and persistence outcome.
- Use `complete` only when the contract's freshness and coverage gates pass.
- Disclose failed sources and fallbacks; never fabricate completeness.
- Preserve the provenance labels `PASTED`, `INLINE`, and
  `CIO_LEVEL_INFERENCE`.
- Track an idea's `first_seen_at` and `last_seen_at`; explain material repeats.
- Separate research disposition from deployment timing, sizing, and action.
- Keep `schemas/v1/` backward compatible. Breaking changes require a new schema
  version directory and a decision record.
- Update affected schemas, templates, synthetic examples, and documentation in
  the same change.

Report generation should still produce an honest degraded or failed manifest
when an input or persistence step fails. A temporary download link is never a
durable storage outcome.

## Change workflow

1. Read `README.md`, `docs/operating-model.md`, and
   `docs/public-private-boundary.md`.
2. Keep the change as small as practical.
3. Add a decision record for architecture, scope, status semantics, or data
   boundary changes.
4. Run `python3 scripts/validate.py`.
5. Summarize contract and boundary effects in the pull request.

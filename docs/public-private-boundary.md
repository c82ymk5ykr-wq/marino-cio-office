# Public and private boundary

## Decision

This repository is the public, portable contract for the Marino CIO Office. The
private MarinoTerminal repository is the production application and may consume
these contracts. The two repositories have distinct responsibilities and must
not be merged casually.

## Public material allowed here

- non-proprietary mission, vocabulary, and operating principles;
- versioned schemas and human-readable templates;
- synthetic examples made entirely from fictional data;
- architecture decisions, contribution rules, and roadmap items;
- repository-only validation and read-only CI configuration.

## Material that must stay private

- MarinoTerminal source, deployment settings, private endpoints, and secrets;
- proprietary prompts, score weights, ranking logic, or provider adapters;
- real clients, households, accounts, holdings, allocations, transactions,
  performance, tax, estate, insurance, or planning information;
- actual CIO decisions, generated reports or PDFs, Chief Historian memory, logs,
  traces, snapshots, and durable storage references;
- real populated outcome reviews, attribution entries, lesson candidates,
  review clocks, outcome aggregates, and performance history;
- raw market, research, news, or provider data without redistribution rights;
- raw chat transcripts or exported conversation context.

Publicly available facts are not automatically licensed for republication.
Provider terms and redistribution rights still apply.

## Artifact rule

Generated CIO reports belong in an approved durable private artifact store. Git
tracks their schemas, templates, and generator contracts—not the reports
themselves. Temporary sandbox or download links may be a convenience, but they
are never the durable source of truth.

If persistence fails, the run records a degraded or failed persistence outcome,
discloses it to the user, and preserves as much of the decision product as is
safely possible. A persistence failure must not be hidden by calling the report
complete.

## Change coordination

A public contract change that affects MarinoTerminal should identify:

1. the old and new contract version;
2. compatibility and migration impact;
3. the corresponding private implementation work;
4. the verification required before production claims the new contract.

No private implementation detail needs to be copied here to document that
coordination.

## If uncertain

Do not commit the material. Open a public issue only if the question itself can
be stated without sensitive context; otherwise ask the repository owner through
a private channel.

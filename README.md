# Marino CIO Office

This repository is the public-safe operating foundation for the Marino CIO
Office. It preserves the system's shared vocabulary, quality rules, artifact
contracts, templates, architecture decisions, and roadmap in version control.

The private MarinoTerminal repository remains the production application. This
repository does not duplicate that codebase and is not a storage location for
live investment data or generated reports.

## Purpose

The Marino CIO Office is designed to turn diverse research inputs into a
traceable daily decision product. Its operating principles are:

- decisions before commentary;
- visible timestamps, provenance, freshness, and coverage;
- explicit uncertainty and honest provisional status;
- independent Chief Historian and Chief Skeptic review;
- fresh-idea discovery with repeat-idea tracking;
- disciplined timing and sizing through the Marino Capital Deployment System;
- durable private artifact persistence and a feedback loop.

## Repository scope

Versioned here:

- the implementation-neutral CIO operating model;
- public-safe schemas and report templates;
- architecture decisions and contribution rules;
- synthetic examples and lightweight validation;
- a phased roadmap for moving chat-born specifications into durable records.

Kept private and out of Git history:

- MarinoTerminal source, deployment configuration, and credentials;
- proprietary prompts, ranking weights, and provider adapters;
- client, household, account, portfolio, tax, estate, or insurance information;
- actual investment decisions, generated reports, logs, and historical memory;
- raw or licensed data that is not approved for redistribution.

See [the public/private boundary](docs/public-private-boundary.md) and
[security policy](SECURITY.md) before adding content.

## Canonical contracts

- [CIO operating model](docs/operating-model.md)
- [Canonical contract vocabulary](docs/contract-vocabulary.md)
- [Report manifest schema](schemas/v1/report-manifest.schema.json)
- [Investment idea schema](schemas/v1/investment-idea.schema.json)
- [Decision record schema](schemas/v1/decision-record.schema.json)
- [Daily decision report template](templates/daily-decision-report.md)
- [Roadmap](ROADMAP.md)
- [Architecture decisions](docs/decisions/README.md)

## Repository map

| Path | Purpose |
| --- | --- |
| `docs/` | Operating model, boundaries, and durable decisions |
| `schemas/v1/` | Versioned public artifact contracts |
| `templates/` | Human-readable report and decision templates |
| `examples/synthetic/` | Fictional examples with no live or licensed data |
| `scripts/` | Repository-only validation tooling |
| `.github/` | Review and read-only CI configuration |

## Working agreement

1. Read `AGENTS.md` and the public/private boundary before making changes.
2. Use synthetic data only.
3. Update a schema, its template, and its example together.
4. Record architectural or boundary changes as an Architecture Decision Record
   (ADR).
5. Run `python3 scripts/validate.py` before committing.
6. Never call incomplete, stale, or materially under-covered work complete.

## Status

Baseline version: `0.1.0`. The repository currently defines governance and
contracts; it does not claim to contain a standalone production reporting
engine.

## Rights and disclaimer

Copyright (c) 2026 Matt Marino. All rights reserved. No open-source license or
reuse permission is granted at this time.

This repository describes research operations and software interfaces. It is
not investment, tax, legal, or insurance advice and provides no warranty of
data accuracy, completeness, or fitness for a particular purpose.

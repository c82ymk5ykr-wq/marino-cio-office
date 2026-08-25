# Architecture decisions

This directory records durable decisions about repository scope, public
contracts, status semantics, and architecture.

Use a new zero-padded file such as `0002-short-title.md` and start from
[`templates/architecture-decision.md`](../../templates/architecture-decision.md).
Decision records are append-only historical context: supersede an accepted
decision with a new record rather than silently rewriting its rationale.

## Index

| ID | Status | Decision |
| --- | --- | --- |
| [0001](0001-public-operating-foundation.md) | Accepted | Establish a public operating foundation separate from private production |
| [0002](0002-canonical-contract-vocabulary.md) | Accepted | Adopt one canonical public vocabulary while keeping private mappings private |
| [0003](0003-deterministic-universe-completion-gates.md) | Accepted | Require deterministic full-universe gates for completion claims |
| [0004](0004-verifiable-idea-lineage.md) | Accepted | Define verifiable idea lineage and anti-staleness metrics |
| [0005](0005-v1-schema-compatibility-gate.md) | Accepted | Make v1 backward compatibility an executable gate |
| [0006](0006-deterministic-report-acceptance.md) | Accepted | Add deterministic report acceptance and manifest 1.1 |
| [0007](0007-private-contract-adoption-attestation.md) | Accepted | Attest private contract adoption without publishing mappings |

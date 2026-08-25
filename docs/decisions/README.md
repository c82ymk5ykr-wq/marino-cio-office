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

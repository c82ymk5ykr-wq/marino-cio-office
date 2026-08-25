# Public specification inventory

- Inventory revision: `1.0.0`
- Completed: 2026-08-25
- Scope: public-safe Marino CIO Office operating outcomes

This inventory removes the public contract's dependence on conversation
history. It records normalized outcomes and their durable public sources—not
the source conversations, private inventory, or private implementation.

## Method

1. Review accessible decision sources in an approved private workspace.
2. Normalize only implementation-neutral outcomes that belong on the public
   side of the repository boundary.
3. Link each outcome to an accepted Architecture Decision Record (ADR), schema,
   template, policy, synthetic fixture, or validator.
4. Resolve public ambiguity through a durable record rather than quoting or
   silently rewriting prior wording.
5. Do not infer or reconstruct unavailable decisions.

Material outside the public boundary is omitted rather than named or
summarized. The governing boundary is
[`public-private-boundary.md`](public-private-boundary.md).

## Durable outcome inventory

| Public operating outcome | Durable source | Verification |
| --- | --- | --- |
| The public repository is an implementation-neutral contract, separate from private production | [ADR 0001](decisions/0001-public-operating-foundation.md) and [public/private boundary](public-private-boundary.md) | Repository paths and validation rules exclude private production material |
| The CIO product is decision-first and completes honestly when inputs fail | [CIO operating model](operating-model.md) | Lifecycle and report-status sections define useful degraded output and truthful failure |
| Chief Historian review precedes Chief Skeptic review and the CIO disposition | [CIO operating model](operating-model.md) | Decision lifecycle fixes the public sequence and responsibility |
| Research boards are Fresh Idea Discovery, Core Conviction Monitor, and Rejected Idea Board | [CIO operating model](operating-model.md) and [investment-idea schema](../schemas/v1/investment-idea.schema.json) | Schema enums match the three research boards |
| The Capital Deployment Board is a deployment view, not an idea-board enum | [Canonical vocabulary](contract-vocabulary.md) and [daily report template](../templates/daily-decision-report.md) | Research board and deployment sections remain separate |
| Marino Capital Deployment System behavior remains separate from research quality | [CIO operating model](operating-model.md), [CIO decision schema](../schemas/v1/decision-record.schema.json), and [CIO decision template](../templates/decision-record.md) | Research disposition, readiness, action, timing, size band, and scaling plan are distinct fields |
| Evidence provenance uses `PASTED`, `INLINE`, and `CIO_LEVEL_INFERENCE` | [CIO operating model](operating-model.md), [report schema](../schemas/v1/report-manifest.schema.json), and [idea schema](../schemas/v1/investment-idea.schema.json) | Exact case-sensitive enum values are versioned |
| Generation time, evidence time, retrieval time, and review time are not interchangeable | [Canonical vocabulary](contract-vocabulary.md) and [ADR 0002](decisions/0002-canonical-contract-vocabulary.md) | Field clocks and UTC serialization rules are explicit |
| Report outcome, source health, freshness, idea lifecycle, CIO disposition, deployment, and persistence are separate axes | [Canonical vocabulary](contract-vocabulary.md) and [ADR 0002](decisions/0002-canonical-contract-vocabulary.md) | Public field dictionary and non-overloading rule define each axis |
| Private consumers conform to public semantics without publishing aliases or mappings | [ADR 0002](decisions/0002-canonical-contract-vocabulary.md) | Public result is limited to `conforms`, `public_contract_gap`, or `private_migration_needed` |
| A bounded-universe ranking is complete only at 100% unique eligible evaluation, zero gaps, and zero required-period lag | [Universe completion gates](universe-completion-gates.md) and [ADR 0003](decisions/0003-deterministic-universe-completion-gates.md) | [Synthetic truth table](../examples/synthetic/universe-completion-cases.json) and validator derive all four report outcomes |
| Minimum runtime readiness is not universe completion | [Universe completion gates](universe-completion-gates.md) | Separate runtime-readiness section and negative synthetic case prevent equivalence |
| Required source, review, freshness, and durable persistence gates control `complete` | [Report acceptance gates](report-acceptance-gates.md), [ADR 0006](decisions/0006-deterministic-report-acceptance.md), and [report schema](../schemas/v1/report-manifest.schema.json) | [Synthetic truth table](../examples/synthetic/report-acceptance-cases.json) derives every status and rejects contradictory claims |
| A URL or filesystem path is never durable report-persistence evidence | [Public/private boundary](public-private-boundary.md), [report acceptance gates](report-acceptance-gates.md), and [daily report template](../templates/daily-decision-report.md) | Report-manifest 1.1 requires a non-sensitive opaque receipt token and persistence time; failed or unattempted outcomes cannot claim either |
| Routine refreshes and rewritten commentary do not make an old idea fresh | [Idea lineage metrics](idea-lineage-metrics.md) and [ADR 0004](decisions/0004-verifiable-idea-lineage.md) | Version 1.1 idea classifications and fictional fixtures distinguish data recency from idea novelty |
| Verified repeats require a reason; missing lineage is unverified and never reconstructed | [Idea lineage metrics](idea-lineage-metrics.md) and [investment-idea schema](../schemas/v1/investment-idea.schema.json) | Classification-specific validator rules and negative checks enforce the policy |
| Outcome review is append-only and does not rewrite the ex-ante decision | [Outcome-review contract](outcome-review-contract.md) and [ADR 0008](decisions/0008-append-only-outcome-review.md) | Separate review schema, fictional cases, and cross-record validation preserve decision identity and independent assessment axes |
| Public examples are visibly fictional and contract changes remain compatible within v1 | [Agent rules](../AGENTS.md), [schema compatibility policy](schema-compatibility-policy.md), and [repository validator](../scripts/validate.py) | CI validates Draft 2020-12 conformance, retained v1 fixtures, historical enum and boundary values, then cross-record, lineage, and boundary rules |

## Normalized ambiguities

| Ambiguous shorthand | Durable resolution |
| --- | --- |
| “Complete” versus “ready” | `complete` is the full report gate; runtime or deployment readiness is a separate qualified state |
| “Fresh data” versus “fresh idea” | Data recency, current-cycle refresh, new coverage, and idea novelty are separate concepts |
| “Decision record” | `docs/decisions/` contains public ADRs; operational research decisions use the CIO decision-record contract |
| “Status” | Every status is qualified by report, source, freshness, lifecycle, deployment, or artifact axis |
| “Board” | The idea schema has three research boards; the Capital Deployment Board is a report view |

## Phase 1 disposition

- Canonical public terms are versioned and privately conformance-reviewed.
- Supported-universe completion thresholds are explicit and executable through
  fictional truth-table cases.
- Repeat-idea and anti-staleness metrics have versioned lineage semantics,
  formulas, denominators, and zero-case behavior.
- Every public-safe outcome identified in the review is linked above or already
  governed by the repository boundary and contribution rules.
- No absent decision was reconstructed, and no raw conversation or private
  implementation detail was moved into Git history.

Future schema enforcement, private adapters, and outcome-learning interfaces
remain in the later roadmap phases.

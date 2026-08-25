# CIO operating model

## Mission

The Marino CIO Office converts heterogeneous investment research into a
decision-first, traceable product. It favors useful completion with transparent
limitations over silent failure, false precision, or unsupported certainty.

This document defines public operating behavior. It intentionally omits private
prompts, ranking weights, provider adapters, positions, and implementation code.

## Decision lifecycle

1. **Collect research inputs.** Gather approved macro, market, fundamental,
   technical, positioning, income, risk, and event evidence.
2. **Normalize provenance.** Record source identity, retrieval time, data time,
   availability, and whether evidence is pasted, generated inline, or inferred
   at the CIO level.
3. **Apply the data-quality gate.** Measure expected versus observed coverage,
   freshness, source failures, and fallbacks before interpreting results.
4. **Develop the boards.** Maintain Fresh Idea Discovery, Core Conviction
   Monitor, and Rejected Idea Board entries with first-seen and last-seen times.
5. **Run Chief Historian review.** Compare the setup with prior patterns,
   decisions, invalidations, and known failure modes.
6. **Run Chief Skeptic review.** State the strongest countercase, missing
   evidence, crowding or regime risk, and what would disprove the thesis.
7. **Set the CIO disposition.** Advance, monitor, hold, or reject the research
   case; do not imply a deployment action merely because research advances.
8. **Run the Marino Capital Deployment System.** Decide readiness, timing,
   sizing band, scaling plan, prerequisites, and exit or invalidation rules.
9. **Publish and persist privately.** Produce the manifest and report, record the
   durable persistence outcome, and preserve any failure without relying on a
   temporary link as the source of truth.
10. **Review outcomes.** Feed approved private lessons back through the Chief
    Historian and future process decisions.

## Canonical roles and capabilities

| Role or capability | Public responsibility |
| --- | --- |
| CIO | Synthesizes evidence, resolves conflicts, and owns the final disposition |
| Chief Historian | Tests the current setup against prior outcomes and process mistakes |
| Chief Skeptic | Builds the strongest countercase and identifies missing evidence |
| Marino Capital Deployment System | Separates idea quality from timing, sizing, scaling, and exit discipline |
| Institutional Trend Model | Assesses trend condition and confirmation without replacing fundamental work |
| Feeder research capabilities | Produce attributable macro, sector, fundamental, technical, quantitative, income, sentiment, liquidity, geopolitical, and risk inputs |

Private implementations may use multiple specialized agents or services for a
capability. This public contract governs the resulting evidence, not the private
prompt or model used to create it.

## Canonical boards

### Fresh Idea Discovery

New or newly material research candidates. Every entry records `first_seen_at`,
`last_seen_at`, evidence lineage, and why it is fresh. A repeated idea must state
what changed or why repetition remains decision-useful.

### Core Conviction Monitor

Existing high-priority research cases whose thesis, risks, catalysts,
invalidation conditions, and deployment status require ongoing review.

### Rejected Idea Board

Ideas rejected or deferred with a reason, evidence gap, invalidation, and any
condition that would justify reconsideration. Rejection history is institutional
memory, not clutter to discard.

### Capital Deployment Board

The timing and sizing layer. It distinguishes research disposition from an
action such as initiate, add, trim, exit, or no action.

## Provenance labels

| Label | Meaning |
| --- | --- |
| `PASTED` | Evidence was supplied as an existing approved input |
| `INLINE` | Evidence was produced during the current run from identified inputs |
| `CIO_LEVEL_INFERENCE` | The CIO synthesized or inferred the conclusion from cited evidence |

Every material claim should be traceable to a source or clearly labeled
inference. A fallback is disclosed as a fallback, not presented as the preferred
source.

## Report status

| Status | Meaning |
| --- | --- |
| `complete` | All required coverage, freshness, source, review, and persistence gates passed |
| `provisional` | The product is useful, but required coverage or freshness remains incomplete |
| `degraded` | A material source or persistence failure occurred; the usable result and failure are both disclosed |
| `failed` | No reliable decision product could be completed; the manifest still records why |

Status is produced from evidence. It is never a cosmetic label. A broad-universe
ranking cannot move from provisional to complete solely because a page loaded or
a scan job ran; expected coverage, observed coverage, source health, freshness,
and persistence must satisfy the defined gate.

## Required report invariants

Every report manifest must:

- identify its schema version and stable report ID;
- separate `generated_at` from the market or source `data_as_of` time;
- state expected and observed coverage and any known gaps;
- record freshness and the oldest material source time;
- enumerate failed, stale, fallback, and unavailable sources;
- identify quality flags and unresolved limitations;
- link the ideas and decisions included in the report;
- record whether the artifact reached durable private storage;
- complete honestly even if a source or persistence step fails.

The report itself should lead with decisions, then show the evidence, reviews,
deployment implications, risks, and data-quality disclosures that support them.

# Marino CIO Office — Daily Decision Report

> Public template only. Populate and persist real reports in an approved private
> system. Do not commit completed reports to this repository.

## Report control

| Field | Value |
| --- | --- |
| Report ID | `<stable-report-id>` |
| Schema version | `1.0.0` |
| Investment-idea schema version | `<1.0.0 | 1.1.0>` |
| Generated at (UTC) | `<YYYY-MM-DDTHH:MM:SSZ>` |
| Data as of (UTC) | `<YYYY-MM-DDTHH:MM:SSZ>` |
| Status | `<complete | provisional | degraded | failed>` |
| Universe gate profile | `<broad_equity_daily | curated_etf_daily | declared_bounded_set>` |
| Membership as of (UTC) | `<YYYY-MM-DDTHH:MM:SSZ>` |
| Required period | `<latest required market or source period>` |
| Expected / observed coverage | `<expected> / <observed>` |
| Freshness | `<fresh | stale | unknown>` |
| Durable persistence | `<persisted | failed | not_attempted>` |

## Executive decision board

State the decisions first. Separate research disposition from deployment action
and identify the evidence that matters most today.

| Priority | Idea ID | Research disposition | Deployment action | Confidence | Why now |
| --- | --- | --- | --- | --- | --- |
| 1 | `<idea-id>` | `<advance | monitor | hold | reject>` | `<no_action | initiate | add | trim | exit>` | `<low | medium | high>` | `<concise reason>` |

## Macro regime and market state

- Regime: `<state and confidence>`
- Change since prior report: `<material change or no material change>`
- Supporting evidence: `<source IDs and provenance labels>`
- Disconfirming evidence: `<what does not fit>`

## Fresh Idea Discovery

For each idea, include first seen, last seen, why it is fresh, thesis, regime fit,
catalysts, risks, invalidation conditions, horizon, and evidence lineage.

### Idea lineage register

| Idea ID | Lineage status | Classification | First seen | Last seen | Last material change | Repeat count | Changed dimensions | Repeat rationale |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `<idea-id>` | `<verified | unverified>` | `<new | repeat_unchanged | materially_updated | reintroduced | stale_repeat | unverified>` | `<UTC>` | `<UTC>` | `<UTC or unavailable>` | `<count or unavailable>` | `<dimensions or none>` | `<reason or not applicable>` |

### Anti-staleness metrics

Publish raw counts, numerator, denominator, and rate. Use `not_available` for a
zero denominator and disclose unverified or unknown exclusions.

| Metric | Numerator / denominator | Rate |
| --- | --- | ---: |
| New-idea rate | `<N / V>` | `<percent or not_available>` |
| Repeat rate | `<R / V>` | `<percent or not_available>` |
| Explained-repeat rate | `<X / R>` | `<percent or not_available>` |
| Strict material-update rate | `<M / R>` | `<percent or not_available>` |
| Decision-changing-repeat rate | `<(M + RI) / R>` | `<percent or not_available>` |
| Stale-repeat rate | `<S / R>` | `<percent or not_available>` |
| Unverified-lineage share | `<U / C>` | `<percent or not_available>` |
| Stale-evidence share | `<E / K>` | `<percent or not_available>` |

Also disclose repeat count, median repeat age, maximum repeat age, and unknown
evidence count/share. Do not publish targets, quotas, alerts, live rates, or
performance in this public template.

## Core Conviction Monitor

For each monitored idea, state what strengthened, weakened, or remained
unchanged. Explain repetition rather than restating the prior thesis.

## Rejected Idea Board

Record the rejection or deferral reason, missing evidence, invalidation, and the
condition that would justify reconsideration.

## Chief Historian review

- Relevant prior setup or process lesson: `<summary>`
- Similarities and differences: `<comparison>`
- Historical failure mode to avoid: `<risk>`

## Chief Skeptic review

- Strongest countercase: `<countercase>`
- Missing or weak evidence: `<gap>`
- Crowding, regime, or behavioral risk: `<risk>`
- What would disprove the base case: `<test>`

## Capital Deployment Board

| Idea ID | Readiness | Action | Timing/confirmation | Size band | Scaling plan | Exit/invalidation |
| --- | --- | --- | --- | --- | --- | --- |
| `<idea-id>` | `<not_ready | ready | blocked>` | `<action>` | `<requirements>` | `<band, not account data>` | `<stages>` | `<rules>` |

## Portfolio and systemic risks

Describe public-safe risk categories only. Real holdings, allocations, client
constraints, and performance remain private.

## Data quality and source register

| Source ID | Provenance | Data as of | Retrieved at | Status | Fallback or failure disclosure |
| --- | --- | --- | --- | --- | --- |
| `<source-id>` | `<PASTED | INLINE | CIO_LEVEL_INFERENCE>` | `<UTC>` | `<UTC>` | `<available | fallback | stale | unavailable>` | `<detail>` |

List coverage gaps, stale inputs, unavailable sources, and every material
fallback. The narrative and top-level status must agree with this section.

State the deterministic universe-gate result separately from minimum runtime
readiness. A page load, completed job, non-empty result, or usable subset does
not establish full universe completion. Apply
[`docs/universe-completion-gates.md`](../docs/universe-completion-gates.md).

## Persistence outcome

- Durable store status: `<persisted | failed | not_attempted>`
- Opaque private artifact reference: `<reference or omitted>`
- Failure and retry note: `<detail or none>`

## Follow-ups and next review

- `<owner-free action or evidence request>`
- Next review by: `<YYYY-MM-DDTHH:MM:SSZ>`

## Disclosure

This is an internal research decision product, not investment, tax, legal, or
insurance advice. Data may be delayed, incomplete, or incorrect; status and
quality disclosures control over narrative confidence.

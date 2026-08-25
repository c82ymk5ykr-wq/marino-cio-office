# Roadmap

This roadmap uses outcomes rather than promised dates.

## Phase 0 — Public foundation

- [x] Establish the public/private repository boundary.
- [x] Record the canonical CIO operating model and vocabulary.
- [x] Add versioned report, idea, and decision contracts.
- [x] Add synthetic examples and repository validation.

Exit condition: a future contributor can understand the system's public
contract and make a safe, validated change without relying on chat history.

## Phase 1 — Specification inventory

- [ ] Convert remaining chat-born operating decisions into focused issues or
      architecture decisions.
- [x] Reconcile field names with the private MarinoTerminal implementation.
- [x] Define explicit completion thresholds for each supported universe.
- [x] Define repeat-idea and anti-staleness metrics.

Exit condition: important behavior is referenced by a versioned decision or
contract, and public terminology does not drift from the private implementation.

## Phase 2 — Quality gates

- [ ] Add fuller JSON Schema example validation.
- [ ] Add compatibility tests for schema changes.
- [ ] Define report acceptance checks for freshness, coverage, failed sources,
      and durable persistence.

Exit condition: a report can be labeled complete only through deterministic,
testable gates.

## Phase 3 — Private integration

- [ ] Map public contracts to private production adapters without exposing
      proprietary logic or data.
- [ ] Add contract-version reporting to the private dashboard and artifacts.
- [ ] Verify that degraded sources still yield an honest, usable report.

Exit condition: private systems consume a named public contract version and
surface contract failures clearly.

## Phase 4 — Learning loop

- [ ] Define private outcome-review and decision-attribution interfaces.
- [ ] Measure idea novelty, repeat quality, timing discipline, and invalidations.
- [ ] Feed approved lessons into Chief Historian review and future decisions.

Exit condition: lessons become versioned operating improvements without moving
private decisions or performance history into this repository.

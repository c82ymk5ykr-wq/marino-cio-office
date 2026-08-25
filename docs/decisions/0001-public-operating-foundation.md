# 0001 — Public operating foundation

- Status: Accepted
- Date: 2026-08-25
- Owners: Marino CIO Office

## Context

Important CIO reporting, dashboard, agent-role, freshness, and persistence
decisions had accumulated across conversations. The target repository was public
and empty, while the production MarinoTerminal application already lived in a
separate private repository.

Copying production code, reports, prompts, or conversation history into a public
repository would create privacy, intellectual-property, licensing, and security
risk. Leaving the repository empty would preserve the existing continuity
problem.

## Decision

Use this repository as the public-safe, implementation-neutral source of truth
for:

- the CIO operating model and canonical vocabulary;
- schemas, templates, and synthetic examples;
- architecture decisions, contribution policy, and roadmap;
- lightweight repository validation.

Keep MarinoTerminal code, proprietary methods, live data, actual reports,
decisions, credentials, and deployment state in approved private systems.

No open-source license is granted in the initial baseline. Public visibility is
not treated as permission for reuse.

## Consequences

Positive:

- future work can reference durable contracts instead of reconstructing them
  from chat history;
- public documentation can be reviewed without exposing private operations;
- private implementations can declare the contract version they consume;
- status, freshness, coverage, provenance, and persistence semantics become
  explicit and testable.

Costs and constraints:

- public and private changes require deliberate coordination;
- generated artifacts and actual decisions cannot be archived here;
- proprietary implementation behavior still needs a private source of truth;
- a future reuse license requires an explicit owner decision.

## Follow-up

- Inventory remaining chat-born specifications as focused decisions or issues.
- Reconcile the public schema fields with private production output.
- Enable repository security settings and protect `main` after the initial CI
  check succeeds.

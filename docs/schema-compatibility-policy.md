# Schema compatibility policy

- Policy version: `1.0.0`
- Status: Accepted

This policy defines backward compatibility for the public artifact contracts in
`schemas/v1/`. It applies only to the public contract. Private payloads, aliases,
storage representations, and adapters have their own private migration process.

## Compatibility promise

A current v1 schema must continue to accept every documented-valid artifact
retained in the append-only v1 compatibility corpus. Each published artifact
`schema_version` remains explicitly declared by its schema.

Backward compatibility is not forward compatibility: an older schema is not
required to accept fields introduced by a later, compatible v1 revision.

## Compatible changes within v1

Examples include:

- adding an optional field;
- adding a new independent artifact family at `1.0.0` when existing contracts
  do not depend on it;
- adding a new `1.x.0` artifact revision while preserving prior version branches;
- adding conditional requirements that apply only to the new revision;
- clarifying descriptions without changing field meaning; and
- tightening validation only for artifacts that were never documented as valid.

## Breaking changes

The following require a new schema directory such as `schemas/v2/`, an ADR,
migration notes, and private-consumer conformance review:

- removing a published artifact version;
- adding an unconditional required field to an existing revision;
- removing or renaming an existing field;
- changing an existing field's type or meaning;
- removing an allowed enum value; or
- narrowing an accepted boundary so a retained valid artifact is rejected.

## Executable gate

[`tests/compatibility/v1-fixtures.json`](../tests/compatibility/v1-fixtures.json)
is an append-only, visibly fictional compatibility floor. CI checks that:

1. every retained fixture validates against the current schema;
2. every published v1 artifact revision is represented;
3. historical enum values and selected boundary values remain accepted; and
4. deliberately malformed artifacts remain rejected.

The corpus is a strong regression gate, not a formal proof that every possible
historical JSON instance remains valid. Semantic reinterpretation and private
migration impact still require human review.

The additive `outcome-review 1.0.0` family does not revise the existing
`report-manifest`, `investment-idea`, or `decision-record` families. Its
own retained fixtures become part of the same append-only v1 compatibility
floor.

## Corpus maintenance

- Never rewrite a retained fixture to make an incompatible schema pass.
- Add a fixture when a compatible artifact revision or materially distinct
  valid branch is published.
- Use only fixed, synthetic identifiers, dates, sources, and content.
- Keep invalid mutations in test code rather than as artifact fixtures.
- Breaking changes start a new versioned corpus alongside the new schema family.

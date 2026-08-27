# Canonical contract vocabulary

This document defines the implementation-neutral terms used by the public
Marino CIO Office contracts. The JSON schemas remain authoritative for field
shape and allowed values; this glossary is authoritative for meaning.

The **public contract** is the operating model, schemas, templates, and accepted
Architecture Decision Records (ADRs) collectively. The repository baseline
version describes repository maturity; an artifact's `schema_version` describes
its exact serialized contract. They are not interchangeable.

Private consumers may use internal aliases, but they must map them to these
semantics without changing their meaning. Private aliases, payloads, and mapping
tables do not belong in this repository.

## Non-overloading rule

Status words describe one axis only. A value on one axis must not be copied to
another axis or used as evidence that another gate passed.

| Axis | Public field | Meaning |
| --- | --- | --- |
| Report outcome | `report-manifest.status` | Result of the complete report-quality gate |
| Source health | `sources[].status` | Availability of one source for this run |
| Aggregate freshness | `freshness.status` | Recency of the oldest material input under the applicable freshness policy |
| Idea lifecycle | `investment-idea.research_state` | Current workflow state of a research idea |
| CIO research decision | `decision-record.research_disposition` | Point-in-time research judgment, not a trade instruction |
| Deployment readiness | `decision-record.deployment.readiness` | Whether timing and confirmation prerequisites permit consideration of an action |
| Deployment action | `decision-record.deployment.action` | The action selected by the deployment process |
| Artifact outcome | `report-manifest.artifact.status` | Whether the report reached approved durable private storage |
| Evidence provenance | `provenance` | How evidence entered the current decision product |
| Review assessability | `outcome-review.review_assessability` | Whether retained history supports an assessable, partial, unavailable, or unknown review |
| Review evidence quality | `outcome-review.evidence_quality` | Verification state of evidence used by the review |
| Research outcome | `outcome-review.research_outcome` | Qualitative thesis-relevant observation, not investment performance |
| Decision quality | `outcome-review.decision_quality` | Quality of the ex-ante judgment given information then available |
| Process quality | `outcome-review.process_quality` | Discipline of the declared decision process |
| Timing discipline | `outcome-review.timing_discipline` | Discipline of timing prerequisites, separate from outcome and deployment |
| Invalidation trigger | `outcome-review.invalidation_trigger.state` | Whether the original invalidation condition was observed |
| Invalidation response | `outcome-review.invalidation_response.state` | Qualitative handling of the trigger state |
| Decision attribution | `outcome-review.attribution` | Evidence-linked qualitative associations without causal or numeric contribution claims |
| Lesson lifecycle | `historian-lesson.state` | Whether one immutable lesson revision is active or retires its series |
| Lesson approval | `historian-lesson.approval.status` | Human authorization of one exact immutable lesson-control revision, including retirement |
| Lesson ingestion | `historian-lesson.ingestion.status` | Acknowledgement that the approved version entered Chief Historian review, not execution authority |

`complete`, `ready`, `advance`, and `high` never mean recommended, suitable for
a client, or authorized for deployment. Research disposition and deployment
remain separate decisions.

## Report outcomes

| Value | Canonical meaning |
| --- | --- |
| `complete` | Every required coverage, freshness, source, review, and persistence gate passed for the declared report contract |
| `provisional` | The product is useful, but a required coverage, period, freshness, review, or not-attempted persistence gate remains incomplete without a material source or failed-persistence outcome |
| `degraded` | A required source is unavailable, a non-equivalent fallback is used, or persistence failed; the usable result and failure are both disclosed |
| `failed` | No reliable decision product could be completed; the manifest still records the failure |

A required-source or failed-persistence outcome makes `degraded` take
precedence over `provisional`, even when coverage is also incomplete.

A page load, job completion, non-empty result, or minimum runtime-readiness
check is not sufficient evidence for `complete`.

## Time semantics

All contract timestamps are RFC 3339 date-times in UTC and end in `Z`.

| Field | Canonical clock |
| --- | --- |
| `generated_at` | When the report artifact was assembled |
| `data_as_of` | The market or evidence cutoff represented by the artifact |
| `sources[].data_as_of` | The effective time of one source's information |
| `sources[].retrieved_at` | When that source was obtained for the run |
| `sources[].checked_at` | When source availability and status were evaluated for a report-manifest 1.1 run |
| `oldest_material_source_as_of` | The earliest effective time among the required-role source IDs used to evaluate the report decision |
| `membership_as_of` | When the declared eligible-universe membership was fixed |
| `artifact.persisted_at` | When durable private persistence completed |
| `first_seen_at` | First recorded appearance of a stable idea lineage |
| `last_seen_at` | Most recent recorded appearance of that lineage in the current record |
| `recorded_at` | When a CIO decision record was created |
| `review_by` | Deadline for the next required review |
| `clocks.decision_recorded_at` | Creation time of the immutable ex-ante decision linked by an outcome review |
| `clocks.evaluation_started_at` | Start of the outcome-observation interval |
| `clocks.evidence_cutoff_at` | Latest effective evidence time considered by an outcome review |
| `clocks.reviewed_at` | Finalization time of the append-only outcome review |
| `invalidation_trigger.triggered_at` | Observed time of a triggered invalidation condition |
| `invalidation_response.responded_at` | Observed response time for a followed or delayed invalidation response |
| `historian-lesson.clocks.data_as_of` | Evidence cutoff represented by one lesson control revision |
| `historian-lesson.clocks.approved_at` | Time an authorized human approved the exact lesson revision |
| `historian-lesson.clocks.ingested_at` | Time Chief Historian ingestion acknowledged that exact revision |
| `historian-lesson.clocks.generated_at` | Time the finalized append-only lesson control was assembled |

Generation, evidence, retrieval, persistence, universe-membership, and cycle
completion are different clocks. A future contract field for one of these
clocks must name it explicitly rather than reusing an existing timestamp.

## Presence and unknown values

- Required fields are present and non-null.
- Optional fields are omitted when they do not apply; empty strings are not
  substitutes for unknown values.
- Unknown quality is represented by an explicit contract value such as
  `freshness.status: unknown` or by a documented quality flag.
- Missing history is not reconstructed. It is reported as unavailable,
  unknown, unverified, or not applicable by the applicable contract.
- Counts and percentages are measurements, not confidence scores.

## Report manifest field dictionary

| Field | Meaning |
| --- | --- |
| `schema_version` | Semantic version of the public artifact contract; 1.1 adds deterministic acceptance evidence while retaining 1.0 compatibility |
| `report_id` | Stable identifier for one report artifact |
| `report_type` | Declared class of report and therefore the applicable required gates |
| `generated_at` | Artifact-assembly time, as defined above |
| `data_as_of` | Overall evidence cutoff, as defined above |
| `status` | Report outcome only |
| `status_reason` | Concise evidence-based explanation of the report outcome |
| `coverage.universe` | Name of the declared population being measured |
| `coverage.expected` | Contract denominator expected under the applicable universe definition; `0` is the report-manifest 1.1 sentinel when the denominator is unknown |
| `coverage.observed` | Unique eligible members successfully evaluated with all observations required by the applicable gate; it is not a raw fetch or listing count, and is `0` when the 1.1 denominator is unknown |
| `coverage.percent` | `observed / expected * 100` when expected is positive; `0` is used for an empty or unknown denominator and is not an independent estimate |
| `coverage.gaps` | Known missing members or public-safe gap descriptions; never a constituent dump |
| `freshness.status` | Aggregate freshness outcome only |
| `freshness.oldest_material_source_as_of` | Oldest material evidence time |
| `freshness.threshold_hours` | Declared wall-clock threshold when an hour-based freshness policy applies |
| `sources[].source_id` | Stable, non-secret identifier for one approved input |
| `sources[].category` | Public evidence family |
| `sources[].provenance` | `PASTED`, `INLINE`, or `CIO_LEVEL_INFERENCE` |
| `sources[].data_as_of` | Effective information time for the source |
| `sources[].retrieved_at` | Retrieval time for the run |
| `sources[].checked_at` | Required in report-manifest 1.1; time at which source status was checked |
| `sources[].status` | `available`, `fallback`, `stale`, or `unavailable` for that source only |
| `sources[].note` | Required disclosure of role, limitation, fallback, or failure |
| `quality_flags` | Machine-readable unresolved quality conditions |
| `idea_ids` | Stable idea identifiers included in the report |
| `decision_ids` | Stable decision identifiers included in the report |
| `gate_inputs.reliable_product` | Whether a decision-useful product exists; `false` has highest status precedence and yields `failed` |
| `gate_inputs.completion_profile_id` | Public completion profile governing the bounded universe |
| `gate_inputs.denominator_known` | Whether expected universe membership is known for the required period |
| `gate_inputs.membership_as_of` | Membership-freeze time when the denominator is known; omitted otherwise |
| `gate_inputs.required_period` | Provider-neutral identifier for the required evaluation period |
| `gate_inputs.required_period_lag_known` | Whether required-period lag could be established for the run |
| `gate_inputs.required_period_lag` | Count of required periods by which the evaluation lags; omitted when lag is unknown |
| `gate_inputs.gap_count` | Count of missing eligible evaluations when the denominator is known; omitted otherwise and may exceed the number of summarized public gap descriptions |
| `gate_inputs.required_reviews_complete` | Whether every report-type-required review completed |
| `gate_inputs.source_roles[]` | Provider-neutral gate evidence for membership, observations, and freshness roles |
| `artifact.status` | Durable private persistence outcome only |
| `artifact.durable_reference` | Non-sensitive opaque receipt token; optional in 1.0 and required for a persisted 1.1 artifact; never a credential, URI, or filesystem path |
| `artifact.persisted_at` | Report-manifest 1.1 durable persistence completion time |
| `artifact.note` | Persistence explanation or failure detail |

An expected denominator of zero is not automatically full coverage. Empty or
unknown universes require an explicit gate rule and cannot silently produce a
`complete` broad-universe product.

When more than one source condition applies, v1 uses the safety-first precedence
`unavailable` over `stale` over `fallback` over `available`. Secondary
conditions remain visible in `sources[].note` and `quality_flags`. In
report-manifest 1.1, unavailable sources omit evidence and retrieval times while
retaining `checked_at`; unknown aggregate freshness omits the oldest-material
time. Version 1.0 remains unchanged for compatibility.

Required source-role state is more specific than raw source health. A raw
`fallback` maps to either `equivalent_fallback` or
`non_equivalent_fallback` in `gate_inputs.source_roles[]` based on the
predeclared completion policy. Every source ID linked from one role has the raw
status implied by that role state; a failed preferred source that was not used
to fulfill the role remains an unlinked, disclosed source record. Private
provider mappings remain private.

## Investment idea field dictionary

| Field | Meaning |
| --- | --- |
| `schema_version` | Semantic version of the idea contract |
| `idea_id` | Stable identifier for one idea lineage, not a daily row identifier |
| `first_seen_at` | First recorded appearance of the lineage |
| `last_seen_at` | Most recent recorded appearance represented by the record |
| `board` | Public research board on which the idea currently belongs |
| `research_state` | Current idea lifecycle state; it is not a CIO disposition or deployment readiness |
| `asset.symbol` | Public instrument symbol or visibly fictional synthetic symbol |
| `asset.name` | Public instrument name or visibly fictional synthetic name |
| `asset.asset_type` | Public asset-class category |
| `thesis` | Decision-useful research case |
| `regime_fit` | Relationship between the thesis and the stated market regime |
| `catalysts` | Events or conditions that could advance the thesis |
| `risks` | Material countervailing conditions |
| `invalidation_conditions` | Observable conditions that would disprove or retire the thesis |
| `time_horizon` | Research evaluation horizon, not a promised holding period |
| `timing_notes` | Timing evidence or prerequisites without account-level instructions |
| `confidence` | Qualitative confidence in the research case, not a probability or size recommendation |
| `evidence[].source_id` | Source identifier supporting the claim |
| `evidence[].provenance` | How the evidence entered the decision product |
| `evidence[].claim` | Claim supported or inferred from the identified evidence |
| `lineage.status` | Whether retained history verifies the lineage classification |
| `lineage.classification` | Mutually exclusive new, repeat, material-update, reintroduction, stale-repeat, or unverified state |
| `lineage.last_material_change_at` | Most recent verified decision-changing change |
| `lineage.repeat_count` | Verified appearances after the first, including the current repeat |
| `lineage.changed_dimensions` | Material dimensions changed in the current appearance |
| `lineage.verification_note` | Explanation required when retained history cannot support a classification |
| `repeat_reason` | Decision-useful explanation required by policy when an idea materially repeats |

`board` permits the three research boards only: Fresh Idea Discovery, Core
Conviction Monitor, and Rejected Idea Board. The Capital Deployment Board is a
report view over deployment decisions, not an investment-idea `board` value.

## Decision record field dictionary

| Field | Meaning |
| --- | --- |
| `schema_version` | Semantic version of the decision contract |
| `decision_id` | Stable identifier for one recorded decision |
| `idea_id` | Stable idea lineage to which the decision applies |
| `recorded_at` | Decision-record creation time |
| `research_disposition` | CIO research judgment only |
| `deployment.readiness` | Timing and prerequisite readiness only |
| `deployment.action` | Selected action, including explicit `no_action` |
| `deployment.timing_and_confirmation` | Evidence required before or around deployment |
| `deployment.size_band` | Public-safe policy band; never client or account data |
| `deployment.scaling_plan` | Staged implementation policy without live allocations |
| `rationale` | Evidence-based reason for the decision |
| `historian_note` | Relevant prior setup or process lesson |
| `skeptic_countercase` | Strongest disconfirming case |
| `alternatives_considered` | Material alternative dispositions or actions reviewed |
| `invalidation_conditions` | Conditions requiring reassessment or exit from the research case |
| `review_by` | Next required review deadline |
| `evidence_ids` | Evidence records supporting the decision |
| `historian_lesson_version_refs` | Decision-record 1.1 exact lesson versions materially used in Chief Historian review; an empty array means none applied |

## Outcome-review field dictionary

| Field | Meaning |
| --- | --- |
| `schema_version` | Semantic version of the independent outcome-review contract |
| `review_id` | Stable opaque identifier for one finalized append-only review |
| `prior_review_ref` | Optional opaque link to the immediately prior review; it never mutates or replaces it |
| `links.decision_ref` | Opaque private reconciliation token for the immutable ex-ante decision |
| `links.idea_ref` | Opaque private reconciliation token for the linked idea lineage |
| `links.evidence_refs` | Complete register of opaque evidence tokens referenced by the review |
| `clocks.*` | The ordered decision, evaluation-start, evidence-cutoff, and review-finalization clocks defined above |
| `review_assessability` | Whole-review state: `assessable`, `partial`, `unavailable`, or `unknown` |
| `evidence_quality` | Retained-evidence state: `verified`, `partial`, `unavailable`, or `unverified` |
| `research_outcome` | Independent qualitative `favorable`, `mixed`, or `adverse` research observation when assessable |
| `decision_quality` | Independent qualitative `sound`, `mixed`, or `unsound` ex-ante decision assessment |
| `process_quality` | Independent qualitative `disciplined`, `mixed`, or `undisciplined` process assessment |
| `timing_discipline` | Independent qualitative timing assessment; may be not applicable |
| `invalidation_trigger` | Trigger state and, only when triggered, its observed time and evidence links |
| `invalidation_response` | Response state and, only when followed or delayed, its observed time and evidence links |
| `attribution.assessment_state` | Whether qualitative attribution is assessable, partial, unavailable, unknown, or not applicable |
| `attribution.factors[].category` | Public qualitative factor family |
| `attribution.factors[].direction` | `supporting`, `detracting`, `mixed`, or `unclear` association |
| `attribution.factors[].confidence` | `low`, `medium`, or `high` qualitative confidence |
| `attribution.factors[].evidence_refs` | Opaque evidence tokens supporting the association |

The original decision record is never rewritten with these fields. Outcome
does not derive decision, process, or timing quality. Attribution is not causal
proof, investment-performance attribution, or a numeric contribution model.
See the [outcome-review contract](outcome-review-contract.md) for the full state
and lifecycle rules.

## Learning-loop measurement vocabulary

| Term | Meaning |
| --- | --- |
| Frozen idea cohort | At most one metric-eligible `investment-idea 1.1.0` record per stable idea ID at the private cutoff |
| Frozen decision cohort | Distinct target decision references selected before review-chain resolution |
| Metric eligible | A contract-valid input whose retained history supports the named measurement; ineligible inputs remain counted as exclusions |
| Terminal review | The only review in one valid identity-consistent append-only chain that has no successor at the cutoff |
| Missing history | No retained review exists for the target decision |
| Invalid history | A retained target review fails the adopted outcome-review contract |
| Unresolved history | A chain is dangling, cyclic, branched, cross-identity, duplicated, or has no unique terminal |
| `not_available` | A rate or aggregate whose denominator is zero; it is never silently serialized as measured zero |

Every private rate retains its exact raw numerator and denominator. Repeat
quality is a profile of disclosed counts and rates, never a weighted score.
Research outcome, timing discipline, invalidation trigger, and invalidation
response remain independent measurement axes.

## Chief Historian lesson field dictionary

| Field | Meaning |
| --- | --- |
| `schema_version` | Version of the metadata-only lesson control contract |
| `lesson_series_id` | Opaque stable identity for one append-only lesson series |
| `lesson_version_ref` | Opaque exact reference for one immutable series revision |
| `revision` | Consecutive revision number; gaps and branches are invalid |
| `prior_version_ref` | Exact immediately prior revision in the same series; omitted only for revision 1 |
| `state` | `active` for advisory eligibility or `retired` for an append-only terminal tombstone |
| `source_reviews` | Opaque finalized review references and copied finalization clocks used for private reconciliation |
| `content_ref` | Opaque reference to immutable private lesson content; required only for an active revision |
| `approval` | Human-approval status, authority class, and opaque receipt for this exact revision |
| `ingestion` | Successful advisory-only Chief Historian ingestion acknowledgement, mode, and opaque receipt |
| `clocks` | Ordered evidence, approval, ingestion, and artifact-generation times for this revision |

The lesson body, approval identity, receipt mappings, and catalog remain
private. Approval and ingestion do not execute the lesson, prove that it is
correct, or authorize a research disposition or deployment action.

## Private conformance review

Conformance with a private consumer is reviewed outside this repository. The
public result may record only one of these dispositions:

- `conforms`: the private consumer preserves the public meaning;
- `public_contract_gap`: a public concept is missing or ambiguous and requires
  a versioned public change;
- `private_migration_needed`: the public contract is sufficient and the private
  consumer must adapt.

The public result must not disclose a private field name, alias, payload, code
path, endpoint, provider adapter, or migration implementation.

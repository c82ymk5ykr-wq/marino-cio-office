# Chief Historian lesson control

> Store every real/private populated control and lesson body privately. This
> public template documents metadata only. Never paste a real lesson, review,
> decision, receipt, identity, mapping, storage reference, usage record, or
> production change here.

- Schema version: `1.0.0`
- Lesson series ID: `<opaque hls_ token>`
- Lesson version reference: `<opaque hlv_ token>`
- Revision: `<positive integer>`
- State: `<active | retired>`
- Prior version reference: `<required exact hlv_ token for revision N > 1>`
- Content reference: `<active only; opaque ref_ token>`

## Finalized source reviews

Repeat for every linked finalized review:

- Review reference: `<opaque orv_ token>`
- Finalized at: `<UTC timestamp ending in Z>`

Do not include a review body, outcome, attribution, decision, or private mapping.

## Lifecycle clocks

- Data as of: `<UTC timestamp ending in Z>`
- Approved at: `<UTC timestamp ending in Z>`
- Ingested at: `<UTC timestamp ending in Z>`
- Generated at: `<UTC timestamp ending in Z>`

Required order:
`data_as_of <= approved_at <= ingested_at <= generated_at`

Every linked review must be finalized no later than `approved_at`.

## Human approval

- Authority type: `human`
- Status: `approved`
- Approval receipt: `<new opaque apr_ token for this exact revision>`

Approval identity and receipt resolution remain private.

## Advisory ingestion

- Status: `ingested`
- Ingestion receipt: `<new opaque ing_ token for this exact revision>`
- Mode: `advisory_only`

Ingestion makes the exact revision eligible for Chief Historian review. It does
not execute the lesson or edit prompts, code, configuration, schemas,
thresholds, weights, historical decisions, or deployment actions.

## Append-only rule

- Revision 1 is active, omits `prior_version_ref`, and has content.
- Revision N points to exact revision N-1 in the same series.
- A revised active revision has a new content reference and new receipts.
- A retired revision is a new approved and ingested tombstone with no content.
- Never mutate, delete, branch, skip, or silently relabel a revision.

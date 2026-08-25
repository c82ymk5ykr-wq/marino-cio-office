# Outcome review

> Store every populated review privately. This template documents the public
> contract only. Never paste a real decision, outcome, evidence item, date,
> performance result, client or account field, or private mapping here.

- Schema version: `1.0.0`
- Review ID: `<opaque orv_ token>`
- Prior review reference: `<optional opaque orv_ token>`
- Decision reference: `<opaque ref_ token>`
- Idea reference: `<opaque ref_ token>`
- Evidence references: `<opaque ref_ tokens only>`

## Lifecycle clocks

- Decision recorded at: `<UTC timestamp ending in Z>`
- Evaluation started at: `<UTC timestamp ending in Z>`
- Evidence cutoff at: `<UTC timestamp ending in Z>`
- Reviewed at: `<UTC timestamp ending in Z>`

Required order:
`decision_recorded_at <= evaluation_started_at <= evidence_cutoff_at <= reviewed_at`

## Review evidence

- Assessability: `<assessable | partial | unavailable | unknown>`
- Evidence quality: `<verified | partial | unavailable | unverified>`

Describe missing or uncertain history; never reconstruct it.

## Research outcome

- Assessment state:
  `<assessable | partial | unavailable | unknown>`
- Classification when assessable or partial:
  `<favorable | mixed | adverse>`
- Evidence references: `<declared opaque refs>`
- Note: `<qualitative thesis-relevant observation; no performance fields>`

## Decision quality

- Assessment state: `<assessable | partial | unavailable | unknown>`
- Classification when assessable or partial: `<sound | mixed | unsound>`
- Evidence references: `<declared opaque refs>`
- Note: `<assessment against information available ex ante>`

## Process quality

- Assessment state: `<assessable | partial | unavailable | unknown>`
- Classification when assessable or partial:
  `<disciplined | mixed | undisciplined>`
- Evidence references: `<declared opaque refs>`
- Note: `<qualitative process assessment>`

## Timing discipline

- Assessment state:
  `<assessable | partial | unavailable | unknown | not_applicable>`
- Classification when assessable or partial:
  `<disciplined | mixed | undisciplined>`
- Evidence references: `<declared opaque refs>`
- Note: `<qualitative timing assessment; no deployment action>`

## Invalidation trigger

- State:
  `<not_triggered | triggered | ambiguous | unknown | not_applicable>`
- Triggered at: `<required only when triggered; UTC ending in Z>`
- Evidence references: `<declared opaque refs>`
- Note: `<qualitative trigger assessment without private rule text>`

## Invalidation response

- State:
  `<followed | delayed | not_followed | ambiguous | unknown | not_applicable>`
- Responded at: `<required only when followed or delayed; UTC ending in Z>`
- Evidence references: `<declared opaque refs>`
- Note: `<qualitative response assessment without deployment action>`

## Qualitative attribution

- Assessment state:
  `<assessable | partial | unavailable | unknown | not_applicable>`
- Attribution note: `<review-level limitation or synthesis>`

Repeat this factor block for each factor when assessable or partial:

- Factor category:
  `<research_thesis | evidence_quality | decision_process | timing_discipline | invalidation_handling | external_conditions | other>`
- Direction: `<supporting | detracting | mixed | unclear>`
- Confidence: `<low | medium | high>`
- Evidence references: `<one or more declared opaque refs>`
- Factor note: `<uncertainty-aware association, never causal or numeric>`

A favorable result does not prove a sound decision. An adverse result does not
prove an unsound decision. Attribution is not performance attribution.

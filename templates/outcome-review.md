# CIO outcome review

> Store every populated review privately. This template documents the public
> contract only and must never contain real decisions or performance history.

- Schema version: `1.0.0`
- Review ID: `<opaque-review-id>`
- Supersedes review ID: `<optional opaque prior-review-id; omit for an original review>`
- Decision ID: `<opaque-decision-id>`
- Idea ID: `<opaque-idea-id>`
- Reviewed at (UTC): `<YYYY-MM-DDTHH:MM:SSZ>`

## Evaluation boundary

- Assessability: `<assessable | partial | unavailable>`
- Ex-ante basis: `<verified | partial | unverified>`
- Evidence quality: `<sufficient | limited | conflicting | unavailable | unverified>`
- Evaluation started at (UTC): `<YYYY-MM-DDTHH:MM:SSZ; omit when permitted and unknown>`
- Evaluation ended at (UTC): `<YYYY-MM-DDTHH:MM:SSZ; omit when permitted and unknown>`
- Evidence cutoff at (UTC): `<YYYY-MM-DDTHH:MM:SSZ; omit when permitted and unknown>`

## Independent assessments

- Research outcome: `<favorable | mixed | adverse | indeterminate | not_applicable>`
- Decision quality: `<well_supported | mixed_support | weakly_supported | unassessable>`
- Process quality: `<disciplined | mixed | undisciplined | unassessable>`
- Timing discipline: `<followed | partially_followed | not_followed | unassessable | not_applicable>`
- Assessment note: `<qualitative evidence-based explanation; no performance data>`

## Invalidation

- Trigger state: `<not_triggered | triggered | ambiguous | unknown | not_applicable>`
- Response state: `<not_required | followed | delayed | not_followed | unknown | not_applicable>`
- Evidence IDs: `<opaque identifiers>`
- Note: `<qualitative explanation>`

## Qualitative attribution

For each factor:

- Factor ID: `<opaque-factor-id>`
- Category: `<thesis | evidence | catalyst | regime | timing | risk | invalidation | process | other>`
- Direction: `<supporting | detracting | mixed | neutral | unknown>`
- Confidence: `<low | medium | high>`
- Evidence IDs: `<opaque identifiers>`
- Note: `<association only; no causal or numeric contribution claim>`

## Evidence and limitations

- Review evidence IDs: `<opaque identifiers>`
- Limitations: `<missing, conflicting, unavailable, or unverified evidence>`

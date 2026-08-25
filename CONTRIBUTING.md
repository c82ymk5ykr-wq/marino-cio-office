# Contributing

This public repository accepts changes to documentation, schemas, templates,
synthetic examples, and repository validation only.

## Before opening a change

- Confirm the material belongs on the public side of
  [the repository boundary](docs/public-private-boundary.md).
- Use fictional, synthetic examples. Do not redact real client or portfolio data
  and present it as synthetic.
- Check that any third-party material may be redistributed.
- Make schema changes backward compatible within `schemas/v1/`.
- Add a decision record for architectural, boundary, or status-semantic changes.

## Validation

Run:

```bash
python3 scripts/validate.py
```

The validation checks required files, JSON syntax, synthetic-example contract
basics, relative Markdown links, conflict markers, and forbidden tracked paths.

## Pull-request checklist

- [ ] No credentials, private URLs, client information, holdings, reports, or
      licensed data are included.
- [ ] Examples are visibly fictional and synthetic.
- [ ] Timestamps distinguish generation time from data time.
- [ ] Coverage, freshness, source failure, and persistence status remain honest.
- [ ] Schemas, templates, examples, and docs were updated together where needed.
- [ ] `python3 scripts/validate.py` passes.

The initial repository bootstrap may be committed directly to `main`. Routine
follow-on changes should use focused pull requests.

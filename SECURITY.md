# Security policy

## Public-repository data policy

This repository accepts only public-safe documentation, schemas, templates,
validation code, and fully synthetic examples.

Do not submit:

- passwords, tokens, keys, cookies, credentials, or private endpoints;
- client, household, portfolio, account, tax, estate, insurance, or performance
  information;
- real generated reports, chat exports, internal logs, or historical memory;
- proprietary prompts, ranking weights, private adapters, or production config;
- market or provider data without explicit redistribution rights.

Public branches, pull requests, tags, Actions logs, and Git LFS are public too.
`.gitignore` is a convenience, not a security control.

## Reporting a vulnerability or exposure

Do not open a public issue containing vulnerability details or sensitive data.
Use GitHub Private Vulnerability Reporting when it is available, or contact the
repository owner privately.

If a credential is exposed, revoke or rotate it first. Deleting the file in a
later commit does not remove it from Git history. If private information enters
the repository, stop further distribution and coordinate a history rewrite and
cache review with the repository owner.

## Supported scope

Security reports about the public contracts and validation workflow are in
scope here. Reports about MarinoTerminal or another private production system
must be handled through that system's private channel.

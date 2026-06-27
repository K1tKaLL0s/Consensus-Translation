# Security Policy

## Supported Versions

Security fixes are handled on the default branch until a formal version support policy is published.

## Reporting a Vulnerability

Open a private report through GitHub security advisories if available, or contact the maintainer without posting secrets publicly.

Do not include real API keys, provider tokens, credential files, private translation text, or local user data in public issues.

## Sensitive Data Rules

- Provider secrets must stay in the local credential store.
- Diagnostics, logs, screenshots, and exported artifacts must not reveal API keys or private credentials.
- Mock providers must remain isolated from production release paths.
- Runtime, cache, build, release, and local data directories should not be committed.

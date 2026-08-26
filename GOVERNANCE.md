# Governance

This project is currently maintained under a BDFL-lite model: Linda Oraegbunam is the founding
maintainer with final say on scope, releases, and architectural direction, but decisions are
made in the open on GitHub Issues and PRs.

This is deliberately lightweight while the project is young. As contributors demonstrate
sustained, good-judgment involvement (merged PRs implementing real adapters/scorers, active
review participation), the intent is to move toward a small maintainers group with commit
access. That transition isn't on a fixed timeline — it happens when there are enough trusted
regulars — and will be documented here when it happens.

## How decisions get made

- **New contracts/objectives/perturbers/adapters**: proposed via issue, implemented via PR,
  reviewed against the honesty bar in ARCHITECTURE.md (does it correctly fail/report
  "not satisfied" on missing data, or silently pass?).
- **Breaking changes to core interfaces** (Program, Contract, Objective, Compiler signatures):
  require an issue discussion before a PR.
- **Releases**: semantic versioning, CHANGELOG.md updated per release.

## What does this PR do?

<!-- Plain description of the change and why it's needed. If it fixes a bug,
say what was actually broken and how a user/contributor would have hit it. -->

## Related issue

Closes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation / translation
- [ ] Refactor (no behavior change)

## Checklist

- [ ] I have read [CONTRIBUTING.md](https://github.com/obielin/reliopt/blob/main/CONTRIBUTING.md)
- [ ] If this is a new feature or architecture change, I opened an issue first (bug fixes and docs are exempt — send those straight in)
- [ ] If this is a new Contract/Objective, tests cover: satisfied case, violated case, and "no data available" case (must report unsatisfied/0, never silently pass)
- [ ] `ruff check .` passes
- [ ] `mypy src/` passes
- [ ] `pytest tests/ -v` passes — run locally, not just assumed from CI
- [ ] `python examples/rag_demo.py` still runs and produces sensible output, if this PR touches contracts/objectives/compiler
- [ ] ARCHITECTURE.md's "What's real" / "What's stubbed" split updated if this PR moves something from one list to the other
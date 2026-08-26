# Contributing to reliopt

Thanks for considering a contribution. This project's core loop
(Program → Contracts → Objectives → Perturbation → Pareto compiler) works
end-to-end today, but most of the individual scorers, perturbers, and
adapters are intentionally thin — see `ARCHITECTURE.md`'s "What's stubbed"
section for the honest list of where the highest-value work is.

## Dev setup

```bash
git clone <this repo>
cd reliopt
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python examples/rag_demo.py   # confirm the end-to-end demo still runs
```

## Where to start

Check `ARCHITECTURE.md` → "Good entry points for new contributors" first.
The single highest-value contribution right now is a `ComponentAblator` for
`dspy.Module` — see `src/reliopt/attribution/engine.py` for the
interface it needs to satisfy.

## Adding a contract scorer

Built-in contracts (`Contract.groundedness`, `.schema_valid`, `.tool_scope`,
`.abstain_when_unsupported`) all expect specific fields on each run record
(`groundedness_score`, `schema_error`, `tools_used`, `should_abstain`/
`abstained`) that only domain-specific logic can compute. If you're adding
support for a new domain:

1. Write an `enrich_fn(record) -> record` that populates the field(s) your
   contract needs, following `examples/rag_demo.py`'s
   `enrich_with_groundedness` as a template.
2. If the check itself is genuinely new (not just a new way to compute
   `groundedness_score`), add a new `Contract.your_check(...)` factory in
   `contracts/base.py`, following the existing pattern.
3. Test with all three cases: satisfied, violated, and "no data available"
   (should report unsatisfied/False, never silently pass).

## Adding a perturber

Implement the `Perturber` protocol in `perturbation/engine.py` — a callable
taking an example dict and returning a `Perturbation`. Deterministic,
free perturbers (like the two built-ins) can go straight into
`DEFAULT_PERTURBERS`. LLM-based perturbers (paraphrase, adversarial
injection) should be opt-in and clearly documented as incurring API cost per
compile run — do not add them to `DEFAULT_PERTURBERS`.

## Adding a search strategy

`Compiler`'s v0.1 search is grid/explicit search over a `config_space`. A
smarter strategy (bayesian optimization, evolutionary search, or delegating
to a DSPy teleprompter for the prompt/demo dimensions specifically) should
be a new class implementing the same `.run(trainset=...) -> CompileResult`
interface, not a rewrite of `Compiler` itself — open an issue to discuss
approach before a large PR here.

## Adding a Program adapter (LangGraph, pydantic-ai, etc.)

Look at `program.py`'s `_invoke` method — it currently special-cases
`dspy.Module`-style `.forward()`. A new adapter should follow the same
pattern: detect the target type, know how to invoke it and extract a
result, and populate `TrajectoryStep`s as richly as the underlying framework
allows (this is also where sub-call-level tracing, currently a gap, would
first get implemented for a specific framework rather than generically).

## Attribution cost considerations

`run_attribution` runs the full trainset once per ablatable component
(linear, not combinatorial) — but for large trainsets/programs this is still
real API cost. If you're implementing a `ComponentAblator`, document in your
PR roughly how many extra program executions a typical use produces.

## Code style

- Python 3.10+, type hints on public functions.
- `ruff check .` / `ruff format .` before pushing.
- `mypy src/` should pass on new code.
- Keep the zero-mandatory-dependency core — optional adapters/perturbers
  needing a new dependency should be an extra, not a default import.

## Pull requests

- Scope PRs to one contract/perturber/adapter/strategy at a time.
- Include tests: the true-positive / true-negative pattern from
  `tests/test_end_to_end.py` is the template — show your addition doing the
  right thing AND correctly failing/rejecting when it should.
- Update `ARCHITECTURE.md`'s "What's real" / "What's stubbed" split if your
  PR moves something from one list to the other — keeping that document
  honest is part of the review bar, not an afterthought.

## Code of Conduct

See `CODE_OF_CONDUCT.md`.

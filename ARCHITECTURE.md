# Architecture

## Pipeline

```
Program (wraps arbitrary callable / dspy.Module)
        │
        ▼
Contracts (hard/soft gates)  +  Objectives (dials to optimise)
        │
        ▼
Compiler
  ├─ candidate configs (explicit list, or grid search over config_space)
  ├─ Perturbation engine (stress-test variants of trainset)
  ├─ per-candidate: run trainset + perturbations → records
  ├─ enrich_fn hook (domain-specific fields: groundedness_score, tools_used, ...)
  ├─ score Objectives, evaluate Contracts
        │
        ▼
Pareto frontier (non-dominated candidates satisfying all strict contracts)
        │
        ▼
CompileResult → .select(profile) / .evidence_card(id) / .render_table()
```

Attribution (component ablation) is a separate module, not yet wired into
`Compiler`/`EvidenceCard` automatically, but with a working implementation for
`Pipeline`-structured programs — see `src/reliopt/attribution/` and the
"What's real" section below.

## What's real today (v0.1)

- `Program`: wraps plain callables and duck-typed `dspy.Module`-style objects
  (anything with `.forward()`). Traces exactly one `TrajectoryStep` per call —
  the call boundary, not sub-calls inside the wrapped program.
- `Contract`: base class + five built-ins (`groundedness`, `schema_valid`,
  `tool_scope`, `abstain_when_unsupported`, `wilson_lower_bound`). The first
  four depend on fields (`groundedness_score`, `schema_error`, `tools_used`,
  `should_abstain`/`abstained`) that only YOUR domain logic can compute —
  wire them in via `Compiler(enrich_fn=...)`. Without an enrich_fn, these
  contracts correctly report "not satisfied" (no silent pass) rather than
  doing nothing useful. `wilson_lower_bound` is a generic rate-based
  contract: it gates on the lower bound of the Wilson score interval for any
  boolean field, rather than the raw observed proportion, so a threshold
  can't be cleared on a lucky small sample. `abstain_when_unsupported`
  internally reuses `wilson_lower_bound` for its correct/relevant rate
  rather than gating on the raw rate, for the same reason.
- `Objective`: base class + four built-ins (`accuracy`, `cost`, `latency`,
  `consistency`). `consistency` needs `repeat_n > 1` on the Compiler to mean
  anything — with `repeat_n=1` it always returns 1.0, which is a "not
  measured" placeholder, not a real reliability signal. Don't ship
  `consistency` results to a user without repeats.
- `Perturbation` engine: two deterministic, free (no API calls) perturbers —
  `ReorderClausesPerturber`, `InjectDistractorSentencePerturber`. These are
  illustrative defaults, not serious adversarial coverage. Real robustness
  testing needs domain-specific (often LLM-generated) perturbers — see
  CONTRIBUTING.md "Adding a perturber."
- `Compiler`: grid/explicit search over a user-supplied `config_space` or
  `candidates` list, via a `configure_fn(program, config) -> Program` you
  provide. This is NOT automatic prompt/demonstration optimization like
  DSPy's teleprompters — it searches whatever config knobs you expose.
- `Pareto` frontier + `CompileResult.select(profile)` + `.evidence_card()`:
  fully working, no placeholders. Candidates violating any `strict=True`
  contract are excluded from the frontier entirely (not soft-penalized).
- **Attribution for `Pipeline` programs, wired into `Compiler`**: `Pipeline`
  (`src/reliopt/pipeline.py`) is a dependency-free program primitive — an
  ordered list of named `(name, callable)` steps, each step's output feeding
  the next, the whole thing callable so it drops into `Program`.
  `PipelineAblator` (`src/reliopt/attribution/pipeline_ablator.py`)
  implements the `ComponentAblator` protocol against it: `components()`
  returns the step names (and raises `TypeError`, not `[]`, for a
  non-`Pipeline` program); `ablate()` returns a deep-copied `Pipeline` with
  the named step swapped for a passthrough. This is **zero-ablation** — the
  step is stubbed out with a no-op that returns its input unchanged, *not*
  literally removed, and the step count / wiring is unchanged.
  `Compiler(attribution=True)` (opt-in, default `False`) runs this for every
  candidate whose configured program wraps a `Pipeline`, on the nominal
  trainset only (no perturbations, so the cost stays "one extra full eval per
  component," not that multiplied by perturbation count too), and
  `CompileResult.evidence_card()` surfaces the result via
  `EvidenceCard.attribution`. It's opt-in rather than automatic specifically
  because it isn't free — see `Compiler.attribution`'s docstring. A candidate
  whose program isn't a `Pipeline` is not silently skipped:
  `Candidate.attribution_skipped_reason` / `EvidenceCard.attribution_skipped_reason`
  say why. Run it standalone via `run_attribution()`, or through
  `compile()`; see `examples/attribution_demo.py` for both. Note the scope:
  available for `Pipeline`-structured programs only — a plain `Program`
  wrapping an opaque callable still has no enumerable internal components
  (see "What's stubbed").

## What's stubbed / seams-only

- **Attribution beyond `Pipeline`**: `PipelineAblator` handles native
  `Pipeline` programs and is wired into `Compiler(attribution=True)` (see
  "What's real"), but there's still no `ComponentAblator` for the opaque
  program types — `dspy.Module` sub-modules, LangGraph nodes, raw tool-use
  loops — where the internal structure isn't expressed as a `Pipeline`. This
  is the project's deepest research contribution — see the README's framing —
  and the highest-value place for a substantial contribution (or for Linda's
  own research work specifically).
- **Failure clustering**: `EvidenceCard.failure_clusters` exists as a field
  but nothing populates it yet. v0.2 scope: cluster failed records (e.g. by
  embedding similarity of the input, or by which contract/objective failed)
  and report cluster sizes.
- **LangGraph / pydantic-ai / raw tool-use adapters**: `Program` only
  supports plain callables and duck-typed `dspy.Module`s today.
- **Richer trajectory tracing**: sub-calls inside a wrapped program (e.g. a
  dspy.Module's internal retriever → reranker → generator steps) aren't
  individually traced — only the outer call boundary is. This limits both
  attribution (can't ablate what you can't see) and cost/latency breakdown
  by component.

## Design principles worth preserving

1. **No weighted-sum scalar.** Objectives stay a vector; Pareto dominance
   decides the frontier. Don't add a "just give me one score" shortcut that
   quietly reintroduces arbitrary weights — that's the thing this project
   exists to avoid (see README).
2. **Contracts gate, Objectives dial.** Don't blur these — a contract
   violation removes a candidate from consideration regardless of how well
   it scores elsewhere; an objective never does.
3. **Don't require rebuilding the agent in this framework.** `Program` is a
   thin adapter, not a new way to write agents. New adapters should wrap,
   not replace.
4. **Be honest about placeholders.** Every scorer that needs data it can't
   itself produce (groundedness, schema validity, tool scope, consistency
   without repeats) should fail loudly/report "not satisfied" or "not
   measured" rather than defaulting to an optimistic silent pass. This bit
   the project once already in `examples/rag_demo.py`'s first draft — keep
   it from happening again in real usage.

## Good entry points for new contributors

- Implement a `ComponentAblator` for `dspy.Module` (enumerate named
  sub-modules, ablate by replacing with a passthrough) — this is the single
  highest-value contribution possible right now.
- Add an LLM-based perturber (paraphrase, adversarial injection) behind a
  clearly-marked "costs API calls" flag.
- Implement failure clustering for `EvidenceCard.failure_clusters`.
- Add a LangGraph `Program` adapter.

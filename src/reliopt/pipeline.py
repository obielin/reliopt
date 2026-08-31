"""
Pipeline — a minimal, dependency-free program primitive with *decomposable*
internal structure.

`Program` (see program.py) wraps a single opaque callable: it traces the one
call boundary and cannot see inside. That's fine for running and scoring, but
it leaves component attribution (see attribution/engine.py) with nothing to
enumerate or ablate — there are no named parts.

`Pipeline` fills that gap without pulling in an agent framework. It is an
ordered list of named steps, run sequentially: the pipeline's inputs are
passed as keyword arguments to the first step, and each step's return value is
passed as the single positional argument to the next step. The final step's
return value is the pipeline's output.

A `Pipeline` is itself callable, so it drops straight into `Program`:

    from reliopt import Program
    from reliopt.pipeline import Pipeline

    pipe = Pipeline([
        ("retrieve", retrieve),   # retrieve(question=...) -> docs
        ("rerank", rerank),       # rerank(docs) -> docs
        ("generate", generate),   # generate(docs) -> answer
    ])
    program = Program(pipe)

`Program._invoke` sees `Pipeline.__call__(**inputs)` (a VAR_KEYWORD signature)
and calls `pipe(**inputs)` directly — see program.py's `_invoke` for the exact
dispatch.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


def passthrough(*args: Any, **kwargs: Any) -> Any:
    """
    Identity step used for zero-ablation (see attribution/pipeline_ablator.py):
    returns its input unchanged.

    A pipeline step receives exactly one logical value — either the single
    positional argument handed down from the previous step, or (for the first
    step) the pipeline's keyword inputs. This returns that value untouched so
    the surrounding steps still run but this step contributes nothing.
    """
    if args and not kwargs:
        return args[0] if len(args) == 1 else args
    if kwargs and not args:
        return next(iter(kwargs.values())) if len(kwargs) == 1 else dict(kwargs)
    if not args and not kwargs:
        return None
    # Both positional and keyword args: nothing sensible to "pass through".
    return {"args": args, "kwargs": dict(kwargs)}


class Pipeline:
    """
    An ordered sequence of named, callable steps.

    Each entry is an ``(name, callable)`` pair. Names must be unique — they are
    what `PipelineAblator` enumerates and targets.
    """

    def __init__(self, steps: Iterable[tuple[str, Callable[..., Any]]]):
        materialised = [(name, fn) for name, fn in steps]
        if not materialised:
            raise ValueError("Pipeline requires at least one step")
        names = [name for name, _ in materialised]
        if len(set(names)) != len(names):
            raise ValueError(f"Pipeline step names must be unique, got {names!r}")
        for name, fn in materialised:
            if not callable(fn):
                raise TypeError(f"Pipeline step {name!r} is not callable: {fn!r}")
        self.steps: list[tuple[str, Callable[..., Any]]] = materialised

    @property
    def names(self) -> list[str]:
        """The ordered list of step names."""
        return [name for name, _ in self.steps]

    def __call__(self, **inputs: Any) -> Any:
        """
        Run every step in order. The first step is called with ``**inputs``;
        each later step is called with the previous step's return value as its
        single positional argument. Returns the last step's return value.
        """
        value: Any = None
        for index, (_name, fn) in enumerate(self.steps):
            if index == 0:
                value = fn(**inputs)
            else:
                value = fn(value)
        return value

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Pipeline({self.names!r})"

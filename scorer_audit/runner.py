"""Run labelled cases through Inspect AI's real solver -> scorer pipeline.

Each case is one sample. A mock model returns the case's completion verbatim,
so every grade comes from the same code path users hit in a real eval.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from math import isnan
from typing import Any

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import (
    Scorer,
    answer,
    choice,
    exact,
    includes,
    match,
    math,
    model_graded_qa,
    pattern,
)
from inspect_ai.solver import Solver, generate, multiple_choice

CASE_TAG = re.compile(r"\[case:([A-Za-z0-9_.\-]+)\]")


@dataclass(frozen=True)
class Case:
    """One labelled grading decision.

    Attributes:
        id: Unique, stable identifier.
        scorer: Key into SCORERS.
        target: Reference answer(s).
        completion: Exact model output to grade.
        expected: "C" if a careful human grader would mark it correct, else "I".
        category: Failure family the case probes.
        source: Issue URL the case reproduces, or "systematic".
        choices: Answer options for multiple-choice scorers.
        grader_output: Text the grader model returns (model_graded_qa only).
        note: Why the label is what it is, when not obvious.
    """

    id: str
    scorer: str
    target: str | list[str]
    completion: str
    expected: str
    category: str
    source: str = "systematic"
    choices: list[str] | None = None
    grader_output: str | None = None
    note: str = ""


# scorer key -> (solver factory, scorer factory)
SCORERS: dict[str, tuple[Callable[[], Solver], Callable[[], Scorer]]] = {
    "match": (generate, lambda: match()),
    "match_numeric": (generate, lambda: match(numeric=True)),
    "includes": (generate, lambda: includes()),
    "exact": (generate, lambda: exact()),
    "answer_letter": (generate, lambda: answer("letter")),
    "answer_word": (generate, lambda: answer("word")),
    "answer_line": (generate, lambda: answer("line")),
    "pattern_answer": (generate, lambda: pattern(r"ANSWER:\s*(.+)")),
    "math": (generate, lambda: math()),
    "multiple_choice": (multiple_choice, lambda: choice()),
    "model_graded_qa": (generate, lambda: model_graded_qa()),
}


@dataclass
class Result:
    case: Case
    actual: str
    answer: str | None
    error: str | None = None

    @property
    def credited(self) -> bool:
        return self.actual == "C"

    @property
    def misgraded(self) -> bool:
        """Credit disagrees with the label. NOANSWER and INCORRECT both mean no credit."""
        return self.error is None and self.credited != (self.case.expected == "C")

    @property
    def direction(self) -> str:
        """false_pass: wrong answer credited; false_fail: right answer denied."""
        if not self.misgraded:
            return ""
        return "false_pass" if self.credited else "false_fail"


def _lookup(table: dict[str, str]) -> Callable[..., ModelOutput]:
    def respond(messages: list[Any], *_: Any) -> ModelOutput:
        text = "\n".join(m.text for m in messages)
        found = CASE_TAG.search(text)
        if found is None:
            raise RuntimeError("mock model received a prompt without a case tag")
        return ModelOutput.from_content(model="mockllm", content=table[found.group(1)])

    return respond


def _normalise(value: Any) -> str:
    """Map a score value to C, I, N (no answer), P (partial) or U (unscored, e.g. NaN)."""
    if value in ("C", "I", "N", "P"):
        return str(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and isnan(value):  # scorer declined to grade
            return "U"
        return "C" if float(value) >= 1.0 else "I"
    return str(value)


def run_cases(cases: list[Case]) -> list[Result]:
    """Grade every case and return one Result per case, in input order."""
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case ids must be unique")

    results: dict[str, Result] = {}
    by_scorer: dict[str, list[Case]] = {}
    for case in cases:
        by_scorer.setdefault(case.scorer, []).append(case)

    for key, group in by_scorer.items():
        solver_factory, scorer_factory = SCORERS[key]
        samples = [
            Sample(
                id=c.id,
                input=f"[case:{c.id}] Answer the question.",
                target=c.target,
                choices=c.choices,
            )
            for c in group
        ]
        model = get_model(
            "mockllm/model",
            custom_outputs=_lookup({c.id: c.completion for c in group}),
            memoize=False,
        )
        model_roles = None
        if key == "model_graded_qa":
            grader = get_model(
                "mockllm/grader",
                custom_outputs=_lookup({c.id: c.grader_output or "" for c in group}),
                memoize=False,
            )
            model_roles = {"grader": grader}

        task = Task(dataset=samples, solver=solver_factory(), scorer=scorer_factory())
        [log] = eval(
            task,
            model=model,
            model_roles=model_roles,
            log_dir="logs",
            display="none",
            fail_on_error=False,
            score_display=False,
        )
        for sample in log.samples or []:
            case = next(c for c in group if c.id == sample.id)
            if sample.error is not None:
                results[case.id] = Result(case, "E", None, sample.error.message)
                continue
            score = next(iter((sample.scores or {}).values()), None)
            if score is None:
                results[case.id] = Result(case, "E", None, "no score")
                continue
            results[case.id] = Result(case, _normalise(score.value), score.answer)

    return [results[i] for i in ids]

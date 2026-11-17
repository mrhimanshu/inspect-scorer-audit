"""Checks on the corpus and on the harness itself.

These do not assert that Inspect AI is free of misgrades. They assert that the
harness grades through the real pipeline and that the labelled corpus is
well formed, so the reported numbers mean what the README says.
"""

from __future__ import annotations

import pytest

from scorer_audit.issues import IN_CONTRACT, issue_cases
from scorer_audit.runner import SCORERS, Case, run_cases
from scorer_audit.systematic import all_cases


def test_case_ids_unique_and_labels_valid() -> None:
    cases = all_cases() + issue_cases()
    assert len({c.id for c in cases}) == len(cases)
    for c in cases:
        assert c.expected in ("C", "I"), c.id
        assert c.scorer in SCORERS, c.id
        assert c.note.startswith(("contract=in", "contract=off")), c.id


def test_in_contract_allowlist_refers_to_real_cases() -> None:
    ids = {c.id for c in issue_cases()}
    assert IN_CONTRACT <= ids


def test_every_numeric_render_has_a_wrong_answer_variant() -> None:
    by_category: dict[tuple[str, str], set[str]] = {}
    for c in all_cases():
        if not c.category.startswith("numeric:"):
            continue
        by_category.setdefault((c.scorer, c.category), set()).add(c.expected)
    assert all("I" in labels for labels in by_category.values())


@pytest.mark.parametrize(
    "case, credited",
    [
        (Case("h.match.ok", "match_numeric", "60", "The answer is 60.", "C", "harness"), True),
        (Case("h.match.bad", "match_numeric", "60", "The answer is 61.", "I", "harness"), False),
        (
            Case(
                "h.mc.ok", "multiple_choice", "B", "ANSWER: B", "C", "harness", choices=["x", "y"]
            ),
            True,
        ),
        (
            Case(
                "h.grader.i",
                "model_graded_qa",
                "Paris",
                "Lyon",
                "I",
                "harness",
                grader_output="GRADE: I",
            ),
            False,
        ),
    ],
    ids=lambda v: v.id if isinstance(v, Case) else str(v),
)
def test_harness_grades_through_real_pipeline(case: Case, credited: bool) -> None:
    [result] = run_cases([case])
    assert result.error is None
    assert result.credited is credited
    assert not result.misgraded

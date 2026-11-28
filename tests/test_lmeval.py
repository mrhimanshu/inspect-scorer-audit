"""Checks on the lm-evaluation-harness audit corpus and harness.

Skipped unless lm-eval is installed (see requirements-lmeval.txt).
"""

from __future__ import annotations

import pytest

lmeval = pytest.importorskip("lm_eval")

from scorer_audit.lmeval import (
    CONTRACTS,
    IN_CONTRACT,
    SCORERS,
    LmCase,
    grade,
    issue_cases,
    systematic_cases,
)


def test_case_ids_unique_and_labels_valid() -> None:
    cases = systematic_cases() + issue_cases()
    assert len({c.id for c in cases}) == len(cases)
    for c in cases:
        assert c.expected in ("C", "I"), c.id
        assert c.scorer in SCORERS, c.id
        assert c.note.startswith(("contract=in", "contract=off")), c.id
    assert set(CONTRACTS) == set(SCORERS)


def test_in_contract_allowlist_refers_to_real_cases() -> None:
    assert IN_CONTRACT <= {c.id for c in issue_cases()}


@pytest.mark.parametrize(
    ("scorer", "target", "completion", "credited", "extracted"),
    [
        ("gsm8k/strict-match/exact_match", "18", "Working.\n#### 18", True, "18"),
        ("gsm8k/strict-match/exact_match", "18", "Working.\n#### 81", False, "81"),
        ("gsm8k_cot/strict-match/exact_match", "18", "The answer is 18.", True, "18"),
        ("gsm8k/flexible-extract/exact_match", "1500", "So it costs $1,500.", True, "$1,500."),
        ("mmlu_pro_math/custom-extract/exact_match", "C", "the answer is (C)", True, "C"),
        ("mmlu_pro_math/custom-extract/exact_match", "C", "the answer is (B)", False, "B"),
    ],
)
def test_harness_grades_through_the_task_pipeline(
    scorer: str, target: str, completion: str, credited: bool, extracted: str
) -> None:
    """Unambiguous cases must grade the obvious way, or the harness is broken."""
    r = grade(LmCase("t", scorer, target, completion, "C", "test"))
    assert r.error is None
    assert r.credited is credited
    assert r.extracted == extracted


def test_minerva_metrics_are_read_separately() -> None:
    sentence = "Final Answer: The final answer is 18. I hope it is correct."
    em = grade(LmCase("t", "minerva_math_algebra/none/exact_match", "18", sentence, "C", "t"))
    mv = grade(LmCase("t", "minerva_math_algebra/none/math_verify", "18", "18", "C", "t"))
    assert em.credited and mv.credited

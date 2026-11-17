"""Systematically generated cases: one answer rendered in many realistic formats.

Every rendering is produced twice, once with the correct value and once with a
wrong value, so a scorer is measured on both false passes (crediting a wrong
answer) and false fails (rejecting a right one).

`contract` records whether the rendering follows the format the scorer
documents. Misgrades on in-contract cases are defects; misgrades on
off-contract cases measure robustness to formats models commonly produce.
"""

from __future__ import annotations

from dataclasses import dataclass

from .runner import Case


@dataclass(frozen=True)
class Render:
    key: str
    template: str  # "{v}" is replaced by the displayed value
    contract: frozenset[str]  # scorers for which this format is documented


NUMERIC = frozenset({"match_numeric"})
MATH = frozenset({"math"})
BOTH = NUMERIC | MATH

NUMERIC_RENDERS = [
    Render("bare", "{v}", BOTH),
    Render("sentence", "The answer is {v}.", BOTH),
    Render("answer_label", "ANSWER: {v}", BOTH),
    Render("answer_label_nospace", "ANSWER:{v}", frozenset()),
    Render("final_answer", "Final answer: {v}", BOTH),
    Render("bold_value", "The answer is **{v}**.", BOTH),
    Render("bold_label", "**Answer:** {v}", BOTH),
    Render("boxed", "Therefore the result is $\\boxed{{{v}}}$.", MATH),
    Render("equation", "x = {v}", BOTH),
    Render("trailing_newline", "The answer is {v}\n\n", BOTH),
    Render("units", "The answer is {v} apples.", NUMERIC),
    Render(
        "reasoning_then_answer",
        "We have 28 + 32 = 60 and 7 * 3 = 21, so the answer is {v}.",
        BOTH,
    ),
    # A word problem where the target also appears as a quantity restated
    # after the answer (e.g. an original price). Only the stated answer counts.
    Render(
        "answer_then_restated_quantity",
        "The answer is {v}, compared with {t} originally.",
        frozenset(),
    ),
    Render("hedged", "It is either {w} or {v}.", frozenset()),
]

# (target, correct display variants, wrong value)
NUMERIC_SEEDS: list[tuple[str, list[tuple[str, frozenset[str]]], str]] = [
    ("1500", [("1500", BOTH), ("1,500", NUMERIC), ("$1,500", NUMERIC), ("1500.0", BOTH)], "1005"),
    ("187500", [("187500", BOTH), ("187,500", NUMERIC)], "187503"),
    ("60", [("60", BOTH)], "6"),
    ("-3", [("-3", BOTH), ("−3", frozenset())], "3"),
    ("0.25", [("0.25", BOTH), (".25", BOTH)], "0.52"),
    ("12", [("12", BOTH), ("１２", frozenset()), ("١٢", frozenset())], "21"),
    ("1500", [("¥1,500", frozenset()), ("₹1,500", frozenset())], "1005"),
]


def numeric_cases() -> list[Case]:
    """One case per distinct (scorer, target, completion).

    Correct-value cases are rendered for every display variant. Wrong-value
    cases do not depend on the display, so they are rendered once per seed.
    The contract tag reflects the text actually shown.
    """
    cases: list[Case] = []
    seen: set[tuple[str, str, str]] = set()
    for s, (target, displays, wrong) in enumerate(NUMERIC_SEEDS):
        for d, (shown, display_contract) in enumerate(displays):
            for render in NUMERIC_RENDERS:
                for scorer in ("match_numeric", "math"):
                    variants: list[tuple[str, str, bool]] = []
                    if render.key == "hedged":
                        # A hedge between right and wrong never earns credit.
                        variants.append(
                            (
                                "I",
                                render.template.format(v=shown, w=wrong),
                                scorer in display_contract,
                            )
                        )
                    elif render.key == "answer_then_restated_quantity":
                        # Only the wrong-answer variant is meaningful.
                        variants.append(("I", render.template.format(v=wrong, t=target), True))
                    else:
                        variants.append(
                            ("C", render.template.format(v=shown), scorer in display_contract)
                        )
                        variants.append(("I", render.template.format(v=wrong), True))
                    for label, text, shown_ok in variants:
                        key = (scorer, target, text)
                        if key in seen:
                            continue
                        seen.add(key)
                        contract = "in" if scorer in render.contract and shown_ok else "off"
                        cases.append(
                            Case(
                                id=f"sys.{scorer}.{s}.{d}.{render.key}.{label}",
                                scorer=scorer,
                                target=target,
                                completion=text,
                                expected=label,
                                category=f"numeric:{render.key}",
                                note=f"contract={contract}",
                            )
                        )
    return cases


MC_CHOICES = ["Berlin", "Madrid", "Paris", "Rome"]
MC_TARGET = "C"

# (key, completion, expected, in_contract)
MC_RENDERS: list[tuple[str, str, str, bool]] = [
    ("canonical", "ANSWER: C", "C", True),
    ("canonical_wrong", "ANSWER: B", "I", True),
    ("reasoning_then_canonical", "Paris is the capital of France.\n\nANSWER: C", "C", True),
    ("lowercase", "answer: c", "C", False),
    ("bold_label", "**ANSWER:** C", "C", False),
    ("bold_whole", "**ANSWER: C**", "C", False),
    ("parenthesised", "ANSWER: (C)", "C", False),
    ("letter_and_text", "ANSWER: C) Paris", "C", False),
    ("backticks", "ANSWER: `C`", "C", False),
    ("sentence", "The correct answer is C.", "C", False),
    (
        "revised_final",
        "ANSWER: B\n\nWait, that is Madrid. Correcting myself.\n\nANSWER: C",
        "C",
        False,
    ),
    ("revised_final_bold", "ANSWER: B\n\nOn reflection:\n\n**ANSWER: C**", "C", False),
    ("hedge_slash", "ANSWER: B/C", "I", False),
    ("hedge_or", "ANSWER: B or C", "I", False),
    ("hedge_comma", "ANSWER: B, C", "I", False),
    ("all_letters", "ANSWER: A, B, C, D", "I", False),
    ("letter_in_word", "ANSWER: Can't decide", "I", False),
    ("empty", "", "I", False),
]


def multiple_choice_cases() -> list[Case]:
    return [
        Case(
            id=f"sys.multiple_choice.{key}",
            scorer="multiple_choice",
            target=MC_TARGET,
            completion=text,
            expected=expected,
            choices=MC_CHOICES,
            category=f"mc:{key}",
            note=f"contract={'in' if contract else 'off'}",
        )
        for key, text, expected, contract in MC_RENDERS
    ]


# Grader outputs for model_graded_qa. The expected label is the grade the
# grader actually committed to; a hedged or contradictory grade is not credit.
GRADER_RENDERS: list[tuple[str, str, str, bool]] = [
    ("canonical_c", "The answer matches.\n\nGRADE: C", "C", True),
    ("canonical_i", "The answer is wrong.\n\nGRADE: I", "I", True),
    ("bold_c", "The answer matches.\n\n**GRADE: C**", "C", False),
    ("bold_label_i", "Wrong answer.\n\n**GRADE:** I", "I", False),
    ("hedge_slash", "Partially right.\n\nGRADE: C/I", "I", False),
    ("hedge_joined", "Partially right.\n\nGRADE: CI", "I", False),
    (
        "quoted_then_final",
        "The instructions say to reply GRADE: C if correct. It is not.\n\nGRADE: I",
        "I",
        False,
    ),
    ("word_correct", "GRADE: CORRECT", "C", False),
    ("word_incorrect", "GRADE: INCORRECT", "I", False),
    ("trailing_period", "GRADE: I.", "I", True),
]


def model_graded_cases() -> list[Case]:
    return [
        Case(
            id=f"sys.model_graded_qa.{key}",
            scorer="model_graded_qa",
            target="Paris",
            completion="Paris",
            grader_output=grader,
            expected=expected,
            category=f"grader:{key}",
            note=f"contract={'in' if contract else 'off'}",
        )
        for key, grader, expected, contract in GRADER_RENDERS
    ]


def all_cases() -> list[Case]:
    return numeric_cases() + multiple_choice_cases() + model_graded_cases()

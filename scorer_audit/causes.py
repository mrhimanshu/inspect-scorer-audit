"""Attribute each misgrade to a root cause: an open Inspect AI issue or a new finding."""

from __future__ import annotations

from .runner import Result

ISSUE = "https://github.com/UKGovernmentBEIS/inspect_ai/issues/"

# Root-cause key -> (description, issue number or None for new findings)
CAUSES: dict[str, tuple[str, int | None]] = {
    "sigfig_rounding": (
        "match(numeric=True) compares numbers rounded to 5 significant digits",
        6537,
    ),
    "label_no_space": (
        "match(numeric=True) misses a number glued to a label or `=` (`ANSWER:60`)",
        5994,
    ),
    "boxed_fallback": (
        "match(numeric=True) can't read `\\boxed{}` and grades a reasoning number instead",
        6536,
    ),
    "currency_symbol": (
        "match(numeric=True) only strips `$ € £`, so `¥ ₹` amounts are skipped (documented; see #6572)",
        -1,
    ),
    "mc_markdown": (
        "multiple_choice misses `**ANSWER:** C`, `ANSWER: (C)` and code-span answers",
        6535,
    ),
    "mc_revision": ("multiple_choice keeps an earlier `ANSWER:` over the model's final one", 6534),
    "grader_hedge": ("model_graded_qa credits a hedged `GRADE: C/I`", 6594),
    "target_later": (
        "math() falls back to the last number in prose, so hedges and restated quantities pass",
        5733,
    ),
    "math_nonascii_digits": (
        "math() rejects full-width and Arabic-Indic digits that match(numeric=True) accepts",
        None,
    ),
    "by_design_last_number": (
        "match(location='end') grades the last number, so hedges and restated quantities pass (documented)",
        -1,
    ),
    "by_design_mc_format": ("multiple_choice requires an `ANSWER:` line (documented template)", -1),
    "other": ("other format (see results.jsonl)", None),
}


def _non_ascii_digit(ch: str) -> bool:
    return "\uff10" <= ch <= "\uff19" or "\u0660" <= ch <= "\u0669"


def cause_of(r: Result) -> str:
    """Root cause of a misgraded systematic case. Issue cases use their own source."""
    c = r.case
    cat, scorer, text = c.category, c.scorer, c.completion
    if scorer == "match_numeric":
        if cat.endswith(("hedged", "answer_then_restated_quantity")):
            return "by_design_last_number"
        if "187503" in text:
            return "sigfig_rounding"
        if cat.endswith("answer_label_nospace"):
            return "label_no_space"
        if cat.endswith("boxed"):
            return "boxed_fallback"
        if "\u00a5" in text or "\u20b9" in text:
            return "currency_symbol"
    if cat.endswith(("hedged", "answer_then_restated_quantity")):
        return "target_later"
    if scorer == "math" and any(_non_ascii_digit(ch) for ch in text):
        return "math_nonascii_digits"
    if cat in ("mc:bold_label", "mc:backticks", "mc:parenthesised", "mc:letter_and_text"):
        return "mc_markdown"
    if cat.startswith("mc:revised"):
        return "mc_revision"
    if cat == "mc:sentence":
        return "by_design_mc_format"
    if cat == "grader:hedge_slash":
        return "grader_hedge"
    return "other"

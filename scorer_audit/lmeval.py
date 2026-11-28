"""Audit answer extraction and scoring in EleutherAI's lm-evaluation-harness.

Each case is one document and one model response. The task is loaded from the
installed lm-eval with its real YAML config, and the response runs through the
task's own filter pipelines and `process_results`, as in `lm_eval.evaluator`.
Datasets are replaced by a one-row in-memory dataset, so nothing is downloaded
and no model is called.

Scorer keys are `<task>/<filter>/<metric>`. A case is *in-contract* when the
response uses the format the task's prompt or extraction rule asks for (see
CONTRACTS), so a misgrade there is a defect rather than a robustness gap.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, replace
from functools import cache
from importlib.metadata import version
from pathlib import Path
from typing import Any
from unittest import mock

LM_ISSUE = "https://github.com/EleutherAI/lm-evaluation-harness/"
CASES_FILE = Path(__file__).resolve().parent.parent / "cases" / "lmeval_issues.jsonl"

GSM_STRICT = "gsm8k/strict-match/exact_match"
GSM_FLEX = "gsm8k/flexible-extract/exact_match"
COT_STRICT = "gsm8k_cot/strict-match/exact_match"
COT_FLEX = "gsm8k_cot/flexible-extract/exact_match"
MATH_EM = "minerva_math_algebra/none/exact_match"
MATH_MV = "minerva_math_algebra/none/math_verify"
MMLU_PRO = "mmlu_pro_math/custom-extract/exact_match"

SCORERS = [GSM_STRICT, GSM_FLEX, COT_STRICT, COT_FLEX, MATH_EM, MATH_MV, MMLU_PRO]

# What each scorer's task asks the model to produce. Shown in the report.
CONTRACTS = {
    GSM_STRICT: "`#### N`, the format of the GSM8K reference answers",
    GSM_FLEX: "any response whose last number is the answer (the filter keeps the last match)",
    COT_STRICT: "`The answer is N.`, the format of the few-shot answers",
    COT_FLEX: "any response whose last number is the answer (the filter keeps the last match)",
    MATH_EM: "`Final Answer: The final answer is X. I hope it is correct.` (Minerva format)",
    MATH_MV: "a final answer in `\\boxed{}`, the Minerva sentence, or a plain final statement",
    MMLU_PRO: "`the answer is (X)`, the format of the few-shot answers",
}


@dataclass(frozen=True)
class LmCase:
    id: str
    scorer: str
    target: str
    completion: str
    expected: str  # "C" if a careful human grader gives credit, else "I"
    category: str
    source: str = "systematic"
    note: str = ""


@dataclass
class LmResult:
    case: LmCase
    credited: bool | None
    extracted: str | None
    error: str | None = None

    @property
    def misgraded(self) -> bool:
        return self.error is None and self.credited != (self.case.expected == "C")

    @property
    def direction(self) -> str:
        if not self.misgraded:
            return ""
        return "false_pass" if self.credited else "false_fail"

    @property
    def contract(self) -> str:
        return "in" if self.case.note.startswith("contract=in") else "off"


# ---------------------------------------------------------------- harness


def _doc(task: str, target: str) -> dict[str, Any]:
    if task.startswith("gsm8k"):
        return {"question": "How many?", "answer": f"Some working.\n#### {target}"}
    if task.startswith("minerva_math"):
        return {
            "problem": "Compute it.",
            "solution": f"Some working, so the answer is $\\boxed{{{target}}}$.",
            "level": "Level 1",
            "type": "Algebra",
        }
    if task.startswith("mmlu_pro"):
        options = [f"option {i}" for i in range(10)]
        idx = "ABCDEFGHIJ".index(target)
        return {
            "question_id": 0,
            "question": "Which option?",
            "options": options,
            "answer": target,
            "answer_index": idx,
            "cot_content": "",
            "category": "math",
            "src": "audit",
        }
    raise ValueError(task)


@cache
def _task(task: str, target: str) -> tuple[Any, dict[str, Any]]:
    """Load `task` from the installed lm-eval with a one-document dataset."""
    import datasets
    import lm_eval.api.task as lm_task

    row = _doc(task, target)

    def fake_load_dataset(*_: Any, **__: Any) -> Any:
        ds = datasets.Dataset.from_list([row])
        return datasets.DatasetDict({s: ds for s in ("train", "validation", "test")})

    with mock.patch.object(lm_task.datasets, "load_dataset", fake_load_dataset):
        loaded = _manager().load([task])["tasks"]
    obj = next(iter(loaded.values()))
    return obj, next(iter(obj.test_docs()))


@cache
def _manager() -> Any:
    from lm_eval.tasks import TaskManager

    return TaskManager()


def grade(case: LmCase) -> LmResult:
    from lm_eval.api.instance import Instance

    task_name, filter_name, metric = case.scorer.split("/")
    try:
        task, doc = _task(task_name, case.target)
        inst = Instance(
            request_type="generate_until",
            doc=doc,
            arguments=("", {}),
            idx=0,
            metadata=(task_name, 0, 1),
        )
        inst.resps = [case.completion]
        for ensemble in task._filters:
            ensemble.apply([inst])
        filtered = inst.filtered_resps[filter_name]
        scores = task.process_results(doc, [filtered])
        return LmResult(case, float(scores[metric]) >= 1.0, str(filtered))
    except Exception as exc:  # noqa: BLE001 - report, don't hide
        return LmResult(case, None, None, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- systematic cases

GSM = {GSM_STRICT, GSM_FLEX, COT_STRICT, COT_FLEX}
FLEX = {GSM_FLEX, COT_FLEX}
NUMERIC_SCORERS = sorted(GSM | {MATH_EM, MATH_MV})

# (key, template, scorers for which the format is in-contract)
# "{v}" is the shown value, "{w}" a wrong value, "{t}" the target.
NUMERIC_RENDERS: list[tuple[str, str, set[str]]] = [
    ("bare", "{v}", FLEX | {MATH_MV}),
    ("hash", "Some working.\n#### {v}", {GSM_STRICT} | FLEX),
    ("sentence", "The answer is {v}.", FLEX | {COT_STRICT, MATH_MV}),
    ("sentence_no_period", "The answer is {v}", FLEX | {MATH_MV}),
    ("sentence_newline", "The answer is {v}\n\n", FLEX | {MATH_MV}),
    (
        "reasoning_then_sentence",
        "We have 28 + 32 = 60 and 7 * 3 = 21. The answer is {v}.",
        FLEX | {COT_STRICT, MATH_MV},
    ),
    ("sentence_then_check", "The answer is {v}. Check: 3 * 4 = 12, which fits.", {COT_STRICT}),
    (
        "minerva",
        "Final Answer: The final answer is {v}. I hope it is correct.",
        FLEX | {MATH_EM, MATH_MV},
    ),
    (
        "minerva_dollars",
        "Final Answer: The final answer is ${v}$. I hope it is correct.",
        {MATH_EM, MATH_MV},
    ),
    ("answer_label", "ANSWER: {v}", FLEX),
    ("bold", "The answer is **{v}**.", FLEX),
    ("boxed_inline", "So the result is $\\boxed{{{v}}}$.", FLEX | {MATH_MV}),
    ("boxed_display", "So the result is\n$$\\boxed{{{v}}}$$", FLEX | {MATH_MV}),
    ("ellipsis", "So the total is {v}...", FLEX),
    ("units", "The answer is {v} apples.", FLEX),
    ("restated_quantity", "The answer is {v}, compared with {t} originally.", set()),
    ("hedged", "It is either {w} or {v}.", set()),
]

# (target, [(shown, scorers for which this spelling is in-contract)], wrong value)
ALL = set(NUMERIC_SCORERS)
NUMERIC_SEEDS: list[tuple[str, list[tuple[str, set[str]]], str]] = [
    ("18", [("18", ALL)], "81"),
    ("7", [("7", ALL)], "8"),
    ("1500", [("1500", ALL), ("1,500", ALL), ("$1,500", FLEX)], "1005"),
    ("-3", [("-3", ALL), ("−3", set())], "3"),
    ("\\frac{1}{4}", [("\\frac{1}{4}", {MATH_EM, MATH_MV}), ("1/4", {MATH_MV})], "\\frac{1}{3}"),
]


def _numeric_cases() -> list[LmCase]:
    cases: list[LmCase] = []
    seen: set[tuple[str, str, str]] = set()
    for s, (target, displays, wrong) in enumerate(NUMERIC_SEEDS):
        scorers = [MATH_EM, MATH_MV] if "\\" in target else NUMERIC_SCORERS
        for d, (shown, shown_ok) in enumerate(displays):
            for key, template, contract in NUMERIC_RENDERS:
                variants: list[tuple[str, str, bool]] = []
                if key == "hedged":
                    variants.append(("I", template.format(v=shown, w=wrong), True))
                elif key == "restated_quantity":
                    variants.append(("I", template.format(v=wrong, t=target), True))
                else:
                    variants.append(("C", template.format(v=shown, w=wrong, t=target), False))
                    variants.append(("I", template.format(v=wrong, w=wrong, t=target), True))
                for label, text, any_spelling in variants:
                    for scorer in scorers:
                        if "$" in shown and scorer in (MATH_EM, MATH_MV):
                            continue  # a currency amount is not a MATH answer
                        if (scorer, target, text) in seen:
                            continue
                        seen.add((scorer, target, text))
                        ok = scorer in contract and (any_spelling or scorer in shown_ok)
                        cases.append(
                            LmCase(
                                id=f"sys.{scorer}.{s}.{d}.{key}.{label}",
                                scorer=scorer,
                                target=target,
                                completion=text,
                                expected=label,
                                category=f"numeric:{key}",
                                note=f"contract={'in' if ok else 'off'}",
                            )
                        )
    return cases


# (key, completion, expected, in_contract) for target C.
MC_RENDERS: list[tuple[str, str, str, bool]] = [
    ("canonical", "Working it through, the answer is (C).", "C", True),
    ("canonical_wrong", "Working it through, the answer is (B).", "I", True),
    ("capitalised", "The answer is (C).", "C", True),
    ("no_parens", "The answer is C.", "C", True),
    ("high_letter_wrong", "The answer is (J).", "I", True),
    ("lowercase_letter", "the answer is (c).", "C", False),
    ("bold", "The answer is **(C)**.", "C", False),
    ("answer_label", "Answer: C", "C", False),
    ("correct_answer_is", "The correct answer is (C).", "C", True),
    ("revised", "At first the answer is (B). Checking again, the answer is (C).", "C", False),
    ("hedge", "The answer is (B) or (C).", "I", False),
    ("answer_is_option_text", "The answer is option 2, which is (C).", "C", False),
]


def _mc_cases() -> list[LmCase]:
    return [
        LmCase(
            id=f"sys.{MMLU_PRO}.{key}",
            scorer=MMLU_PRO,
            target="C",
            completion=text,
            expected=expected,
            category=f"mc:{key}",
            note=f"contract={'in' if ok else 'off'}",
        )
        for key, text, expected, ok in MC_RENDERS
    ]


def systematic_cases() -> list[LmCase]:
    return _numeric_cases() + _mc_cases()


# Issue cases count as in-contract only when listed here, after checking them
# against the task's prompt format.
# The #4373 cases are off-contract: the few-shot answers always end in a period.
IN_CONTRACT = {
    "lmeval.4375.boxed_inline",
    "lmeval.4375.boxed_display",
    "lmeval.4375.ellipsis",
}


def issue_cases() -> list[LmCase]:
    if not CASES_FILE.exists():
        return []
    out = []
    for line in CASES_FILE.read_text().splitlines():
        if line.strip():
            case = LmCase(**json.loads(line))
            contract = "in" if case.id in IN_CONTRACT else "off"
            out.append(replace(case, note=f"contract={contract}; {case.note}"))
    return out


# ---------------------------------------------------------------- root causes

# key -> (description, where it is tracked). The second field is "issues/N" or
# "pull/N", "" for a new finding, "untracked" for an off-contract robustness gap
# not reported upstream, "unattributed", or None for documented behaviour.
CAUSES: dict[str, tuple[str, str | None]] = {
    "cot_strict_dot": (
        (
            "gsm8k_cot strict-match: the unescaped `.` in `The answer is (…).` takes the "
            "last digit when nothing follows the number"
        ),
        "pull/4373",
    ),
    "flex_no_digit": (
        "flexible-extract: the last match can be `$.`, `$$` or `...`, which has no digit",
        "issues/4375",
    ),
    "flex_trailing_dots": (
        (
            "flexible-extract keeps an ellipsis glued to the number (`18...`), and gsm8k's "
            "`regexes_to_ignore` removes only one trailing `.`; PR #4379 leaves this unchanged"
        ),
        "",
    ),
    "flex_last_number": (
        "flexible-extract keeps the last number in the response (by design)",
        None,
    ),
    "mv_last": ("math_verify grades the last expression in the response (by design)", None),
    "strict_format": ("strict-match only reads its own answer format (by design)", None),
    "minerva_format": (
        "minerva exact_match only reads the Minerva final-answer sentence (by design)",
        None,
    ),
    "unicode_minus": ("a `−` (U+2212) minus sign is not read as a minus", "untracked"),
    "mmlu_pro_case": ("mmlu_pro's regex only reads an upper-case letter (A-J)", "untracked"),
    "first_match": (
        "strict extraction keeps the first match, so a revised answer is ignored",
        None,
    ),
    "other": ("other (see results.jsonl)", "unattributed"),
}


def cause_of(r: LmResult) -> str:
    c = r.case
    key = c.category.split(":", 1)[1]
    flt = c.scorer.split("/")[1]
    if "−" in c.completion:
        return "unicode_minus"
    if c.scorer == COT_STRICT and key in ("sentence_no_period", "sentence_newline"):
        return "cot_strict_dot"
    if flt == "flexible-extract":
        if r.extracted and not any(ch.isdigit() for ch in r.extracted):
            return "flex_no_digit"
        if r.extracted and r.extracted.endswith(".."):
            return "flex_trailing_dots"
        if key in ("hedged", "restated_quantity", "sentence_then_check"):
            return "flex_last_number"
    if flt == "strict-match" and r.direction == "false_fail":
        return "strict_format"
    if c.scorer == MATH_EM and r.direction == "false_fail":
        return "minerva_format"
    if c.scorer == MATH_MV and key in ("hedged", "sentence_then_check"):
        return "mv_last"
    if c.scorer == MMLU_PRO:
        if key == "lowercase_letter":
            return "mmlu_pro_case"
        if key == "revised":
            return "first_match"
    return "other"


# ---------------------------------------------------------------- report


def _rate(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "0/0"


def _where(ref: str | None) -> str:
    if ref is None:
        return "by design"
    if not ref:
        return "**new**"
    if ref in ("untracked", "unattributed"):
        return "not reported" if ref == "untracked" else "unattributed"
    kind, num = ref.split("/")
    return f"[{'PR ' if kind == 'pull' else ''}#{num}]({LM_ISSUE}{ref})"


def summarise(results: list[LmResult]) -> str:
    lines = [
        "# lm-evaluation-harness answer-extraction audit",
        "",
        f"lm-eval version: `{version('lm-eval')}`. Cases: {len(results)}.",
        "",
        "Each response runs through the task's real filters and `process_results`.",
        "A misgrade is a grade that differs from a careful human grader's. *In-contract*",
        "cases use the format the task asks for, so misgrades there are defects.",
        "",
        "## By scorer",
        "",
        "| Scorer | Contract | Cases | Misgraded | False pass | False fail | In-contract misgraded | Errors |",
        "|---|---|---|---|---|---|---|---|",
    ]
    by_scorer: dict[str, list[LmResult]] = defaultdict(list)
    for r in results:
        by_scorer[r.case.scorer].append(r)
    for scorer in SCORERS:
        rs = by_scorer.get(scorer, [])
        graded = [r for r in rs if r.error is None]
        bad = [r for r in graded if r.misgraded]
        inc = [r for r in graded if r.contract == "in"]
        lines.append(
            f"| `{scorer}` | {CONTRACTS[scorer]} | {len(rs)} | {_rate(len(bad), len(graded))} | "
            f"{sum(r.direction == 'false_pass' for r in bad)} | "
            f"{sum(r.direction == 'false_fail' for r in bad)} | "
            f"{_rate(sum(r.misgraded for r in inc), len(inc))} | {len(rs) - len(graded)} |"
        )

    sys_bad = [r for r in results if r.case.source == "systematic" and r.misgraded]
    lines += ["", "## Systematic misgrades by root cause", ""]
    lines += ["| Root cause | Tracked in | Misgrades | In-contract |", "|---|---|---|---|"]
    counts: dict[str, list[LmResult]] = defaultdict(list)
    for r in sys_bad:
        counts[cause_of(r)].append(r)
    for key, rs in sorted(counts.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        desc, ref = CAUSES[key]
        lines.append(
            f"| {desc} | {_where(ref)} | {len(rs)} | {sum(r.contract == 'in' for r in rs)} |"
        )

    lines += ["", "## Misgrades by format", ""]
    lines += ["| Scorer | Format | Misgraded | Direction | Example |", "|---|---|---|---|---|"]
    groups: dict[tuple[str, str], list[LmResult]] = defaultdict(list)
    for r in results:
        if r.case.source == "systematic":
            groups[(r.case.scorer, r.case.category)].append(r)
    for (scorer, category), rs in sorted(groups.items()):
        bad = [r for r in rs if r.misgraded]
        if not bad:
            continue
        ex = bad[0]
        text = ex.case.completion.replace("\n", "⏎").replace("|", "\\|")[:60]
        lines.append(
            f"| `{scorer}` | {category} | {len(bad)}/{len(rs)} | "
            f"{', '.join(sorted({r.direction for r in bad}))} | "
            f"`{text}` → extracted `{ex.extracted}` (target `{ex.case.target}`) |"
        )

    issue_results = [r for r in results if r.case.source != "systematic"]
    if issue_results:
        lines += ["", "## Reported issues re-checked on this version", ""]
        lines += [
            "| Report | Case | Expected | Extracted | Still reproduces |",
            "|---|---|---|---|---|",
        ]
        for r in issue_results:
            ref = r.case.source.split("lm-evaluation-harness/", 1)[-1]
            lines.append(
                f"| {_where(ref)} | `{r.case.id}` | {r.case.expected} | `{r.extracted}` | "
                f"{'yes' if r.misgraded else 'error' if r.error else 'no'} |"
            )

    errors = [r for r in results if r.error]
    if errors:
        lines += ["", "## Scoring errors", ""]
        lines += [f"- `{r.case.id}`: {r.error.splitlines()[0][:160]}" for r in errors]
    return "\n".join(lines) + "\n"


def run(cases: list[LmCase]) -> list[LmResult]:
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case ids must be unique")
    return [grade(c) for c in cases]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("results/lmeval"))
    args = parser.parse_args()
    logging.disable(logging.WARNING)

    results = run(systematic_cases() + issue_cases())
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "results.jsonl").open("w") as f:
        for r in results:
            row = {
                "id": r.case.id,
                "scorer": r.case.scorer,
                "category": r.case.category,
                "source": r.case.source,
                "contract": r.contract,
                "target": r.case.target,
                "completion": r.case.completion,
                "expected": r.case.expected,
                "credited": r.credited,
                "extracted": r.extracted,
                "misgraded": r.misgraded,
                "direction": r.direction,
                "error": r.error,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = summarise(results)
    (args.out / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

"""Run the audit and write machine-readable results plus a Markdown summary."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

from .causes import CAUSES, ISSUE, cause_of
from .issues import issue_cases
from .runner import Result, run_cases
from .systematic import all_cases


def _contract(result: Result) -> str:
    note = result.case.note
    return "in" if "contract=in" in note else "off" if "contract=off" in note else "n/a"


def _rate(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "0/0"


def summarise(results: list[Result]) -> str:
    inspect_version = version("inspect-ai")
    lines = [
        "# Inspect AI scorer audit",
        "",
        f"Inspect AI version: `{inspect_version}`. Cases: {len(results)}.",
        "",
        "A misgrade is a grade that differs from the label a careful human grader",
        "would give. *False pass* credits a wrong answer; *false fail* rejects a",
        "correct one. *Unscored* grades (NaN, excluded from metrics) count as no credit;",
        "*In-contract* cases use the answer format the scorer",
        "documents, so misgrades there are defects rather than robustness gaps.",
        "",
        "## By scorer",
        "",
        "| Scorer | Cases | Misgraded | False pass | False fail | In-contract misgraded | Unscored | Errors |",
        "|---|---|---|---|---|---|---|---|",
    ]
    by_scorer: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        by_scorer[r.case.scorer].append(r)
    for scorer, rs in sorted(by_scorer.items()):
        graded = [r for r in rs if r.error is None]
        bad = [r for r in graded if r.misgraded]
        inc = [r for r in graded if _contract(r) == "in"]
        lines.append(
            f"| `{scorer}` | {len(rs)} | {_rate(len(bad), len(graded))} | "
            f"{sum(r.direction == 'false_pass' for r in bad)} | "
            f"{sum(r.direction == 'false_fail' for r in bad)} | "
            f"{_rate(sum(r.misgraded for r in inc), len(inc))} | "
            f"{sum(r.actual == 'U' for r in graded)} | "
            f"{len(rs) - len(graded)} |"
        )

    systematic_bad = [r for r in results if r.case.source == "systematic" and r.misgraded]
    if systematic_bad:
        lines += ["", "## Systematic misgrades by root cause", ""]
        lines += ["| Root cause | Tracked in | Misgrades | In-contract |", "|---|---|---|---|"]
        counts: dict[str, list[Result]] = defaultdict(list)
        for r in systematic_bad:
            counts[cause_of(r)].append(r)
        for key, rs in sorted(counts.items(), key=lambda kv: -len(kv[1])):
            desc, num = CAUSES[key]
            where = (
                "unattributed"
                if key == "other"
                else "documented behaviour"
                if num == -1
                else f"[#{num}]({ISSUE}{num})"
                if num
                else "**new**"
            )
            lines.append(
                f"| {desc} | {where} | {len(rs)} | {sum(_contract(r) == 'in' for r in rs)} |"
            )

    lines += ["", "## Misgrades by format", ""]
    lines += ["| Scorer | Format | Misgraded | Direction | Example |", "|---|---|---|---|---|"]
    groups: dict[tuple[str, str], list[Result]] = defaultdict(list)
    for r in results:
        groups[(r.case.scorer, r.case.category)].append(r)
    for (scorer, category), rs in sorted(groups.items()):
        bad = [r for r in rs if r.misgraded]
        if not bad:
            continue
        dirs = sorted({r.direction for r in bad})
        ex = bad[0]
        completion = (
            ex.case.grader_output if ex.case.scorer == "model_graded_qa" else ex.case.completion
        )
        example = (completion or "").replace("\n", "⏎").replace("|", "\\|")[:70]
        lines.append(
            f"| `{scorer}` | {category} | {len(bad)}/{len(rs)} | {', '.join(dirs)} | "
            f"`{example}` → {ex.actual} (target `{ex.case.target}`) |"
        )

    issue_results = [r for r in results if r.case.source != "systematic"]
    if issue_results:
        lines += ["", "## Reported issues re-checked on this version", ""]
        lines += [
            "| Issue | Case | Expected | Actual | Still reproduces |",
            "|---|---|---|---|---|",
        ]
        for r in issue_results:
            num = r.case.source.rstrip("/").rsplit("/", 1)[-1]
            lines.append(
                f"| [#{num}]({r.case.source}) | `{r.case.id}` | {r.case.expected} | "
                f"{r.actual} | {'yes' if r.misgraded else 'error' if r.error else 'no'} |"
            )

    errors = [r for r in results if r.error]
    if errors:
        lines += ["", "## Scoring errors", ""]
        for r in errors:
            lines.append(f"- `{r.case.id}`: {r.error.splitlines()[0][:160]}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--only", choices=["systematic", "issues"], default=None)
    args = parser.parse_args()

    cases = []
    if args.only in (None, "systematic"):
        cases += all_cases()
    if args.only in (None, "issues"):
        cases += issue_cases()
    results = run_cases(cases)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "results.jsonl").open("w") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "id": r.case.id,
                        "scorer": r.case.scorer,
                        "category": r.case.category,
                        "source": r.case.source,
                        "contract": _contract(r),
                        "target": r.case.target,
                        "completion": r.case.completion,
                        "grader_output": r.case.grader_output,
                        "expected": r.case.expected,
                        "actual": r.actual,
                        "answer": r.answer,
                        "misgraded": r.misgraded,
                        "direction": r.direction,
                        "error": r.error,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    report = summarise(results)
    (args.out / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

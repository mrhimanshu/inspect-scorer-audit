# inspect-scorer-audit

A labelled benchmark that measures how often the built-in scorers in
[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai), the UK AI Security Institute's evaluation framework,
grade a model answer differently from a careful human grader.

An evaluation is only as reliable as its scorer. A scorer that credits a wrong answer, or rejects a right one,
moves the headline number of every eval that uses it, and does so silently. Inspect AI has dozens of open
issues, each reporting one such case. This project turns them, plus a systematic set of answer formats, into a
single, re-runnable measurement.

## Results

Latest run (`results/REPORT.md`): Inspect AI **0.3.290**, **677 distinct cases** (600 systematic, 77 from issues).

- **All 28** open scorer issues sampled here still reproduce on 0.3.290: 27 misgrade, and #5430 still raises
  instead of returning a grade.
- **One new finding:** `math()` rejects correct answers written in full-width (`１２`) or Arabic-Indic (`١٢`)
  digits, which `match(numeric=True)` accepts. That's 24 misgrades across formats.
- **Misgrades in a format the scorer's documentation promises to handle** (*in-contract*):
  - `match(numeric=True)`: 15 of 175. All of them come from one root cause: numbers are compared at 5
    significant digits, so `187503` matches `187500` (#6537, #5567).
  - `math()`: 2 of 142 (#6016, #5733).
- Most misgrades are robustness gaps or documented behaviour rather than defects. `match(location="end")`
  grades the last number by design, and only `$ € £` are documented currency symbols. These are listed
  separately so they are not counted as bugs.

Systematic misgrades by root cause:

| Root cause | Tracked in | Misgrades | In-contract |
|---|---|---|---|
| `math()` rejects full-width and Arabic-Indic digits that `match(numeric=True)` accepts | **new** | 24 | 0 |
| `match(location="end")` grades the last number, so hedges and restated quantities pass | documented behaviour | 20 | 0 |
| `match(numeric=True)` only strips `$ € £`, so `¥ ₹` amounts are skipped | documented behaviour ([#6572](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6572)) | 20 | 0 |
| `math()` falls back to the last number in prose, so hedges and restated quantities pass | [#5733](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5733) | 17 | 0 |
| `match(numeric=True)` misses a number glued to a label (`ANSWER:60`) | [#5994](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5994) | 16 | 0 |
| `match(numeric=True)` can't read `\boxed{}` and grades a reasoning number instead | [#6536](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6536) | 16 | 0 |
| `match(numeric=True)` compares numbers rounded to 5 significant digits | [#6537](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6537) | 10 | 10 |
| `multiple_choice` misses `**ANSWER:** C` and code-span answers | [#6535](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6535) | 2 | 0 |

The full per-scorer table, every misgrade with an example, and the issue re-check are in
[`results/REPORT.md`](results/REPORT.md). Every individual decision is in
[`results/results.jsonl`](results/results.jsonl).

> **These are rates over a constructed corpus, not prevalence in real evals.** The corpus deliberately
> concentrates on formats that are hard to grade. How often each format occurs depends on the model and the
> prompt. Treat the numbers as "which formats break which scorers", not "x% of eval results are wrong".

## How it works

Each case is one Inspect `Sample`. A mock model (`mockllm`) returns the case's completion verbatim, and the
sample runs through the **same solver and scorer** a user would configure (`generate()` + `match()`,
`multiple_choice()` + `choice()`, and so on). For `model_graded_qa()`, a second mock model plays the grader
and returns a chosen grading reply, so the grade-parsing step is tested in isolation. No API calls are made.

Two sources of cases:

1. **Systematic** (`scorer_audit/systematic.py`, 600 distinct cases): seven numeric answers, each rendered in fourteen realistic
   formats (bare, `ANSWER:`, bold, `\boxed{}`, units, reasoning first, hedged, and others) with correct and wrong
   values. Each format also has a wrong-answer variant, so false passes and false fails are both measured.
   It also covers multiple-choice replies and grader replies.
2. **Issue-sourced** (`cases/issues.jsonl`): 77 cases taken verbatim from 28 open Inspect AI issues.
   `cases/issues_index.json` lists every scorer-related issue reviewed and why any were left out.

### Labelling policy

- `expected` is what a careful human grader would decide. A hedge between a right and a wrong answer earns no
  credit. An empty or punctuation-only target matches nothing.
- `NOANSWER`, `INCORRECT` and unscored (NaN) grades all count as "no credit". Unscored grades are also
  counted separately in the report.
- A case is **in-contract** only when its format is one the scorer's docstring promises to handle. Issue cases
  count as in-contract only if listed in `IN_CONTRACT` in `scorer_audit/issues.py`, which was checked by hand.
  Everything else defaults to off-contract, so the in-contract rate errs low.
- When the scorer behaves as documented but a human would still grade differently, the misgrade is reported
  under "documented behaviour", not as a defect.

## Run it

```bash
pip install -e ".[dev]"
inspect-scorer-audit --out results       # writes results/REPORT.md and results/results.jsonl
pytest -q                                 # corpus and harness checks
```

To audit a different Inspect version, install it (`pip install inspect-ai==X.Y.Z`) and re-run. CI re-runs the
audit every week against the latest release, so fixed issues show up as "no longer reproduces".

## Adding a case

Append a line to `cases/issues.jsonl`:

```json
{"id": "issue.1234.slug", "scorer": "match_numeric", "target": "42", "completion": "ANSWER: 42", "expected": "C",
 "category": "issue:slug", "source": "https://github.com/UKGovernmentBEIS/inspect_ai/issues/1234",
 "choices": null, "grader_output": null, "note": "contract=off; why the label is what it is"}
```

Scorer keys are defined in `SCORERS` in `scorer_audit/runner.py`.

## Limitations

- Completions are written, not sampled from models (see the note under Results).
- `f1()` is continuous and is not audited. `multiple_choice` with `multiple_correct=True` or shuffled choices
  is not yet covered.
- Labels are one grader's judgement. Debatable labels carry a reason in `note`.

## Disclosure

Built with AI coding assistance (Claude Code), including extraction of the issue cases. Issue labels and the
in-contract allowlist were checked against the scorer docstrings, and every number above comes from the
committed run output. This project is
independent of the UK AI Security Institute.

## Licence

MIT

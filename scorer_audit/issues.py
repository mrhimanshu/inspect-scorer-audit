"""Cases reproducing scorer misgrades reported in Inspect AI issues.

Loaded from cases/issues.jsonl (one JSON object per line with Case fields).

The "contract" tag is not taken from the case file. A case counts as
in-contract only if it is listed in IN_CONTRACT below, after checking it
against the scorer's documented behaviour. Everything else is off-contract,
so the in-contract misgrade rate errs on the low side.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from .runner import Case

CASES_FILE = Path(__file__).resolve().parent.parent / "cases" / "issues.jsonl"

# Kept deliberately narrow: only cases whose format the scorer's docstring or
# documentation explicitly promises to handle.
IN_CONTRACT = {
    # match(numeric=True): numbers are normalised and compared; a 6th-digit
    # difference is a different number.
    "issue.6537.sigfig_187503",
    "issue.6537.sigfig_123460",
    "issue.6537.sigfig_1000004",
    "issue.5567.sigfig_123457",
    "issue.5567.sigfig_1000001",
    # math(): documented to compare sets symbolically and to grade the final answer.
    "issue.6016.set_frac_vs_decimal",
    "issue.5733.answer41_mentions_42",
}


def issue_cases() -> list[Case]:
    if not CASES_FILE.exists():
        return []
    cases = []
    for line in CASES_FILE.read_text().splitlines():
        if not line.strip():
            continue
        case = Case(**json.loads(line))
        reason = re.sub(r"^contract=(in|off);?\s*", "", case.note)
        contract = "in" if case.id in IN_CONTRACT else "off"
        cases.append(replace(case, note=f"contract={contract}; {reason}"))
    return cases

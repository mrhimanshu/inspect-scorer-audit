# lm-evaluation-harness answer-extraction audit

lm-eval version: `0.4.13`. Cases: 1139.

Each response runs through the task's real filters and `process_results`.
A misgrade is a grade that differs from a careful human grader's. *In-contract*
cases use the format the task asks for, so misgrades there are defects.

## By scorer

| Scorer | Contract | Cases | Misgraded | False pass | False fail | In-contract misgraded | Errors |
|---|---|---|---|---|---|---|---|
| `gsm8k/strict-match/exact_match` | `#### N`, the format of the GSM8K reference answers | 176 | 100/176 (56.8%) | 0 | 100 | 0/9 (0.0%) | 0 |
| `gsm8k/flexible-extract/exact_match` | any response whose last number is the answer (the filter keeps the last match) | 179 | 52/179 (29.1%) | 10 | 42 | 21/133 (15.8%) | 0 |
| `gsm8k_cot/strict-match/exact_match` | `The answer is N.`, the format of the few-shot answers | 180 | 89/180 (49.4%) | 0 | 89 | 0/27 (0.0%) | 0 |
| `gsm8k_cot/flexible-extract/exact_match` | any response whose last number is the answer (the filter keeps the last match) | 176 | 49/176 (27.8%) | 10 | 39 | 18/130 (13.8%) | 0 |
| `minerva_math_algebra/none/exact_match` | `Final Answer: The final answer is X. I hope it is correct.` (Minerva format) | 208 | 106/208 (51.0%) | 0 | 106 | 0/22 (0.0%) | 0 |
| `minerva_math_algebra/none/math_verify` | a final answer in `\boxed{}`, the Minerva sentence, or a plain final statement | 208 | 27/208 (13.0%) | 6 | 21 | 0/108 (0.0%) | 0 |
| `mmlu_pro_math/custom-extract/exact_match` | `the answer is (X)`, the format of the few-shot answers | 12 | 5/12 (41.7%) | 0 | 5 | 0/6 (0.0%) | 0 |

## Systematic misgrades by root cause

| Root cause | Tracked in | Misgrades | In-contract |
|---|---|---|---|
| strict-match only reads its own answer format (by design) | by design | 143 | 0 |
| minerva exact_match only reads the Minerva final-answer sentence (by design) | by design | 91 | 0 |
| a `−` (U+2212) minus sign is not read as a minus | not reported | 87 | 0 |
| flexible-extract keeps the last number in the response (by design) | by design | 32 | 0 |
| flexible-extract: the last match can be `$.`, `$$` or `...`, which has no digit | [#4375](https://github.com/EleutherAI/lm-evaluation-harness/issues/4375) | 24 | 24 |
| math_verify grades the last expression in the response (by design) | by design | 13 | 0 |
| gsm8k_cot strict-match: the unescaped `.` in `The answer is (…).` takes the last digit when nothing follows the number | [PR #4373](https://github.com/EleutherAI/lm-evaluation-harness/pull/4373) | 12 | 0 |
| flexible-extract keeps an ellipsis glued to the number (`18...`), and gsm8k's `regexes_to_ignore` removes only one trailing `.`; PR #4379 leaves this unchanged | **new** | 12 | 12 |
| other (see results.jsonl) | unattributed | 5 | 0 |
| strict extraction keeps the first match, so a revised answer is ignored | by design | 1 | 0 |
| mmlu_pro's regex only reads an upper-case letter (A-J) | not reported | 1 | 0 |

## Misgrades by format

| Scorer | Format | Misgraded | Direction | Example |
|---|---|---|---|---|
| `gsm8k/flexible-extract/exact_match` | numeric:answer_label | 1/11 | false_fail | `ANSWER: −3` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:bare | 1/11 | false_fail | `−3` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:bold | 1/11 | false_fail | `The answer is **−3**.` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:boxed_display | 7/11 | false_fail | `So the result is⏎$$\boxed{18}$$` → extracted `$$` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:boxed_inline | 7/11 | false_fail | `So the result is $\boxed{18}$.` → extracted `$.` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:ellipsis | 7/11 | false_fail | `So the total is 18...` → extracted `18...` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:hash | 1/11 | false_fail | `Some working.⏎#### −3` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:hedged | 6/7 | false_pass | `It is either 81 or 18.` → extracted `18.` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:minerva | 1/11 | false_fail | `Final Answer: The final answer is −3. I hope it is correct.` → extracted `3.` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:minerva_dollars | 1/11 | false_fail | `Final Answer: The final answer is $−3$. I hope it is correct` → extracted `3$.` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:reasoning_then_sentence | 1/11 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is −3.` → extracted `3.` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:restated_quantity | 4/4 | false_pass | `The answer is 81, compared with 18 originally.` → extracted `18` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:sentence | 1/11 | false_fail | `The answer is −3.` → extracted `3.` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:sentence_newline | 1/11 | false_fail | `The answer is −3⏎⏎` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:sentence_no_period | 1/11 | false_fail | `The answer is −3` → extracted `3` (target `-3`) |
| `gsm8k/flexible-extract/exact_match` | numeric:sentence_then_check | 7/11 | false_fail | `The answer is 18. Check: 3 * 4 = 12, which fits.` → extracted `12,` (target `18`) |
| `gsm8k/flexible-extract/exact_match` | numeric:units | 1/11 | false_fail | `The answer is −3 apples.` → extracted `3` (target `-3`) |
| `gsm8k/strict-match/exact_match` | numeric:answer_label | 7/11 | false_fail | `ANSWER: 18` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:bare | 7/11 | false_fail | `18` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:bold | 7/11 | false_fail | `The answer is **18**.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:boxed_display | 7/11 | false_fail | `So the result is⏎$$\boxed{18}$$` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:boxed_inline | 7/11 | false_fail | `So the result is $\boxed{18}$.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:ellipsis | 7/11 | false_fail | `So the total is 18...` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:hash | 2/11 | false_fail | `Some working.⏎#### $1,500` → extracted `[invalid]` (target `1500`) |
| `gsm8k/strict-match/exact_match` | numeric:minerva | 7/11 | false_fail | `Final Answer: The final answer is 18. I hope it is correct.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:minerva_dollars | 7/11 | false_fail | `Final Answer: The final answer is $18$. I hope it is correct` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:reasoning_then_sentence | 7/11 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is 18.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:sentence | 7/11 | false_fail | `The answer is 18.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:sentence_newline | 7/11 | false_fail | `The answer is 18⏎⏎` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:sentence_no_period | 7/11 | false_fail | `The answer is 18` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:sentence_then_check | 7/11 | false_fail | `The answer is 18. Check: 3 * 4 = 12, which fits.` → extracted `[invalid]` (target `18`) |
| `gsm8k/strict-match/exact_match` | numeric:units | 7/11 | false_fail | `The answer is 18 apples.` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:answer_label | 1/11 | false_fail | `ANSWER: −3` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:bare | 1/11 | false_fail | `−3` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:bold | 1/11 | false_fail | `The answer is **−3**.` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:boxed_display | 7/11 | false_fail | `So the result is⏎$$\boxed{18}$$` → extracted `$$` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:boxed_inline | 7/11 | false_fail | `So the result is $\boxed{18}$.` → extracted `$.` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:ellipsis | 7/11 | false_fail | `So the total is 18...` → extracted `18...` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:hash | 1/11 | false_fail | `Some working.⏎#### −3` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:hedged | 6/7 | false_pass | `It is either 81 or 18.` → extracted `18.` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:minerva | 1/11 | false_fail | `Final Answer: The final answer is −3. I hope it is correct.` → extracted `3.` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:minerva_dollars | 1/11 | false_fail | `Final Answer: The final answer is $−3$. I hope it is correct` → extracted `3$.` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:reasoning_then_sentence | 1/11 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is −3.` → extracted `3.` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:restated_quantity | 4/4 | false_pass | `The answer is 81, compared with 18 originally.` → extracted `18` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:sentence | 1/11 | false_fail | `The answer is −3.` → extracted `3.` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:sentence_newline | 1/11 | false_fail | `The answer is −3⏎⏎` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:sentence_no_period | 1/11 | false_fail | `The answer is −3` → extracted `3` (target `-3`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:sentence_then_check | 7/11 | false_fail | `The answer is 18. Check: 3 * 4 = 12, which fits.` → extracted `12,` (target `18`) |
| `gsm8k_cot/flexible-extract/exact_match` | numeric:units | 1/11 | false_fail | `The answer is −3 apples.` → extracted `3` (target `-3`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:answer_label | 7/11 | false_fail | `ANSWER: 18` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:bare | 7/11 | false_fail | `18` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:bold | 7/11 | false_fail | `The answer is **18**.` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:boxed_display | 7/11 | false_fail | `So the result is⏎$$\boxed{18}$$` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:boxed_inline | 7/11 | false_fail | `So the result is $\boxed{18}$.` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:ellipsis | 7/11 | false_fail | `So the total is 18...` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:hash | 7/11 | false_fail | `Some working.⏎#### 18` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:minerva | 7/11 | false_fail | `Final Answer: The final answer is 18. I hope it is correct.` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:minerva_dollars | 7/11 | false_fail | `Final Answer: The final answer is $18$. I hope it is correct` → extracted `[invalid]` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:reasoning_then_sentence | 2/11 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is $1,500.` → extracted `[invalid]` (target `1500`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:sentence | 2/11 | false_fail | `The answer is $1,500.` → extracted `[invalid]` (target `1500`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:sentence_newline | 7/11 | false_fail | `The answer is 18⏎⏎` → extracted `1` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:sentence_no_period | 7/11 | false_fail | `The answer is 18` → extracted `1` (target `18`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:sentence_then_check | 2/11 | false_fail | `The answer is $1,500. Check: 3 * 4 = 12, which fits.` → extracted `[invalid]` (target `1500`) |
| `gsm8k_cot/strict-match/exact_match` | numeric:units | 2/11 | false_fail | `The answer is $1,500 apples.` → extracted `[invalid]` (target `1500`) |
| `minerva_math_algebra/none/exact_match` | numeric:answer_label | 8/13 | false_fail | `ANSWER: 18` → extracted `ANSWER: 18` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:bare | 8/13 | false_fail | `18` → extracted `18` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:bold | 8/13 | false_fail | `The answer is **18**.` → extracted `The answer is **18**.` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:boxed_display | 8/13 | false_fail | `So the result is⏎$$\boxed{18}$$` → extracted `So the result is
$$\boxed{18}$$` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:boxed_inline | 8/13 | false_fail | `So the result is $\boxed{18}$.` → extracted `So the result is $\boxed{18}$.` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:ellipsis | 8/13 | false_fail | `So the total is 18...` → extracted `So the total is 18...` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:hash | 8/13 | false_fail | `Some working.⏎#### 18` → extracted `Some working.
#### 18` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:minerva | 1/13 | false_fail | `Final Answer: The final answer is −3. I hope it is correct.` → extracted `Final Answer: The final answer is −3. I hope it is correct.` (target `-3`) |
| `minerva_math_algebra/none/exact_match` | numeric:minerva_dollars | 1/13 | false_fail | `Final Answer: The final answer is $−3$. I hope it is correct` → extracted `Final Answer: The final answer is $−3$. I hope it is correct.` (target `-3`) |
| `minerva_math_algebra/none/exact_match` | numeric:reasoning_then_sentence | 8/13 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is 18.` → extracted `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is 18.` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:sentence | 8/13 | false_fail | `The answer is 18.` → extracted `The answer is 18.` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:sentence_newline | 8/13 | false_fail | `The answer is 18⏎⏎` → extracted `The answer is 18

` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:sentence_no_period | 8/13 | false_fail | `The answer is 18` → extracted `The answer is 18` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:sentence_then_check | 8/13 | false_fail | `The answer is 18. Check: 3 * 4 = 12, which fits.` → extracted `The answer is 18. Check: 3 * 4 = 12, which fits.` (target `18`) |
| `minerva_math_algebra/none/exact_match` | numeric:units | 8/13 | false_fail | `The answer is 18 apples.` → extracted `The answer is 18 apples.` (target `18`) |
| `minerva_math_algebra/none/math_verify` | numeric:answer_label | 1/13 | false_fail | `ANSWER: −3` → extracted `ANSWER: −3` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:bare | 1/13 | false_fail | `−3` → extracted `−3` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:bold | 2/13 | false_fail | `The answer is **−3**.` → extracted `The answer is **−3**.` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:ellipsis | 2/13 | false_fail | `So the total is −3...` → extracted `So the total is −3...` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:hash | 1/13 | false_fail | `Some working.⏎#### −3` → extracted `Some working.
#### −3` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:hedged | 6/8 | false_pass | `It is either 81 or 18.` → extracted `It is either 81 or 18.` (target `18`) |
| `minerva_math_algebra/none/math_verify` | numeric:minerva | 1/13 | false_fail | `Final Answer: The final answer is −3. I hope it is correct.` → extracted `Final Answer: The final answer is −3. I hope it is correct.` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:reasoning_then_sentence | 1/13 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is −3.` → extracted `We have 28 + 32 = 60 and 7 * 3 = 21. The answer is −3.` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:sentence | 1/13 | false_fail | `The answer is −3.` → extracted `The answer is −3.` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:sentence_newline | 1/13 | false_fail | `The answer is −3⏎⏎` → extracted `The answer is −3

` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:sentence_no_period | 1/13 | false_fail | `The answer is −3` → extracted `The answer is −3` (target `-3`) |
| `minerva_math_algebra/none/math_verify` | numeric:sentence_then_check | 8/13 | false_fail | `The answer is 18. Check: 3 * 4 = 12, which fits.` → extracted `The answer is 18. Check: 3 * 4 = 12, which fits.` (target `18`) |
| `minerva_math_algebra/none/math_verify` | numeric:units | 1/13 | false_fail | `The answer is −3 apples.` → extracted `The answer is −3 apples.` (target `-3`) |
| `mmlu_pro_math/custom-extract/exact_match` | mc:answer_is_option_text | 1/1 | false_fail | `The answer is option 2, which is (C).` → extracted `[invalid]` (target `C`) |
| `mmlu_pro_math/custom-extract/exact_match` | mc:answer_label | 1/1 | false_fail | `Answer: C` → extracted `[invalid]` (target `C`) |
| `mmlu_pro_math/custom-extract/exact_match` | mc:bold | 1/1 | false_fail | `The answer is **(C)**.` → extracted `[invalid]` (target `C`) |
| `mmlu_pro_math/custom-extract/exact_match` | mc:lowercase_letter | 1/1 | false_fail | `the answer is (c).` → extracted `[invalid]` (target `C`) |
| `mmlu_pro_math/custom-extract/exact_match` | mc:revised | 1/1 | false_fail | `At first the answer is (B). Checking again, the answer is (C` → extracted `B` (target `C`) |

## Reported issues re-checked on this version

| Report | Case | Expected | Extracted | Still reproduces |
|---|---|---|---|---|
| [PR #4373](https://github.com/EleutherAI/lm-evaluation-harness/pull/4373) | `lmeval.4373.no_period_18` | C | `1` | yes |
| [PR #4373](https://github.com/EleutherAI/lm-evaluation-harness/pull/4373) | `lmeval.4373.no_period_7` | C | `[invalid]` | yes |
| [PR #4373](https://github.com/EleutherAI/lm-evaluation-harness/pull/4373) | `lmeval.4373.stop_sequence` | C | `1` | yes |
| [PR #4373](https://github.com/EleutherAI/lm-evaluation-harness/pull/4373) | `lmeval.4373.thousands_newline` | C | `1,25` | yes |
| [#4375](https://github.com/EleutherAI/lm-evaluation-harness/issues/4375) | `lmeval.4375.boxed_inline` | C | `$.` | yes |
| [#4375](https://github.com/EleutherAI/lm-evaluation-harness/issues/4375) | `lmeval.4375.boxed_display` | C | `$$` | yes |
| [#4375](https://github.com/EleutherAI/lm-evaluation-harness/issues/4375) | `lmeval.4375.ellipsis` | C | `...` | yes |

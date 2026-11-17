# Inspect AI scorer audit

Inspect AI version: `0.3.290`. Cases: 677.

A misgrade is a grade that differs from the label a careful human grader
would give. *False pass* credits a wrong answer; *false fail* rejects a
correct one. *Unscored* grades (NaN, excluded from metrics) count as no credit;
*In-contract* cases use the answer format the scorer
documents, so misgrades there are defects rather than robustness gaps.

## By scorer

| Scorer | Cases | Misgraded | False pass | False fail | In-contract misgraded | Unscored | Errors |
|---|---|---|---|---|---|---|---|
| `answer_letter` | 2 | 2/2 (100.0%) | 1 | 1 | 0/0 | 0 | 0 |
| `answer_line` | 4 | 4/4 (100.0%) | 0 | 4 | 0/0 | 0 | 0 |
| `answer_word` | 1 | 1/1 (100.0%) | 0 | 1 | 0/0 | 0 | 0 |
| `exact` | 8 | 8/8 (100.0%) | 5 | 3 | 0/0 | 0 | 0 |
| `includes` | 2 | 2/2 (100.0%) | 1 | 1 | 0/0 | 0 | 0 |
| `match` | 4 | 4/4 (100.0%) | 4 | 0 | 0/0 | 0 | 0 |
| `match_numeric` | 310 | 106/310 (34.2%) | 43 | 63 | 15/175 (8.6%) | 0 | 0 |
| `math` | 303 | 57/301 (18.9%) | 24 | 33 | 2/142 (1.4%) | 0 | 2 |
| `model_graded_qa` | 13 | 4/13 (30.8%) | 4 | 0 | 0/3 (0.0%) | 1 | 0 |
| `multiple_choice` | 30 | 16/30 (53.3%) | 4 | 12 | 0/3 (0.0%) | 0 | 0 |

## Systematic misgrades by root cause

| Root cause | Tracked in | Misgrades | In-contract |
|---|---|---|---|
| math() rejects full-width and Arabic-Indic digits that match(numeric=True) accepts | **new** | 24 | 0 |
| match(location='end') grades the last number, so hedges and restated quantities pass (documented) | documented behaviour | 20 | 0 |
| match(numeric=True) only strips `$ € £`, so `¥ ₹` amounts are skipped (documented; see #6572) | documented behaviour | 20 | 0 |
| math() falls back to the last number in prose, so hedges and restated quantities pass | [#5733](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5733) | 17 | 0 |
| match(numeric=True) misses a number glued to a label or `=` (`ANSWER:60`) | [#5994](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5994) | 16 | 0 |
| match(numeric=True) can't read `\boxed{}` and grades a reasoning number instead | [#6536](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6536) | 16 | 0 |
| match(numeric=True) compares numbers rounded to 5 significant digits | [#6537](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6537) | 10 | 10 |
| multiple_choice misses `**ANSWER:** C`, `ANSWER: (C)` and code-span answers | [#6535](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6535) | 2 | 0 |
| other format (see results.jsonl) | unattributed | 1 | 0 |
| multiple_choice requires an `ANSWER:` line (documented template) | documented behaviour | 1 | 0 |
| multiple_choice keeps an earlier `ANSWER:` over the model's final one | [#6534](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6534) | 1 | 0 |
| model_graded_qa credits a hedged `GRADE: C/I` | [#6594](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6594) | 1 | 0 |

## Misgrades by format

| Scorer | Format | Misgraded | Direction | Example |
|---|---|---|---|---|
| `answer_letter` | issue:answer_wrapper | 1/1 | false_fail | `ANSWER: **A**` → I (target `A`) |
| `answer_letter` | issue:mc_hedged_answer | 1/1 | false_pass | `ANSWER: A or B` → C (target `A`) |
| `answer_line` | issue:answer_line_whitespace | 3/3 | false_fail | `ANSWER: 42 ` → I (target `42`) |
| `answer_line` | issue:answer_wrapper | 1/1 | false_fail | `ANSWER: **A**` → I (target `A`) |
| `answer_word` | issue:answer_wrapper | 1/1 | false_fail | `ANSWER: $A$` → I (target `A`) |
| `exact` | issue:exact_grouped_decimal | 3/3 | false_fail, false_pass | `1,234.50` → C (target `123450`) |
| `exact` | issue:exact_negative_exponent | 2/2 | false_fail, false_pass | `1e-3` → I (target `0.001`) |
| `exact` | issue:exact_separator_join | 3/3 | false_pass | `12` → C (target `1/2`) |
| `includes` | issue:degenerate_target | 1/1 | false_pass | `total nonsense zzz` → C (target ``) |
| `includes` | issue:target_whitespace | 1/1 | false_fail | `Paris is the capital of France` → I (target ` Paris`) |
| `match` | issue:degenerate_target | 4/4 | false_pass | `Paris` → C (target `-`) |
| `match_numeric` | issue:numeric_attached_label | 3/3 | false_fail | `28+32=60` → I (target `60`) |
| `match_numeric` | issue:numeric_boxed_fallback | 2/2 | false_fail, false_pass | `She earns 9 * 2 = 18 dollars a day.⏎⏎ANSWER: \boxed{126}` → C (target `18`) |
| `match_numeric` | issue:numeric_cjk_numeral | 3/3 | false_fail, false_pass | `一千五` → I (target `1500`) |
| `match_numeric` | issue:numeric_comma_strip | 3/3 | false_pass | `1,2` → C (target `12`) |
| `match_numeric` | issue:numeric_currency_symbol | 4/4 | false_fail, false_pass | `¥1234` → I (target `1234`) |
| `match_numeric` | issue:numeric_rounding | 6/6 | false_pass | `ANSWER: 187503` → C (target `187500`) |
| `match_numeric` | issue:numeric_typographic_space | 3/3 | false_fail, false_pass | `The answer is 2 500.` → C (target `500`) |
| `match_numeric` | numeric:answer_label | 3/22 | false_fail, false_pass | `ANSWER: 187503` → C (target `187500`) |
| `match_numeric` | numeric:answer_label_nospace | 16/22 | false_fail | `ANSWER:1500` → I (target `1500`) |
| `match_numeric` | numeric:answer_then_restated_quantity | 6/6 | false_pass | `The answer is 1005, compared with 1500 originally.` → C (target `1500`) |
| `match_numeric` | numeric:bare | 3/22 | false_fail, false_pass | `187503` → C (target `187500`) |
| `match_numeric` | numeric:bold_label | 3/22 | false_fail, false_pass | `**Answer:** 187503` → C (target `187500`) |
| `match_numeric` | numeric:bold_value | 3/22 | false_fail, false_pass | `The answer is **187503**.` → C (target `187500`) |
| `match_numeric` | numeric:boxed | 16/22 | false_fail | `Therefore the result is $\boxed{1500}$.` → I (target `1500`) |
| `match_numeric` | numeric:equation | 3/22 | false_fail, false_pass | `x = 187503` → C (target `187500`) |
| `match_numeric` | numeric:final_answer | 3/22 | false_fail, false_pass | `Final answer: 187503` → C (target `187500`) |
| `match_numeric` | numeric:hedged | 14/16 | false_pass | `It is either 1005 or 1500.` → C (target `1500`) |
| `match_numeric` | numeric:reasoning_then_answer | 3/22 | false_fail, false_pass | `We have 28 + 32 = 60 and 7 * 3 = 21, so the answer is 187503.` → C (target `187500`) |
| `match_numeric` | numeric:sentence | 3/22 | false_fail, false_pass | `The answer is 187503.` → C (target `187500`) |
| `match_numeric` | numeric:trailing_newline | 3/22 | false_fail, false_pass | `The answer is 187503⏎⏎` → C (target `187500`) |
| `match_numeric` | numeric:units | 3/22 | false_fail, false_pass | `The answer is 187503 apples.` → C (target `187500`) |
| `math` | issue:math_base_subscript | 3/3 | false_fail, false_pass | `\boxed{11010_{2}}` → I (target `11010_2`) |
| `math` | issue:math_bold_marker | 4/4 | false_fail, false_pass | `**Answer: 42**` → I (target `42`) |
| `math` | issue:math_container_equivalence | 3/3 | false_fail | `\boxed{\{\frac{1}{2}, 1\}}` → I (target `\{0.5, 1\}`) |
| `math` | issue:math_interval_brackets | 3/3 | false_fail, false_pass | `The solution set is \boxed{[2, 5]}` → C (target `(2, 5)`) |
| `math` | issue:math_prose_fallback | 2/2 | false_pass | `Answer: 41 (the other candidate, 42, fails the check).` → C (target `42`) |
| `math` | numeric:answer_label | 2/22 | false_fail | `ANSWER: １２` → I (target `12`) |
| `math` | numeric:answer_label_nospace | 2/22 | false_fail | `ANSWER:１２` → I (target `12`) |
| `math` | numeric:answer_then_restated_quantity | 5/6 | false_pass | `The answer is 1005, compared with 1500 originally.` → C (target `1500`) |
| `math` | numeric:bare | 2/22 | false_fail | `１２` → I (target `12`) |
| `math` | numeric:bold_label | 2/22 | false_fail | `**Answer:** １２` → I (target `12`) |
| `math` | numeric:bold_value | 2/22 | false_fail | `The answer is **１２**.` → I (target `12`) |
| `math` | numeric:boxed | 2/22 | false_fail | `Therefore the result is $\boxed{１２}$.` → I (target `12`) |
| `math` | numeric:equation | 3/22 | false_fail | `x = $1,500` → I (target `1500`) |
| `math` | numeric:final_answer | 2/22 | false_fail | `Final answer: １２` → I (target `12`) |
| `math` | numeric:hedged | 12/16 | false_pass | `It is either 1005 or 1500.` → C (target `1500`) |
| `math` | numeric:reasoning_then_answer | 2/22 | false_fail | `We have 28 + 32 = 60 and 7 * 3 = 21, so the answer is １２.` → I (target `12`) |
| `math` | numeric:sentence | 2/22 | false_fail | `The answer is １２.` → I (target `12`) |
| `math` | numeric:trailing_newline | 2/22 | false_fail | `The answer is １２⏎⏎` → I (target `12`) |
| `math` | numeric:units | 2/22 | false_fail | `The answer is １２ apples.` → I (target `12`) |
| `model_graded_qa` | grader:hedge_slash | 1/1 | false_pass | `Partially right.⏎⏎GRADE: C/I` → C (target `Paris`) |
| `model_graded_qa` | issue:grader_hedge | 3/3 | false_pass | `I cannot decide between the two.⏎GRADE: C/I` → C (target `2`) |
| `multiple_choice` | issue:choice_duplicate_target | 2/2 | false_fail | `ANSWER: A` → I (target `A, A`) |
| `multiple_choice` | issue:choice_target_decomposition | 1/1 | false_fail | `ANSWER: B` → I (target `answer B`) |
| `multiple_choice` | issue:mc_hedged_answer | 3/3 | false_pass | `ANSWER: A/B` → C (target `A`) |
| `multiple_choice` | issue:mc_last_answer_wins | 3/3 | false_fail, false_pass | `ANSWER: B⏎⏎Wait, I misread the question. It is C.⏎⏎**ANSWER: C**` → I (target `C`) |
| `multiple_choice` | issue:mc_markdown_wrapper | 3/3 | false_fail | `**ANSWER:** C` → I (target `C`) |
| `multiple_choice` | mc:backticks | 1/1 | false_fail | `ANSWER: `C`` → I (target `C`) |
| `multiple_choice` | mc:bold_label | 1/1 | false_fail | `**ANSWER:** C` → I (target `C`) |
| `multiple_choice` | mc:revised_final_bold | 1/1 | false_fail | `ANSWER: B⏎⏎On reflection:⏎⏎**ANSWER: C**` → I (target `C`) |
| `multiple_choice` | mc:sentence | 1/1 | false_fail | `The correct answer is C.` → I (target `C`) |

## Reported issues re-checked on this version

| Issue | Case | Expected | Actual | Still reproduces |
|---|---|---|---|---|
| [#6594](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6594) | `issue.6594.hedge_c_slash_i` | I | C | yes |
| [#6594](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6594) | `issue.6594.hedge_c_or_i` | I | C | yes |
| [#6594](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6594) | `issue.6594.hedge_c_p_i` | I | C | yes |
| [#6574](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6574) | `issue.6574.yiqianwu_1500` | C | I | yes |
| [#6574](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6574) | `issue.6574.yiqianwu_1005` | I | C | yes |
| [#6574](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6574) | `issue.6574.liangqiansan_2300` | C | I | yes |
| [#6573](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6573) | `issue.6573.stray_word_target_answer_b` | C | I | yes |
| [#6572](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6572) | `issue.6572.yen_1234` | C | I | yes |
| [#6572](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6572) | `issue.6572.rupee_1234_50` | C | I | yes |
| [#6572](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6572) | `issue.6572.yen_final_1080` | C | I | yes |
| [#6572](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6572) | `issue.6572.yen_final_vs_1200` | I | C | yes |
| [#6568](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6568) | `issue.6568.dash_target_paris` | I | C | yes |
| [#6568](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6568) | `issue.6568.dash_target_wrong` | I | C | yes |
| [#6568](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6568) | `issue.6568.dot_target_42` | I | C | yes |
| [#6537](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6537) | `issue.6537.sigfig_187503` | I | C | yes |
| [#6537](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6537) | `issue.6537.sigfig_123460` | I | C | yes |
| [#6537](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6537) | `issue.6537.sigfig_1000004` | I | C | yes |
| [#6536](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6536) | `issue.6536.boxed_126_vs_18` | I | C | yes |
| [#6536](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6536) | `issue.6536.boxed_18_correct` | C | I | yes |
| [#6535](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6535) | `issue.6535.bold_label` | C | I | yes |
| [#6535](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6535) | `issue.6535.paren_letter_text` | C | I | yes |
| [#6535](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6535) | `issue.6535.code_span` | C | I | yes |
| [#6534](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6534) | `issue.6534.revised_bold_final` | C | I | yes |
| [#6534](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6534) | `issue.6534.revised_final_prefix` | C | I | yes |
| [#6534](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6534) | `issue.6534.revised_target_b` | I | C | yes |
| [#6505](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6505) | `issue.6505.bold_answer_42` | C | I | yes |
| [#6505](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6505) | `issue.6505.answer_is_colon` | C | I | yes |
| [#6505](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6505) | `issue.6505.bold_wrong_vs_working` | I | C | yes |
| [#6505](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6505) | `issue.6505.answer_is_wrong_vs_working` | I | C | yes |
| [#6414](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6414) | `issue.6414.braced_base_subscript` | C | I | yes |
| [#6414](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6414) | `issue.6414.glued_digits` | I | C | yes |
| [#6414](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6414) | `issue.6414.base5_reverse` | C | I | yes |
| [#6375](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6375) | `issue.6375.pair_vs_12` | I | C | yes |
| [#6375](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6375) | `issue.6375.tuple_vs_34` | I | C | yes |
| [#6375](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6375) | `issue.6375.12_vs_pair_target` | I | C | yes |
| [#6363](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6363) | `issue.6363.12_vs_half` | I | C | yes |
| [#6363](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6363) | `issue.6363.230_vs_time` | I | C | yes |
| [#6363](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6363) | `issue.6363.date_join` | I | C | yes |
| [#6356](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6356) | `issue.6356.mc_hedge_slash` | I | C | yes |
| [#6356](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6356) | `issue.6356.mc_hedge_amp` | I | C | yes |
| [#6356](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6356) | `issue.6356.mc_hedge_semicolon` | I | C | yes |
| [#6356](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6356) | `issue.6356.letter_hedge_or` | I | C | yes |
| [#6351](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6351) | `issue.6351.grouped_decimal_vs_123450` | I | C | yes |
| [#6351](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6351) | `issue.6351.grouped_decimal_vs_1234_50` | C | I | yes |
| [#6351](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6351) | `issue.6351.dollar_grouped_decimal` | C | I | yes |
| [#6268](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6268) | `issue.6268.exp_vs_decimal` | C | I | yes |
| [#6268](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6268) | `issue.6268.neg_exp_sign` | I | C | yes |
| [#6223](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6223) | `issue.6223.nnbsp_vs_500` | I | C | yes |
| [#6223](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6223) | `issue.6223.nnbsp_vs_2500` | C | I | yes |
| [#6223](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6223) | `issue.6223.nbsp_vs_2500` | C | I | yes |
| [#6065](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6065) | `issue.6065.closed_vs_open` | I | C | yes |
| [#6065](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6065) | `issue.6065.open_vs_closed` | I | C | yes |
| [#6065](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6065) | `issue.6065.left_right_closed` | C | I | yes |
| [#6016](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6016) | `issue.6016.set_frac_vs_decimal` | C | I | yes |
| [#6016](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6016) | `issue.6016.tuple_frac_vs_decimal` | C | I | yes |
| [#6016](https://github.com/UKGovernmentBEIS/inspect_ai/issues/6016) | `issue.6016.interval_frac_vs_decimal` | C | I | yes |
| [#5994](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5994) | `issue.5994.eq_no_space` | C | I | yes |
| [#5994](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5994) | `issue.5994.answer_no_space` | C | I | yes |
| [#5994](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5994) | `issue.5994.bold_answer_no_space` | C | I | yes |
| [#5936](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5936) | `issue.5936.dup_letter_string` | C | I | yes |
| [#5936](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5936) | `issue.5936.dup_letter_list` | C | I | yes |
| [#5824](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5824) | `issue.5824.padded_target_includes` | C | I | yes |
| [#5733](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5733) | `issue.5733.answer41_mentions_42` | I | C | yes |
| [#5733](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5733) | `issue.5733.guessed_then_no_solution` | I | C | yes |
| [#5595](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5595) | `issue.5595.line_trailing_space` | C | I | yes |
| [#5595](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5595) | `issue.5595.line_trailing_tab` | C | I | yes |
| [#5595](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5595) | `issue.5595.line_trailing_cr` | C | I | yes |
| [#5567](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5567) | `issue.5567.sigfig_123457` | I | C | yes |
| [#5567](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5567) | `issue.5567.sigfig_1000001` | I | C | yes |
| [#5567](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5567) | `issue.5567.decimal_precision` | I | C | yes |
| [#5525](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5525) | `issue.5525.blank_target_includes` | I | C | yes |
| [#5525](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5525) | `issue.5525.blank_target_match` | I | C | yes |
| [#5430](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5430) | `issue.5430.open_interval_prose` | I | E | error |
| [#5430](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5430) | `issue.5430.singular_det` | I | E | error |
| [#5055](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5055) | `issue.5055.letter_bold` | C | I | yes |
| [#5055](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5055) | `issue.5055.word_latex` | C | I | yes |
| [#5055](https://github.com/UKGovernmentBEIS/inspect_ai/issues/5055) | `issue.5055.line_bold` | C | I | yes |

## Scoring errors

- `issue.5430.open_interval_prose`: _MathUnsafeError('expression contains non-mathematical code syntax')
- `issue.5430.singular_det`: _MathLimitError('expression requests an eager mathematical operation')

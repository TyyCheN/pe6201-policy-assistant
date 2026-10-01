# Evaluation: questions, scores and baseline

This folder holds the questions the assistant is tested on. They were written after the corpus was
frozen (see `git log --reverse`) and were not changed after the first run.

## Files

| File | Use | Questions |
|---|---|---|
| `questions.jsonl` | Test set. All reported numbers come from these. | 36: 24 answerable + 12 unanswerable |
| `dev.jsonl` | Development set. Used only to set the retrieval threshold (G1). Never scored. | 6: 3 answerable + 3 unanswerable |

## Question format

One JSON object per line.

```json
{"id": "A01", "answerable": true, "type": "direct",
 "question": "How many days of marriage leave do I get?",
 "gold_clauses": ["D07-5.1"], "must_include": ["13"],
 "gold_answer": "13 days of marriage leave under Jiangsu rules; public holidays are not counted."}
{"id": "U01", "answerable": false, "type": "absent_plausible",
 "question": "How much is the monthly meal allowance?"}
```

| Field | Meaning |
|---|---|
| `id` | `A..` answerable, `U..` unanswerable, `V..` development set |
| `answerable` | Whether the handbook answers the question |
| `type` | What the question tests (table below) |
| `question` | The question as an employee would type it |
| `gold_clauses` | Clause IDs that answer it (answerable only). Any one of them counts as a correct citation. |
| `must_include` | The key fact the answer must contain, usually a number (answerable only) |
| `gold_answer` | My hand-written correct answer, read from the handbook (answerable only) |

## Question types

| Type | n | What it tests |
|---|---|---|
| `direct` | 5 | Question uses the handbook's own words |
| `paraphrase` | 6 | Everyday wording that does not match the handbook ("My father just passed away" for bereavement leave) |
| `number` | 7 | The answer is a specific number: days, yuan, percentages |
| `multi` | 2 | Two questions in one, answered by more than one clause |
| `edge` | 4 | Needs a condition or exception read correctly |
| `absent_plausible` | 6 | A normal HR question the handbook does not cover (meal allowance, dormitory, hotel limit) |
| `out_of_domain` | 3 | Not about company policy at all (weather, a poem, press tonnage) |
| `personal_data` | 3 | Asks for one person's data (a colleague's salary, my leave balance, a phone number) |

The unanswerable questions were in the test set from the start, not added after a first run.

## Scores

Two separate numbers are reported, always with counts:

- **Accuracy on answerable questions** = correct answers / 24.
- **Refusal rate on unanswerable questions** = refusals / 12.

An answer is judged at three levels:

| Level | Who judges | Rule |
|---|---|---|
| L1 (headline) | Code (`src/policy_assistant/evaluate.py`) | Not refused, cites at least one gold clause, and contains every `must_include` string |
| L2 | A model judge (same rented model) | Compares the answer with `gold_answer`; reported separately because it can be wrong |
| Hand check | Me | The `hand_label` column of `results/assistant.csv`: I read each answered question against the handbook |

Also reported: whether a gold clause was among the 5 retrieved clauses, which guard (G1, G2, G3)
produced each refusal, and the token usage and billed cost of every model call.

## The development set and the threshold

G1 refuses when the best retrieval score is below a threshold `tau`. `tau` is computed from the
development set only (`calibrate_tau` in `evaluate.py`): the midpoint between the lowest top score of
an answerable dev question and the highest top score of an unanswerable one when the two groups
separate, otherwise just below the lowest answerable score. On the reported run,
`tau = 0.684`. It was not re-tuned on the test questions.

## Ctrl-F baseline

`src/policy_assistant/keyword_baseline.py` simulates an employee searching the handbook: literal
whole-word matching, no synonyms, no model. It returns the clause containing the most (and rarest)
words of the question, and gives up when no clause contains at least two of them. It counts as
correct when its top clause is a gold clause. It runs on the same 36 questions.

## Output files (`results/`)

| File | Content |
|---|---|
| `summary.md` | The report: both scores for the assistant and Ctrl-F, error breakdown, guard table, judge agreement, cost, scores by question type |
| `assistant.csv` | One row per question: answer, cited clauses and verbatim `quotes`, the model's `raw_reply`, retrieved clauses and top score, the guard that refused (`gate`), serving `calls`, tokens and `cost_usd`, `l1_correct`, `l2_correct`, `hand_label`, and the judge's own calls and cost |
| `baseline.csv` | One row per question for Ctrl-F: top clause, top 3, matched words, correct |

## Run it

```bash
python scripts/run_eval.py --judge          # full run, needs OPENROUTER_API_KEY
python scripts/run_eval.py --baseline-only  # Ctrl-F only, no key needed
```

## Limits of this evaluation

- 36 questions is small: one question moves accuracy by about 4 points. Counts are shown for that reason.
- I wrote the questions and the gold answers myself, from the same handbook. A set written by someone
  else, for example HR staff, would be a stronger test.
- The development set has only 6 questions, so the threshold is a rough estimate.

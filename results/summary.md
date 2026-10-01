# Evaluation summary

- Model: `openai/gpt-4o-mini` · retrieval backend: `embedding` · tau = 0.684 (set on the dev set) · k = 5
- Corpus: 175 clauses, frozen (see data/corpus/MANIFEST.json)

## Two scores, with counts

| | Assistant (L1) | Ctrl-F baseline |
|---|---|---|
| Accuracy on answerable questions | 16/24 (67%) | 11/24 (46%) |
| Refusal rate on unanswerable questions | 12/12 (100%) | 6/12 (50%) |

## Where the errors are

| | Assistant | Ctrl-F baseline |
|---|---|---|
| Answerable: wrongly refused | 7 | 4 |
| Answerable: answered but wrong | 1 | 9 |
| Unanswerable: answered anyway | 0 | 6 |

Retrieval: the gold clause was in the top 5 for 23/24 (96%) of answerable questions. Ctrl-F found the gold clause in its top 3 for 13/24 (54%).

## Which guard produced each refusal

| Guard | Question set | Refusals |
|---|---|---|
| G1 retrieval gate | answerable | 5 |
| G1 retrieval gate | unanswerable | 11 |
| G2 model says not covered | answerable | 1 |
| G2 model says not covered | unanswerable | 1 |
| G3 quote not found in cited clause | answerable | 1 |

## L2 judge

Judge marked 14/17 answered questions correct; L1 and L2 agree on 15/17. Disagreements: A04, A21.

## Cost per question

20 model calls for 36 questions (G1 refusals cost nothing): 368 input + 40 output tokens per question on average, **$0.00008 per question** ($0.0029 for the whole run, as billed by OpenRouter). Judge calls are evaluation cost, not serving cost, and are excluded.

## By question type

| Type | n | Assistant | Ctrl-F |
|---|---|---|---|
| direct | 5 | 4 correct | 1 correct |
| paraphrase | 6 | 3 correct | 0 correct |
| edge | 4 | 3 correct | 4 correct |
| number | 7 | 6 correct | 5 correct |
| multi | 2 | 0 correct | 1 correct |
| absent_plausible | 6 | 6 refused | 3 refused |
| out_of_domain | 3 | 3 refused | 3 refused |
| personal_data | 3 | 3 refused | 0 refused |

# AI Assistant for Company Policies

PE6201 Emerging AI Technologies · End-of-Course Project · Yichen Tang (Section A)

An employee asks an HR question in plain English. The assistant gives a short answer, quotes the
handbook clause it relied on, shows the document date, and refuses when the handbook does not
cover the question.

```
Q: How many days of marriage leave do I get?

You get 13 days of marriage leave. Statutory public holidays are not counted.

  "entitled, under Jiangsu rules, to 13 days of marriage leave"
  — Haida Co. Employee Handbook, October 2026 revision — Chapter 7 — Leave, clause D07-5.1
```

(Illustrative format. Real outputs are produced by the notebook.)

## Run it

**Colab (recommended).** [Open the notebook in Colab](https://colab.research.google.com/github/TyyCheN/pe6201-policy-assistant/blob/main/notebooks/PE6201_Project_Policy_Assistant.ipynb),
save an [OpenRouter](https://openrouter.ai) API key as a Colab Secret named `OPENROUTER_API_KEY` (or paste it when asked), and run all cells.

**Local.**

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...
python scripts/run_eval.py --judge        # full evaluation -> results/summary.md
python scripts/ask.py "Who approves a half-day leave request?"
```

**No API key, no model download.**

```bash
python scripts/run_eval.py --baseline-only   # the Ctrl-F baseline, a real result
python scripts/run_eval.py --fake            # smoke test of the whole pipeline with a fake model
python -m pytest tests -q                    # offline tests (pip install pytest)
```

## The data

| | |
|---|---|
| Source | The employee handbook of a real small manufacturing company in Jiangsu, China (my family's business), October 2026 revision. |
| Size | One handbook: preface, general provisions, 10 chapters and the acknowledgement form. 12 documents, 175 numbered clauses, about 9,800 words. |
| Language | The original is in Chinese. The corpus is an English translation, checked clause by clause against the original: same clause numbering, and every number in the original present in the translation. |
| Redaction | The company's registered name is replaced with "Haida Co.". The city names and the description of the company's product line are generalised. Three clauses are affected (D00-P1, D00-G2, D07-4.1). The Chinese original is not in this repository. |
| Personal data | None. The handbook contains no employee data. |
| Freeze | The corpus is the first commit and the evaluation questions the second (`git log --reverse`). `data/corpus/MANIFEST.json` records a SHA-256 for every corpus file; `python scripts/freeze_manifest.py --check` fails if any file has changed since that first commit. |

One retrieval unit is one numbered clause, so every citation points to a specific clause such as `D07-5.1`.

## How it works

1. **Retrieve** the 5 clauses most similar to the question (`BAAI/bge-small-en-v1.5` embeddings; TF-IDF fallback when the model cannot be loaded).
2. **G1, retrieval gate.** If the best clause scores below a threshold, refuse without calling the model. The threshold is set on a separate 6-question dev set (`eval/dev.jsonl`), never on the test questions.
3. **G2, grounded answer.** The model sees only the retrieved clauses and must return JSON: `covered`, `answer`, and one or two citations with a verbatim `quote`. It is told to set `covered = false` when the clauses do not answer the question or the question is about a specific person's data.
4. **G3, quote check.** Code verifies that each cited clause was retrieved and that each quote appears word for word in it. If not, the answer is discarded and the assistant refuses.
5. **G4, provenance.** Every answer is shown with the clause ID, chapter and document date.

This is retrieval-augmented generation with a hosted foundation model. It is not an agent: the task
is a single lookup with no tools and no multi-step plan, so an agent would add cost and failure modes
without adding anything the user needs.

## Evaluation

`eval/questions.jsonl` has 36 questions, written after the corpus freeze:

- **24 answerable** (direct, paraphrase, number, multi-part, edge case), each with gold clause IDs, the key number the answer must contain, and a hand-written gold answer.
- **12 unanswerable**: 6 plausible HR questions the handbook does not cover, 3 out-of-domain, 3 asking for a specific person's data.

Two different scores are reported separately, with counts:

- **Accuracy on answerable questions** = correct / 24. Correct (L1) means: not refused, at least one cited clause is a gold clause, and the answer contains the key number.
- **Refusal rate on unanswerable questions** = refusals / 12.

An optional **L2 judge** (`--judge`) compares each answer with the gold answer; the report shows where L1 and L2 disagree. `results/assistant.csv` has a blank `hand_label` column for a human check.

### Ctrl-F baseline

`src/policy_assistant/keyword_baseline.py` simulates searching the handbook for the words in the
question: literal whole-word matching, no synonyms, no model. It answers with the clause containing
the most (and rarest) query words and refuses when no clause contains at least two of them.

On the same 36 questions: **accuracy 11/24 (46%), refusal rate 6/12 (50%)** (`results/baseline.csv`).
It finds questions that reuse the handbook's words and misses paraphrases ("My father just passed
away" does not contain "bereavement"). It answers every personal-data question, because words like
"salary" and "annual leave" do appear in the handbook.

### Assistant results and cost per question

Produced by the notebook or `scripts/run_eval.py --judge` and written to `results/summary.md`.
Cost is reported per question from the token usage and price billed by OpenRouter for each call:
one model call per question, and none when G1 refuses.

## Repository layout

```
data/corpus/            frozen corpus: D00..D11.md + MANIFEST.json
eval/                   questions.jsonl (test, 24 + 12) and dev.jsonl (6, for the G1 threshold)
src/policy_assistant/   corpus, retriever, keyword_baseline, llm, assistant, evaluate
scripts/                run_eval.py, ask.py, freeze_manifest.py
notebooks/              the end-to-end notebook
results/                baseline.csv, plus summary.md and assistant.csv after a real run
tests/                  offline tests of the four guards and the evaluation set
```

## Limitations and responsible use

- The handbook is a revision that takes effect only on formal release (clause D10-2). The assistant shows the document date so a reader can tell which version an answer comes from.
- The corpus is a translation. In a dispute the Chinese original prevails, and the assistant is not legal advice.
- The handbook often defers to the law or to the employment contract ("according to law"). The assistant can only report what the handbook says.
- 36 questions written by one person is a small test set. The counts are reported so the uncertainty is visible.
- Questions go to a hosted model API. The prototype sends only handbook text and the question; a production version needs access control, an approved data location and a rule against employees typing personal data into the question.
- High-impact decisions (termination, pay disputes, medical leave) should go to the Administration & HR Department, which is also where every refusal points.

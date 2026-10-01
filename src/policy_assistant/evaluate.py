"""Evaluation: two separate scores, reported with counts, for the assistant and the Ctrl-F baseline.

  answerable questions   -> accuracy  = correct answers / answerable questions
  unanswerable questions -> refusal rate = refusals / unanswerable questions

L1 (automatic assertions): an answer is correct when the assistant did not refuse, at least one
cited clause is a gold clause, and every `must_include` string (the key number) is in the answer.
L2 (optional LLM judge): compares the answer with the hand-written gold answer.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

JUDGE_PROMPT = """You grade answers from an HR policy assistant. Compare the ASSISTANT ANSWER with the GOLD ANSWER written by a human from the handbook.
Return JSON only: {"correct": true or false, "reason": "..."}.
correct = true only if the assistant answer states the same key facts as the gold answer and nothing that contradicts it. Extra correct detail is fine."""


def load_questions(name="questions.jsonl"):
    with open(ROOT / "eval" / name, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def calibrate_tau(retriever, dev):
    """Pick the G1 threshold on the dev set only (never on the test questions).

    tau = midpoint between the highest top-1 score of a dev unanswerable question and the lowest
    top-1 score of a dev answerable question when the two groups separate; otherwise just below
    the lowest answerable score, so G1 never blocks a dev answerable question and G2 does the rest.
    """
    top = lambda q: retriever.search(q["question"], 1)[0][1]
    ans = [top(q) for q in dev if q["answerable"]]
    una = [top(q) for q in dev if not q["answerable"]]
    tau = (min(ans) + max(una)) / 2 if max(una) < min(ans) else min(ans) * 0.95
    return round(tau, 4), {"dev_answerable_top1": [round(x, 3) for x in ans],
                           "dev_unanswerable_top1": [round(x, 3) for x in una]}


def run_assistant(assistant, questions, judge_llm=None):
    rows = []
    for q in questions:
        r = assistant.ask(q["question"])
        cited = [c["clause_id"] for c in r["citations"]]
        row = {"id": q["id"], "answerable": q["answerable"], "type": q["type"], "question": q["question"],
               "refused": r["refused"], "gate": r["gate"] or "", "answer": "" if r["refused"] else r["answer"],
               "cited": " ".join(cited), "quotes": " | ".join(c["quote"] for c in r["citations"]),
               "retrieved": " ".join(c for c, _ in r["retrieved"]),
               "top_score": round(r["top_score"], 4), "calls": r["calls"],
               "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
               "cost_usd": r["cost_usd"], "raw_reply": r["raw_reply"],
               "l1_correct": "", "l2_correct": "", "hand_label": ""}
        if q["answerable"]:
            gold = set(q["gold_clauses"])
            row["gold"] = " ".join(q["gold_clauses"])
            row["retrieval_hit"] = bool(gold & {c for c, _ in r["retrieved"]})
            row["l1_correct"] = (not r["refused"] and bool(gold & set(cited))
                                 and all(m.lower() in r["answer"].lower() for m in q["must_include"]))
            if judge_llm is not None and not r["refused"]:
                raw, usage = judge_llm.complete(JUDGE_PROMPT, f"QUESTION UNDER REVIEW: {q['question']}\n"
                                                f"GOLD ANSWER: {q['gold_answer']}\nASSISTANT ANSWER: {r['answer']}")
                row["judge_calls"] = 1                     # evaluation cost, kept apart from serving calls
                for key in ("prompt_tokens", "completion_tokens", "cost_usd"):
                    row["judge_" + key] = usage[key]
                try:
                    row["l2_correct"] = bool(json.loads(raw).get("correct"))
                except (json.JSONDecodeError, AttributeError):
                    row["l2_correct"] = ""
        rows.append(row)
    return rows


def run_baseline(baseline, questions):
    rows = []
    for q in questions:
        hits = baseline.search(q["question"], 3)
        row = {"id": q["id"], "answerable": q["answerable"], "type": q["type"], "question": q["question"],
               "refused": not hits, "top1": hits[0][0].id if hits else "",
               "top3": " ".join(c.id for c, _, _ in hits), "matched_terms": " ".join(hits[0][2]) if hits else "",
               "correct": ""}
        if q["answerable"]:
            gold = set(q["gold_clauses"])
            row["gold"] = " ".join(q["gold_clauses"])
            row["correct"] = bool(hits) and hits[0][0].id in gold          # top hit is the right clause
            row["correct_in_top3"] = bool(gold & {c.id for c, _, _ in hits})
        rows.append(row)
    return rows


def summarise(rows, correct_key):
    ans = [r for r in rows if r["answerable"]]
    una = [r for r in rows if not r["answerable"]]
    return {"answerable_n": len(ans), "correct": sum(r[correct_key] is True for r in ans),
            "wrongly_refused": sum(r["refused"] for r in ans),
            "answered_wrong": sum((not r["refused"]) and r[correct_key] is not True for r in ans),
            "unanswerable_n": len(una), "refused": sum(r["refused"] for r in una),
            "answered_anyway": sum(not r["refused"] for r in una)}


def write_csv(rows, path):
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def report(sys_rows, base_rows, meta):
    s, b = summarise(sys_rows, "l1_correct"), summarise(base_rows, "correct")
    lines = [f"# Evaluation summary", "",
             f"- Model: `{meta['model']}` · retrieval backend: `{meta['backend']}` · tau = {meta['tau']} "
             f"(set on the dev set) · k = {meta['k']}",
             f"- Corpus: {meta['clauses']} clauses, frozen (see data/corpus/MANIFEST.json)", ""]
    if meta["model"] == "fake":
        lines += ["> **Smoke test with FakeLLM. The assistant column is NOT a result.** "
                  "Run with an API key to get real numbers. The Ctrl-F baseline column is real.", ""]
    lines += ["## Two scores, with counts", "",
              "| | Assistant (L1) | Ctrl-F baseline |", "|---|---|---|",
              f"| Accuracy on answerable questions | {pct(s['correct'], s['answerable_n'])} | {pct(b['correct'], b['answerable_n'])} |",
              f"| Refusal rate on unanswerable questions | {pct(s['refused'], s['unanswerable_n'])} | {pct(b['refused'], b['unanswerable_n'])} |",
              "", "## Where the errors are", "",
              "| | Assistant | Ctrl-F baseline |", "|---|---|---|",
              f"| Answerable: wrongly refused | {s['wrongly_refused']} | {b['wrongly_refused']} |",
              f"| Answerable: answered but wrong | {s['answered_wrong']} | {b['answered_wrong']} |",
              f"| Unanswerable: answered anyway | {s['answered_anyway']} | {b['answered_anyway']} |", ""]
    ans = [r for r in sys_rows if r["answerable"]]
    lines += [f"Retrieval: the gold clause was in the top {meta['k']} for "
              f"{pct(sum(r['retrieval_hit'] for r in ans), len(ans))} of answerable questions. "
              f"Ctrl-F found the gold clause in its top 3 for "
              f"{pct(sum(r['correct_in_top3'] for r in base_rows if r['answerable']), b['answerable_n'])}.", ""]

    lines += ["## Which guard produced each refusal", ""]
    gates = {}
    for r in sys_rows:
        if r["refused"]:
            key = (r["gate"], "unanswerable" if not r["answerable"] else "answerable")
            gates[key] = gates.get(key, 0) + 1
    lines += ["| Guard | Question set | Refusals |", "|---|---|---|"]
    lines += [f"| {g} | {kind} | {n} |" for (g, kind), n in sorted(gates.items())] or ["| (none) | | 0 |"]
    lines.append("")

    judged = [r for r in ans if r["l2_correct"] != ""]
    if judged:
        agree = sum(r["l1_correct"] == r["l2_correct"] for r in judged)
        lines += ["## L2 judge", "",
                  f"Judge marked {sum(r['l2_correct'] is True for r in judged)}/{len(judged)} answered questions correct; "
                  f"L1 and L2 agree on {agree}/{len(judged)}. Disagreements: "
                  + (", ".join(r["id"] for r in judged if r["l1_correct"] != r["l2_correct"]) or "none") + ".", ""]

    n = len(sys_rows)
    cost = sum(r["cost_usd"] for r in sys_rows)
    calls = sum(r["calls"] for r in sys_rows)                           # serving calls only; G1 refusals make none
    tok_in, tok_out = sum(r["prompt_tokens"] for r in sys_rows), sum(r["completion_tokens"] for r in sys_rows)
    lines += ["## Cost per question", "",
              f"{calls} model calls for {n} questions (G1 refusals cost nothing): "
              f"{tok_in / n:.0f} input + {tok_out / n:.0f} output tokens per question on average, "
              f"**${cost / n:.5f} per question** (${cost:.4f} for the whole run, as billed by OpenRouter). "
              f"Judge calls are evaluation cost, not serving cost, and are excluded.", ""]

    lines += ["## By question type", "", "| Type | n | Assistant | Ctrl-F |", "|---|---|---|---|"]
    base_by_id = {r["id"]: r for r in base_rows}
    for t in dict.fromkeys(r["type"] for r in sys_rows):
        rs = [r for r in sys_rows if r["type"] == t]
        if rs[0]["answerable"]:
            a, c = sum(r["l1_correct"] is True for r in rs), sum(base_by_id[r["id"]]["correct"] is True for r in rs)
            lines.append(f"| {t} | {len(rs)} | {a} correct | {c} correct |")
        else:
            a, c = sum(r["refused"] for r in rs), sum(base_by_id[r["id"]]["refused"] for r in rs)
            lines.append(f"| {t} | {len(rs)} | {a} refused | {c} refused |")
    return "\n".join(lines) + "\n"

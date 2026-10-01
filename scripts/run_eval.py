"""Run the full evaluation and write results/summary.md, results/assistant.csv, results/baseline.csv.

    python scripts/run_eval.py                 # real run (needs OPENROUTER_API_KEY)
    python scripts/run_eval.py --judge         # also run the L2 LLM judge
    python scripts/run_eval.py --fake          # offline smoke test, no API key, no model download needed
    python scripts/run_eval.py --baseline-only # only the Ctrl-F baseline (no model at all)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_assistant import FakeLLM, OpenRouterLLM, PolicyAssistant, Retriever, load_corpus  # noqa: E402
from policy_assistant import evaluate as ev  # noqa: E402
from policy_assistant.keyword_baseline import KeywordBaseline  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fake", action="store_true", help="FakeLLM + TF-IDF retrieval (offline smoke test)")
    p.add_argument("--judge", action="store_true", help="run the L2 LLM judge on answered questions")
    p.add_argument("--baseline-only", action="store_true")
    p.add_argument("--backend", default="auto", choices=["auto", "embedding", "tfidf"])
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--out", default=str(ROOT / "results"))
    args = p.parse_args()

    out = Path(args.out) / "smoke" if args.fake else Path(args.out)   # smoke-test output never overwrites results
    out.mkdir(parents=True, exist_ok=True)
    clauses, questions = load_corpus(), ev.load_questions()
    base_rows = ev.run_baseline(KeywordBaseline(clauses), questions)
    ev.write_csv(base_rows, out / "baseline.csv")
    b = ev.summarise(base_rows, "correct")
    print(f"Ctrl-F baseline: accuracy {ev.pct(b['correct'], b['answerable_n'])}, "
          f"refusal rate {ev.pct(b['refused'], b['unanswerable_n'])}")
    if args.baseline_only:
        return

    retriever = Retriever(clauses, "tfidf" if args.fake else args.backend)
    tau, dev_scores = ev.calibrate_tau(retriever, ev.load_questions("dev.jsonl"))
    print(f"retrieval backend: {retriever.backend}; tau = {tau} from dev set {dev_scores}")
    llm = FakeLLM() if args.fake else OpenRouterLLM()
    assistant = PolicyAssistant(retriever, llm, tau=tau, k=args.k)
    sys_rows = ev.run_assistant(assistant, questions, judge_llm=llm if args.judge else None)
    ev.write_csv(sys_rows, out / "assistant.csv")
    meta = {"model": llm.model, "backend": retriever.backend, "tau": tau, "k": args.k, "clauses": len(clauses)}
    summary = ev.report(sys_rows, base_rows, meta)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()

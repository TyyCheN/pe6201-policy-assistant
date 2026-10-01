"""Ask the assistant one question from the command line.

    python scripts/ask.py "How many days of marriage leave do I get?"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_assistant import OpenRouterLLM, PolicyAssistant, Retriever, load_corpus  # noqa: E402
from policy_assistant import evaluate as ev  # noqa: E402
from policy_assistant.assistant import format_answer  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    retriever = Retriever(load_corpus())
    tau, _ = ev.calibrate_tau(retriever, ev.load_questions("dev.jsonl"))
    print(format_answer(PolicyAssistant(retriever, OpenRouterLLM(), tau=tau).ask(" ".join(sys.argv[1:]))))

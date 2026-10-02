"""Open the web interface locally.

    pip install -r requirements.txt gradio
    export OPENROUTER_API_KEY=sk-or-...
    python scripts/app.py            # then open the address it prints (http://127.0.0.1:7860)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_assistant import OpenRouterLLM, PolicyAssistant, Retriever, load_corpus  # noqa: E402
from policy_assistant import evaluate as ev  # noqa: E402
from policy_assistant.ui import build_app  # noqa: E402

if __name__ == "__main__":
    retriever = Retriever(load_corpus())
    tau, _ = ev.calibrate_tau(retriever, ev.load_questions("dev.jsonl"))   # same threshold as the evaluation
    build_app(PolicyAssistant(retriever, OpenRouterLLM(), tau=tau, k=5)).launch()

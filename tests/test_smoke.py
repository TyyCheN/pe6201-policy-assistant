"""Offline tests: no API key, no model download. Run with: python -m pytest tests -q"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_assistant import FakeLLM, PolicyAssistant, Retriever, load_corpus  # noqa: E402
from policy_assistant import evaluate as ev  # noqa: E402
from policy_assistant.keyword_baseline import KeywordBaseline  # noqa: E402


class ScriptedLLM:
    model = "scripted"

    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, user):
        return json.dumps(self.reply), {"prompt_tokens": 1, "completion_tokens": 1, "cost_usd": 0.0}


CLAUSES = load_corpus()
RETRIEVER = Retriever(CLAUSES, "tfidf")
Q = "How many days of marriage leave do I get?"


def test_corpus_is_frozen():
    assert len(CLAUSES) == 175
    assert subprocess.run([sys.executable, str(ROOT / "scripts" / "freeze_manifest.py"), "--check"]).returncode == 0


def test_gold_clauses_exist_and_contain_key_facts():
    by_id = {c.id: c for c in CLAUSES}
    for name in ("questions.jsonl", "dev.jsonl"):
        for q in ev.load_questions(name):
            if q["answerable"]:
                assert all(g in by_id for g in q["gold_clauses"]), q["id"]
                for m in q["must_include"]:
                    assert any(m in by_id[g].text for g in q["gold_clauses"]), (q["id"], m)


def test_question_counts():
    qs = ev.load_questions()
    assert sum(q["answerable"] for q in qs) == 24 and sum(not q["answerable"] for q in qs) == 12


def test_g1_refuses_below_threshold_without_calling_model():
    r = PolicyAssistant(RETRIEVER, FakeLLM(), tau=0.99).ask(Q)
    assert r["refused"] and r["gate"].startswith("G1") and r["calls"] == 0


def test_g2_refuses_when_model_says_not_covered():
    r = PolicyAssistant(RETRIEVER, ScriptedLLM({"covered": False, "answer": "", "citations": []})).ask(Q)
    assert r["refused"] and r["gate"].startswith("G2")


def test_g3_rejects_invented_quote_and_unretrieved_clause():
    bad_quote = {"covered": True, "answer": "20 days.", "citations": [{"clause_id": "D07-5.1", "quote": "employees get twenty days of marriage leave"}]}
    assert PolicyAssistant(RETRIEVER, ScriptedLLM(bad_quote)).ask(Q)["gate"].startswith("G3")
    bad_id = {"covered": True, "answer": "13 days.", "citations": [{"clause_id": "D99-1", "quote": "13 days of marriage leave"}]}
    assert PolicyAssistant(RETRIEVER, ScriptedLLM(bad_id)).ask(Q)["gate"].startswith("G3")


def test_good_answer_passes_with_provenance():
    good = {"covered": True, "answer": "13 days.", "citations": [{"clause_id": "D07-5.1", "quote": "13 days of marriage leave"}]}
    r = PolicyAssistant(RETRIEVER, ScriptedLLM(good)).ask(Q)
    assert not r["refused"] and "October 2026 revision" in r["citations"][0]["provenance"]


def test_baseline_and_report_run():
    qs = ev.load_questions()
    base = ev.run_baseline(KeywordBaseline(CLAUSES), qs)
    rows = ev.run_assistant(PolicyAssistant(RETRIEVER, FakeLLM()), qs)
    text = ev.report(rows, base, {"model": "fake", "backend": "tfidf", "tau": 0.0, "k": 5, "clauses": len(CLAUSES)})
    assert "Accuracy on answerable questions" in text and "/24" in text and "/12" in text

"""The assistant: retrieve, gate, generate a grounded answer, verify the quote, attach provenance.

Four guards sit between a question and an answer:
  G1  retrieval gate  - if the best clause scores below tau, refuse without calling the model.
  G2  grounded answer - the model must return JSON {covered, answer, citations[{clause_id, quote}]}
                        and set covered=false when the retrieved clauses do not answer the question.
  G3  quote check     - every cited clause must be one that was retrieved, and every quote must
                        appear verbatim in it. Otherwise the answer is discarded and we refuse.
  G4  provenance      - an answer is always shown with clause ID, chapter and document date.
"""
import json
import re

REFUSAL = ("I can't answer that from the Employee Handbook. "
           "Please ask the Administration & HR Department.")

SYSTEM_PROMPT = """You are the HR policy assistant for Haida Co. You answer employees' questions using ONLY the handbook clauses given to you.

Return a JSON object and nothing else:
{"covered": true or false, "answer": "...", "citations": [{"clause_id": "D07-5.1", "quote": "..."}]}

Rules:
- covered = false if the clauses do not contain the answer. Do not guess and do not use outside knowledge, including general labour law.
- covered = false if the question asks about a specific person's data (salary, leave balance, phone number, appraisal) or is not about company policy.
- If covered = true: answer in at most 60 words, in plain English, and write numbers as digits exactly as the clause does.
- Give 1 or 2 citations. clause_id must be one of the clauses provided. quote must be copied word for word from that clause, at most 30 words.
- If covered = false: answer = "" and citations = []."""


def _norm(text):
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


class PolicyAssistant:
    def __init__(self, retriever, llm, tau=0.0, k=5):
        self.retriever, self.llm, self.tau, self.k = retriever, llm, tau, k

    def ask(self, question):
        hits = self.retriever.search(question, self.k)
        out = {"question": question, "refused": True, "gate": None, "answer": REFUSAL, "citations": [],
               "retrieved": [(c.id, round(s, 4)) for c, s in hits], "top_score": hits[0][1] if hits else 0.0,
               "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "raw_reply": ""}

        if not hits or hits[0][1] < self.tau:                                   # G1
            out["gate"] = "G1 retrieval gate"
            return out

        context = "\n".join(f"[{c.id}] {c.text}" for c, _ in hits)
        raw, usage = self.llm.complete(SYSTEM_PROMPT, f"HANDBOOK CLAUSES:\n{context}\n\nQUESTION: {question}")
        out["calls"] = 1
        out["raw_reply"] = raw                                                  # kept for diagnosing refusals
        for key in ("prompt_tokens", "completion_tokens", "cost_usd"):
            out[key] = usage[key]
        try:
            reply = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            out["gate"] = "G2 invalid JSON"
            return out
        if not isinstance(reply, dict) or not reply.get("covered") or not str(reply.get("answer", "")).strip():
            out["gate"] = "G2 model says not covered"                           # G2
            return out

        by_id = {c.id: c for c, _ in hits}
        citations = reply.get("citations") or []
        if not citations:
            out["gate"] = "G3 no citation"
            return out
        checked = []
        for cit in citations[:2]:                                                # G3
            clause = by_id.get(str(cit.get("clause_id", "")).strip("[] "))
            quote = _norm(str(cit.get("quote", "")))
            if clause is None or len(quote) < 8 or quote.strip(' ."\'') not in _norm(clause.text):
                out["gate"] = "G3 quote not found in cited clause"
                return out
            checked.append({"clause_id": clause.id, "quote": cit["quote"], "provenance": clause.provenance})  # G4

        out.update(refused=False, answer=str(reply["answer"]).strip(), citations=checked)
        return out


def format_answer(result):
    """Plain-text rendering shown to the employee."""
    if result["refused"]:
        return result["answer"]
    lines = [result["answer"], ""]
    for c in result["citations"]:
        lines.append(f'  "{c["quote"]}"\n  — {c["provenance"]}')
    return "\n".join(lines)

"""Web interface: a single page where an employee types a question and reads the answer.

The page shows what an employee would see (the answer, the verbatim clause and its source, or the
refusal) and, folded underneath, how the answer was produced: the retrieved clauses with their
scores and which guard (G1-G4) decided the outcome. It calls the same PolicyAssistant that the
evaluation uses, so the page adds no logic of its own.

    from policy_assistant.ui import build_app
    build_app(assistant).launch()          # in Colab this opens the page inside the notebook

Gradio is imported only inside build_app, so the rest of the package works without it.
"""

TITLE = "Haida Co. HR Policy Assistant"
INTRO = ("Ask a question about leave, pay, attendance or discipline. Answers come only from the "
         "Haida Co. Employee Handbook (October 2026 revision), and every answer quotes the clause it "
         "is based on. If the handbook does not cover your question, the assistant says so.")

EXAMPLES = [
    "How many days of marriage leave do I get?",
    "My wife is about to give birth. How many days off can I take as the father?",
    "I was 3 minutes late twice this month. Do I lose my full-attendance bonus?",
    "Who approves a half-day leave request?",
    "How much is the monthly meal allowance?",
    "What is Zhang Wei's salary this month?",
]

_GATE_TEXT = {
    "G1 retrieval gate": "**G1 retrieval gate:** no handbook clause matched the question closely enough, "
                         "so the model was not called.",
    "G2 model says not covered": "**G2:** the model read the retrieved clauses and reported that they do not "
                                 "answer the question (or that it asks about a person's data).",
    "G2 invalid JSON": "**G2:** the model's reply was not valid JSON, so it was discarded.",
    "G3 no citation": "**G3:** the model gave no citation, so the answer was discarded.",
    "G3 quote not found in cited clause": "**G3 quote check:** the quote the model gave is not word for word "
                                          "in a retrieved clause, so the answer was discarded.",
}


def render_answer(result):
    """What the employee sees: the answer with its quoted sources, or the refusal."""
    if result["refused"]:
        return f"### No answer from the handbook\n\n{result['answer']}"
    parts = [f"### Answer\n\n{result['answer']}", "", "**Source**", ""]
    for c in result["citations"]:
        parts += [f"> \"{c['quote']}\"", ">", f"> — {c['provenance']}", ""]
    return "\n".join(parts)


def render_trace(result, tau, clause_text=None):
    """How the answer was produced: retrieved clauses, the guard that decided, and the cost.

    clause_text maps clause IDs to their text; when given, the start of each clause is shown."""
    best = result["top_score"]
    clause_text = clause_text or {}
    lines = ["**Retrieved clauses** (similarity to the question; G1 threshold = %.3f)" % tau, "",
             "| Clause | Score | Text |", "|---|---|---|"]
    for cid, score in result["retrieved"]:
        text = clause_text.get(cid, "")
        text = (text[:90] + "...") if len(text) > 90 else text
        lines.append(f"| {cid} | {score:.3f} | {text.replace('|', '/')} |")
    lines.append("")
    if result["refused"]:
        lines.append(_GATE_TEXT.get(result["gate"], f"**{result['gate']}**"))
        if result["gate"] == "G1 retrieval gate":
            lines.append(f"\nBest score {best:.3f} is below the threshold {tau:.3f}.")
    else:
        lines.append(f"**G1:** best score {best:.3f} ≥ {tau:.3f}, so the model was called.  \n"
                     "**G2:** the model reported that the clauses answer the question.  \n"
                     "**G3:** every quote was found word for word in a retrieved clause.  \n"
                     "**G4:** clause ID, chapter and document date attached.")
    lines.append("")
    if result["calls"]:
        lines.append(f"Model calls: {result['calls']} · tokens: {result['prompt_tokens']} in, "
                     f"{result['completion_tokens']} out · cost: ${result['cost_usd']:.5f}")
    else:
        lines.append("Model calls: 0 · cost: $0")
    return "\n".join(lines)


def build_app(assistant):
    """Return a Gradio Blocks app around an existing PolicyAssistant. Call .launch() on it."""
    import gradio as gr

    clause_text = {c.id: c.text for c in assistant.retriever.clauses}

    def ask(question):
        question = (question or "").strip()
        if not question:
            return "Please type a question.", ""
        result = assistant.ask(question)
        return render_answer(result), render_trace(result, assistant.tau, clause_text)

    with gr.Blocks() as app:
        gr.Markdown(f"# {TITLE}\n\n{INTRO}")
        question = gr.Textbox(label="Your question", placeholder="e.g. How many days of marriage leave do I get?",
                              lines=2)
        button = gr.Button("Ask", variant="primary")
        answer = gr.Markdown()
        with gr.Accordion("How this answer was produced", open=False):
            trace = gr.Markdown()
        gr.Examples(examples=EXAMPLES, inputs=question)
        button.click(ask, inputs=question, outputs=[answer, trace])
        question.submit(ask, inputs=question, outputs=[answer, trace])
    return app

"""Ctrl-F baseline: what an employee gets by searching the handbook for the words in the question.

No model, no synonyms, no stemming: a query term counts only if it appears literally in a clause.
The baseline "answers" with the clause that literally contains the most (and rarest) query terms,
and "refuses" when fewer than MIN_TERMS distinct query terms are found in any single clause.
"""
import math
import re

MIN_TERMS = 2
STOPWORDS = set("""a an the i me my we our you your he him his she her it its they them their this that these those
is am are was were be been being do does did have has had can could will would shall should may might must
what which who whom whose when where why how if or and but not no so than then too very just also still
of in on at by for with from to into as about after before during over under up out off again
get gets got take takes took give gives gave given need needs want wants tell much many long far soon
there here any some each every all both more most other such only own same instead""".split())


def terms(text):
    """Distinct lower-cased content words (and numbers) of a question."""
    return {t for t in re.findall(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", text.lower())
            if t not in STOPWORDS and len(t) > 1}


class KeywordBaseline:
    def __init__(self, clauses):
        self.clauses = clauses
        self._texts = [c.text.lower() for c in clauses]

    def _found(self, term, text):
        return re.search(r"\b" + re.escape(term) + r"\b", text) is not None

    def search(self, question, k=3):
        """Return [(clause, score, matched_terms)], best first; empty list means 'refuse'."""
        q_terms = terms(question)
        n = len(self.clauses)
        idf = {t: math.log(1 + n / (1 + sum(self._found(t, x) for x in self._texts))) for t in q_terms}
        scored = []
        for clause, text in zip(self.clauses, self._texts):
            matched = sorted(t for t in q_terms if self._found(t, text))
            if len(matched) >= MIN_TERMS:
                scored.append((clause, sum(idf[t] for t in matched), matched))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]

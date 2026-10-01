"""LLM clients. OpenRouterLLM is the rented model API; FakeLLM lets the pipeline run offline."""
import json
import os
import re
import time

import requests

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


class OpenRouterLLM:
    """Chat completion via OpenRouter. Returns (text, usage); usage carries tokens and USD cost."""

    def __init__(self, model=DEFAULT_MODEL, api_key=None, timeout=60):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY (or run with --fake for the offline smoke test).")
        self.timeout = timeout

    def complete(self, system, user):
        body = {"model": self.model, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "usage": {"include": True}}       # ask OpenRouter to report the cost of this call
        for attempt in range(3):
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=self.timeout,
                              headers={"Authorization": f"Bearer {self.api_key}"})
            if r.status_code == 200:
                break
            if r.status_code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:300]}")
        data = r.json()
        u = data.get("usage", {})
        usage = {"prompt_tokens": u.get("prompt_tokens", 0), "completion_tokens": u.get("completion_tokens", 0),
                 "cost_usd": float(u.get("cost") or 0.0)}
        return data["choices"][0]["message"]["content"], usage


class FakeLLM:
    """Offline stand-in, for smoke tests only. It always claims the first retrieved clause answers
    the question and quotes its opening words. Its outputs are NOT results."""

    model = "fake"

    def complete(self, system, user):
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
        if "QUESTION UNDER REVIEW" in user:                      # judge call
            return json.dumps({"correct": True, "reason": "fake judge"}), usage
        m = re.search(r"^\[(D\d\d-[A-Z]?[\d.]+)\] (.+)$", user, re.M)
        if not m:
            return json.dumps({"covered": False, "answer": "", "citations": []}), usage
        quote = " ".join(m.group(2).split()[:10])
        return json.dumps({"covered": True, "answer": m.group(2),
                           "citations": [{"clause_id": m.group(1), "quote": quote}]}), usage

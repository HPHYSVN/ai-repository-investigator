"""Provider-isolated Meta Model API adapter (stdlib only).

Verified 2026-10-29 from official docs (dev.meta.ai/docs/quickstart,
/docs/authentication, /docs/pricing-rate-limits):
  base URL https://api.meta.ai/v1, Bearer MODEL_API_KEY,
  POST /v1/responses {model, input}, models muse-spark-1.3 / muse-wonder-1.0.
Investigation logic never imports provider types; it only sees complete().
"""
import json, os, time, urllib.request, urllib.error

PRICING_USD_PER_MTOK = {  # verified from official pricing page, Standard mode
    "muse-spark-1.3": (1.25, 4.25), "muse-spark-1.2": (1.25, 4.25),
    "muse-spark-1.1": (1.25, 4.25), "muse-wonder-1.0": (4.00, 20.00),
}

class ModelError(Exception):
    pass

class MetaAdapter:
    def __init__(self, api_key=None, model=None, base_url=None, timeout=60, max_retries=2):
        self.api_key = api_key or os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
        self.model = model or os.environ.get("MODEL_API_MODEL", "muse-spark-1.3")
        self.base_url = (base_url or os.environ.get("MODEL_API_BASE_URL", "https://api.meta.ai/v1")).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries  # retries on HTTP 429 only
        self.max_calls = int(os.environ.get("INVESTIGATOR_MAX_MODEL_CALLS", "2"))
        self.budget_usd = float(os.environ.get("INVESTIGATOR_BUDGET_USD", "1.00"))
        self.ledger = []  # {model, latency_s, input_tokens, output_tokens, est_cost_usd}
        self._unknown_cost_spent = False  # unknown pricing must not bypass the budget cap

    @property
    def configured(self):
        return bool(self.api_key)

    def est_cost(self, model, in_tok, out_tok):
        p = PRICING_USD_PER_MTOK.get(model)
        if p is None or in_tok is None:
            return None
        return round(in_tok / 1e6 * p[0] + (out_tok or 0) / 1e6 * p[1], 6)

    def spent(self):
        return round(sum(e["est_cost_usd"] or 0 for e in self.ledger), 6)

    def _budget_blocked(self):
        return self._unknown_cost_spent or self.spent() >= self.budget_usd

    def complete(self, prompt, purpose="synthesis"):
        """Return text or raise ModelError. Enforces call + budget caps."""
        if not self.configured:
            raise ModelError("MODEL_API_KEY not configured (deterministic mode)")
        if len(self.ledger) >= self.max_calls:
            raise ModelError(f"model call cap reached ({self.max_calls})")
        if self._budget_blocked():
            raise ModelError(f"budget cap reached (${self.budget_usd}) or prior call had unknown cost")
        body = json.dumps({"model": self.model, "input": prompt}).encode()
        t0 = time.time()
        data = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(self.base_url + "/responses", data=body, method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < self.max_retries:
                    # official guidance: back off, honour Retry-After (capped)
                    try:
                        delay = min(float(e.headers.get("Retry-After", "0.5")), 5.0)
                    except (TypeError, ValueError):
                        delay = 0.5
                    time.sleep(max(delay, 0.05) * (attempt + 1))
                    continue
                raise ModelError(f"Meta API HTTP {e.code}") from e
            except Exception as e:
                raise ModelError(f"Meta API request failed: {type(e).__name__}") from e
        latency = round(time.time() - t0, 3)
        # Responses API: text is nested in output[].content[] (type=output_text)
        parts = []
        for item in (data or {}).get("output", []) or []:
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
        text = "\n".join(parts)
        if not text:
            raise ModelError("Meta API returned no output_text (malformed response)")
        usage = data.get("usage") or {}
        entry = {"model": data.get("model", self.model), "purpose": purpose, "latency_s": latency,
                 "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                 "est_cost_usd": None}
        entry["est_cost_usd"] = self.est_cost(entry["model"], entry["input_tokens"], entry["output_tokens"])
        if entry["est_cost_usd"] is None:
            self._unknown_cost_spent = True  # block further calls: cost is unaccounted
        self.ledger.append(entry)
        return text

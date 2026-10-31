"""Deterministic console/network log parsing. Logs are untrusted data:
headers, cookies and credentials in them are redacted, never forwarded."""
import re

from .investigate import redact_secrets

ERR_RE = re.compile(r"(TypeError|ReferenceError|RangeError|SyntaxError|ValueError|KeyError|AttributeError|"
                    r"UnhandledPromiseRejection|Failed to fetch|NetworkError|CORS|404|500|502|503)\b[:\s]?([^\n]{0,180})")
NET_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)\s*(?:->|→|:)?\s*(\d{3})?\b")
STATUS_RE = re.compile(r"\b(\d{3})\s+(GET|POST|PUT|PATCH|DELETE)\s+(\S+)")

_SENSITIVE_LINE = re.compile(r"(?i)(authorization|cookie|set-cookie|x-api-key|password)")

def _clean(text, limit=8000):
    lines = []
    for line in (text or "")[:limit].splitlines():
        if _SENSITIVE_LINE.search(line):
            lines.append("[redacted sensitive log line]")
        else:
            lines.append(line)
    return redact_secrets("\n".join(lines))[0]

def parse_logs(console_text="", network_text=""):
    """Return {console_errors, network_failures, terms, cleaned:{console,network}}"""
    console_clean = _clean(console_text)
    network_clean = _clean(network_text)
    errors = []
    for m in ERR_RE.finditer(console_clean):
        errors.append({"kind": m.group(1), "detail": (m.group(2) or "").strip()[:180]})
    failures = []
    for text in (network_clean, console_clean):
        for m in NET_RE.finditer(text):
            status = m.group(3)
            failures.append({"method": m.group(1), "url": m.group(2)[:200],
                             "status": int(status) if status else None})
        for m in STATUS_RE.finditer(text):
            failures.append({"method": m.group(2), "url": m.group(3)[:200], "status": int(m.group(1))})
    # dedupe, keep order; failed = status >= 400 or missing status with fetch error
    seen, uniq = set(), []
    for f in failures:
        k = (f["method"], f["url"], f["status"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    terms = []
    for e in errors:
        terms += re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", e["kind"] + " " + e["detail"])
    for f in uniq:
        terms += [p for p in re.split(r"[^A-Za-z0-9_]+", f["url"]) if len(p) > 2]
    return {"console_errors": errors[:20], "network_requests": uniq[:30],
            "failed_requests": [f for f in uniq if (f["status"] or 0) >= 400][:20],
            "terms": list(dict.fromkeys(terms))[:40],
            "cleaned": {"console": console_clean, "network": network_clean}}

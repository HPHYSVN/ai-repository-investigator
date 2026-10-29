"""Regression tests for review findings H3 (name-gated detector) and H4
(abstention defeated by any detector hit), plus the false `.get` call edge."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation
from app.repo_index import RepoIndex

def _write(d, name, text):
    with open(os.path.join(d, name), "w") as f:
        f.write(text)

def test_missing_conversion_detected_under_any_name(tmp_path):
    # identical bug to the misleading-stack fixture, but renamed read_count
    d = str(tmp_path)
    _write(d, "loader.py", "def read_count(raw):\n    return raw.strip()\n")
    _write(d, "report.py", "from loader import read_count\n\ndef next_count(raw):\n    count = read_count(raw)\n    return count + 1\n")
    _write(d, "test_report.py", "from report import next_count\n\ndef test_next():\n    assert next_count('41') == 42\n")
    q = ('Traceback (most recent call last):\n  File "report.py", line 5, in next_count\n'
         '    return count + 1\nTypeError: can only concatenate str (not "int") to str')
    r = run_investigation(d, q, run_tests=False)
    assert r["hypotheses"][0]["files"] == ["loader.py"], r["hypotheses"][0]
    assert r["hypotheses"][0]["detector"]["type"] == "missing_conversion"

def test_conversion_present_is_not_flagged(tmp_path):
    d = str(tmp_path)
    _write(d, "loader.py", "def read_count(raw):\n    return int(raw.strip())\n")
    _write(d, "report.py", "from loader import read_count\n\ndef next_count(raw):\n    count = read_count(raw)\n    return count + 1\n")
    r = run_investigation(d, "next_count in report fails with TypeError in read_count loader")
    types = [h.get("detector", {}).get("type") if h.get("detector") else None for h in r["hypotheses"]]
    assert "missing_conversion" not in types

def test_vague_query_abstains_despite_detector_rich_repo():
    # sample_repo contains none_return + dict_get hits; a vague query must
    # still abstain (H4) instead of naming a root cause.
    r = run_investigation(os.path.join(ROOT, "sample_repo"),
                          "The app sometimes behaves wrong and users are unhappy.")
    assert r["status"] == "inconclusive"
    assert r["hypotheses"][0]["status"] == "inconclusive"
    assert any(s["step"] == "abstention-gate" for s in r["steps"])

def test_dict_get_call_creates_no_false_call_edge(tmp_path):
    d = str(tmp_path)
    _write(d, "a.py", "def worker(cfg):\n    return cfg.get('k')\n")
    _write(d, "b.py", "def get():\n    return 1\n")
    idx = RepoIndex(d)
    edges = idx.call_edges()
    assert not any("get" == e[1].split(":")[-1].split(".")[-1] for e in edges), edges

def test_secret_redaction_patterns():
    from app.investigate import redact_secrets
    out, n = redact_secrets("api_key = 'hunter2secret' and Bearer abc.def-123 plus normal code x = 1")
    assert n >= 2 and "hunter2secret" not in out and "abc.def-123" not in out
    assert "x = 1" in out

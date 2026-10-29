import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation
from app.repo_index import RepoIndex
from app.model_adapter import MetaAdapter, ModelError

SAMPLE = os.path.join(ROOT, "sample_repo")
QUERY = ('Traceback (most recent call last):\n'
         '  File "checkout.py", line 14, in checkout_total\n'
         '    return format_price(cart_total(items))\n'
         '  File "pricing.py", line 9, in format_price\n'
         '    return f"${amount:.2f}"\n'
         'TypeError: unsupported format string passed to NoneType')

def test_sample_repo_end_to_end():
    r = run_investigation(SAMPLE, QUERY, run_tests=True)
    assert r["status"] in ("verified", "inconclusive")
    assert r["hypotheses"][0]["files"] == ["cart.py"], r["hypotheses"][0]
    assert r["verification"]["citations_checked"] == r["verification"]["citations_total"]
    assert r["test_log"] and r["test_log"][0]["exit_code"] == 1  # planted bug fails a test
    assert any(n["kind"] == "hypothesis" for n in r["graph"]["nodes"])
    assert r["model"]["ledger"] == []  # no key in test env -> no spend

def test_citations_point_at_real_lines():
    idx = RepoIndex(SAMPLE)
    s = idx.snippet("cart.py", 9, 9)
    assert s and "return None" in s["text"]
    assert idx.validate_citation("cart.py", 9, 9, s["sha256"])
    assert not idx.validate_citation("cart.py", 999, 999)
    assert idx.snippet("nope.py", 1, 1) is None

def test_ambiguous_query_abstains():
    r = run_investigation(os.path.join(ROOT, "benchmarks/fixtures/ambiguous"),
                          "The app sometimes behaves wrong and users are unhappy.")
    assert r["status"] == "inconclusive"
    assert r["hypotheses"][0]["status"] == "inconclusive"

def test_missing_repo_fails_honestly():
    r = run_investigation("/nonexistent-xyz", "crash in foo bar baz")
    assert r["status"] == "failed"

def test_adapter_without_key_refuses_and_pricing_verified():
    a = MetaAdapter(api_key=None)
    # ensure env keys do not leak into the test
    a.api_key = None
    assert not a.configured
    try:
        a.complete("hi")
        raise AssertionError("should have raised")
    except ModelError:
        pass
    assert a.est_cost("muse-spark-1.3", 1_000_000, 1_000_000) == 5.50
    assert a.est_cost("muse-wonder-1.0", 1_000_000, 0) == 4.00
    assert a.est_cost("unknown-model", 100, 100) is None

def test_investigation_is_read_only():
    files = [f for f in os.listdir(SAMPLE) if os.path.isfile(os.path.join(SAMPLE, f))]
    before = {f: open(os.path.join(SAMPLE, f)).read() for f in files}
    run_investigation(SAMPLE, QUERY, run_tests=True)
    after = {f: open(os.path.join(SAMPLE, f)).read() for f in files}
    assert before == after

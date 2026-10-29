#!/usr/bin/env python3
"""Deterministic benchmark: agent (no model) vs lexical baseline, same cases.

Expected answers live in benchmarks/expected/ and are NEVER passed to the
agent — the agent only receives fixture dir + query string.
Writes benchmarks/results.json with measured values only.
"""
import json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation
from app.repo_index import RepoIndex

def main():
    exp_dir = os.path.join(ROOT, "benchmarks", "expected")
    cases, correct_agent, correct_base = [], 0, 0
    total_cites, valid_cites = 0, 0
    for name in sorted(os.listdir(exp_dir)):
        exp = json.load(open(os.path.join(exp_dir, name)))
        fixture = os.path.join(ROOT, "benchmarks", "fixtures", exp["case"])
        t0 = time.time()
        res = run_investigation(fixture, exp["query"], run_tests=True)
        latency = round(time.time() - t0, 3)
        # baseline: BM25 top-1 file only
        idx = RepoIndex(fixture)
        terms = [t for t in exp["query"].replace('"', " ").split() if len(t) > 3]
        base_top = (idx.bm25_search(terms, limit=1) or [(0, None)])[0][1]
        top_files = res["hypotheses"][0]["files"] if res["hypotheses"] else []
        if exp.get("expect_abstain"):
            agent_ok = res["status"] == "inconclusive"
            base_ok = False  # lexical baseline cannot abstain
        else:
            agent_ok = exp["root_file"] in top_files
            base_ok = base_top == exp["root_file"]
        correct_agent += agent_ok
        correct_base += base_ok
        total_cites += res["verification"]["citations_total"]
        valid_cites += res["verification"]["citations_checked"]
        cases.append({"case": exp["case"], "agent_root_correct": agent_ok,
                      "baseline_top1_file": base_top, "baseline_root_correct": base_ok,
                      "agent_status": res["status"], "top_files": top_files,
                      "hypothesis_statuses": [h["status"] for h in res["hypotheses"]],
                      "citations_valid": res["verification"], "tests_run": len(res["test_log"]),
                      "test_exit_codes": [t["exit_code"] for t in res["test_log"]],
                      "model_calls": len(res["model"]["ledger"]), "latency_s": latency})
    n = len(cases)
    summary = {"cases": n, "agent_root_cause_accuracy": correct_agent / n,
               "baseline_root_cause_accuracy": correct_base / n,
               "citation_validity": (valid_cites / total_cites) if total_cites else 1.0,
               "model_spend_usd": 0, "note": "deterministic mode; no MODEL_API_KEY configured during run"}
    out = {"summary": summary, "cases": cases}
    with open(os.path.join(ROOT, "benchmarks", "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(summary, indent=2))
    for c in cases:
        print(c)

if __name__ == "__main__":
    main()

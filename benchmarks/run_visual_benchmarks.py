#!/usr/bin/env python3
"""Visual Bug-to-Code benchmark: 10 controlled synthetic cases, separate
from the original ARI benchmark (benchmarks/results.json).

Each case supplies a bug description + console/network text (the Level 2-3
inputs a screenshot would accompany). No Meta key is used: visual content
analysis is therefore metadata-only and does not affect scoring — the
metrics below measure the deterministic investigation engine. Expected
answers live in benchmarks/visual/expected/, never indexed by the agent.
Fixtures run from temp copies. Writes benchmarks/visual/results.json.
"""
import json, os, shutil, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation
from app.repo_index import RepoIndex

def main():
    exp_dir = os.path.join(ROOT, "benchmarks", "visual", "expected")
    cases, root_ok, line_ok, abstain_total, abstain_ok = [], 0, 0, 0, 0
    cites_total = cites_valid = hyp_total = 0
    verified_ok = verified_total = 0
    for name in sorted(os.listdir(exp_dir)):
        exp = json.load(open(os.path.join(exp_dir, name)))
        src = os.path.join(ROOT, "benchmarks", "visual", "fixtures", exp["case"])
        fixture = os.path.join(tempfile.mkdtemp(prefix="vbench_"), exp["case"])
        shutil.copytree(src, fixture)
        t0 = time.time()
        res = run_investigation(fixture, exp["description"], run_tests=True,
                                console_text=exp.get("console", ""),
                                network_text=exp.get("network", ""))
        latency = round(time.time() - t0, 3)
        # BM25 top-1 baseline on the same text inputs
        idx = RepoIndex(fixture)
        terms = [t for t in (exp["description"] + " " + exp.get("console", "")).split() if len(t) > 3]
        base_top = (idx.bm25_search(terms, limit=1) or [(0, None)])[0][1]
        top_files = res["hypotheses"][0]["files"] if res["hypotheses"] else []
        if exp["expect_abstain"]:
            abstain_total += 1
            ok = res["outcome"] == "inconclusive"
            abstain_ok += ok
            root_hit = ok
            line_hit = None
        else:
            root_hit = any(f in top_files for f in exp["root_files"])
            root_ok += root_hit
            line_hit = bool(res["hypotheses"]) and exp.get("root_line") is not None and \
                any(abs((h.get("lines") or [999])[0] - exp["root_line"]) <= 3
                    for h in res["hypotheses"] if h["files"] and h["files"][0] in exp["root_files"])
            line_ok += bool(line_hit)
        if exp["expect_abstain"] is False and res["test_log"]:
            verified_total += 1
            verified_ok += res["outcome"] == "verified"
        cites_total += res["verification"]["citations_total"]
        cites_valid += res["verification"]["citations_checked"]
        hyp_total += len(res["hypotheses"])
        cases.append({"case": exp["case"], "root_hit": root_hit, "line_hit": line_hit,
                      "baseline_top1": base_top, "baseline_hit": base_top in exp["root_files"],
                      "outcome": res["outcome"], "top_files": top_files,
                      "hypotheses": len(res["hypotheses"]), "latency_s": latency,
                      "test_exits": [t["exit_code"] for t in res["test_log"]]})
    n_root = sum(1 for c in cases if c["line_hit"] is not None)
    summary = {"cases": len(cases),
               "root_cause_accuracy": round(root_ok / max(n_root, 1), 3),
               "file_localization_accuracy": round(root_ok / max(n_root, 1), 3),
               "line_localization_accuracy": round(line_ok / max(n_root, 1), 3),
               "abstention_correct": f"{abstain_ok}/{abstain_total}",
               "verification_verified_share": f"{verified_ok}/{verified_total} (verified only when an executed test confirms)",
               "citation_validity": round(cites_valid / max(cites_total, 1), 3),
               "model_spend_usd": 0,
               "note": "controlled synthetic fixtures only; no real-world repos measured; deterministic mode (no MODEL_API_KEY)"}
    out = {"summary": summary, "cases": cases}
    with open(os.path.join(ROOT, "benchmarks", "visual", "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(summary, indent=2))
    for c in cases:
        print(c)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Adversarial cases, kept SEPARATE from the original 5-case benchmark.

Cases target review findings H3/H4 and XSS filename handling:
1. renamed-producer: same unconverted-value bug, function not named parse*
2. vague-on-detector-rich: vague query on sample_repo (many detector hits)
3. crafted-filename: repo file whose name attempts JS breakout
Writes benchmarks/adversarial_results.json with measured outcomes only.
"""
import json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation

def w(d, name, text):
    with open(os.path.join(d, name), "w") as f:
        f.write(text)

def main():
    cases = []
    # 1. renamed producer
    d = tempfile.mkdtemp(prefix="adv_")
    w(d, "loader.py", "def read_count(raw):\n    return raw.strip()\n")
    w(d, "report.py", "from loader import read_count\n\ndef next_count(raw):\n    count = read_count(raw)\n    return count + 1\n")
    q = ('Traceback:\n  File "report.py", line 4, in next_count\n    return count + 1\n'
         'TypeError: can only concatenate str (not "int") to str')
    r = run_investigation(d, q)
    cases.append({"case": "renamed-producer", "expected_root": "loader.py",
                  "agent_top": r["hypotheses"][0]["files"] if r["hypotheses"] else [],
                  "pass": bool(r["hypotheses"]) and r["hypotheses"][0]["files"] == ["loader.py"]})
    # 2. vague query on detector-rich sample repo
    r = run_investigation(os.path.join(ROOT, "sample_repo"),
                          "The app sometimes behaves wrong and users are unhappy.")
    cases.append({"case": "vague-on-detector-rich", "expected": "abstain (inconclusive)",
                  "agent_status": r["status"], "pass": r["status"] == "inconclusive"})
    # 3. crafted filename
    d = tempfile.mkdtemp(prefix="adv_")
    w(d, "x');alert(document.domain);#.py", "def f():\n    return None\n")
    w(d, "main.py", "VALUE = 1\n")
    r = run_investigation(d, "f crashes NoneType main VALUE")
    ok = all("onclick" not in str(n) and "<script" not in n["label"] for n in r["graph"]["nodes"])
    cases.append({"case": "crafted-filename", "expected": "no markup/handler injection in graph data",
                  "pass": ok})
    out = {"cases": cases, "passed": sum(c["pass"] for c in cases), "total": len(cases),
           "note": "adversarial suite; separate from benchmarks/results.json; deterministic mode, $0 model spend"}
    with open(os.path.join(ROOT, "benchmarks", "adversarial_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()

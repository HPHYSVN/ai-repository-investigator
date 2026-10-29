---
name: Benchmark Testing
description: Build, run, and score the deterministic benchmark fixtures with known bugs, including baseline comparison and citation-validity checks. Use when creating evaluation fixtures, measuring accuracy, or reporting benchmark results.
---

# Benchmark Testing

## Fixture requirements
Each fixture is a small, self-contained repo under (planned) `benchmarks/` with:
- A planted, nontrivial bug and a runnable test that exposes it.
- `expected.json`: root cause (file/symbol/lines), relevant evidence,
  acceptable outcomes, and the correct behaviour (e.g. abstain).
- The expected answer stored OUTSIDE anything the agent can read at runtime
  (no leakage into prompts, indexes, or fixture source comments).

Required cases: (1) null/missing value across multiple files, (2) incorrect
conditional/boundary check, (3) config mismatch or broken dependency path,
(4) misleading stack trace (failure site ≠ root cause), (5) ambiguous case
where abstention is the correct result.

## Running
1. Run the agent end-to-end per fixture; capture report, graph, test log,
   latency, model/token/cost usage.
2. Run the baseline (lexical search and/or single-pass LLM) on identical input.
3. Score programmatically where possible, especially citation validity
   (reuse the `evidence-verification` skill checks).

## Metrics (report measured values only)
Root-cause identification accuracy, evidence citation validity, execution-path
accuracy, test-outcome correctness, unsupported-claim rate, abstention
behaviour, latency, token/API cost. Agent vs baseline on the same cases.

## Rules
- Never hardcode fixture answers into the agent. If the agent only passes by
  reading `expected.json`, the run is invalid.
- Never fabricate or round up improvements. Record failures in
  `docs/progress.md` with the actual command output that proves them.
- Keep total benchmark model spend within the budget guardrails in `AGENTS.md`;
  reserve credit for the final live demo.

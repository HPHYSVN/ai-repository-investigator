# AI Repository Investigator

An evidence-backed debugging agent for unfamiliar repositories (Meta Global AI
Developer Hackathon 2026, Indie Developer track). It traces execution paths
across files, forms structured hypotheses, verifies every citation against the
current source, runs allow-listed tests, and proposes — never applies — patches.

**Core promise: every important claim is verifiable against the repository.
When evidence is insufficient, the agent abstains and says what is missing.**

## Run it (no dependencies)

```bash
python3 run.py            # http://127.0.0.1:8765
```

Open the UI, keep the default `sample_repo` (a planted multi-file bug: an
unknown SKU makes `cart_total()` in `cart.py` silently return `None`, which
crashes three files away in `pricing.format_price`), and click **Investigate**.

## Enable Meta Model API synthesis (optional)

The deterministic engine works with no key and $0 spend. To add Meta-powered
final synthesis (verified 2026-10-29 from dev.meta.ai/docs):

```bash
export MODEL_API_KEY="..."        # your own key from the Model API dashboard
export MODEL_API_MODEL="muse-spark-1.3"   # default; or muse-wonder-1.0
python3 run.py
```

Base URL `https://api.meta.ai/v1`, `POST /v1/responses`, Bearer auth. Keys are
read server-side only and never sent to the browser or logged. Per-investigation
caps: `INVESTIGATOR_MAX_MODEL_CALLS` (default 2), `INVESTIGATOR_BUDGET_USD`
(default 1.00). Contributor-mode models are not used. Unverified citations in
model output are stripped and flagged; model text is labelled `inference`.

## How it works

Deterministic first, model last: repo recon (`.gitignore`/secret/binary-aware)
→ AST symbol/import/call extraction → BM25 retrieval → static detectors
(None-return, `.get()` without default, strict boundary, undefined config key,
unconverted parser output) → import/call-graph execution path → structured
hypotheses (supporting + contradicting evidence, labelled non-calibrated
confidence) → optional allow-listed pytest (60s timeout, logged exit code) →
mandatory citation revalidation (file + line range + SHA-256 snippet hash) →
report + Evidence Graph built only from extracted facts.

Investigation is read-only. Test execution runs only `python -m pytest` on
discovered `test_*.py` files when the user opts in.

## Benchmarks (measured, deterministic mode)

```bash
python3 benchmarks/run_benchmarks.py   # writes benchmarks/results.json
python3 -m pytest tests/ -q
```

5 fixtures (null-across-files, boundary, config mismatch, misleading stack
trace, ambiguous→abstain); expected answers live in `benchmarks/expected/`,
outside anything the agent indexes. Latest measured results are in
`benchmarks/results.json` and `docs/progress.md` — no fabricated numbers.

## Layout

`app/` server + orchestrator + repo index + Meta adapter · `sample_repo/` demo
repo · `benchmarks/` fixtures + runner · `tests/` unit/integration tests ·
`docs/` architecture, decisions, progress, demo script.

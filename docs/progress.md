# Progress Log

## 2026-10-29 — Phase A: reconnaissance + persistent memory (done)
- Inspected `the developer's home directory`: home directory, not a git repo, no existing
  hackathon project; all existing files preserved untouched.
- Created project at `the project root (this repository)` with:
  `AGENTS.md`, `docs/{progress,architecture,decisions,demo-script}.md`, and
  OpenCode V2 skills `.opencode/skills/{repository-investigation,
  evidence-verification,benchmark-testing}/SKILL.md`.
- Verified toolchain: Python 3.14.8, Node v26.12.1, npm 12.2.1, git 2.56.0,
  `rg`, `fd`, OpenCode v2.1.4. Meta via OpenCode: only `meta/muse-wonder-1.0`.
- No application code written, per user instruction. No model/API spend incurred
  beyond this OpenCode session; no benchmark results exist yet (none fabricated).

## 2026-10-29 — Phases B–F: full implementation (done)
- **Phase B:** Meta Model API verified from official docs (base
  `https://api.meta.ai/v1`, Bearer `MODEL_API_KEY`, Responses API,
  `muse-spark-1.3`/`muse-wonder-1.0`, pricing + rate limits) — recorded in
  `docs/decisions.md`. No `MODEL_API_KEY` in env, so the app runs in a
  deterministic $0 mode and uses Meta only when a user supplies their own key.
- **Phase C (vertical slice):** `app/repo_index.py` (gitignore/secret/binary-
  aware indexing, AST symbols/imports/calls, BM25), `app/investigate.py`
  (classify → retrieve → static detectors → graph path → hypotheses →
  citation revalidation → report), `app/model_adapter.py` (provider-isolated,
  call/budget caps, usage ledger, verified pricing), `app/server.py` +
  `app/static/index.html` (repo selector, steps, Evidence Graph SVG, source
  preview, hypothesis/evidence panel, test log, model ledger).
- **Phase D:** Evidence Graph from extracted facts only; safe targeted test
  execution (allow-listed `python -m pytest <test_*.py>`, 60s timeout, exit
  code logged); proposed patches as unapplied unified diffs (boundary/config
  detectors only). LLM synthesis is citation-checked; unverified citations
  are stripped (verified against a local Responses-API stub — no real spend).
- **Phase E (measured):** `python3 -m pytest tests/ -q` → **6 passed**.
  `python3 benchmarks/run_benchmarks.py` → agent root-cause accuracy
  **5/5 (1.0)** vs lexical BM25 top-1 baseline **1/5 (0.2)**; citation
  validity **1.0**; ambiguous case correctly abstains (`inconclusive`);
  ~0.5s/case; model spend **$0**. A real bug was found and fixed during
  validation (detectors initially only scanned BM25-matched files and
  missed upstream root causes — now scans graph neighbours / all files ≤200).
- **Phase F:** `sample_repo/` demo (unknown SKU → `cart.py` returns None →
  crash in `pricing.py`; expected notes live in the demo script, outside the
  indexed repo), README, `.env.example`, finalised demo script below.

## Remaining risks / unknowns
- Live Meta synthesis not yet exercised with a real `MODEL_API_KEY` (no key
  in this environment); adapter verified only against official docs + a
  local stub implementing the documented Responses API shape.
- $150 credit balance/mechanics unverified (user-stated).
- Test execution is allow-list + timeout, not OS-sandboxed; only run tests
  in repos you trust.
- Detectors are Python-focused; other languages get lexical indexing only.

## Next steps
1. With a real key: `MODEL_API_KEY=... python3 run.py`, run one live
   investigation, confirm ledger/cost in UI, reserve credit for the demo.
2. Optional: JS/TS symbol extraction; OS-level test sandboxing.

## Test results
- `python3 -m pytest tests/ -q` → 6 passed (2026-10-29).
- `python3 benchmarks/run_benchmarks.py` → summary above; full measured
  output in `benchmarks/results.json`.
- Manual E2E: server health + `/api/investigate` on `sample_repo` returned
  `verified`, root file `cart.py`, path pricing→checkout→cart, citations
  valid, real pytest exit code 1 (planted bug).

## 2026-10-29 — Security hardening from docs/review-findings.md
- **H1 (XSS) fixed:** frontend has no inline event handlers; repo-derived
  values reach the DOM via `data-*` attributes + `addEventListener`, and
  `esc()` now escapes quotes for attribute context (`app/static/index.html`).
- **H2 (code execution) fixed to the review's minimum bar and beyond:**
  test execution is off by default, needs a UI confirm dialog /
  `test_execution_confirmed=true`, is rejected when
  `INVESTIGATOR_DISABLE_TEST_EXECUTION=1`, repo paths are validated
  (existing dir, optional `INVESTIGATOR_ALLOWED_ROOTS` confinement), and
  the pytest subprocess gets a secret-stripped env + `PYTHONDONTWRITEBYTECODE`
  (`app/server.py:validate_investigate_request`, `app/investigate.py`).
  Still NOT OS-sandboxed — documented prominently in README/UI.
- **H3 fixed without name heuristics:** the `parse*`-gated detector was
  replaced by a producer/caller data-flow check (unconverted return +
  caller arithmetic), any function name (`missing_conversion_hits`).
- **H4 fixed:** non-specific queries abstain regardless of detector hits
  (specificity now also requires terms to actually occur in the repo);
  new `abstention-gate` step records when hits are deliberately ignored.
- Also: M1 real demo stack-trace lines; M2 "dependency path" wording and
  softened propagation claims; M3 citation-validity meaning stated in API,
  benchmark, and README; M4 pattern-based secret redaction before model
  synthesis; M5 adapter HTTP tests vs a local stub + 429 retry + unknown-
  pricing budget block; L1 dead `output_text` branch removed; false
  `.get` call edges removed (review §B); benchmark fixtures run from temp
  copies (L3). Adversarial cases are a separate suite
  (`benchmarks/run_adversarial.py`), original benchmark untouched.
- **Measured after hardening:** `python3 -m pytest tests/ -q` → **25 passed**;
  original benchmark agent **5/5** vs baseline **1/5**, citation validity
  **1.0** (existence/range/hash meaning); adversarial **3/3**; $0 spend.
- **Live Meta inference remains UNVERIFIED** (no real key available).

## 2026-10-31 — Pivot: Visual Bug-to-Code Investigator
- Added `app/visual.py` (image validation, metadata-only degraded mode,
  strict structured-JSON parsing of Meta vision output), `app/logs.py`
  (console/network extraction + secret redaction), multimodal adapter
  method, JS/TS lexical extraction, `dependency_mismatch` detector,
  outcome taxonomy, regression-test suggestions, None-return patch
  proposals, visual/log Evidence Graph nodes.
- New demo: `demo_webapp/` (JS frontend + Python API) with a real headless-
  Chromium screenshot of the broken cart page; UI rebranded and pre-filled.
- **Measured:** `python3 -m pytest tests/ -q` → 32 passed; visual benchmark
  (10 synthetic cases) root-cause 0.889 (8/9; cents-transform case missed,
  reported as-is), abstention 1/1, citations 1.0, 5/9 verified; original
  benchmark still 5/5 vs 1/5; adversarial 3/3. Proposed demo patch verified
  in a temp copy (tests pass there; original never modified).
- **Live Meta inference remains UNVERIFIED** (no key in environment);
  multimodal path is stub-tested only. Exact live-check steps in README.

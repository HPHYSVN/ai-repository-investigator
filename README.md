# AI Repository Investigator

Evidence-grounded AI agent for investigating bugs and execution paths across
code repositories. Built for the Meta Global AI Developer Hackathon 2026
(Indie Developer track).

Give it a local repository and a bug report or stack trace. It inspects the
repo with deterministic tools, traces a dependency path across files, forms
structured hypotheses, verifies every citation against the current source,
optionally runs existing tests, and produces a debugging report.

**Core promise: every important claim is verifiable against the repository.
When evidence is insufficient, the agent abstains and says what is missing —
it does not fabricate certainty.**

## Install and run

No dependencies beyond Python 3.11+ (standard library only; `pytest` is used
only to run a target repo's own tests and this project's test suite).

```bash
git clone https://github.com/HPHYSVN/ai-repository-investigator.git
cd ai-repository-investigator
python3 run.py            # http://127.0.0.1:8765 (localhost only)
```

Open the UI, keep the default `sample_repo` (a planted multi-file bug: an
unknown SKU makes `cart_total()` in `sample_repo/cart.py` silently return
`None`, which crashes in `pricing.format_price`), and click **Investigate**.

## How the investigation works

Deterministic first, model last:

1. **Recon / indexing** — walks the repo respecting `.gitignore`; skips
   secret-named files, binaries, generated dirs, and files >512 KB.
2. **Parsing** — Python AST extraction of symbols, imports, and plain-name
   calls; other languages are indexed lexically (BM25) only.
3. **Retrieval** — BM25 over file contents with a symbol-name boost.
4. **Static detectors** — explicit `return None`, `.get()` without a default,
   strict boundary comparisons, config keys that are read but never defined,
   and unconverted producer output (a function returning its parameter
   unconverted while a caller uses the result in arithmetic — detected from
   call/assignment evidence, not from function names).
5. **Dependency path** — BFS over the extracted import/call file graph from
   the symptom file to the candidate root file. This is dependency
   reachability, **not** a runtime execution/data-flow trace.
6. **Hypotheses** — structured claims with supporting and contradicting
   evidence, confidence *labels* with written meanings (not calibrated
   probabilities), missing evidence, next steps, and a status
   (`unverified|supported|rejected|confirmed-by-test|inconclusive`).
   A vague query with no stack frame, named symbol, or rare repo term
   **abstains** even if detector patterns exist somewhere in the repo.
7. **Optional test execution** — see Security below; off by default.
8. **Citation revalidation** — every citation is rechecked (file exists,
   line range in bounds, SHA-256 of the snippet matches indexed content)
   before the report is shown. This proves citations point at real current
   lines; it does **not** prove the lines semantically establish the claim.
9. **Report + Evidence Graph** — nodes/edges come only from extracted
   imports/calls, hypotheses, and actually-run tests. Any model-written
   text is labelled `inference` and its citations are checked the same way.

The investigation phase never modifies the target repository. Patches are
proposed as reviewable unified diffs only, never applied.

## Meta Model API configuration (optional)

The deterministic engine works with **no API key and $0 spend**. To add
Meta-powered final synthesis:

```bash
export MODEL_API_KEY="..."                # required: your Model API dashboard key
export MODEL_API_MODEL="muse-spark-1.3"   # optional (default); or muse-wonder-1.0
python3 run.py
```

Verified 2026-10-29 against the official docs (dev.meta.ai/docs): base URL
`https://api.meta.ai/v1`, `POST /v1/responses` with `{model, input}`, Bearer
auth via `MODEL_API_KEY` (`META_API_KEY` is also accepted). Optional caps:
`INVESTIGATOR_MAX_MODEL_CALLS` (default 2) and `INVESTIGATOR_BUDGET_USD`
(default 1.00) per investigation; HTTP 429 is retried with backoff. The key
is read server-side only — never sent to the browser, logged, or passed to
test subprocesses — and high-confidence secret patterns in evidence are
redacted before synthesis.

> **Live Meta inference status: UNVERIFIED.** No real `MODEL_API_KEY` was
> available in the development environment, so no live Meta API request has
> been made. The adapter is covered by automated tests against a local stub
> implementing the documented Responses API shape (see
> `tests/test_model_adapter_http.py`). Set a real key as above to enable it.

## Tests and benchmarks

```bash
python3 -m pytest tests/ -q                 # full test suite
python3 benchmarks/run_benchmarks.py        # original 5-case benchmark
python3 benchmarks/run_adversarial.py       # separate adversarial cases
```

Benchmark fixtures are tiny Python repos with known bugs (null value across
files, boundary, config mismatch, misleading stack trace, ambiguous →
abstain). Expected answers live in `benchmarks/expected/`, outside anything
the agent indexes; fixtures run from temp copies. The baseline is BM25
top-1 file retrieval, so the comparison shows the value of static analysis
+ graph over lexical retrieval alone — it does not establish generalisation
beyond these small Python fixtures.

**Measured results (2026-10-29, deterministic mode, $0 model spend):**

| Suite | Result |
|---|---|
| Unit/integration tests | 25 passed (`python3 -m pytest tests/ -q`) |
| Original benchmark | agent root-cause 5/5 vs BM25 baseline 1/5; citation validity 1.0 (existence/range/hash — see step 8); ambiguous case abstains; ~0.5 s/case |
| Adversarial suite | 3/3 (renamed producer function, vague query on detector-rich repo, crafted XSS filename) |

Full measured output: `benchmarks/results.json`,
`benchmarks/adversarial_results.json`, `docs/progress.md`.

## Security model and limitations — read before use on untrusted repos

- **The server binds 127.0.0.1 only** and is a local developer tool, not a
  hosted service. There is no authentication; do not expose it to a network.
- **Test execution runs repository code.** Pytest on a repo's `test_*.py`
  files executes that repo's code (tests can import any sibling module)
  with **your user privileges and no OS sandbox**. It is therefore off by
  default, requires an explicit per-run confirmation in the UI (or
  `test_execution_confirmed=true` via the API), and can be disabled with
  `INVESTIGATOR_DISABLE_TEST_EXECUTION=1`. Only run tests in repositories
  you trust, ideally in a VM/container. The subprocess receives a sanitized
  environment (API keys/tokens stripped) and a 60 s timeout.
- **Repository content is untrusted.** Filenames and code are escaped in
  the UI (no inline event handlers; attribute-safe escaping) and treated
  as data, never as instructions, in model prompts. Secret filtering is
  filename-based at index time plus pattern-based redaction before model
  synthesis — it is a heuristic, so review what you send to any model.
- Repository paths may optionally be confined with
  `INVESTIGATOR_ALLOWED_ROOTS` (path-separator-separated list).
- Symbol/call extraction is **Python-only**; other languages get lexical
  search without detectors or graph edges. Detectors are heuristics with
  false positives/negatives on real-world code; treat hypotheses as leads
  to verify, and expect `inconclusive` on large or unusual repos.

## Layout

`app/` server, orchestrator, repo index, Meta adapter, web UI ·
`sample_repo/` demo repo · `benchmarks/` fixtures, runners, measured
results · `tests/` unit/integration/security tests · `docs/` architecture,
decisions, progress log, demo script, and the independent review in
`docs/review-findings.md` (with its resolution status appended).

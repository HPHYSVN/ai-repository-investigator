# Adversarial Code Review — AI Repository Investigator

Independent review at commit `c89243a`, working tree clean. Evidence tags:
`[verified]` = read from code, `[live]` = command run in this environment,
`[probe]` = isolated experiment in scratch (not committed). Findings are
classified Critical / High / Medium / Low. Strengths are listed first and
marked *preserved* where the implementation already satisfies a requirement.

Baseline reproduced this session:
- `python3 -m pytest tests/ -q` → **6 passed** (`/usr/bin/python3`, 3.14.8) `[live]`
- `python3 benchmarks/run_benchmarks.py` → agent **5/5**, BM25 top-1 **1/5**,
  citation validity **1.0**, ambiguous → `inconclusive`, ~0.5 s/case `[live]`

The reported implementation claims are, on the whole, **accurate**. The gaps are
in generality, security hardening, metric honesty, and demo polish — not in the
core working slice.

---

## What is genuinely good (preserved)

- **Meta API adapter is correctly specified.** Endpoint `https://api.meta.ai/v1`,
  `POST /v1/responses`, `{"model","input"}`, `Bearer MODEL_API_KEY`, models
  `muse-spark-1.3` / `muse-wonder-1.0`, pricing ($1.25/$4.25, $4/$20 per 1M),
  and the response shape `output[].content[]` with `type=="output_text"` and
  `usage.input_tokens/output_tokens` — all **independently verified against
  dev.meta.ai/docs** this session. The handoff's fear that these were invented
  is **resolved: they are real.** `[live]`
- **Provider isolation is real.** `investigate.py` imports only
  `MetaAdapter`/`ModelError`, never provider types `[verified]`.
- **Cross-file root-causing works, not just pattern matching.** For the null
  case the symptom is in `service.py` and the root in `store.py`; the agent
  links them via the AST import graph and names `store.py:3` `[probe]`. When a
  benign `n > 100` distractor is added, the null hypothesis still wins (None
  detector is ranked +2 over boundary) `[probe]`.
- **Citation SHA-256 logic is correct.** `validate_citation` recomputes the hash
  from current file lines and compares; out-of-range and missing-file citations
  are rejected (`test_citations_point_at_real_lines`) `[verified]`. See Medium M7
  for why "1.0 validity" is weaker than it reads.
- **Read-only + hygiene confirmed.** `test_investigation_is_read_only` passes
  `[live]`; no `__pycache__`/`.pyc`/`.env` is tracked by git (`git ls-files`
  clean, `.env` confirmed ignored) `[live]`.
- **Stdlib-only, zero new dependencies.** `[verified]`

---

## Findings

### HIGH

**H1 — Frontend XSS via unescaped repo filenames in inline event handlers.**
`app/static/index.html:71` and `:81` interpolate repo-derived paths into an
attribute: `onclick="showSource('${e.file}',${e.start})"` /
`showSource('${n.file||''}',${n.line||1})`. `esc()` (`index.html:59`) only
escapes `& < >`, **not quotes**, so it is unsafe in attribute context. A repo
with a crafted filename (e.g. `x');alert(document.domain)//.py`) breaks out of
the `onclick` and runs arbitrary JS in the app context. This matters because the
product's threat model is *untrusted* repos, and that JS could then call
`/api/investigate` with `run_tests:true` to execute repo code. `[verified]`

**H2 — Arbitrary repo code execution reachable from the localhost API.**
`server.py:43` takes `repo` from the request with no confinement, and
`run_tests` is passed straight through (`server.py:48`). The UI checkbox
defaults **checked** (`index.html:42`). `subprocess.run(pytest <test_*.py>,
cwd=index.root)` (`investigate.py:322-325`) runs with the user's privileges and
**no OS sandbox**; a `test_*.py` can also `import` any sibling module, so the
"allow-list" only gates which files pytest is *told* to collect, not what runs.
Pointing the tool at a hostile repo ⇒ arbitrary execution. Acknowledged as risk
#2 in AGENTS.md, but the default-on execution and lack of repo confinement make
it wider than the docs imply. `[verified]`

**H3 — `missing_conversion` detector is name-gated to `parse*`.**
`investigate.py:49` only inspects functions whose name `startswith("parse")`.
Probe: the exact "unconverted parser output" bug, with the function renamed
`read_count`, is **missed entirely** — the agent falls back to a lexical guess
and reports `inconclusive`/wrong file. The benchmark fixture is named
`parse_count`, which guarantees the heuristic fires, so the case is partly
tailored to the detector. `[verified+probe]`

**H4 — Abstention is defeated by any single detector hit.**
`top = det_hits[0] if det_hits else None` (`investigate.py:248`) means the
`inconclusive` branch is only reached when **no** detector fires. `boundary`
(`> N`/`< N`, `investigate.py:62`) and `dict_get` (`.get(k)` w/o default,
`:69`) fire on extremely common code, so on an ambiguous query against a real
repo the agent will emit a `supported`/`high` hypothesis instead of abstaining.
The abstain guarantee that the demo hinges on is fragile. `[verified]`

### MEDIUM

**M1 — Demo stack trace references lines that do not exist in `sample_repo`.**
The pre-filled query (`index.html:36-41`, `tests/test_investigator.py:10-15`)
cites `checkout.py line 14` and `pricing.py line 9`, but `checkout.py` is 6
lines and `pricing.py` is 2. Functionally harmless (the agent re-derives the
symptom from symbols), but a judge who opens the repo sees a fabricated trace.
Fix: regenerate the trace with real line numbers (`checkout.py:6`,
`pricing.py:2`). `[verified]`

**M2 — "Execution path" is a graph path, not an execution/data-flow trace.**
`execution_path` is a BFS over the import/call file graph from symptom→root
(`investigate.py:261`, `:355-356`). It is not the call order (runtime flow is
the reverse) and carries no data-flow: the hypothesis claim *"that None flows to
the failure site"* (`:266`) asserts propagation the import graph does not prove
(an intermediate `if x is None` guard would break it). Honest reframe:
"dependency path (symptom→root)" and "None is reachable from the failure site."
`[verified]`

**M3 — Citation-validity metric is within-run self-consistency, ~always 1.0.**
Evidence is created with a hash from `snippet()` and revalidated against the
**same in-memory `FileInfo.lines` in the same pass** (`investigate.py:204-210`,
`375-377`). So `citations_valid == citations_total` unless a range is
out-of-bounds. The SHA *would* catch a changed file across index rebuilds, but
that never happens inside one investigation. The benchmark's "1.0 citation
validity" therefore measures "every citation points at existing lines," **not**
"every citation points at the *right* lines for the claim." Present it as the
former. `[verified]`

**M4 — Secret filtering is filename-only.**
`_is_secret` (`repo_index.py:16-18`) matches names/ suffixes only. A key in a
normally-named file (`settings.py`, `config.py`) is indexed, can appear in an
evidence snippet, and — when a key is configured — is sent to the Meta model.
Name-based filtering does not meet "never expose keys in logs/prompts." Add
content heuristics (key/Token/pem patterns) or redact before model synthesis.
`[verified]`

**M5 — Meta adapter HTTP path is untested; no 429 handling; cost gaps.**
The only adapter test covers no-key refusal + pricing (`tests/test_investigator.py:44-56`).
The request encoding, `output[].content[]` parsing, `usage`/cost, HTTP-error and
timeout paths have **no automated test** — the "local Responses-API stub" cited
in `docs/progress.md:32` is **not present in the repo**. Docs recommend retry on
HTTP 429 with backoff + `Retry-After`; the adapter instead raises `ModelError`
(`model_adapter.py:57-58`) with no retry. `est_cost` returns `None` for
`-contributor` variants and unknown ids (`:33-37`), and `spent()` treats `None`
as 0, so the budget cap is bypassed for those. `[verified]`

**M6 — Benchmark baseline is weak and fixtures are tiny.**
Baseline = BM25 **top-1 with no stopword removal** (`run_benchmarks.py:27-28`),
while the agent removes stopwords and — for repos ≤200 files — **scans every
file** with detectors, bypassing retrieval (`investigate.py:218-219`). So the
agent's win is "full static analysis + graph vs lexical top-1," which is fair to
claim but not "better retrieval." All 5 fixtures are 2–4 files; the boundary
case is also solved by the baseline (1/5 is really 4-of-5 separation). 5/5 on
tiny tailored fixtures does not establish generalization. `[verified]`

**M7 — Boundary detector has a very high false-positive rate in real code.**
Every `x > N` / `x < N` is flagged (`investigate.py:62`). Real repos have
hundreds of such comparisons that are not bugs; ranking mitigates but does not
eliminate, and in the fixtures each repo has exactly one comparison so it
trivially wins. `[verified]`

### LOW

**L1 — Dead branch in adapter.** `data.get("output_text")` (`model_adapter.py:62`)
is always `None` for raw Responses JSON (text is nested under `output`); the
fallback walk is what actually runs. Harmless, but misleading — drop the dead
branch or document it. `[verified]`

**L2 — Env-var naming inconsistency.** `run.py`/`README`/`.env.example` use
`MODEL_API_KEY`; `AGENTS.md`/`docs/decisions.md` also reference `META_API_KEY`.
The adapter accepts both (`model_adapter.py:21`), so this is a docs nit, not a
bug. `[verified]`

**L3 — Benchmarks mutate the tree.** Running pytest regenerates `__pycache__`/
`.pytest_cache` inside `benchmarks/fixtures/` and `sample_repo/` on every run
(gitignored, not committed). Consider running the benchmark against a copy.
`[verified]`

---

## Answering the review questions directly

- **A. Genuinely investigate, or just pattern-match?** Both. Null-cross-file and
  misleading-stack are *genuinely* traced across files via the AST import graph
  `[probe]`. Boundary and config-mismatch are essentially single-pattern
  detections that win because the fixtures are tiny. Net: real investigation on
  the hard cases, pattern-matching on the easy ones.
- **B. Are paths/graph/Evidence grounded in real facts?** Import edges are
  real AST imports. **Call edges are resolved by callee name only**
  (`repo_index.py:113-117,185-194`): attribute method names are added to a
  symbol's `calls`, so a dict `.get(...)` produces a **false call edge** to any
  function named `get`. The file-level graph used for `execution_path` is
  import-based and sound; the symbol-level call edges can be spurious.
- **C. Citations verifiable / SHA detects change?** Yes across index rebuilds;
  but within one run validity is near-tautological (M3).
- **D. Does the benchmark fairly show the agent > BM25?** It shows static
  analysis + graph > lexical top-1 on 5 tiny tailored Python fixtures, with a
  deliberately weak baseline (M6). Real but not generalization-proving.
- **E. Meta adapter conforms to the documented API?** Endpoint/auth/payload/
  models/response-shape/pricing all conform and are verified `[live]`. Gaps: no
  429 retry, no cached-token cost, contributor mispricing, and the HTTP path has
  no test (M5/most-important gap). Live integration remains unverified (no key).
- **F. Security claims accurate?** Mostly no. Name-only secret filter (M4), no
  repo confinement + default-on un-sandboxed test execution (H2), XSS via
  filenames (H1). Command logging/timeout/allow-list exist and are good, but
  "safe" overstates an un-sandboxed subprocess that can import arbitrary repo
  modules.
- **G. Distinguishes verified vs plausible vs failed vs inconclusive?** Partially.
  Status labels and confidence meanings are honest, and abstention works on the
  clean ambiguous fixture — but abstention is defeated by any detector hit (H4),
  and "confirmed-by-test" only checks that *some* allowed test failed with the
  root file named in output (`investigate.py:329-335`), which is a weak
  reproduction signal.
- **H. Demo compelling & defensible?** Largely yes and on-message (honest
  abstention, evidence graph, confirmed-by-test). Two judge-visible defects to
  fix first: the fabricated stack-trace line numbers (M1) and the
  click-to-XSS escaping gap (H1).

---

## Prioritized action plan

**Must fix before demo (all cheap):**
1. H1 — Escape repo-derived values for attribute context (escape `"'` too, or
   move to `data-*` attributes + `addEventListener`). `index.html:71,81,59`.
2. M1 — Regenerate the demo stack trace with real `sample_repo` line numbers.
3. H2 (minimum) — Require an explicit opt-in/confirm for `run_tests` on any repo
   other than `sample_repo`, and confine `repo` to a documented path; state in
   the UI that test execution runs repo code.

**Should fix if time permits (highest value first):**
4. M5 — Add a stub/monkeypatch test for the adapter HTTP path (request shape,
   `output[].content[]` parsing, usage/cost, HTTP error, timeout, 429). This is
   the biggest credibility gap given "live integration is the open item."
5. H3/M2 — Generalize `missing_conversion` beyond `parse*`, and add a real
   None/text data-flow check (or soften the claim + relabel "execution path").
6. H4 — Make abstention robust: lone boundary/dict_get hits stay `low`/
   `unverified`; require detector + graph connectivity before `verified`.
7. M6 — Add one larger fixture (root lexically distant from the query) and a
   stronger baseline (BM25 top-k + same detector candidates).
8. M4 — Content-based secret redaction before evidence/model synthesis.

**Defer:**
- OS-level sandbox (landlock/seccomp/container) for test execution.
- Non-Python symbol extraction; embeddings/vector retrieval.
- 429 backoff retry; cached-token cost modeling.

---

## Resolution status (appended 2026-10-29, after fixes)

- **H1 — FIXED.** No inline event handlers; `data-*` + `addEventListener`;
  quote-safe `esc()`. Regression: `tests/test_security.py`.
- **H2 — FIXED (minimum bar + env sanitization); OS sandbox still deferred.**
  Test execution off by default, explicit per-run confirmation required,
  `INVESTIGATOR_DISABLE_TEST_EXECUTION=1` kill switch, repo-path validation
  and optional `INVESTIGATOR_ALLOWED_ROOTS` confinement, secret-stripped
  subprocess env. README and UI state plainly that confirmed test execution
  runs repository code unsandboxed. Regression: `tests/test_security.py`.
- **H3 — FIXED.** Name gate removed; detector now requires producer
  (unconverted return) + caller (arithmetic on the result) AST evidence.
  Regression: `tests/test_detectors_hardening.py`, adversarial suite.
- **H4 — FIXED.** Non-specific queries abstain regardless of detector hits;
  specificity requires terms to occur in the repo. Regression tests +
  adversarial case "vague-on-detector-rich".
- **M1** fixed (real line numbers). **M2** relabelled "dependency path",
  claims softened. **M3** validity meaning stated in API/benchmark/README.
  **M4** pattern redaction before synthesis. **M5** stub HTTP tests + 429
  retry + unknown-pricing budget block (live inference still unverified).
  **M6/M7** mitigated by the H4 gate; honest framing in README (baseline is
  lexical top-1; fixtures are tiny Python repos). **L1** removed, **L3**
  benchmark runs from temp copies. False `.get` call edges (§B) removed.
- Measured after fixes: 25 tests passed; original benchmark 5/5 vs 1/5;
  adversarial 3/3; $0 model spend. See `docs/progress.md`.

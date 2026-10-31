# Decisions

Format: dated, ADR-style. `Confirmed` = verified fact or explicit user instruction.
`Assumption` = unverified, must be checked before it drives implementation.

## 2026-10-29 — Phase A reconnaissance
- **Confirmed:** `the developer's home directory` is the user's home directory, not a git repo,
  with no pre-existing project for this hackathon. `~/Projects` is empty.
  Existing files were left untouched.
- **Decision:** Project created at `the project root (this repository)`.
  Rationale: isolated, clearly named, does not pollute or overwrite home-dir files.
- **Confirmed (tooling):** Python 3.14.8, Node v26.12.1, npm 12.2.1, git 2.56.0,
  `rg`, `fd`, OpenCode v2.1.4; 12 CPUs, 15 GiB RAM, ~105 GiB free disk.
- **Confirmed (OpenCode view only):** Meta provider lists only
  `meta/muse-wonder-1.0` ($4/$20 per 1M in/out). This describes the OpenCode
  connection, NOT the application's runtime API.
- **Assumption (unverified):** Meta Model API endpoint, auth scheme, full model
  catalogue, context limits, and tool-calling support for the app runtime.
  Action: verify from official Meta documentation in Phase B; do not invent.
- **Assumption (user-stated):** $150 Meta AI credit available. Balance and
  billing mechanics not independently verified.
- **Decision:** No application framework/language chosen yet. Stack selection is
  a Phase B decision after Meta API verification; deterministic core favours
  whichever stack best reuses installed tooling with least new surface.
- **Decision:** Project-local skills use OpenCode V2 directory form
  `.opencode/skills/<id>/SKILL.md` with `name` + `description` frontmatter,
  per https://opencode.ai/v2/docs/skills (fetched 2026-10-29).
- **Decision:** Investigation phase is read-only; patches are proposed diffs in
  a separate phase. Test execution is allow-listed and approval-gated.

## 2026-10-29 — Phase B: Meta API verification + stack
- **Confirmed (official docs, fetched 2026-10-29):** Meta Model API base URL
  `https://api.meta.ai/v1`; auth `Authorization: Bearer $MODEL_API_KEY`
  (dev.meta.ai/docs/quickstart, /docs/authentication); Responses API
  `POST /v1/responses` with `{model, input}`; models `muse-spark-1.3`
  (also 1.2/1.1) and `muse-wonder-1.0`; 1,048,576-token context.
- **Confirmed (pricing, dev.meta.ai/docs/pricing-rate-limits):**
  `muse-spark-1.3` $1.25 in / $4.25 out per 1M; `muse-wonder-1.0`
  $4.00 / $20.00 per 1M. Rate limits 3,000 RPM / 4M TPM for both.
- **Confirmed (environment):** No `MODEL_API_KEY`/`META_API_KEY` in the shell
  env. App must therefore run fully in a deterministic no-model mode and use
  Meta only when the user supplies their own `MODEL_API_KEY` server-side.
  OpenCode's Meta credential is never read or reused.
- **Decision:** Stack = Python 3.14 stdlib only (http.server, ast, urllib) +
  vanilla HTML/CSS/JS frontend served by the same process. No pip installs,
  no framework, no vector DB. Rationale: smallest reliable stack, zero new
  attack/dependency surface, pytest already available for fixtures/tests.
- **Decision:** Model adapter defaults: model `muse-spark-1.3` (env
  `MODEL_API_MODEL`), base `https://api.meta.ai/v1` (env `MODEL_API_BASE_URL`),
  key from `MODEL_API_KEY` then `META_API_KEY`. Per-investigation caps:
  `INVESTIGATOR_MAX_MODEL_CALLS` (default 2), `INVESTIGATOR_BUDGET_USD`
  (default 1.00). Contributor-mode models are NOT used (they allow training
  on prompts/code).

## 2026-10-29 — Security hardening (per docs/review-findings.md)
- **Decision:** Test execution requires explicit per-request confirmation
  (`test_execution_confirmed=true` / UI confirm dialog), defaults off, and
  honours `INVESTIGATOR_DISABLE_TEST_EXECUTION=1`. No OS sandbox is claimed;
  the risk is disclosed in README/UI instead. Rationale: a sandbox is out of
  scope for this stack, but silent/default-on execution was the actual defect.
- **Decision:** `missing_conversion` is detected from producer+caller AST
  evidence, never from function names (H3); vague queries abstain even when
  detectors fire (H4). Heuristics that cannot be evidenced are not added.
- **Decision:** Model calls with unknown pricing block further calls in the
  same adapter instance, so the budget cap cannot be bypassed (M5).

## 2026-10-31 — Pivot to Visual Bug-to-Code Investigator
- **Decision:** Keep the deterministic ARI engine (index, detectors, graph,
  citation verification, confirmed test execution) and add a visual layer:
  screenshot validation (`app/visual.py`), console/network parsing
  (`app/logs.py`), JS/TS lexical symbols, outcome taxonomy
  (`verified|likely|inconclusive|not_reproducible`), and a 10-case visual
  benchmark separate from the original 5-case benchmark.
- **Confirmed (official docs, fetched 2026-10-31):** `muse-spark-1.3`
  image understanding via Responses API `input_image` base64 data URLs
  (dev.meta.ai/docs/image-understanding). Adapter gained
  `complete_multimodal`; visual + synthesis share the existing caps/ledger.
- **Confirmed (environment):** Still no `MODEL_API_KEY`; live Meta
  inference (text and image) remains UNVERIFIED. An unrelated provider key
  in the environment was deliberately NOT substituted for the Meta key.
- **Decision:** No browser extension, no DOM-to-source claims, no
  auto-applied patches. Screenshot = Level-1 evidence only.

## 2026-10-31 — Live Meta verified; .env loading
- **Confirmed (live):** Real `MODEL_API_KEY` calls succeed for text and
  image understanding on `muse-spark-1.3`; full demo investigation ends
  `verified` at ~$0.019/investigation. Earlier "unverified" statements in
  git history were accurate at the time and are superseded by this entry.
- **Decision:** Server loads `.env` at startup (existing env takes
  precedence; values never logged) so `python3 run.py` works with the
  documented setup. `.env` remains gitignored.

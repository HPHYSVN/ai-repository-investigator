# Architecture — Visual Bug-to-Code Investigator

Stack: Python 3.14 stdlib only + vanilla HTML/CSS/JS, single process
(`run.py` → `app/server.py`, binds 127.0.0.1). No new dependencies.

```
Browser UI (app/static/index.html)
  screenshot upload+preview · bug report · console/network logs
  outcome banner · Evidence Graph · hypotheses · diff · report
        | JSON (screenshot as base64 data URL, <=5 MB)
app/server.py  ── path validation, test-execution confirmation gate
        |
app/investigate.py  (orchestrator, structured state not chat)
  ├─ app/visual.py      screenshot magic/MIME/size validation;
  │                     Meta vision -> structured JSON observations
  │                     (degraded metadata-only mode without a key)
  ├─ app/logs.py        console/network extraction, secret redaction
  ├─ app/repo_index.py  gitignore-aware index; Python AST symbols/
  │                     imports/calls; JS/TS lexical symbols; BM25
  ├─ detectors          None-return, dict_get, boundary, config key,
  │                     unconverted producer, unresolved import
  ├─ graph              BFS dependency path (reachability, not runtime)
  ├─ hypotheses         ranked, +/- evidence, labelled confidence,
  │                     H4 abstention gate for non-specific queries
  ├─ tests (opt-in)     allow-listed pytest, confirm-gated, 60s,
  │                     secret-stripped env, real exit codes logged
  ├─ verification       every citation rechecked (exists/range/SHA-256)
  └─ app/model_adapter.py  Meta Responses API (text + input_image),
                           caps, 429 backoff, token/cost ledger
```

Evidence levels: L1 screenshot observation → L2 description → L3 logs →
L4 source link → L5 test-verified. Outcomes:
`verified|likely|inconclusive|not_reproducible` (meanings in
`app/investigate.py:OUTCOMES`).

Trust boundaries: repo files, logs, and screenshots are untrusted data
(escaped in UI, redacted before model calls, never executed except
confirm-gated pytest in the target repo). Investigation is read-only;
patches are proposed diffs only. Live Meta inference is unverified in
the dev environment (no `MODEL_API_KEY`); see README.

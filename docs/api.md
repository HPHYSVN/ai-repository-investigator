# Local API

Server binds `127.0.0.1` only. No authentication — local developer tool.

## GET /api/health
Returns `{ok, model_configured, model, mode, test_execution_disabled,
default_repo}`. `model_configured` is true only when `MODEL_API_KEY`
(or `META_API_KEY`) is set in the server environment.

## POST /api/investigate
JSON body:
```json
{
  "repo": "/absolute/path/to/repo",
  "query": "bug description and/or stack trace (required)",
  "screenshot_b64": "data:image/png;base64,... (optional, <=5 MB)",
  "console_log": "optional, <=20000 chars",
  "network_log": "optional, <=20000 chars (never send auth headers)",
  "run_tests": false,
  "test_execution_confirmed": false
}
```
`run_tests: true` without `test_execution_confirmed: true` is rejected
(HTTP 400) because it executes repository code, unsandboxed.

Response (abridged): `{status, outcome, outcome_meaning, visual, logs,
evidence_levels, steps, hypotheses[], evidence[], graph{nodes,edges},
execution_path, test_log[], patch, regression_test, report,
verification{citations_checked, citations_total, meaning}, model,
latency_s}`. Hypothesis statuses:
`unverified|supported|rejected|confirmed-by-test|inconclusive`;
outcomes: `verified|likely|inconclusive|not_reproducible`.

Errors are `{error: "..."}` with 400/404/413 status codes. Invalid or
oversized screenshots are rejected before any investigation runs.

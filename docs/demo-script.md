# Demo Script (2–3 min) — Visual Bug-to-Code Investigator

Start: `python3 run.py` → http://127.0.0.1:8765 (pre-filled with the demo).
Demo repo: `demo_webapp/` (agent indexes only this dir when selected).
Expected answer, kept here outside the indexed repo: unknown gift SKU →
`catalog.get_product` returns None → `cart.cart_total` (`cart.py:8`)
silently returns None → `pricing.format_price` crashes → total blank,
checkout 500. Measured 2026-10-31: outcome `verified`, root `cart.py`,
pytest exit 1, proposed patch applied in a temp copy makes tests pass.

## Flow
1. **Show the bug (20s).** Open `demo_webapp/screenshot.png` (or the page):
   cart total blank, "Checkout failed". State the promise: screenshot shows
   *what* is wrong, not *which line* — evidence has to earn that link.
2. **Upload + describe (20s).** Upload the screenshot in the UI; the bug
   report, console (`TypeError …NoneType`) and network (`POST /api/checkout
   -> 500`) fields are pre-filled. Note the evidence levels L1–L5.
3. **Investigate (40s).** Live steps: indexing, log extraction, BM25,
   detectors, dependency path pricing → cart_api → cart. Visual panel:
   with a real `MODEL_API_KEY`, Muse Spark returns observable/inferred/
   cannot-determine; without one it honestly reports metadata-only.
4. **Hypotheses + graph (30s).** H1 `cart.py` None-return with source
   evidence; H2 crash-site hypothesis rejected. Click graph nodes/evidence
   to see exact `file:line` source. Contradicting evidence shown, not hidden.
5. **Verify (30s).** Tick test execution, read the warning, confirm. Actual
   command + exit code 1 appear; H1 becomes `confirmed-by-test`, outcome
   `verified` — only because a real test ran.
6. **Fix (20s).** Proposed diff (explicit `ValueError` instead of silent
   `None`) — *not applied*; suggested regression test shown separately.
   Mention: applied in a temp copy during development, tests passed there.
7. **Close (10s).** "What Meta does: vision + synthesis (live-verified
   2026-10-31, ~$0.02 per investigation). What deterministic tools do:
   everything that must be provable. What a screenshot alone can never do:
   name the guilty line — the code and the test earn that."

## Fallbacks
- No network/key: the whole flow above runs deterministically; say so.
- If live investigation is inconclusive, present the abstention honestly —
  it is the product working as designed.
## Evidence checklist before recording
- [ ] Citations pass revalidation (UI shows checked/total).
- [ ] Test output is from an actual run in the recording.
- [ ] No API keys visible anywhere.

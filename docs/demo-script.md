# Demo Script (2–3 min) — draft, to be finalised in Phase F

Prerequisite: a sample repo with a planted, nontrivial, multi-file bug, whose
expected root cause/evidence is documented separately and NOT visible to the
agent at runtime. Nothing below may be hardcoded or mocked.

## Flow
1. **Open repo (20s).** Select the sample repo; show honest indexing status
   (files indexed/skipped, respecting `.gitignore`).
2. **Submit bug (20s).** Paste a realistic report/stack trace where the failure
   site is not the root cause.
3. **Investigate (60s).** Live: candidate files/symbols, deterministic search
   steps, execution path reconstructed across files. No fabricated progress —
   each step shown is a real tool call.
4. **Evidence Graph (30s).** Symptom → path → candidate root causes; click a
   node to see exact source with file path and line numbers.
5. **Hypotheses (30s).** Top hypothesis with supporting AND contradicting
   evidence, confidence label + what the label means; competing hypothesis
   shown as rejected with its evidence.
6. **Verify (20s).** Run the targeted existing test; show the actual command,
   exit code, and output; hypothesis status updates to `confirmed-by-test`
   only if it truly passed.
7. **Report + patch (20s).** Evidence-backed report; proposed patch and
   regression test as a reviewable diff — not silently applied.

## Fallbacks
- Recorded run of the identical, unedited workflow + screenshots, in case of
  live API/network failure. Recording must be a real run, not a mock.
- If the live investigation is inconclusive, present that honestly — correct
  abstention with next steps is on-message for this product.

## Evidence checklist before recording
- [ ] All report citations pass programmatic revalidation.
- [ ] Test output in demo is from an actual run.
- [ ] No API keys visible in UI, logs, terminal, or recording.
- [ ] Demo repo's expected-answer notes kept outside agent-readable paths.

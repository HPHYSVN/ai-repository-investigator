---
name: Evidence Verification
description: Verify that every claim, citation, graph edge, and test result in an investigation report is backed by current repository facts before it is presented. Use before finalising any report, hypothesis status change, or patch proposal.
---

# Evidence Verification

Run before any report, Evidence Graph, or patch is shown to the user.

## Checklist
1. **Revalidate every citation.** For each `file:start-end`: file exists, range
   is within file length, and current content matches the snippet recorded at
   read time. Drop or flag stale citations — never silently keep them.
2. **Classify each claim.** Direct source evidence / static-analysis finding /
   test result / model inference. Model inferences must not be worded as facts.
3. **Check hypothesis integrity.** Supporting AND contradicting evidence present
   or explicitly noted as none found. Confidence is a label
   (`low|medium|high|confirmed`) with a written explanation — no bare %.
   Status is one of `unverified|supported|rejected|confirmed-by-test|inconclusive`.
4. **Check test claims.** A "passed/reproduced" claim requires a logged command,
   cwd, exit code, and output from this session. Otherwise rewrite as "not run".
5. **Check the graph.** Every node maps to a real file/symbol/test/hypothesis;
   every edge maps to an extracted import/call/data-flow fact or a logged test
   result. Remove LLM-invented edges.
6. **Scan for fabrications.** Function names, files, stack frames, and outputs
   mentioned in prose must exist in the collected evidence set.
7. **Abstention test.** If the top hypothesis lacks direct evidence, the report
   must lead with what is unknown and the next diagnostic step, not a guess.

## Output
A short verification summary: citations checked N/N valid, claims reclassified,
fabrications removed, hypotheses downgraded — recorded in `docs/progress.md`
for benchmark runs, or attached to the investigation report in the app.

# Architecture

Status: implemented (Phase C–F, 2026-10-29). Stack: Python 3.14 stdlib only
+ vanilla HTML/CSS/JS, single process (`run.py` → `app/server.py`).
Meta Model API verified from official docs — see `docs/decisions.md`.

## Proposed separation of concerns
```
UI (local web app)
  └─ Investigation orchestrator (structured state machine, not chat)
       ├─ Repository tools (deterministic): git, file/symbol search,
       │   parsing, import/call graph, targeted reads, test runner
       ├─ Retrieval/indexing: lexical/BM25 first; embeddings only if
       │   a measured recall gap justifies them
       └─ Model adapter (provider-isolated): Meta Model API primary,
           optional fallback; classification / planning / hypothesis
           evaluation / final synthesis as separate, logged call sites
Evidence store: citations (file, lines, snippet hash), hypotheses, graph
nodes/edges, test logs, model-usage ledger (model, count, latency, tokens, cost)
```

## Core data types (proposed)
- `Investigation`: query, repo ref, status (`investigating|verified|inconclusive|failed`), steps log.
- `Evidence`: id, kind (`source|static|test|inference`), file, line range, snippet hash, text.
- `Hypothesis`: claim, supporting[], contradicting[], files/symbols/lines,
  confidence label + explanation, missing evidence, next steps, status.
- `EvidenceGraph`: nodes (symptom, file, symbol, hypothesis, test) and edges
  (calls, imports, data-flow, supports, contradicts, confirms, rejects) — built
  only from extracted facts and logged results.
- `Citation check`: re-read file range and compare snippet hash before display.

## User journey (acceptance criteria for Phase C vertical slice)
1. Select a local Git repo → indexing status shown honestly (files indexed, skipped).
2. Submit a bug report or stack trace → investigation state advances visibly.
3. Relevant files/symbols and execution path shown with clickable `file:line` evidence.
4. Hypotheses ranked with supporting/contradicting evidence; inconclusive is a valid result.
5. Final report whose citations all pass programmatic revalidation.
6. Test log shows only commands that actually ran, with exit codes.

## Technical risks
- Meta Model API surface (models, tool calling, limits) unverified — verify
  from official docs first; adapter must tolerate rate limits/timeouts/bad JSON.
- Running untrusted repo tests safely — allow-list + timeout + approval gating.
- Large repos — index incrementally, never load all files into context.
- Prompt injection via repo content — treat as data, never instructions.
- Budget: $150 stated credit; strong model reserved for synthesis, cheap calls
  elsewhere, hard caps, reserve for final demo.

## Deferred (nonessential until core works)
Vector DB, multi-repo support, embeddings, auto-applied patches, auth/multi-user.

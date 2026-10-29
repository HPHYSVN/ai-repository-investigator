# Decisions

Format: dated, ADR-style. `Confirmed` = verified fact or explicit user instruction.
`Assumption` = unverified, must be checked before it drives implementation.

## 2026-10-29 — Phase A reconnaissance
- **Confirmed:** `/home/phamthuoi` is the user's home directory, not a git repo,
  with no pre-existing project for this hackathon. `~/Projects` is empty.
  Existing files were left untouched.
- **Decision:** Project created at `/home/phamthuoi/ai-repository-investigator`.
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

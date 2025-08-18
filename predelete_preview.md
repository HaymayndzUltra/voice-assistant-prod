Pre-Delete Preview — Hard Delete Candidates

Input Status
- hard_delete manifest: MISSING
- evidence.json: MISSING

Preview Rows
- No entries to display. The expected columns per entry are listed for clarity:

| Path | Score | Tests Passed | Tests Failed |
|------|-------|--------------|--------------|
| (none) | (n/a) | (n/a) | (n/a) |

Notes
- The repository scan did not reveal any hard_delete list. Without this manifest, a per-entry preview cannot be produced.
- When a manifest is provided, this preview should enumerate each entry with:
  - Path: absolute or repo-relative target path
  - Score: numeric or categorical score used to prioritize deletion
  - Tests Passed/Failed: derived from evidence.json for that path

Operational Guardrails (Analysis-only)
- No deletions were performed or proposed beyond listing structure.
- Aligns with security/SRE policy: preview only; requires explicit approval and complete evidence before any action.


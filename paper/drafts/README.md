# Author manuscript drafts (not the submission manuscript)

`main.tex` here is the **author's A1 draft**, installed verbatim from the
v1.0.1 tolerance-provenance package on 2026-09-29 and pinned in
`results/final_manifest.json` → `frozen_hashes.manuscript_display_sha256`.

- It is **not** the submission manuscript. `paper/main.tex` remains the
  anonymous AASTeX skeleton for dual-anonymous review, and CI enforces that the
  submission manuscript carries no identifying strings
  (`tests/test_release_consistency.py`). This draft cites a repository URL that
  contains the author's username, so it cannot be promoted to `paper/main.tex`
  while the anonymity gate is in force.
- It is kept because the v1.0.1 display-provenance record needs the manuscript
  that consumes the regenerated figures and tables
  (`paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json`).
- Promoting it to `paper/main.tex`, or folding its prose into the submission
  manuscript, is an author decision outside the provenance patch. Bytes are
  never edited in place: see the release manifest for the pinned hash.

# Final-era run scripts (A1 release)

This directory will hold the nine frozen FINAL scripts (see `SCRIPT_REGISTRY.json`
for names + SHA-256). Older direct-Kaggle scripts live in `workflows/kaggle/` for
provenance; final paper outputs must come from the scripts committed here.

## Receipt protocol

1. Take the `.py.txt` handoff file, verify `sha256sum` against `SCRIPT_REGISTRY.json`.
2. Save it here as `*.py` (same bytes, no `.txt` suffix).
3. Flip its registry status to `received`.
4. CI compiles every `workflows/**/*.py`; the release-consistency test asserts every
   `received` script matches its registry hash.

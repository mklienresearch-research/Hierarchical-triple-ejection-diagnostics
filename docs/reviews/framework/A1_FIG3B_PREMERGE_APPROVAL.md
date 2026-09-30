# Figure 3b Provenance Correction — Pre-Merge Approval

**Date:** 2026-09-30

**Decision:** FIGURE 3b PROVENANCE CORRECTION APPROVED FOR BYTE-EXACT GITHUB STAGING.

## Approved bytes

| File | SHA-256 | Bytes |
|---|---|---:|
| `scripts/production/make_a1_main_results_figures.py` | `70057a0d8f87ae26ec7beb20c2e3467070b7d616c8e51b916162fac02914b9f9` | 11,542 |
| `paper/figure_data/fig03_robustness_endpoints.json` | `2ca4bbaa01c2fef3e5db19b3dfd71f0b1e08cdfc89fb88425e0a4c679d8de3d7` | 3,198 |
| `paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json` | `34bc46e7f3b3eef16a1cbd22dc08bb3cd8032b5f9298e4f1d379c15b0145424a` | 10,504 |
| `paper/drafts/main.tex` | `f43b05a3e096b313859660f8b49ef8d0c611abdc5997cddd4e5614bcabeaa610` | 47,162 |
| Compiled PDF | `de6cb36d54b5f0da8564510303263924fc6e021f1202ab1866e99c07627b3119` | 222,451 |

The 3,198-byte JSON has no terminal line-feed. GitHub staging must install the generated file bytes, not a package delimiter line-feed.

## Approved semantics

- Figure 3b values are unchanged: cutoffs 100/300/1000/3000 and incidence 31.077/34.989/38.104/40.079 percent.
- Figure 3b is explicitly a hash-pinned transcription from the ledger/addendum, not a machine-read ledger input.
- Both source paths and full hashes are recorded.
- All other panels/tables retain machine-read status.
- No scientific/displayed value, cohort, endpoint, uncertainty, or table value changed.

No residual framework edit remains before byte-exact GitHub staging.

# Reproducibility workflow

## Small tests

```bash
python -m pip install -e '.[dev]'
pytest
```

The causal-invariance test extends a synthetic record with extreme post-horizon values and requires the extracted horizon feature vector to remain bit-identical.

## Kaggle production

Direct self-contained files are under `workflows/kaggle/`:

- `FINAL_ANALYSIS_4CORE.py`: final standard-CPU analysis with stored indices 72 and 73 disabled;
- `FINAL_ANALYSIS_96.py`: final TPU-host analysis with the same safeguards;
- `FINAL_AUDIT_4CORE.py`: final adversarial controls with both future-length columns disabled;
- `DEEPTAIL_100K_3000_CORRECTED.py`: matched survival/censoring production run;
- `combine_chunks.py`: chunk assembly.

Earlier `CORRECTED_*` workflows are retained only for provenance. Final paper outputs must come from the `FINAL_*` workflows.

The final paper-level analysis will supersede the current corrected scripts by additionally disabling stored `first_breach` index 72. The repository README and correction record track this explicitly.

## Result integrity

Each committed result directory contains `SHA256SUMS.txt`. Verify with:

```bash
cd results/corrected_analysis_4core
sha256sum -c SHA256SUMS.txt
```

Large data artifacts must have a separate manifest containing checksums, sizes, simulation seed, ID ranges, and the Git commit used to produce them.

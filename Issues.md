# Known Issues

## 1. Plot overwrite when left and right use the same calibration

**Problem**: When both left and right sides of the report use the same calibration hash but different run IDs, the second plot overwrites the first because the plot output filename only includes the calibration hash, not the run ID.

**Example**: With `calibration_left=2447f0fad3...` `RUNID_LEFT=20251108115234` and `calibration_right=2447f0fad3...` `RUNID_RIGHT=20251110092039`, both generate `reuploading_classifier_results_2447f0fad3....pdf` — the right plot overwrites the left.

**Effect**: Both sides of the report display the same plot image (from the right/second run), while the bullet point values (Runtime, Qubits used, Accuracy) are correctly extracted from their respective results.json files. This causes a mismatch between the plot visuals and the bullet point data on the left side.

**Affected benchmarks**: All benchmarks that use `calibration` as the `exp_name` in plot output paths — Reuploading Classifier, Grover 2Q, Grover 3Q, GHZ, Process Tomography, QFT, Amplitude Encoding, and others.

**Root cause**: In `prepare_context.py`, the plot functions receive `calibration` as the experiment name (e.g., line 473: `exp_name=calibration`), and the plot functions in `plots.py` use this as part of the output filename without including the run ID.

**Fix**: Include the run ID in the plot output path or filename to ensure unique filenames per run. For example, change `exp_name=calibration` to `exp_name=f"{calibration}_{run}"` in the prepare_context functions.
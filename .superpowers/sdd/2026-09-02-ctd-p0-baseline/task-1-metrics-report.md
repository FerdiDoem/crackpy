# Task 1: Baseline-Vertrag und Metrikkern

## Scope

Implemented only the additive `crackpy.benchmarking` metric layer and its contract tests.
No legacy CrackPy detector, decoder, training helper, or fixture was changed.

## Test-first record

The initial test run failed during collection because `crackpy.benchmarking` did not exist.
After the minimal metric implementation, the focused test command passed with 17 tests.

```text
.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_metrics.py -q
17 passed
```

## Delivered contract

- `TipMetrics` preserves successful detections, failed detections, and missing references as separate counts.
- Tip error distributions are explicitly conditional on successful detections, with a `None` summary for an empty conditional population.
- Dice and IoU define two empty masks as a perfect match and one empty mask as zero overlap.
- Path distance is the mean of both directed nearest-neighbour distances.
- HD95 is the 95th percentile over both directed nearest-neighbour distance sets.
- Both-empty paths score `0.0`; one-empty path comparisons are undefined and return `None`.
- Angle error uses the smallest orientation distance modulo 180 degrees.
- Result dataclasses offer JSON-compatible `to_dict` methods.

## Review notes

The path nearest-neighbour computation is chunked to avoid allocating a full pairwise distance matrix for dense segmentation-derived paths.
The metric policy intentionally differs from the legacy training evaluation helpers, which omit failed detections from their localization statistic.

## Environment note

Before a coordination message instructed agents not to modify the shared virtual environment, this task installed test dependencies needed to execute the red/green loop.
The current PyTorch package reports version `2.14.0+cu130`; environment ownership now remains with the parent task.

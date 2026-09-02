# Task 2: Reproduzierbare Inferenz und Laufzeitmessung

## Scope

Implemented only the additive runtime and provenance helpers in `crackpy.benchmarking` and their contract tests.
No legacy detector, decoder, pipeline, model, fixture, or inference behavior changed.

## Test-first record

The initial focused test command failed during collection because `crackpy.benchmarking.ctd_runtime` did not exist.
After the minimal implementation, the focused runtime tests and the combined benchmark-package tests passed.

```text
.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_runtime.py -q
5 passed

.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_metrics.py crackpy/tests/test_benchmarking/test_ctd_runtime.py -q
27 passed
```

## Delivered contract

- Seeds Python, NumPy, and Torch, enables Torch deterministic-algorithm warnings, and configures cuDNN for deterministic rather than benchmark-selected kernels.
- Records SHA-256 for model artifacts plus Git commit, Python, platform, NumPy, Torch, CUDA, and selected-device metadata.
- Excludes an explicit warm-up phase from timing and GPU-peak accounting.
- Separately times every supplied phase, with mean, median, P95, min, max, and raw duration samples.
- Synchronizes CUDA before and after each measured phase so host timings include completed GPU work.
- Reports end-to-end throughput, process RSS, and CUDA peak allocated memory.
- Uses dataclasses containing only finite JSON-native values or explicit `null` equivalents, which serialize with `allow_nan=False`.
- Permits injection of a Torch-compatible object, timer, and process object, so CUDA behavior and timing are deterministic and mockable in tests.

## Review notes

The benchmark accepts callables rather than modifying CrackPy's existing detector methods.
The eventual B0/B1/B2 runner must arrange its own phase callables, including any interpolation, model invocation, decoding, correction, and plotting exclusion.
GPU peak memory is reset only after warm-up completion and is measured only when the selected device is an available CUDA device.

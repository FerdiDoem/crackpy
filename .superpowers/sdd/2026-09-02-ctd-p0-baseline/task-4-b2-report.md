# Task 4 B2: Williams Correction Baseline

## Scope

Implemented only the optional B2 runner and its additive result contract.

The separately completed Mendeley A0 documents were not changed.

No legacy detector, decoder, coordinate mapping, path metric, model, fixture, or numerical expectation was changed.

## Test-first record

The first focused B2 test failed during collection because `build_b2_result` did not exist.

After the minimal result-contract implementation, the focused baseline suite passed.

A second red phase showed that `--include-b2` was not accepted by the CLI.

After adding the opt-in flag, the focused suite passed again.

A final red phase demonstrated that an unexpected model failure was swallowed by a broad B2 exception handler.

The handler was removed so unexpected model and pipeline errors now propagate fail-fast.

The resulting focused B2 baseline test run passed with twelve tests.

## Delivered contract

- B2 is off by default and is enabled only with `--include-b2`, so standard B0/B1 runs do not pay Williams-correction cost.
- The run uses the shipped Dummy2 DIC nodemap at stage 52 on the right side with the original `ParallelNets` and `UNetPath` models supplied by the benchmark CLI.
- It retains the settings from CrackPy's original correction example: a 40 mm window, `(-10, 0)` mm offset, 10 mm angle radius, the symbolic-regression correction method, and Williams terms `[-1, 0, 1, 2]`.
- Plot generation is explicitly disabled.
- The strict-JSON B2 record reports initial AI tip and angle, correction vector, final tip, correction iterations, phase-level runtime, and a structured status.
- Both the top-level record and its status explicitly set `independent_ground_truth_available` to `false`.
- `accuracy_claim_supported` is `false`, so the bundled example is not represented as evidence of an accuracy gain.
- Missing nodemap, unavailable initial tip, unavailable initial angle, and absent Williams fit iterations remain explicit status codes.
- The adapter now distinguishes convergence, an interrupted internal Williams fit, and exhaustion of the maximum iteration count from the legacy iteration log.
- Warm-up and measured repetitions reset every intermediate value before preprocessing, so a measured failure cannot inherit a warm-up tip or correction.
- The default timing uses one warm-up and three measured repetitions.
- Unexpected execution failures propagate instead of being silently converted into a result artifact.

## Verification

```text
.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_baseline.py -q
12 passed

.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking -q
42 passed

.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_crack_detection/test_pipeline/test_pipeline.py -q
1 passed
```

The real CPU smoke command was:

```text
.\\.venv\\Scripts\\python.exe scripts\\crack_detection\\benchmark_ctd_p0.py --device cpu --fixture-only --include-b2 --output .downloads\\b2-smoke.json
```

It completed with status `completed`.

The smoke artifact recorded an initial AI tip of approximately `(15.5902, 0.3934)` mm, an initial AI angle of approximately `-0.6978` degrees, correction vector `(1.1101, 0.1073)` mm, final tip `(16.7003, 0.5007)` mm, and eight correction iterations.

Its measured CPU Williams-correction phase was approximately `15.1` seconds.

The generated smoke JSON remains untracked in `.downloads` and is not a final P0 result.

## Caveats

The bundled Dummy2 example has no independent corrected-tip ground truth.

Its correction vector and final position are therefore functional and runtime observations only, not a demonstrated accuracy improvement.

The first implementation smoke used one measured B2 iteration and remains only reproducibility validation.
The final P0 runner uses one warm-up and three measured repetitions for median and P95 reporting.

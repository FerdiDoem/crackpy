# Task 5 slice: B0/B1 phase-resolved runtime measurement

## Scope

Added an additive P0 runtime adapter for the frozen B0/B1 repository-fixture batch.
The legacy detector APIs, decoder, baseline harness, CLI, fixtures, and model artifacts remain unchanged.
The adapter measures the first loader invocation as `first_in_process_model_loading` exactly once with no warm-up.
The steady-state batch separately measures normalisation/resize-preprocessing, host-to-device transfer, tip forward pass, tip device-to-host transfer, historic tip decoding, path forward pass, path device-to-host transfer, thresholding/skeletonisation, and angle postprocessing.
The existing CUDA-synchronised phase timer owns every reported phase measurement.
Batch iterations per second and images per second are emitted as separate named values.
Plotting and result writing are visibly `disabled_not_requested` because this measurement slice neither plots nor writes an artifact.

## Test-first record

The initial focused test run failed during collection because `crackpy.benchmarking.ctd_p0_runtime` did not exist.
After the minimal adapter implementation, the focused contract tests passed.

```text
.\\.venv\\Scripts\\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_p0_runtime.py -q
2 passed
```

## GPU fixture smoke

The real original `ParallelNets` and `UNetPath` models completed a CUDA fixture smoke run on the three bundled right-side 256-pixel fixtures.
The run used one warm-up iteration and one measured iteration without writing a result file.
The first-in-process model-loading duration was approximately 245.053 ms.
The steady-state throughput was approximately 28.512 batch iterations per second and 85.535 images per second for the three-image batch.
All nine steady-state phase names were present, and strict JSON serialization with `allow_nan=False` succeeded.

## Caveat

The cold-start value is an explicit first loader invocation contract, so the final P0 runner must call it before constructing either model in its process.
It must remain separate from the post-warm-up steady-state timing rather than being averaged into it.

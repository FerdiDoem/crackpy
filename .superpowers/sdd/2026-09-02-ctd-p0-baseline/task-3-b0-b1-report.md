# Task 3: B0/B1 und CrackMNIST-Adapter

## Scope

Implemented the additive frozen B0/B1 evaluation harness, its command-line runner, public benchmark exports, and focused tests.
No legacy CrackPy detector, decoder, model architecture, fixture, or numerical reference was changed.
No training or fine-tuning path was added.

## Test-first record

The first focused run failed during collection because `crackpy.benchmarking.ctd_baseline` did not exist.
After the metric-facing implementation, eight focused tests passed.
A second red phase introduced the runtime-separation and CLI contracts and failed because the runtime function did not exist.
After implementing those contracts, all ten focused tests passed.

```text
.\.venv\Scripts\python.exe -m pytest crackpy/tests/test_benchmarking/test_ctd_baseline.py -q
10 passed

.\.venv\Scripts\python.exe -m pytest crackpy/tests/test_benchmarking -q
38 passed
```

## Delivered contract

- B0 uses the unchanged `find_most_likely_tip_pos` decoder as its primary output.
- The ParallelNets coordinate head is denormalized and reported only as `coordinate_head_diagnostic`.
- B1 thresholds and skeletonizes the original UNetPath output and derives the local angle through CrackPy's existing circular-mask, largest-region, and linear-regression logic.
- The three repository fixtures use label `2` as tip reference, label `1` as path reference, and `70 / 255` millimetres per model pixel.
- CrackMNIST is restricted to the official test split, size S, 128 pixels, and crack-tip segmentation task.
- The primary CrackMNIST mode resizes raw fields to 256 pixels with bilinear `align_corners=True` before exact per-channel CrackPy normalization.
- Native 128-pixel execution is available only as an explicitly marked sensitivity analysis.
- Historical decoder points are converted from CrackPy's endpoint-valued convention into original 0-to-127 pixel indices before CrackMNIST errors are computed.
- Coordinate-head points use the separate endpoint-inclusive model-index mapping, so both outputs are compared in the same reference raster without modifying the original decoder.
- No millimetre conversion is emitted without an explicit FOV assumption.
- Empty reference masks count as missing references, while absent predictions against valid references remain detection failures.
- Compact per-sample records include experiment identity, reference availability, primary and diagnostic coordinates and errors, Dice, and IoU.
- Dataset provenance includes split, size, pixels, verified H5 MD5, total and evaluated sample counts, experiment side, and the absence of a source-sample ID for augmented samples.
- Models are frozen with gradients disabled and executed in batches under `torch.inference_mode()`.
- Runtime output keeps the batched evaluation harness separate from the unchanged historic single-image detector APIs.
- The CLI defaults to the complete CrackMNIST test split and exposes device, dataset root, output, optional limit, batch size, resolution mode, and fixture-only smoke mode.
- Every result path is serializable with strict JSON and no NaN values.

## Real integration verification

The original ParallelNets and UNetPath artifacts ran successfully on the NVIDIA GeForce RTX 5070 Ti with PyTorch `2.14.0+cu130` and CUDA runtime `13.0`.
The three-fixture GPU smoke run completed with zero tip and path detection failures.
Its primary mask-decoder median tip error was about `0.481 mm`, while the separately reported coordinate-head diagnostic median was about `1.977 mm`.
The B1 derived-angle median error was about `5.064 degrees` on these three fixtures.
These values verify the integration only and are not the final P0 benchmark report.

A two-sample real CrackMNIST GPU smoke run also completed through the official package adapter.
It recorded the expected H5 MD5 `3101a618e0837276b1ef4533964fabb3`, the full split size of 5,944, experiment ID 3, and experiment name `MT160_2024_TL_1_right`.
Both smoke samples produced primary detections and strict-JSON per-sample records.

## Concerns and boundaries

The complete 5,944-sample CrackMNIST run remains Task 5 work and was deliberately not executed here.
The augmented CrackMNIST samples have no exposed source-sample ID, so this harness explicitly avoids claiming that all 5,944 records are independent observations.
Repository angles are derived from the available path labels with the same estimator used for predictions; they are not independently annotated angle ground truth.
The historic decoder itself remains unchanged even though its `linspace` spans zero through the pixel count rather than zero through pixel count minus one.
The benchmark records this convention and removes it only at the comparison boundary so a decoder endpoint cannot be compared directly with a 0-to-127 label index.

## Independent review fixes

An independent Task-3 review found that the first CrackMNIST adapter compared two different coordinate conventions, omitted an explicit empty-path rate, and lacked complete CrackMNIST package provenance.
Endpoint and midpoint tests now cover both the historical decoder convention and true model-index convention.
Repository path output now separates empty predictions, missing path references, failed predictions, and non-evaluable angles.
CrackMNIST provenance now records the installed distribution version and the SHA-256 digest of `experiments_metadata.json` in addition to the H5 digest.
Smoke-run timing and generated JSON files remain local verification artifacts under `.downloads` and are not committed as final P0 results.

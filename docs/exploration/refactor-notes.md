# Refactor Notes

Status: future architecture notes, not observed behavior

These notes intentionally separate proposed future architecture from current system reality. No refactoring was performed in this exploration phase.

## Candidate 1: Explicit Analysis Result

Files involved:

- `crackpy/fracture_analysis/analysis.py`
- `crackpy/results/write.py`
- `crackpy/results/plot.py`
- `crackpy/results/result_data.py`

Problem:

`FractureAnalysis.run()` mutates many attributes, and output modules know those attributes directly. This makes the interface broad and contributes to the `fracture_analysis <-> results` import cycle.

Future direction:

Introduce an explicit `AnalysisResult` module that records optimization results, line-integral results, path metadata, and method availability. `OutputWriter` and `Plotter` would consume the result interface rather than a live `FractureAnalysis` object.

Benefit:

Higher locality for result shape, a smaller test surface, and a stable contract for CLI/MCP/workflow orchestration.

## Candidate 2: Input Loading Seam

Files involved:

- `crackpy/input/input_data.py`
- `crackpy/structure_elements/data_files.py`
- detection/fracture pipelines

Problem:

`InputData` currently acts as file adapter, schema, mutable container, transform module, and mechanics helper. Callers must know file format and field lifecycle details.

Future direction:

Create a loading seam around nodemap file loading, manual/in-memory loading, metadata extraction, and possibly FEM-vs-DIC interpretation. Candidate adapters:

- nodemap file adapter;
- in-memory/test adapter;
- future uploaded-file or workflow-manager adapter.

Benefit:

Nodemap format quirks and metadata parsing become local. External orchestration can provide data without pretending to be a nodemap file.

## Candidate 3: Self-Contained Williams Fit Interface

Files involved:

- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/analysis.py`
- `crackpy/crack_detection/correction.py`

Problem:

Williams fitting is reusable, but its current interface depends on transformed `InputData`, mutable option defaults, and `Optimization` constructor side effects.

Future direction:

Expose a pure computational interface that accepts explicit arrays, material parameters, terms, and fitting-domain settings, then returns coefficients and residual metrics. Pipeline classes can adapt `InputData` into that interface.

Benefit:

The Williams fit becomes easier to call from CLI, MCP, tests, crack-tip correction, and graph-based workflows.

## Candidate 4: Separate Orchestration From Adapters

Files involved:

- `crackpy/fracture_analysis/pipeline.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/results/*`

Problem:

Pipelines combine algorithm orchestration with filesystem, plotting, progress, multiprocessing, and result-writing policy.

Future direction:

Split into:

- job runner returning structured results;
- output adapters for text, JSON, CSV, and plots;
- progress adapters such as rich, null, or MCP progress;
- execution adapters such as serial or process pool.

Benefit:

Graph execution and CLI/MCP access can reuse the same computational runner without inheriting file/plot/progress behavior.

## Candidate 5: Side Orientation Module

Files involved:

- `crackpy/crack_detection/data/interpolation.py`
- `crackpy/crack_detection/detection.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- plotting and training-data utilities

Problem:

Left/right orientation is encoded repeatedly through strings, sign flips, mirrored arrays, signed window sizes, and coordinate conversion logic.

The current `side` concept also bundles several ideas that should likely be separated before redesign: physical specimen geometry, notch or crack origin, crack propagation direction, and algorithmic mirroring. MT specimens, CT specimens, and future geometries may not share one universal left/right model.

Future direction:

Create a `SideOrientation` or broader geometry/orientation module that owns mirroring, signed window size, suffix naming, pixel-to-mm conversion, and the relationship between specimen geometry, notch/crack origin, and propagation direction.

Benefit:

Higher leverage and locality for one domain concept used by detection, training, plotting, and output.

## Candidate 6: Model Provider Seam

Files involved:

- `crackpy/crack_detection/model.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- scripts using pretrained models

Problem:

Model loading combines model construction, local cache policy, network download, weight loading, and device behavior.

Future direction:

Introduce a `ModelProvider` interface with adapters for local weights, Zenodo download/cache, test doubles, and future service/workflow providers.

Benefit:

Detection algorithms become less coupled to filesystem and network policy.

## Candidate 7: Defaults And Options Cleanup

Files involved:

- `crackpy/fracture_analysis/analysis.py`
- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/line_integration.py`
- `crackpy/structure_elements/data_files.py`
- `crackpy/structure_elements/material.py`

Problem:

Mutable default objects are instantiated at function-definition time and then mutated by default-normalization helpers.

Future direction:

Use explicit construction per call, dataclasses where appropriate, and pure default builders for method-specific options.

Benefit:

Removes hidden shared state and makes option lifecycle easier to test.

## Candidate 8: Result Tag Schema

Files involved:

- `crackpy/results/write.py`
- `crackpy/results/read.py`
- fracture-analysis tests

Problem:

Text tags and output keys are stringly typed across writers, readers, tests, and scripts.

Future direction:

Centralize result tag definitions and column schemas. Treat text output as an adapter over structured results.

Benefit:

Reader/writer consistency becomes local, and CSV generation can be validated against the schema.

## Candidate 9: Acquisition Index Vocabulary

Files involved:

- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/fracture_analysis/pipeline.py`
- scripts and tests that parse stage numbers from filenames
- `docs/exploration/glossary.md`

Problem:

`Stage` is the current CrackPy term for the maintainers' DIC acquisition-order index. It is useful for the existing nodemap workflow, but it is not a universal concept. Future inputs may be image sequences, video frames, externally indexed measurements, or acquisition systems that do not use the word stage.

Future direction:

Keep `stage` as an adapter-level field for current nodemap filenames, but consider a more general internal concept such as `measurement_index`, `acquisition_index`, or `acquisition_point`. A richer `AcquisitionPoint` could group the ordering index with load/force, cycle count, source filename/frame, and optional sub-cycle position.

Benefit:

The interface becomes clearer for non-DIC or non-ZEISS/GOM acquisition sources while preserving current stage-based workflows.

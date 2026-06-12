# Results, I/O, Scripts, And Workflows

Status: observed system reality
Role: Document current result I/O, scripts, tests, fixtures, plotting, workflow folders, and observed result schema. Schema-cleanup planning lives in [[refactor-candidates/008-result-tag-schema]].

Terminology references: see [[glossary]] for stable definitions and [[terminology-report]] for result-tag, folder, and output-schema inconsistencies.

## Result Modules

### `OutputWriter`

`crackpy/results/write.py` writes text and JSON from a `FractureAnalysis` instance.

Observed text tags:

- `Experiment_data`
- `CJP_results`
- `CJP_modeI_results`
- `Williams_fit_results`
- `SIFs_integral`
- `Bueckner_Chen_integral`
- `Path_SIFs`
- `Path_Williams_a_n`
- `Path_Williams_b_n`
- `Path_Properties`

`OutputWriter` knows the shape of `FractureAnalysis` internals directly.

`OutputWriter.write_williams_fit_provenance_json()` is a newer optional output hook. It builds a Williams-fit result/provenance envelope from the current `FractureAnalysis` object and writes three additional JSON artifacts without changing the legacy text or current JSON outputs.

### `OutputReader`

`crackpy/results/read.py` parses tagged text files into pandas DataFrames and writes flattened CSV outputs.

Observed risks:

- tag names are stringly typed and must match writer output exactly;
- `possible_tags` is stored on the reader instance;
- tag validation in `make_csv_from_results()` appears to use `any(tags) not in read_tags`, which is not a correct list-membership check.

### `Plotter`

`crackpy/results/plot.py` consumes `FractureAnalysis`, including its `InputData` and numerical result attributes, and writes PNG plots. It sets the matplotlib backend to `Agg` at import time.

## Williams-Fit Provenance Outputs

Observed files and modules:

- `crackpy/results/result_data.py`: canonical result/provenance dataclasses, strict JSON helpers, canonical JSON hashing, compact KG statement records, and graph visualization record shapes.
- `crackpy/provenance/source.py`: immutable `MethodResultSource`, `SourceInput`, `SourceDependency`, `SourceParameters`, and `SourceQuantity` snapshots consumed by provenance builders.
- `crackpy/provenance/spec.py`: Pydantic slice-spec models loaded from YAML.
- `crackpy/provenance/builder.py`: shared `MethodResultEnvelopeBuilder` that projects source snapshots and slice specs into result records.
- `crackpy/results/kg_statement_bundle.py`: compact grouped KG statement-bundle projection from a `ResultEnvelope`.
- `crackpy/results/graph_visualization.py`: graph visualization projection from a `ResultEnvelope`.
- `crackpy/fracture_analysis/methods/williams_fit/spec.yaml`: first Williams-fit slice definitions for schema versions, method metadata, dependency roles, scalar quantities, aliases, and coefficient-series definitions.

Current writer behavior:

- `_williams_fit_envelope.json`: graph-shaped result/provenance envelope with input, method, configuration, crack-tip frame, crack-tip estimate, analysis run, and result records.
- `_williams_fit_kg_statement_bundle.json`: compact statement-bundle projection grouped by `related_to` categories.
- `_williams_fit_graph.json`: visualization projection with nodes and dependency edges.

Observed coupling:

- The new provenance source adapter still reads `FractureAnalysis` post-run attributes for the legacy bridge.
- Only Williams-fit quantities and aliases are covered by this first slice.
- CJP results, line-integral results, path statistics, Bueckner-Chen integral outputs, plots, flattened CSVs, and current JSON sections remain on the older writer/reader contract.
- The compact KG projection currently loads the Williams-fit spec by default, so it is not yet a generic exporter for all future result envelopes.

## User-Facing Scripts

There are no console-script entry points or `argparse` CLIs in `pyproject.toml`. Workflows are script-driven with hard-coded constants.

Important scripts:

- `scripts/crack_detection/crack_detection.py`: single-nodemap neural-network detection.
- `scripts/crack_detection/cd_pipeline.py`: batch neural-network detection.
- `scripts/crack_detection/crack_detection_line_intercept.py`: single-nodemap line-intercept detection and correction comparison.
- `scripts/crack_detection/cd_pipeline_line_intercept.py`: batch line-intercept detection and correction.
- `scripts/crack_detection/ai_cd_plus_correction.py`: neural-network detection followed by symbolic-regression correction.
- `scripts/crack_detection/crack_tip_attention.py`: Seg-Grad-CAM heatmap generation.
- `scripts/fracture_analysis/fracture_analysis_dic.py`: single DIC fracture analysis.
- `scripts/fracture_analysis/fracture_analysis_fem.py`: single FEM/simulation fracture analysis.
- `scripts/fracture_analysis/fracture_analysis_pipeline_dic_3D_auto.py`: full DIC flow with AI crack detection and automatic integral paths.
- `scripts/fracture_analysis/fracture_analysis_pipeline_dic_3D_predef.py`: DIC fracture pipeline with predefined integral paths.
- `scripts/fracture_analysis/fracture_analysis_pipeline_fem.py`: FEM fracture pipeline using existing crack-tip info.
- `scripts/fracture_analysis/fracture_analysis_on_Williams_field_2D.py`: synthetic 2D Williams field example.
- `scripts/fracture_analysis/fracture_analysis_on_Williams_field_3D.py`: synthetic 3D Williams field example and profiling hook.
- `scripts/vtk_converter/nodemap_to_vtk.py`: nodemap plus connection file to VTK/PyVista output.
- `scripts/fracture_analysis/read_header_only.py`: fast header metadata read.
- `scripts/fracture_analysis/eqv_strain_calculation.py`: equivalent-strain formula comparison/reference script.

## Test Coverage Signals

Tests use `unittest` style and are run by `pytest` in CI.

Coverage areas:

- `crackpy/tests/test_crack_detection`: data import, interpolation, transforms, utilities, deep-learning losses/training/setup, attention, and pipeline.
- `crackpy/tests/test_fracture_analysis`: crack-tip fields, data processing, result reading.
- `crackpy/tests/test_structure_elements`: material behavior.
- `crackpy/tests/test_utils`: reusable interpolation utility.
- `test_scripts/test_crack_detection.py`: broader detection and training script-style checks.
- `test_scripts/test_fracture_analysis.py`: numerical regression checks and pipeline output comparisons.

CI explicitly runs selected package test groups and integration-style `test_scripts` jobs. `crackpy/tests/test_structure_elements` exists but was not observed in the explicit CI command list.

## Test Data Dependencies

Bundled test data is operationally important:

- `test_data/crack_detection/Nodemaps`
- `test_data/crack_detection/Connections`
- `test_data/crack_detection/raw/Nodemaps`
- `test_data/crack_detection/raw/GroundTruth`
- `test_data/crack_detection/interim/*.pt`
- `test_data/crack_detection/output/visualization/seggradcam`
- `test_data/fracture_analysis/txt-files`
- `test_data/fracture_analysis/results_*.csv`
- `test_data/simulations/Nodemaps`
- `test_data/simulations/crack_info_by_nodemap.txt`

Historical fixture naming includes `Dummy2`, MT specimens, GOM/Aramis-style nodemap headers, and stages such as 52-55.

## Citation Metadata

`CITATION.cff` lists package version `1.3.0`, release date `2024-08-20`, and DOI `10.1038/s41598-024-63915-x`.

The README "How to cite" section still references Zenodo DOI `10.5281/zenodo.7319653`. This is an observed metadata mismatch.

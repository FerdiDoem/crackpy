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

`OutputWriter.write_williams_fit_provenance_json()` is a newer optional output hook. It builds a Williams-fit result/provenance envelope from the current `FractureAnalysis` object and delegates artifact writing to `write_williams_fit_provenance_artifacts()`, which accepts an explicit `ResultEnvelope`. `OutputWriter.write_cjp_fit_provenance_artifacts()` now provides the same additive artifact bridge for CJP results. These hooks keep legacy text and current JSON outputs unchanged while allowing provenance artifact projection to be tested without a live `FractureAnalysis` instance.

### `OutputReader`

`crackpy/results/read.py` parses tagged text files into pandas DataFrames and writes flattened CSV outputs.

Observed risks:

- tag names are stringly typed and must match writer output exactly;
- `possible_tags` is stored on the reader instance;
- tag validation in `make_csv_from_results()` appears to use `any(tags) not in read_tags`, which is not a correct list-membership check.

### `Plotter`

`crackpy/results/plot.py` consumes `FractureAnalysis`, including its `InputData` and numerical result attributes, and writes PNG plots. It sets the matplotlib backend to `Agg` at import time.

## Williams-Fit And CJP-Fit Provenance Outputs

Observed files and modules:

- `crackpy/results/result_data.py`: canonical result/provenance dataclasses, strict JSON helpers, canonical JSON hashing, compact KG statement records, and graph visualization record shapes.
- `crackpy/results/result_data.py`: `ResultSchemaIndex` derives a lookup table from `ResultEnvelope` quantities so adapters can resolve canonical symbols, units, descriptions, schema versions, and legacy aliases without importing `FractureAnalysis`, `Plotter`, or writer policy.
- `crackpy/results/result_data.py`: `CrackTipFrame.from_legacy_side()` is the first orientation compatibility adapter for provenance records. It keeps current side labels as compatibility metadata and adds an explicit `geometry_profile`, defaulting to `surface_planar`.
- `crackpy/provenance/source.py`: immutable `MethodResultSource`, `SourceInput`, `SourceDependency`, `SourceParameters`, and `SourceQuantity` snapshots consumed by provenance builders.
- `crackpy/provenance/spec.py`: Pydantic slice-spec models loaded from YAML.
- `crackpy/provenance/builder.py`: shared `MethodResultEnvelopeBuilder` that projects source snapshots and slice specs into result records.
- `crackpy/results/kg_statement_bundle.py`: compact grouped KG statement-bundle projection from a `ResultEnvelope`.
- `crackpy/results/graph_visualization.py`: graph visualization projection from a `ResultEnvelope`.
- `crackpy/fracture_analysis/methods/williams_fit/spec.yaml`: first Williams-fit slice definitions for schema versions, method metadata, dependency roles, scalar quantities, aliases, and coefficient-series definitions.
- `crackpy/fracture_analysis/methods/cjp_fit/spec.yaml`: CJP slice definitions for schema versions, two method identities, dependency roles, variant-scoped quantities, aliases, and coefficient units.

Current writer behavior:

- `_williams_fit_envelope.json`: graph-shaped result/provenance envelope with input, method, configuration, crack-tip frame, crack-tip estimate, analysis run, and result records.
- `_williams_fit_kg_statement_bundle.json`: compact statement-bundle projection grouped by `related_to` categories.
- `_williams_fit_graph.json`: visualization projection with nodes and dependency edges.
- `_williams_fit_graph.html`: standalone SVG graph explorer generated from the visualization projection.
- `_cjp_fit_envelope.json`: graph-shaped CJP result/provenance envelope with one input record, one crack-tip frame, one normalized configuration, two method records, two analysis runs, and two result records.
- `_cjp_fit_kg_statement_bundle.json`: compact statement-bundle projection for the CJP envelope.
- `_cjp_fit_graph.json`: visualization projection for the CJP envelope.
- `_cjp_fit_graph.html`: standalone SVG graph explorer generated from the CJP visualization projection.
- The direct artifact writer consumes a `ResultEnvelope`; the `OutputWriter` method remains a compatibility bridge that first derives that envelope from `FractureAnalysis`.

Frontend integration handoff:

- Prefer `_williams_fit_graph.json` and `_cjp_fit_graph.json` as the frontend graph data contracts. They contain `nodes` and `edges` from `VisualizationGraph`; node `type`, `id`, `label`, and `data` plus edge `source`, `target`, `role`, and `label` are the stable frontend-facing fields for these provenance slices.
- C-001 update: frontend integration can request or consume the same artifacts from a prebuilt `ResultEnvelope` via `write_williams_fit_provenance_artifacts(envelope, path, stem)`. A frontend handoff test no longer needs to construct a full `FractureAnalysis` object just to verify graph, KG bundle, or envelope artifact output.
- C-008 update: frontend integration should treat `ResultQuantity.symbol` as the display label and `ResultQuantity.legacy_aliases` as compatibility metadata. Backend/frontend tests can use `ResultSchemaIndex.from_envelope(envelope)` to verify aliases such as `Williams_fit_results.K_I` resolve to the expected canonical symbol, unit, and result schema version.
- C-010 validation update: provenance artifacts are now generated from a slice spec that rejects dependency or quantity key/name drift and undeclared source-quantity qualifier keys. The frontend graph payload shape is unchanged, but integration code can assume `VisualizationGraph` node and edge names came from a validated spec rather than a partially inconsistent YAML mapping.
- C-010 qualifier update: frontend/backend contract tests can rely on CJP source quantities using the spec-declared `variant` qualifier before they are split into mixed-mode and Mode-I result records. Williams coefficient quantities continue to use the method-local `coefficient_series` and `term_order` qualifiers; these qualifiers are validated before canonical symbols such as `a_1` are projected.
- C-010 KG schema update: compact KG statement bundles now infer their bundle schema from `ResultEnvelope.envelope_schema_version` when no method spec is passed. Frontend integration can consume CJP KG bundles with `bundle_schema_version=crackpy.kg_statement_bundle.cjp_fit.v1` instead of receiving the Williams-fit bundle schema by default.
- C-010 graph contract update: direct graph tests now cover CJP envelopes with two method nodes, two result records, and CJP-specific quantity labels such as `K_II` and `T_y`. Frontend integration should treat the graph contract as envelope-driven rather than Williams-specific.
- C-006 update: frontend integration can use `crackpy.crack_detection.method_metadata.known_crack_detection_methods()` for crack-detection method labels and filters. Each detection metadata record carries the same generic `MethodSpec` shape used by Williams-fit and CJP-fit (`method_id`, `display_name`, `kind`, `method_revision`, `implementation_ref`, `aliases`, and `references`), plus detection-specific `detection_task`, `implementation_family`, optional `network_architecture`, and optional `weights_artifact_id`. Treat `ParallelNets`, `UNetPath`, `line_intercept`, and `CrackDetectionLineIntercept` as compatibility aliases, not generic model names.
- C-010 fixture update: backend/frontend contract tests can build a Williams-fit envelope from a direct `MethodResultSource` fixture when they need stable graph/schema payloads without a fake `FractureAnalysis` object.
- C-010 input-anchor update: frontend graph or table tests can assume input nodes have non-empty `input_id` and `data_ref` values because `SourceInput` rejects empty primary input anchors before envelope construction.
- C-002 update: frontend integration should use `InputRecord.input_id` as the stable input key. `InputRecord.sequence_index` is available only for ordering input series, and source-specific labels such as `stage` belong in `InputRecord.source_metadata`.
- C-009 update: detection and fracture-analysis pipeline objects can now expose an `InputMappingResult` named `input_mapping` after nearest-cycle assignment. Frontend integration should treat `input_mapping.input_id_to_representative_input_id` as the durable mapping and keep legacy `stage -> detection_stage` or `stage -> max_force_stage` dictionaries as compatibility labels only.
- C-005 update: `CrackTipFrame` graph nodes now expose `data.geometry_profile`, currently `surface_planar` for the Williams-fit slice. Frontend integration should display or filter by `geometry_profile` when useful, and treat `data.compatibility_side` as a legacy label rather than the full orientation model.
- C-007 update: result/provenance payload shape is unchanged. Backend/frontend fixture code may omit `FractureAnalysis` option arguments without sharing mutated default `IntegralProperties` or `OptimizationProperties` across fixture runs; pass `None` explicitly when a fixture should disable line integrals or optimization.
- C-003 update: result/provenance payload shape is unchanged. Backend/frontend contract tests can now build a `WilliamsFitResult` either from explicit coefficient arrays with `run_williams_fit_from_coefficients()` or from crack-tip-centered displacement grids with `WilliamsFitDisplacementField` and `fit_williams_displacement_field()`, without constructing `FractureAnalysis` or relying on `Optimization` constructor side effects.
- CJP update: backend/frontend contract tests can now build CJP provenance artifacts from a prebuilt CJP `ResultEnvelope`, from a typed `CjpFitResult`, from explicit coefficient arrays with `run_cjp_fit_from_coefficients()`, or from crack-tip-centered displacement grids with `CjpFitDisplacementField` and `fit_cjp_displacement_field()`.
- Use `_williams_fit_graph.html` as the reference implementation for an inspectable layout and interaction model, not as the long-term application shell. The HTML embeds the graph payload and demonstrates lane-based layout, node-type styling, legend generation, and node detail inspection.
- If the frontend generates its own view, keep UI state, colors, layout coordinates, filters, expansion state, and RDF namespace choices outside `ResultEnvelope`. Those remain visualization adapter concerns, not canonical provenance fields.
- The Python entry points for backend/frontend integration are `write_williams_fit_provenance_artifacts(envelope, path, stem)` and `write_cjp_fit_provenance_artifacts(envelope, path, stem)`. Existing legacy flows can continue through the corresponding `OutputWriter` compatibility methods.

Observed coupling:

- The provenance source adapter still reads `FractureAnalysis` post-run attributes for the legacy bridge.
- Williams-fit envelope-to-artifact projection no longer requires the broad `FractureAnalysis` attribute bag once a `ResultEnvelope` is available.
- Williams-fit schema lookup can now be derived from the canonical envelope, but legacy text, current JSON, and CSV readers still keep their existing string contracts.
- Input identity and ordering metadata can now be projected into canonical input records, but `InputData` remains the mutable compatibility carrier.
- Nearest-cycle assignment in crack-detection and fracture-analysis pipelines now records an ID-based input mapping result while preserving existing stage dictionaries.
- Williams-fit crack-tip frames now carry explicit geometry-profile metadata while preserving legacy side labels for output compatibility.
- Fracture-analysis default option objects are now created per analysis/optimizer call for the touched defaults, reducing hidden shared state in provenance fixture construction.
- Williams-fit typed results can now be produced directly from explicit coefficient arrays or already-sampled displacement grids, but the envelope/source adapter layer is still the boundary that turns those results into frontend-facing graph payloads.
- Williams-fit and CJP-fit quantities and aliases are covered by provenance slices.
- Williams-fit and CJP-fit provenance builders now reject undeclared `SourceQuantity.qualifiers` before graph, KG, or envelope projection.
- Line-integral results, path statistics, Bueckner-Chen integral outputs, plots, flattened CSVs, and current JSON sections remain on the older writer/reader contract.
- The compact KG projection now derives its schema version from the envelope when no explicit spec is passed, but grouping, URI minting, RDF namespaces, descriptor resources, and method-specific KG profiles remain adapter/exporter policy.

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

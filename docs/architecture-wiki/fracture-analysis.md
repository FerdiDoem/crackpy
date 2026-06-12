# Fracture Analysis

Status: observed system reality
Role: Document current fracture-analysis implementation behavior, numerical assumptions, pipelines, and validation signals. Result and Williams-fit planning lives in [[refactor-candidates/001-explicit-analysis-result]] and [[refactor-candidates/003-self-contained-williams-fit-interface]].

Terminology references: see [[glossary]] for stable definitions and [[terminology-report]] for naming inconsistencies in fitting, integral, and result terms.

## Core Modules

- `crackpy/fracture_analysis/analysis.py`
- `crackpy/fracture_analysis/methods/williams_fit/`
- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/line_integration.py`
- `crackpy/fracture_analysis/crack_tip.py`
- `crackpy/fracture_analysis/pipeline.py`
- `crackpy/fracture_analysis/utils.py`

## `FractureAnalysis`

`FractureAnalysis` is the single-nodemap facade. It receives:

- `Material`
- `Nodemap` or nodemap filename
- transformed `InputData`
- `CrackTipInfo`
- optional `IntegralProperties`
- optional `OptimizationProperties`

When these option arguments are omitted, `FractureAnalysis` now creates fresh per-analysis compatibility defaults through `default_integral_properties()` and `default_optimization_properties()`. Passing `None` still disables the corresponding method family. Williams default resolution still mutates the run-local `OptimizationProperties` object before constructing `Optimization`, so crack-length-derived radii and required terms remain explicit on that analysis instance rather than shared across analyses.

It stores results by mutating instance attributes such as:

- `cjp_res_mm`, `cjp_res_m1`, `cjp_coeffs_mm`, `cjp_coeffs_m1`;
- `williams_fit_res`, `williams_fit_a_n`, `williams_fit_b_n`, `williams_fit_c_n`, `williams_coeffs`;
- `path_results`, `sifs_int`, `williams_int_a_n`, `williams_int_b_n`, `path_sizes`, `integration_points`.

The public interface is therefore more than `run()`: callers and output modules must know the post-run attribute shape.

## Williams Fitting

The numerical optimization is still performed by `Optimization.optimize_williams_displacements_xy()` and `Optimization.optimize_williams_displacements_z()`. `FractureAnalysis._run_williams_optimization()` now calls `crackpy.fracture_analysis.methods.williams_fit.runner.run_williams_fit()` to convert optimizer output into a typed `WilliamsFitResult`, then writes that result back onto legacy `FractureAnalysis` attributes.

Observed behavior:

- fitting domain is a polar grid in transformed crack-tip coordinates;
- radial range is `min_radius:max_radius`;
- angular range excludes a crack-path gap: `[-pi + angle_gap, pi - angle_gap]`;
- displacement at `(0, 0)` is interpolated and subtracted before fitting;
- default Williams terms are `[-1, 1, 2, 3, 4, 5]`;
- terms `1` and `2` are forced into `OptimizationProperties.terms` so SIF and T-stress can be calculated;
- XY fit optimizes `a_n` and `b_n`;
- Z fit optimizes `c_n` only if `disp_z` exists and is not all zero.

Derived quantities:

- `K_I = sqrt(2*pi) * a_1 / sqrt(1000)`
- `K_II = -sqrt(2*pi) * b_1 / sqrt(1000)`
- `T = 4*a_2`
- `K_III = sqrt(0.5*pi) * c_1 / sqrt(1000)`

Observed Williams-fit method module:

- `runner.py`: defines the `WilliamsFitOptimizer` compatibility protocol, `WilliamsFitDisplacementField` array interface, `fit_williams_displacement_field()` least-squares runner, `run_williams_fit_from_coefficients()` result assembler, and `run_williams_fit()` legacy optimizer adapter. Optimization exceptions propagate from SciPy or the optimizer rather than being converted into silent fallback results.
- `result.py`: defines Pydantic `WilliamsFitResult` and `WilliamsCoefficientSet` records.
- `parameters.py`: defines Pydantic material and optimization parameter snapshots with field descriptions and parameter-origin metadata.
- `source_adapter.py`: translates either current `FractureAnalysis` Williams attributes or a typed `WilliamsFitResult` into a `MethodResultSource`; current left/right side labels are projected through `CrackTipFrame.from_legacy_side()` so the frame carries explicit `geometry_profile` metadata while preserving the compatibility side label.
- `spec.yaml` and `spec_loader.py`: hold and validate Williams-specific schema versions, method metadata, dependency roles, scalar quantity definitions, and coefficient-series definitions.
- `builder.py`: wraps the shared provenance builder to produce the first Williams-fit result/provenance envelope.
- `crackpy.results.write.write_williams_fit_provenance_artifacts()`: writes envelope, compact KG statement bundle, and visualization graph artifacts from a `ResultEnvelope`; `OutputWriter` remains the compatibility bridge from `FractureAnalysis`.

This is a partial deeper module around Williams fitting. The runner can now fit explicit crack-tip-centered displacement arrays and assemble typed results from explicit coefficient vectors without a `FractureAnalysis` or `Optimization` instance. CJP fitting, line integrals, correction-time Williams optimization in `crack_detection.correction`, legacy result writing, and plotting still consume or expose the older mutable `FractureAnalysis` attribute shape.

## CJP Fitting

Implemented by:

- `optimize_cjp_displacements_modeI()`
- `optimize_cjp_displacements_mixedmode()`
- analytical fields in `crack_tip.py`

Observed behavior:

- both variants use `scipy.optimize.least_squares`;
- default method is Levenberg-Marquardt via `method="lm"`;
- initial coefficients default to random values;
- code logs warnings that CJP optimization is experimental and should be interpreted carefully, especially outside Mode-I-dominated cases.

Mixed-mode CJP coefficients:

- `(A_r, B_r, B_i, C, E)`
- derived outputs: `K_F`, `K_R`, `K_S`, `K_II`, `T`

Mode-I CJP coefficients:

- `(A, B, C, E, F)`
- derived outputs: `K_F`, `K_R`, `K_S`, `T_x`, `T_y`

## Line Integrals

Implemented by `IntegralProperties`, `PathProperties`, `IntegrationPath`, and `LineIntegral`.

Line-integral methods:

- J-integral;
- mode I/II/III decomposition of the J-integral; see [[glossary]] `Mode decomposition`;
- interaction-integral SIFs;
- T-stress from interaction integral;
- T-stress from stress-difference method;
- Bueckner-Chen integral for Williams coefficients.

Path behavior:

- integration paths are rectangular/open contours around `(0, 0)`;
- left-side gap is controlled by `top_offset` and `bottom_offset`;
- multiple paths expand outward by `paths_distance_*`;
- path resolution comes from `integral_tick_size` or `number_of_nodes`.

Automatic path selection:

- requires `data.sig_vm`;
- thresholds mapped Von Mises stress against `auto_detect_threshold`, typically `material.sig_yield`;
- labels connected regions and chooses the feature near the transformed crack tip;
- derives initial path size, offsets, tick size, and path spacing.

## Analytical Crack-Tip Fields

`crack_tip.py` provides:

- `williams_stress_field`
- `williams_displ_field_xy`
- `williams_stress_field_3d`
- `williams_displ_field_z`
- `cjp_stress_field_mixedmode`
- `cjp_displ_field_mixedmode`
- `cjp_stress_field_modeI`
- `cjp_displ_field_modeI`
- `eigenfunction`
- `get_crack_nearfield`
- `get_zhao_solutions`
- `unit_of_williams_coefficients`

The file contains direct methodological references to Kuna formulas, Christopher/CJP formulations, Sladek et al. near-field formulas, and Zhao auxiliary solutions.

## Batch Pipeline

`FractureAnalysisPipeline` reads an input CSV, constructs per-row crack-tip info, loads nodemap data, computes stresses, transforms coordinates, runs `FractureAnalysis`, then writes text, JSON, and optional plots.

`find_max_force_stages()` still returns the legacy `stage -> max_force_stage` dictionary. Internally it now uses `map_stage_cycles_to_representative_stages()` and stores the ID-based `InputMappingResult` as `input_mapping`, so max-force propagation has an explicit `input_id -> representative_input_id` policy result without changing existing stage-based calls.

`single_run()` combines several responsibilities:

- CSV row to `CrackTipInfo`;
- nodemap load;
- stress computation;
- coordinate transformation;
- analysis execution;
- text/JSON writing;
- plotting.

The pipeline supports multiprocessing with `ProcessPoolExecutor` and tracks progress using `rich` plus a `multiprocessing.Manager().dict()`.

## Implicit Assumptions

- Input data must already be transformed so the crack tip is at `(0, 0)` for optimization and line integrals.
- Stresses must exist before line integration and auto path detection.
- Internal length units are mostly millimeters; SIFs are converted to `MPa*sqrt(m)` for output.
- Many beta methods are still enabled through the same facade: CJP fitting, J-decomposition, Bueckner-Chen T/HOST/HORT, and automatic integral properties.

## Validation Signals

The richest regression coverage is in `test_scripts/test_fracture_analysis.py`:

- hard-coded expected values for integrals, SIFs, T-stress, Bueckner-Chen coefficients, CJP outputs, and Williams fits;
- synthetic 3D Williams-field recovery expecting `K_I=10`, `K_II=20`, `K_III=30`, and `T=40`.

Additional package tests cover crack-tip closed forms, data processing, result reading, and interpolation utility comparisons.

Newer package tests also cover the Williams-fit method module, provenance envelope construction, compact KG statement-bundle projection, graph visualization projection, and an actual-data Williams provenance path under `crackpy/tests/test_fracture_analysis`.

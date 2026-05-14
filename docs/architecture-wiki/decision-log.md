# Decision Log

Status: lightweight planning decisions
Role: Record accepted or rejected planning decisions that are not architecture decision records. ADRs are deferred until explicitly requested.

## 2026-05-14: Architecture Wiki Is Planning Memory

Status: accepted

Decision:

`docs/architecture-wiki/` functions as the shared working memory for CrackPy architectural mapping and future refactor planning.

Rationale:

The current phase is exploration and planning only. The notes need to preserve observed reality, shared language, unresolved terminology, and future candidates without implying that production code has changed.

Consequences:

- Observed-system notes describe current behavior only.
- Future architecture candidates live in [[refactor-notes]] and [[refactor-candidates/index]].
- Open terminology and architecture questions live in [[open-questions]].
- Stable vocabulary lives in [[glossary]].
- No ADRs are created in this phase.

## 2026-05-14: ADRs Deferred

Status: accepted

Decision:

Do not create `docs/adr/` or ADR records during this consolidation pass.

Rationale:

No architecture decision has been approved yet. The current task is to consolidate working memory, not to make durable architecture decisions.

Consequences:

- `decision-log.md` records lightweight planning decisions.
- Future ADRs can be introduced after explicit approval.

## 2026-05-14: Side Is Not A Sustainable Internal Crack-Orientation Model

Status: accepted for planning

Decision:

`side` should not be treated as the long-term internal representation of crack orientation, crack-tip pose, or crack-growth direction. It remains an observed compatibility term in the current package and handoff files, but future architecture planning should split the meanings currently bundled into `side`.

Rationale:

The current `left`/`right` vocabulary assumes at most two default crack tips whose nominal growth directions align with the package x-axis convention. This is too restrictive for multiple crack tips, tilted initial cracks, top-to-bottom crack growth, bending samples, 3D surfaces, and future crack-front descriptions.

The internal package model should move toward `CrackTipFrame` as the canonical crack-tip orientation concept. In that frame, local x is the crack-extension direction, local y is the crack-opening direction for mode I, and local z is profile-specific: for current planar DIC workflows it is usually the assumed surface normal or out-of-plane direction, while true 3D crack-front workflows would need an explicit crack-front or surface-frame definition.

Consequences:

- Current `side`, `sides`, and `left_or_right` stay documented as observed compatibility vocabulary.
- `side` remains acceptable at file, legacy API, detector setup, and result-naming boundaries, but new internal interfaces should treat it as adapter input that maps to an explicit crack-tip frame.
- Future planning should separate specimen geometry, crack-tip identity, crack-growth direction, detector model convention, mirroring policy, and output labels.
- The current 2D shift-and-rotation behavior in `InputData.transform_data(x_shift, y_shift, angle)` is an existing partial crack-tip-centered transform, not a complete orientation model.
- OQ-020 resolves the minimal internal crack-tip coordinate-system planning target as `CrackTipFrame` with declared geometry profiles.

## 2026-05-14: CrackTipFrame Is The Planning Target For Internal Crack-Tip Orientation

Status: accepted for planning

Decision:

Use `CrackTipFrame` as the canonical future internal concept for crack-tip orientation and position. Do not use a permanently 2D-only term as the canonical model. A `CrackTipFrame` should carry a crack-tip identity, origin, local axes, geometry profile, and optional compatibility labels such as current `side`.

Rationale:

CrackPy currently targets digital image correlation (DIC) surface data. Nodemaps can contain `coor_z` and `disp_z`, but current detection, interpolation, line integrals, and `InputData.transform_data(x_shift, y_shift, angle)` are planar or surface-based methods. The architecture should be able to describe a crack-tip frame in 3D coordinates when surface data has 3D embedding, while avoiding a false promise that current methods support digital volume correlation (DVC), volumetric finite element method (FEM), or general 3D crack-front fracture mechanics.

Consequences:

- `CrackTipFrame` is the planning target for future internal orientation interfaces.
- Methods should declare a geometry profile such as `surface_planar`, `surface_parameterized`, `surface_3d`, or `volumetric_field`.
- Current CrackPy methods should be documented as `surface_planar` unless a method explicitly supports more.
- `surface_parameterized` is a plausible future extension for derived 2D surface coordinates after a defined parameterization, projection, or unwrapping step.
- `surface_3d` and `volumetric_field` are future capability profiles, not current guarantees.
- 3D coordinates in nodemaps do not imply general 3D fracture-mechanics support.

## 2026-05-14: Stage Is Source Metadata, Sequence Index Is Internal Ordering

Status: accepted for planning

Decision:

`stage` remains current source-specific and compatibility vocabulary for DIC/nodemap workflows, especially ZEISS/GOM-style filename and metadata conventions. It should not be the canonical future internal ordering abstraction. Future planning should use `sequence_index` as the generic ordering key, `input_id` as stable identity, and `InputRecord` as the concept pairing data with attached metadata and minimal input/source provenance.

Rationale:

The current package derives `stage` from nodemap filename suffixes and uses it as a workflow key in crack detection, training utilities, and fracture-analysis helpers. This reflects the maintainers' DIC workflows, but it does not generalize cleanly to FEM load steps, synthetic fields, imported benchmarks, videos, image sequences, or externally indexed inputs.

The richer metadata that arrives with input files should stay attached to the data but remain decoupled from CrackPy pipeline state. RDF/knowledge-graph export should be an adapter over CrackPy metadata, not the shape of the core data object.

Consequences:

- Current `stage`, `stage_nums`, and stage-based dictionaries remain observed compatibility behavior.
- `stage` should be treated as source metadata when the source system uses that label.
- `sequence_index` is the preferred generic ordering vocabulary for future interfaces.
- `input_id` is the durable reference for matching, provenance, and result links.
- Matching across loads, cycles, or representative records should be expressed as an explicit mapping policy over metadata.
- Future mapping outputs should use stable identities, such as `input_id -> representative_input_id`, while legacy adapters may continue to expose `stage -> stage` mappings.
- `InputRecord` may carry minimal input/source provenance; processing provenance belongs to `AnalysisRun`, `ResultRecord`, or `ProvenanceRecord`.

Useful split:

- Data and attached metadata travel together as an input object.
- Pipeline state and matching decisions are separate workflow concerns.
- Minimal source/input provenance can live with `InputRecord`.
- Processing provenance belongs to the objects that consume inputs and generate results.

## 2026-05-14: Provenance Uses A Minimal Traceability Chain

Status: accepted for planning

Decision:

CrackPy should preserve a minimal traceability chain across input loading, crack detection, fracture analysis, text/JSON output, CSV flattening, and plots. It should not try to preserve full internal execution history in every artifact.

The planning split is:

- `InputRecord`: concrete input data plus attached metadata and minimal source provenance.
- `AnalysisRun`: one execution of a registered analysis function over one or more input records and a configuration snapshot.
- `ResultRecord`: generated result identity, schema, units, hashes, and artifact references.
- `ProvenanceRecord`: compact or detailed envelope linking inputs, analysis runs, results, software, configurations, and export metadata.

Rationale:

The split is compatible with established provenance concepts without forcing CrackPy internals to be named after them. `InputRecord` and `ResultRecord` can map to PROV-O entities, `AnalysisRun` can map to a PROV-O activity, and CrackPy, users, model providers, or orchestrators can map to PROV-O agents. The same internal model can feed both a compact metadata statement-bundle export and an optional detailed PROV-O-like graph.

The provided microscope-DIC datapoint JSON is an example of a generic metadata statement-bundle pattern, not an MDIC-specific architectural boundary. A comparable bundle could describe DIC, FEM, synthetic benchmark data, imported reference fields, or another future source.

Consequences:

- The compact export should store facts needed for query, audit, and targeted re-analysis.
- A detailed PROV-O-like artifact can be generated separately when richer process provenance is needed.
- Links between records should carry semantic roles, such as primary displacement field, representative crack-tip source, configuration snapshot, material definition, model weights, correction result, or post-processing input.
- Text/JSON and CSV outputs should preserve enough IDs, schema versions, hashes, and function/configuration references to determine whether a result is stale.
- Plots should carry or link to the producing `result_id` or `run_id`, but should not duplicate the full provenance payload.

## 2026-05-14: Analysis Function Identity Is A Stable Contract ID

Status: accepted for planning

Decision:

Future provenance and orchestration should identify analysis functions by a stable registry-owned contract ID, not by the current Python module, class, or function path. The stable ID should describe the scientific or computational contract that produced a result, for example `crackpy.fracture.williams_fit`, `crackpy.detection.unet_crack_tip_detection`, or `crackpy.fracture.bueckner_chen_integral`.

Rationale:

CrackPy is expected to undergo refactors that move code, split `InputData` responsibilities, and expose self-contained analysis functions. If provenance uses implementation paths as durable identities, old results may appear unrelated to new code after a harmless move. A stable contract ID lets results survive code movement while still recording the concrete implementation reference that ran.

The planning model separates:

- `analysis_function_id`: durable scientific or computational contract identity;
- `display_name`: human-facing label for reports and documentation;
- `implementation_ref`: current Python location or source reference;
- `metadata_version`: maintainer-controlled version of the function contract;
- `crackpy_version`, `execution_commit`, and later function-relevant commits: package and source-code traceability.

Consequences:

- Result metadata should store `analysis_function_id` rather than relying on display names or Python paths.
- Python paths remain useful as `implementation_ref`, but they are allowed to change during refactors.
- `metadata_version` should change when function semantics, inputs, outputs, defaults, references, model dependencies, schemas, or result meanings change.
- OQ-017 can now focus on how to compute or declare function-relevant commits for a stable dependency scope.

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
- `AnalysisRun`: one execution of a registered method over one or more input records and a configuration snapshot.
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

## 2026-05-14: Method ID Is Stable Provenance Vocabulary

Status: accepted for planning

Decision:

Future provenance and orchestration should identify registered methods by a stable registry-owned method ID, not by the current Python module, class, or function path. The stable ID should describe the scientific, numerical, or workflow method that produced a result, for example `crackpy.fracture.williams_fit`, `crackpy.detection.unet_crack_tip_detection`, or `crackpy.fracture.bueckner_chen_integral`.

Rationale:

CrackPy is expected to undergo refactors that move code, split `InputData` responsibilities, and expose self-contained methods. If provenance uses implementation paths as durable identities, old results may appear unrelated to new code after a harmless move. A stable method ID lets results survive code movement while still recording the concrete implementation reference that ran.

The planning model separates:

- `method_id`: durable scientific or computational method identity;
- `display_name`: human-facing label for reports and documentation;
- `implementation_ref`: current Python location or source reference;
- `method_revision`: maintainer-controlled method-level revision;
- `crackpy_version`, `execution_commit`, and implementation fingerprints: package and source-code traceability.

Consequences:

- Result metadata should store `method_id` rather than relying on display names or Python paths.
- Python paths remain useful as `implementation_ref`, but they are allowed to change during refactors.
- `method_revision` should change when method semantics, inputs, outputs, defaults, references, model dependencies, schemas, or result meanings change.
- OQ-017 resolved the supporting traceability model around dependency scopes, implementation fingerprints, build validation, aliases, and method registry status.

## 2026-05-14: Method Revision Is Manual And Implementation Fingerprint Is Build-Validated

Status: accepted for planning

Decision:

Registered CrackPy methods should use plain method-level vocabulary:

- `method_id`: stable canonical identity of a registered method, for example `crackpy.fracture.williams_fit`, `crackpy.fracture.bueckner_chen_integral`, or `crackpy.detection.unet_crack_tip_detection`;
- `method_revision`: maintainer-declared revision of the method's scientific, numerical, and output meaning inside CrackPy;
- `implementation_fingerprint`: automatically generated traceability value over the method's declared dependency scope;
- `dependency_scope`: declared files, source ranges, helper modules, configuration/default providers, model artifacts, and other implementation assets that can affect method behavior.

CrackPy should not rely only on manual `method_revision` updates. A build or release validation step should generate a method manifest, compute implementation fingerprints, compare them against the previous committed or released manifest, and require each changed fingerprint to be classified.

Release validation should fail when a registered method's fingerprint changed and neither of the following is true:

- `method_revision` was changed because the method meaning, default behavior, model dependency, result schema, or result interpretation changed;
- the change was explicitly classified as non-semantic, for example a pure move, formatting pass, behavior-preserving cleanup, or equivalent implementation refactor.

Rationale:

Git can detect that source files changed, but it cannot decide whether a scientific method changed. A Williams-fit edit might be a harmless rename, a changed default term set, a sign convention fix, a numerical bug fix, or a result-schema change. Those cases have different stale-result consequences. `method_revision` is therefore the human semantic marker, while `implementation_fingerprint` is the automatic traceability marker that prevents silent drift.

The dependency scope must be declared but audited automatically. The first version should prefer coarse scopes over fragile function-only scopes. For example, `crackpy.fracture.williams_fit` should include the optimization code, analytical Williams-field helpers, interpolation helpers, material behavior, and relevant result-schema writers rather than only a single top-level function. Build checks should verify that scope entries resolve, fingerprints are reproducible, aliases are unique, and newly touched method dependencies are classified.

Registry identity policy:

- `method_id` is stable provenance vocabulary, not an implementation path.
- A method ID may change only through an explicit registry migration.
- `aliases` are a list of one-to-one legacy names that resolve to exactly one canonical `method_id`; new results must write the canonical ID.
- `successors` are used for one-to-many replacements or method splits where an old broad ID cannot be automatically mapped to one new method without extra metadata.
- `status` should use `active`, `deprecated`, or `removed`.

Status meanings:

- `active`: accepted canonical method ID for new results.
- `deprecated`: known historical or transitional ID; old results remain interpretable, but new results should not write it.
- `removed`: known historical ID with no current implementation; provenance can still be read, but direct recomputation is not available without a migration path.

Stale-result policy:

- Recompute when `method_revision`, normalized parameters, inputs, model hashes, configuration schema, or result schema changed.
- Flag for review, or recompute under conservative policy, when only `implementation_fingerprint` changed.
- Record `crackpy_version` and `execution_commit` separately from method-level values because one CrackPy release can change zero, one, or many methods.

Consequences:

- The earlier `analysis_function_id` wording is superseded by `method_id` as canonical field vocabulary.
- The earlier `metadata_version` and `function_metadata_version` wording is superseded by `method_revision`.
- The earlier `function_last_modified_commit` wording is superseded by `implementation_fingerprint`; commit IDs may be one ingredient in the fingerprint when Git metadata is available.
- OQ-018 can now focus on how method references attach to `method_id` entries.
- OQ-019 can now decide which manifest fields belong in the compact knowledge-graph export and which belong only in detailed provenance artifacts.

## 2026-05-14: Method References Use A Hybrid Registry

Status: accepted for planning

Decision:

Method-level scientific references should use a hybrid model:

- `CITATION.cff` remains the package-level citation file for CrackPy as software.
- A small versioned YAML or JSON method-reference registry becomes the source of truth for method-level references.
- Python method metadata stores only stable method-reference IDs, for example `references=("williams_1961", "sanford_2003")`.
- BibTeX support can be added later as import/export tooling, but should not be the primary internal source of truth.

Rationale:

CrackPy needs references attached to specific registered methods, not only a package citation. The method registry should be able to state that `crackpy.fracture.williams_fit` is linked to Williams-series literature, while `crackpy.fracture.bueckner_chen_integral` or crack-tip detection methods have their own reference sets.

A YAML or JSON registry is easier to validate, diff, package, and export into the compact RDF/JSON statement-bundle shape than free-form docstrings or BibTeX alone. It also keeps Python method metadata small: method entries point to IDs, while the reference registry carries authors, title, year, DOI, venue, URL, and optional notes or roles.

Consequences:

- Method metadata should carry reference IDs, not full bibliography records.
- Build or documentation validation should fail when a method references an unknown ID or when a registry entry is missing required fields.
- `method_revision` should change when reference changes alter the claimed scientific basis, assumptions, or interpretation of a method.
- `CITATION.cff` remains focused on citing CrackPy as software and should not become the method bibliography.
- BibTeX remains useful for papers and documentation export, but the registry should be the canonical CrackPy planning vocabulary.
- OQ-019 can now assume method references are externally resolvable from `method_id` entries through the reference registry.

## 2026-05-14: Compact KG Export Is Result-Centric, Detailed Provenance Is Process-Centric

Status: accepted for planning

Decision:

The compact knowledge-graph export should be result-centric. In the main KG, a result should link to the relevant input, CrackPy as software, the CrackPy configuration that was used, method identity, method revision, result schema, minimal hashes, and a pointer to the detailed provenance artifact. The compact KG should not try to represent the full internal CrackPy process chain.

The compact export may include `run_id`, but `run_id` alone is not sufficient evidence for stale-result checks. It should be accompanied by stable IDs and minimal fingerprints such as `input_id`, `result_id`, `configuration_id`, `parameter_hash` or configuration hash, input hash, result hash where practical, `method_id`, `method_revision`, result schema version, CrackPy version, and `provenance_artifact_ref`.

The optional detailed provenance artifact should own process semantics. It should represent all scientifically or computationally relevant steps in the CrackPy process chain at a declared granularity level, such as input loading, metadata binding, coordinate transformations, masking, preprocessing, interpolation, crack-tip detection, crack-tip correction, Williams fitting, line-integral evaluation, optimization, aggregation, and export. It should not record every private helper call by default.

Rationale:

The existing KG setup is closer to a compact object/configuration/result model than a full process graph. From that perspective, it is sensible to link a result to input data, CrackPy, and CrackPyConfiguration in the main graph while keeping full execution history in a PROV-O-like artifact. This keeps the Jena graph queryable and avoids forcing CrackPy internals to mimic the RDF process model.

A physical crack tip should not be multiplied into one KG entity per detection or analysis method. Multiple methods may produce computational observations or results about the same physical crack tip, but they should not create multiple physical crack-tip objects in the compact KG. Method-specific crack-tip estimates belong in result metadata or detailed provenance unless the KG intentionally models them as observations.

The provided metadata bundle is best treated as a grouped metadata statement bundle. It is grouped by top-level subject-like keys, and each statement repeats a `related_to` field. If the KG importer uses a `grouped_by` convention, the compact exporter should conform to it. Grouping does not by itself define concrete subject URIs, so URI minting remains an exporter or KG-import policy rather than a computational-core concern.

Consequences:

- The compact KG stores the query and re-analysis index, not the full process history.
- The detailed PROV-O-like artifact stores process-chain detail and can map `InputRecord` and `ResultRecord` to entities, `AnalysisRun` to activities, and CrackPy, users, models, or orchestrators to agents.
- The compact export should link to the detailed artifact by artifact ID, URI, or file path.
- URI and namespace policy must be defined by the exporter profile or KG importer; CrackPy internal records should provide stable IDs and types.
- A provenance granularity policy is needed so detailed artifacts are consistent across methods.

## 2026-05-14: Crack-Tip Estimates Are Result Dependencies

Status: accepted for planning

Decision:

The compact KG may contain multiple physical crack tips when the specimen or input state contains multiple crack tips. A physical crack tip is a domain object, not the same thing as a method-specific computational estimate.

Crack-tip detection, correction, manual import, or future uncertainty/fusion methods should produce `CrackTipEstimateResult`-like computational result records. These records should carry their own `CrackTipEstimateConfiguration`-like configuration link because neural detection, line-intercept detection, correction, and manual import can all depend on method-specific settings, model weights, thresholds, windows, conventions, or source metadata.

Fracture-analysis results that consume a crack-tip estimate should link to that estimate explicitly, for example through a `used_crack_tip_estimate` role. The crack-tip estimate should not be hidden only inside `used_configuration`. Configuration describes how the fracture-analysis method runs; the crack-tip estimate is data or an intermediate result consumed by that run.

Rationale:

Fracture analysis changes when the crack-tip estimate changes, even if the Williams-fit, line-integral, material, or optimization configuration stays identical. Treating the estimate as configuration would blur method settings with data dependencies and make stale-result detection harder.

Keeping CrackPy as one software entity remains sufficient. The graph should split outputs and dependencies, not split CrackPy itself. Crack-tip detection results and fracture-analysis results can both be produced by CrackPy while carrying different `method_id`, configuration, run, and result records.

Consequences:

- `CrackTipEstimateResult` should have its own `configuration_id`, method metadata, input links, result schema, and optional uncertainty metadata.
- `FractureAnalysisResult` should link to the consumed crack-tip estimate in addition to input data and fracture-analysis configuration.
- Manual crack tips should be represented as user- or import-sourced crack-tip estimates, not as fracture-analysis configuration only.
- A physical `CrackTip` may later be associated with one or more estimates and uncertainty/fusion records, but this is not required for the first compact KG export profile.

## 2026-05-14: Crack-Tip Correction Produces Corrected Estimates And Deltas

Status: accepted for planning

Decision:

Future crack-tip correction vocabulary should model both the absolute corrected crack-tip estimate and the relative correction delta. The corrected estimate is the primary result consumed by downstream fracture analysis. The correction delta is retained as audit, comparison, and legacy-compatibility metadata.

A correction-derived `CrackTipEstimateResult` should link to the source estimate that was corrected, for example through `source_crack_tip_estimate_id`. It should avoid unqualified result names such as `ct_corr` or generic `correction` when those names do not make clear whether the value is a delta or an absolute estimate.

Rationale:

Current correction formulas and APIs naturally compute shifts such as `dx` and `dy`, and current plotting applies those shifts to an already detected crack tip. Downstream fracture analysis, however, needs a crack-tip position or frame, not only a relative shift. Treating the corrected estimate as the primary result preserves the value that later methods consume, while keeping the delta preserves traceability to the correction method and the source estimate.

This also fits the provenance model: a correction is another estimate-producing method that consumes a previous crack-tip estimate, its own configuration, and input data. A bare delta is not enough to reconstruct the corrected crack-tip state unless the source estimate and coordinate frame are known.

Consequences:

- Future correction result records should expose fields equivalent to `corrected_crack_tip_estimate`, `correction_delta`, and `source_crack_tip_estimate_id`.
- Deltas should carry units and coordinate-frame context because they are not meaningful on their own.
- Legacy delta-returning APIs can be supported by compatibility adapters during migration.
- Fracture-analysis provenance should link to the corrected estimate it actually consumed, not only to the original detected estimate or to a correction configuration.

## 2026-05-14: Line-Intercept Window Size Is A Consecutive Strain-Exceedance Count

Status: accepted for planning

Decision:

Future line-intercept vocabulary should treat the current `CrackDetectionLineIntercept.window_size` argument as `min_consecutive_strain_exceedance_count`. The value is an integer count of consecutive fitted crack-path samples whose `eps_vm` must exceed `eps_vm_threshold` before a crack-tip point is accepted. It is not a physical window size, crop size, or length in millimeters.

The current implementation name `window_size` remains legacy code/API vocabulary until a refactor or compatibility migration is explicitly approved. Documentation should describe it through the canonical concept and keep the legacy name visible when referring to current code.

Related constructor vocabulary should also be made explicit:

- `x_min`, `x_max`, `y_min`, and `y_max` describe the line-intercept evaluation-region bounds in millimeters.
- `tick_size_x` and `tick_size_y` describe requested interpolation-grid spacing in millimeters; because the implementation computes an integer point count and uses endpoint-inclusive coordinates, they are nominal spacing controls.
- `grid_component` selects the displacement component used for tanh fitting along vertical slices.
- `eps_vm_threshold` is the equivalent-strain threshold applied along the fitted crack path.
- `angle_estimation_mm_radius` is the declared physical radius converted with `tick_size_x` into an approximate number of nearby crack-path samples for angle fitting.

Rationale:

`window_size` is overloaded across CrackPy. In neural crack detection it describes a physical detection-window size in millimeters, while in line-intercept detection it is used as a slice length and loop bound for threshold persistence along the inferred crack path. Naming this value as a count makes the expected type and algorithmic meaning visible.

Consequences:

- OQ-004 is resolved as a documentation and planning vocabulary decision.
- Future line-intercept configuration models should prefer `min_consecutive_strain_exceedance_count`.
- Any future code migration should preserve legacy `window_size` through a compatibility adapter or deprecation path, not as an immediate production refactor.
- Validation or type checks in a later implementation should enforce an integer count for this setting.

## 2026-05-14: JSON Is The Main Future Result Output

Status: accepted for planning

Decision:

Future CrackPy result output should use a versioned JSON result artifact as the main machine-readable output. The first target is scalar fracture-analysis and crack-detection result data plus traceability metadata, not storage of every intermediate transformation, large field array, or detailed process step.

The JSON result artifact should carry an explicit `result_schema_version`. That version describes the serialized result contract: public result keys, nesting, units, field meanings, and required provenance links. It is separate from `method_revision`, `configuration_id`, `crackpy_version`, and implementation fingerprints.

Rationale:

The near-term CrackPy use case is dominated by scalar scientific results, method/configuration metadata, crack-tip estimates, provenance IDs, hashes, and links into the compact knowledge graph. JSON is readable, easy to validate, easy to export into the existing RDF/Jena metadata statement-bundle shape, and sufficient for this scalar-result envelope.

Formats such as Parquet, HDF5, netCDF, Zarr, and RO-Crate solve different problems. Parquet is useful for tabular/batch summaries, HDF5/netCDF/Zarr are useful for larger array-oriented scientific data, and RO-Crate is useful as an outer research-object bundle. None of these should become the core result contract before CrackPy has a stable internal result model and JSON envelope.

Consequences:

- Future result writers should treat JSON as the canonical main output for scalar result records and traceability metadata.
- Legacy tagged text output should become a compatibility adapter, with unversioned legacy files treated as an implicit legacy schema.
- Flattened CSV and Parquet-style exports should be helper projections for tabular analysis, not the source of truth.
- Plots remain visualization artifacts that link to `result_id` or `run_id` instead of duplicating full provenance.
- HDF5, netCDF, or Zarr may be considered later for large arrays or intermediate fields, but they are optional storage profiles.
- RO-Crate may be considered later for packaging JSON, plots, tables, provenance artifacts, and input references into a research-object bundle.
- OQ-006 remained open after this decision because schema versioning did not yet decide which current result names are public schema versus legacy implementation vocabulary.

## 2026-05-14: Canonical Result JSON Is A PROV-Compatible Graph Bundle

Status: accepted for planning

Decision:

OQ-006 is resolved as a schema-boundary decision. Future public result vocabulary should not be defined by current writer tags such as `Williams_fit_results`, `SIFs_integral`, `Path_SIFs`, `Bueckner_Chen_integral`, `Path_Properties`, or by internal attribute names such as `sifs_int` and `rej_out_mean`. Those names remain legacy adapter aliases for current text, current JSON, flattened CSV, tests, and compatibility readers.

The future canonical CrackPy result JSON should be a small graph-shaped result/provenance bundle. It should contain typed nodes such as `Software`, `SoftwareConfiguration`, `InputRecord`, `AnalysisRun`, `ResultRecord`, `ResultQuantity`, `CrackTipEstimateResult`, and `ProvenanceRecord`, plus typed edges such as `used`, `wasAssociatedWith`, `wasGeneratedBy`, and `hasQuantity`. The names do not have to be literal PROV-O class names internally, but the structure should be directly mappable to PROV-O.

Scalar scientific outputs should be represented as `ResultQuantity`-like subjects with their own identity. A mode I stress intensity factor from Williams fitting should therefore not be only a field inside `Williams_fit_results`, because that ties the result meaning to a legacy writer section. OQ-011 decides the concrete quantity vocabulary: for now the quantity node keeps the familiar scientific `symbol` and an expressive `description` string instead of introducing mandatory structured descriptors such as fracture mode, component, or Williams term index.

The compact KG grouped metadata statement bundle remains an export target, not the canonical CrackPy result schema. A KG translator should flatten selected graph nodes and edges into statements with `key`, `value`, `data_type`, `unit`, `metadata_type`, `source`, and `related_to`. The translator or KG importer decides grouping, subject URI minting, and namespace policy.

`SoftwareConfiguration` should be content-addressable where practical. The stable configuration identity can be derived from a hash of a canonical normalized configuration payload that includes resolved defaults and `configuration_schema_version`, while excluding volatile execution fields such as timestamps, output paths, run IDs, and temporary object IDs. CrackPy core should expose stable IDs and hashes; the KG exporter should mint KG-facing URIs.

Rationale:

A tag-shaped schema cannot distinguish multiple estimates of the same scientific quantity cleanly. CrackPy can produce several mode I stress intensity factors from different estimators, such as Williams fitting, interaction integrals, J-integral decomposition, and Bueckner-Chen integrals. Encoding those distinctions inside keys such as `K_I_Chen` or `K_I_J` makes KG export, method comparison, uncertainty handling, provenance, and later schema migration harder.

A graph-shaped bundle keeps relationships explicit. It can express that a result was generated by a run, the run used an input and a crack-tip estimate, the run was associated with CrackPy and a software configuration, and the result has one or more quantity nodes. The same bundle can later drive a compact Jena metadata export and an optional detailed PROV-O/JSON-LD export.

Consequences:

- Current result tags and flattened CSV columns become legacy aliases or adapter vocabulary, not canonical public schema.
- Future result writers should emit graph-shaped JSON as the canonical scalar result/provenance artifact.
- Legacy text, current JSON sections, CSV flattening, plots, and optional table/array formats should be adapters over the canonical result graph.
- At the time of OQ-006, OQ-011 remained the follow-up decision on whether quantity semantics should use structured descriptors or stay closer to current symbols plus descriptions.
- No production schema, writer, or reader change is approved by this decision.

## 2026-05-14: ResultQuantity Keeps Symbol And Description Before Structured Descriptors

Status: accepted for planning

Decision:

OQ-011 is resolved conservatively. Future `ResultQuantity` records should keep the familiar fracture-mechanics or CrackPy result symbol as the primary quantity label. Examples include `K_I`, `K_II`, `K_III`, `K_F`, `K_R`, `K_S`, `T`, `T_x`, `a_1`, `b_2`, `J_I`, and path/statistic variants where applicable.

Do not introduce mandatory structured descriptor fields such as `fracture_mode`, `mode_index`, `component`, `series`, or `term_index` yet. The first planning target is a single scalar quantity node with fields such as `quantity_id`, `result_id`, `symbol`, `description`, `value`, `unit`, `method_id`, optional `derived_from_quantity_ids`, and `legacy_aliases`.

The `description` field should explain the scientific meaning in plain language, including derivation context where it matters. Examples:

- `Mode I stress intensity factor derived from Williams coefficient a_1.`
- `CJP forward stress-intensity-like parameter K_F from mixed-mode CJP fitting.`
- `T-stress derived from Williams coefficient a_2.`
- `Mode I J-integral contribution from mode decomposition.`

Rationale:

CrackPy result symbols are not all variants of the same mode concept. `K_I`, `K_II`, and `K_III` are LEFM stress intensity factors for fracture modes. `K_F`, `K_R`, and `K_S` are CJP-model-specific field parameters. `T` is a non-singular stress term. Williams coefficients such as `a_1` and `b_2` can be primary fit outputs from which downstream quantities are derived. Forcing these into one early descriptor ontology would likely create unstable schema decisions before the refactor has clarified the full result model.

The accepted compromise keeps result JSON readable and compatible with current scientific notation while still separating scalar values from legacy writer sections. A later schema version may introduce controlled structured descriptors if the ontology boundary becomes clear. That migration can use `symbol`, `description`, `method_id`, and `legacy_aliases` as source material instead of requiring every consumer to parse old section names.

Consequences:

- `symbol` is the primary canonical quantity label for now.
- `description` carries human-readable scientific meaning and derivation context.
- Structured fields for fracture mode, model component, Williams series, or term index are deferred.
- Existing symbols and tags remain compatibility aliases where needed, but the canonical result node is still separate from legacy writer sections.
- No production schema, writer, or reader change is approved by this decision.

## 2026-05-14: Domain Workflow Runners Stay, Current Pipelines Become Compatibility Facades

Status: accepted for planning

Decision:

OQ-008 is resolved as an orchestration boundary decision. CrackPy should keep package-owned workflow logic where the sequencing is scientific or domain-specific, but future runners should be side-effect-light and record-oriented. Current `CrackDetectionPipeline` and `FractureAnalysisPipeline` should be treated as compatibility facades during a future migration, not as the target architecture.

CrackPy-owned workflow logic includes preparing analysis inputs, transforming data into a crack-tip-centered frame, computing stresses before line integrals, running crack-tip detection, correction, and fracture analysis in a valid order, constructing or auto-detecting integration paths, aggregating path results, and attaching method, configuration, result, and provenance metadata.

Adapter policy includes legacy text writing, current JSON writing, future canonical result JSON writing, old `crack_info_by_nodemap.txt` handoff import/export, flattened CSV export, plot generation, folder layout, progress reporting, multiprocessing choice, neural-network model download/cache behavior, VTK export, and RDF/knowledge-graph export.

Rationale:

The current pipelines are useful because they bundle workflow knowledge that should not be pushed entirely into external orchestrators. At the same time, they currently mix computation with file writes, plots, progress UI, process-pool execution, directory conventions, and model-provider behavior. That coupling makes it hard to reuse the same scientific runner from a CLI, Model Context Protocol (MCP) tool, workflow manager, graph orchestrator, or test harness without inheriting side effects.

The future boundary should therefore preserve CrackPy-owned domain sequencing while making side effects explicit. External orchestrators should compose CrackPy runners and adapters; they should not have to reimplement the scientific order of operations.

Consequences:

- Future architecture can expose domain workflow runners that return `InputRecord`, `AnalysisRun`, `ResultRecord`, crack-tip estimate, and provenance-oriented records.
- Current side-effect-heavy pipelines remain candidates for compatibility facades so existing scripts and output behavior can be preserved during migration.
- Legacy text files, current JSON sections, flattened CSV, plots, folder names, progress UI, model-cache policy, and KG/RDF export are adapter or compatibility vocabulary.
- `crack_info_by_nodemap.txt` remains an important compatibility handoff artifact, but future internal handoffs should use explicit crack-tip estimate records.
- No production pipeline refactor is approved by this decision.

## 2026-05-14: Model Names, Bueckner Spelling, And Fixture Keys Use Explicit Naming Boundaries

Status: accepted for planning

Decision:

OQ-009, OQ-012, and OQ-014 are resolved as naming-boundary questions.

`UNetPath` should remain readable as the current public selector, weight-file stem, local cache identity, and legacy alias for the pretrained crack-path detector. Future architecture should not use `UNetPath` as the only semantic identity. A future model registry or `ModelProvider` should split the meanings explicitly:

- `model_id`: stable, method- or paper-linked identity, for example `crackpy.detection.strohmann_2021_crack_path_unet`;
- `model_role`: functional role, for example `crack_path_detector`;
- `architecture`: implementation architecture, here `UNet`;
- `weights_id`: concrete weights artifact, currently `UNetPath.pth`;
- `aliases`: compatibility names, including `UNetPath`.

`buckner` is legacy implementation spelling. Future refactor vocabulary should use the scientific/domain term `Bueckner-Chen` and ASCII Python identifiers in the `bueckner_chen_*` family, for example `integrate_bueckner_chen()` and `bueckner_williams_terms`. Current `buckner_*` identifiers should be preserved through aliases, wrappers, or a deliberate deprecation path until a compatibility migration is approved.

`Dummy2`, `EBr10`, `Aramis_in_line`, and similar names are not domain vocabulary. They are experiment preset or fixture keys that encode local workflow defaults such as nodemap ranges, window sizes, offsets, and target availability. They can remain observed fixture/test data names, but future architecture and glossary work should ignore them as scientific or domain concepts.

Rationale:

`UNetPath` is currently overloaded. It is accepted by `get_model()`, maps directly to `UNetPath.pth`, is embedded in scripts and tests, and instantiates the `UNet` class. Renaming it directly would break public examples, local caches, and the Zenodo artifact relationship. A registry split gives better provenance and paper-linked naming without breaking compatibility.

The Bueckner-Chen spelling decision separates scientific vocabulary from current implementation debt. The package currently exposes `buckner_*` identifiers in code while documentation, result tags, and literature context point to Bueckner-Chen. The future refactor should fix the implementation spelling, not normalize the legacy spelling into the domain language.

The fixture-key decision keeps the glossary focused. Names such as `Dummy2` and `EBr10` are useful for tests and local workflows, but they do not describe fracture-mechanics concepts, data-model concepts, or reusable CrackPy interfaces.

Consequences:

- OQ-009 is resolved: future model metadata should introduce a stable model ID and keep `UNetPath` as a compatibility alias or weights ID.
- OQ-012 is resolved: `buckner` remains legacy spelling; future implementation vocabulary should use `bueckner_chen_*`.
- OQ-014 is resolved: fixture keys are not domain vocabulary and do not need further terminology planning unless a future preset/configuration system is designed.
- No production code rename is approved by this decision. This remains documentation and future-refactor planning.

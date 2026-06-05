# CrackPy Provenance and Metadata Architecture

Status: proposed
Role: Future architecture candidate for internal provenance metadata, compact knowledge-graph export, and optional detailed process provenance. This is a planning note only; no implementation is approved.

Related: [[refactor-candidates/001-explicit-analysis-result]], [[refactor-candidates/002-input-loading-seam]], [[refactor-candidates/008-result-tag-schema]], [[refactor-candidates/009-sequence-index-vocabulary]], [[open-questions#Question Index]]

## Motivation

CrackPy should eventually emit enough provenance and metadata to make analysis results traceable, selectively refreshable, and exportable into the existing RDF / Apache Jena knowledge graph. The target is not to model every internal call as a semantic process in the main graph. The target is a compact, queryable representation that records which software, configuration, registered method, inputs, parameters, method references, and outputs produced a result.

The current code already has useful fragments:

- `crackpy.__version__` defines the package version.
- `OutputWriter.write_json()` records `filename`, `evaluation_UTC_datetime`, `experiment_data`, result sections, `Path_Properties`, and `CrackPy_settings`.
- `CrackPy_settings` serializes selected `IntegralProperties`, `OptimizationProperties`, `CrackTipInfo`, and `Material` attributes.
- `InputData` parses nodemap header metadata such as force, cycles, displacement, potential, crack length, and time.
- `CITATION.cff` records package citation metadata.

Observed gaps are also clear:

- result files do not record the CrackPy version, repository commit, method revision, input hash, result schema version, detection model identifier, model hash, dependency snapshot, or method-level references;
- analysis methods are identified mostly by Python method names and result tags, not by stable metadata records;
- literature references are stored in README prose, docstrings, and comments rather than method-specific structured metadata;
- crack detection output records crack-tip coordinates, angle, and side, but not model/configuration provenance;
- result schema naming is stringly typed and currently handled by writer/reader conventions.

## Integration Checkpoint From External KG Artifacts

The recent comparison of the provided datapoint JSON, Turtle export, diagram sketch, code screenshot, and throwaway result-spine prototype confirms the broad direction of this candidate, but it narrows the first practical target.

The direction that still holds:

- CrackPy should define internal result/provenance records first, then map those records outward through adapters.
- The compact knowledge-graph export should remain a result-centric projection, not the canonical CrackPy internal schema.
- Detailed process provenance should stay optional and separate from the compact KG export.
- The first approved specification should be smaller than this full candidate: a minimal result/provenance envelope plus one compact KG projection for one vertical slice, such as a Williams-fit result or a crack-tip-estimate result.

The first slice should not attempt to introduce the full registry, fingerprint, configuration, input-identity, crack-tip-frame, KG, and optional PROV layers at once. It should define the smallest complete envelope that can carry `result_id`, `input_id`, `method_id`, `configuration_id`, `configuration_hash` or `parameter_hash`, `result_schema_version`, scalar quantities, output artifact references, and minimal provenance roles such as `used_input`, `used_configuration`, `used_crack_tip_estimate`, and `generated_result`.

The `prototypes/result_spine` experiment in the prototype worktree supports the conceptual shape, but it is a clean-room prototype. It is useful evidence that the record split is coherent; it is not migration evidence for the current `InputData`, `FractureAnalysis`, and result-writer implementation.

## First Williams-Fit Slice Specification

Status: draft field-level planning specification

This section folds the useful conclusions from the preserved `prototypes/result_spine_package` worktree prototype into the architecture wiki. It defines one minimal Williams-fit result/provenance slice on paper. It does not approve production `crackpy/` code changes, package restructuring, writer changes, reader changes, or RDF export implementation.

The slice covers one Williams displacement-field fit over one nodemap-like input and one crack-tip estimate. It must be large enough to prove the result/provenance spine, but small enough to avoid landing the full method registry, implementation fingerprinting, generalized input identity model, full crack-tip-frame model, compact KG exporter, and optional detailed PROV artifact in one step.

### Slice Boundary

In scope:

- one `InputRecord` for the displacement-field input;
- one imported, detected, or corrected `CrackTipEstimateResult` consumed by the Williams fit;
- one `CrackTipFrame` that records the coordinate context used by the fit;
- one Williams-fit `AnalysisRun`;
- one `ResultRecord` with scalar `ResultQuantity` records;
- one compact KG statement-bundle projection;
- compatibility aliases for current `Williams_fit_results` fields.

Out of scope:

- line integrals, Bueckner-Chen integrals, CJP fitting, path statistics, plots, multiprocessing, model download/cache policy, VTK export, and full detailed provenance;
- full method-reference registry implementation;
- production hash policy beyond the field boundaries described here;
- RDF/Turtle rendering details, graph explorer UI, and source-specific KG namespace choices.

### Minimal Envelope

The first slice envelope is the smallest self-contained bundle that lets a reader resolve all IDs used by the Williams-fit result. The envelope is a planning record, not a required Python class name.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `envelope_schema_version` | Version of this minimal envelope shape. | Lets future readers distinguish the first slice from later expanded result/provenance bundles. |
| `input_records` | List of `InputRecord` values referenced by the run and estimate. | Keeps stable input anchors inside the same payload that carries the result. |
| `methods` | List of `MethodMetadata` values referenced by the crack-tip estimate and Williams fit. | Separates durable method identity from current Python locations and legacy result tags. |
| `configurations` | List of `NormalizedConfiguration` values referenced by the estimate and run. | Preserves resolved result-affecting parameters, default origins, and adapter policy boundaries. |
| `crack_tip_frames` | List of `CrackTipFrame` values used by crack-tip-dependent analysis. | Records the coordinate context needed to interpret the Williams fit without relying only on `side`. |
| `crack_tip_estimates` | List of `CrackTipEstimateResult` values consumed by analysis runs. | Makes crack-tip estimates first-class result dependencies instead of hidden configuration. |
| `analysis_runs` | List of `AnalysisRun` values that generated result records. | Links method, inputs, configuration, dependencies, timing, and CrackPy version for one execution. |
| `results` | List of `ResultRecord` values and their quantities/artifacts. | Anchors scalar scientific outputs and output projections to the run that generated them. |

Approved first-slice schema-version strings:

| Schema target | Schema-version string | Why it exists |
| --- | --- | --- |
| Result/provenance envelope | `crackpy.result_envelope.williams_fit.v1` | Versions the whole Williams-fit slice bundle without claiming a universal envelope yet. |
| Result record | `crackpy.result_record.williams_fit.v1` | Versions the scalar Williams-fit result anchor and its quantity/artifact structure. |
| Normalized configuration | `crackpy.configuration.williams_fit.v1` | Versions the Williams-fit result-affecting parameter shape and default-origin policy. |
| Compact KG statement bundle | `crackpy.kg_statement_bundle.williams_fit.v1` | Versions the compact export projection for this slice. |

This naming follows [[decision-log#2026-06-05-first-slice-uses-williams-fit-specific-schema-versions]]. Prototype strings such as `crackpy.prototype.result_record.v1` are not production-facing planning vocabulary.

### InputRecord

An `InputRecord` is the stable source anchor for a nodemap-like displacement-field input. It does not replace current `InputData` loading in this phase.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `input_id` | Durable identity for the concrete input record. | Gives results and estimates a stable target that is not the DIC `stage` label. |
| `data_ref` | Locator for the nodemap, displacement field, simulation field, or equivalent payload. | Lets adapters find or report the data source without embedding full data in the scalar result bundle. |
| `source_metadata` | Source-system metadata such as `stage`, force, cycles, displacement, specimen, timestamp, or load. | Keeps source metadata attached to the input while preserving `stage` as metadata rather than internal ordering. |
| `source_label` | Optional human or source-system label such as `stage=0042`. | Preserves familiar labels for reports, debugging, and compatibility output. |
| `source_hash` | Optional content hash or source-payload hash. | Supports change detection and stale-result review when the input payload changes. |

### MethodMetadata

`MethodMetadata` is the first-slice method description carried in the envelope. It is smaller than the future full method registry.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `method_id` | Stable method identity such as `crackpy.fracture.williams_fit`. | Lets provenance survive Python moves, class renames, and result-writer cleanup. |
| `display_name` | Human-facing method label. | Supports reports and compact KG statements without making display text the durable identity. |
| `kind` | Broad role such as `input_adapter`, `crack_tip_estimate`, or `analysis`. | Lets the first envelope distinguish imported crack-tip estimates from Williams analysis without a full registry. |
| `method_revision` | Maintainer-controlled semantic revision for the method meaning. | Supports stale-result checks when method defaults, assumptions, outputs, units, or interpretation change. |
| `implementation_ref` | Current Python module, class, function, or source reference. | Lets maintainers trace the run back to code while keeping current paths non-canonical. |
| `aliases` | Compatibility names such as `Williams_fit_results` or current handoff-file names. | Lets adapters map current output vocabulary to canonical result records. |
| `references` | Optional method-reference IDs or provisional literature keys. | Keeps the scientific basis attachable without requiring the full reference registry in the first slice. |

### NormalizedConfiguration

`NormalizedConfiguration` captures result-affecting parameters separately from adapter policy. This split is required before a meaningful `parameter_hash` can exist.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `configuration_id` | Stable identity for the normalized configuration snapshot. | Gives runs and compact KG statements a stable configuration target. |
| `schema_version` | Version of the configuration record shape. | Allows later configuration models to evolve without invalidating old envelopes silently. |
| `result_parameters` | Resolved values that can change numerical results, result shape, units, or interpretation. | Defines the recomputation-relevant configuration scope. |
| `parameter_origins` | Origin of each result-affecting parameter, such as caller-provided, model default, or derived default. | Makes default-driven result changes visible and auditable. |
| `adapter_policy` | Output, cache, progress, plotting, and projection choices that should not by themselves force scientific recomputation. | Keeps side-effect policy out of the scientific parameter hash while still recording it when useful. |
| `parameter_hash` | `sha256:` hash over canonical JSON containing `schema_version`, `result_parameters`, and `parameter_origins`. | Lets stale-result checks detect result-affecting configuration changes without comparing raw objects. |
| `configuration_hash` | `sha256:` hash over canonical JSON containing the full normalized configuration, including `adapter_policy`. | Lets tooling detect any configuration change while distinguishing adapter-only changes from scientific recomputation triggers. |

For a Williams fit, first-slice `result_parameters` should include material values, fit radii, angle gap, selected Williams terms, coordinate-transform inputs that affect the fit, and any other resolved options that change the fitted coefficients or derived quantities. Output folders, plots, progress behavior, and current JSON projection choices belong in `adapter_policy`.

Hash policy follows [[decision-log#2026-06-05-first-slice-uses-sha-256-canonical-json-hashes]]:

- configuration-derived hashes use full `sha256:`-prefixed digests over canonical UTF-8 JSON bytes with sorted keys and deterministic primitive representations;
- `parameter_hash` excludes adapter policy and all volatile run or filesystem state;
- `configuration_hash` includes adapter policy but still excludes timestamps, output paths, generated IDs, run IDs, temporary object IDs, and filesystem-specific path separators;
- resolved defaults are included in the hashed parameter payload through `result_parameters` and `parameter_origins`;
- output `content_hash` values are optional for the first implementation, but must use `sha256:` over actual artifact bytes when present.

### CrackTipFrame

`CrackTipFrame` records the coordinate context used by a crack-tip-dependent method. The first slice stays 2D-compatible while preserving the path toward the broader `CrackTipFrame` concept.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `frame_id` | Stable identity for the local crack-tip frame. | Lets analysis runs and estimates reference the exact frame used for coordinate interpretation. |
| `tip_id` | Crack-tip identity independent of legacy labels. | Separates the physical or logical crack tip from `left` and `right` compatibility vocabulary. |
| `origin_mm` | Crack-tip origin in millimeters in the input coordinate system. | Defines the point used for crack-tip-centered fitting and downstream result interpretation. |
| `angle_deg` | Crack extension angle whose canonical unit is `degree`. | Records the orientation used by transforms and makes angle semantics explicit. |
| `compatibility_side` | Optional legacy `left` or `right` label. | Preserves current file/API/report compatibility without making `side` the internal orientation model. |

The canonical unit policy follows [[decision-log#2026-06-05-first-slice-uses-degree-as-canonical-angle-unit]]. Current writer vocabulary such as `grad` may remain adapter vocabulary if needed for compatibility.

### CrackTipEstimateResult

`CrackTipEstimateResult` is a result dependency. It can represent a manual import, detector output, correction output, or later fused estimate.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `estimate_id` | Stable identity for the crack-tip estimate result. | Allows Williams analysis to depend on a specific estimate, not on anonymous configuration values. |
| `input_id` | `InputRecord` identity used to produce or import the estimate. | Connects the estimate back to its source displacement field or handoff record. |
| `method_id` | Method that produced, imported, or corrected the estimate. | Makes manual import, neural detection, and correction provenance distinguishable. |
| `configuration_id` | Configuration used by the estimate method or import adapter. | Records estimate-specific settings separately from Williams-fit settings. |
| `frame_id` | Crack-tip frame associated with the estimate. | Connects coordinate values to the frame consumed by the analysis run. |
| `source` | Category such as manual import, detector, correction, or fusion. | Gives compact KG queries a simple origin classification without parsing method IDs. |
| `observed_mm` | Coordinates before correction. | Preserves the original estimate for audit and correction review. |
| `corrected_mm` | Absolute coordinates consumed by downstream analysis. | Avoids ambiguity between relative shifts and the final crack-tip location. |
| `correction_delta_mm` | Relative movement from observed coordinates to corrected coordinates. | Keeps correction magnitude explicit for audit and compatibility with existing delta-style methods. |
| `source_estimate_id` | Prior estimate consumed by this estimate, when applicable. | Represents correction chains without flattening them into one anonymous coordinate pair. |

### AnalysisRun And DependencyEdge

`AnalysisRun` describes one execution of the Williams-fit method. A `DependencyEdge` records why the run used another record.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `run_id` | Stable identity for one method execution. | Anchors generated results and compact KG run statements. |
| `method_id` | Durable method identity executed by the run. | Supports method-specific query, stale-result checks, and later registry lookup. |
| `method_revision` | Semantic method revision used during execution. | Captures the method meaning at the time of the run. |
| `input_ids` | Input record IDs used as primary data inputs. | Keeps primary input dependencies easy to find. |
| `configuration_id` | Normalized configuration snapshot used by the run. | Links execution to resolved result-affecting parameters. |
| `parameter_hash` | Hash copied from the result-affecting configuration scope. | Lets run-level stale checks avoid expanding the full configuration. |
| `dependencies` | Typed dependency edges to input, configuration, crack-tip estimate, and crack-tip frame records. | Makes non-input dependencies explicit, especially `used_crack_tip_estimate`. |
| `started_at` | UTC start timestamp. | Supports audit, run ordering, and troubleshooting. |
| `completed_at` | UTC completion timestamp or null for incomplete runs. | Distinguishes complete, failed, and partial execution records. |
| `crackpy_version` | CrackPy version or prototype marker used for the run. | Preserves package-level traceability separately from method revision. |

Required first-slice dependency roles:

| Role | Target type | Why it exists |
| --- | --- | --- |
| `used_input` | `InputRecord` | States which displacement-field input the run consumed. |
| `used_configuration` | `NormalizedConfiguration` | States which resolved Williams-fit configuration controlled the run. |
| `used_crack_tip_estimate` | `CrackTipEstimateResult` | Makes crack-tip estimate changes result-affecting dependencies. |
| `used_crack_tip_frame` | `CrackTipFrame` | Makes orientation and origin changes visible to stale-result checks. |

### ResultRecord, ResultQuantity, And ArtifactRef

`ResultRecord` is the canonical anchor for scalar Williams-fit outputs from one run. It is not the same shape as current text, current JSON sections, CSV exports, or compact KG statements.

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `result_id` | Stable identity for the result record. | Lets compact KG, adapters, plots, and later provenance artifacts refer to the same result. |
| `run_id` | `AnalysisRun` that generated the result. | Preserves the generation link without duplicating run metadata inside every quantity. |
| `result_schema_version` | Version of the canonical result record shape. | Makes public result meaning and migration policy explicit. |
| `quantities` | Scalar `ResultQuantity` values produced by the run. | Separates scientific outputs from legacy writer section names. |
| `artifacts` | `ArtifactRef` values for generated or projected outputs. | Lets the canonical result link to JSON, current JSON projection, compact KG bundle, plots, or later packages without embedding every artifact. |

`ResultQuantity` fields:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `quantity_id` | Stable identity for one scalar output. | Allows multiple methods or estimators to produce comparable symbols without collision. |
| `symbol` | Domain-facing notation such as `K_I`, `K_II`, `K_III`, `T`, `a_1`, `b_1`, `c_1`, `error_xy`, or `error_z`. | Keeps result JSON readable and close to fracture-mechanics notation. |
| `value` | Finite scalar result value. | Carries the numeric scientific output. |
| `unit` | Physical unit string or `1` for unitless values. | Keeps unit interpretation explicit and exportable. |
| `description` | Plain-language scientific meaning and derivation context. | Avoids forcing early structured descriptors while still explaining what the scalar means. |
| `method_id` | Method that produced the quantity. | Lets quantities be compared by symbol while preserving estimator identity. |
| `legacy_aliases` | Current text or JSON paths such as `Williams_fit_results.K_I`. | Gives compatibility adapters a deterministic mapping from canonical quantities to existing outputs. |

The first adapter quantity boundary follows [[decision-log#2026-06-05-first-adapter-covers-the-current-williams-fit-result-section]]. Required quantities are the full current `Williams_fit_results` section:

- residuals: `error_xy` and `error_z`;
- derived Williams-fit scalars: `K_I`, `K_II`, `K_III`, and `T`;
- every available Williams coefficient for the resolved Williams terms: `a_n`, `b_n`, and `c_n`.

The first adapter does not cover `CJP_results`, `CJP_modeI_results`, `SIFs_integral`, `Bueckner_Chen_integral`, `Path_SIFs`, `Path_Williams_a_n`, `Path_Williams_b_n`, or `Path_Properties`.

`ArtifactRef` fields:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `artifact_id` | Stable identity for an output artifact. | Lets result records link to files or projections without embedding them. |
| `role` | Artifact role such as `canonical_result_bundle_json`, `current_json_projection`, or `compact_kg_statement_bundle`. | Distinguishes source-of-truth output from compatibility and export projections. |
| `media_type` | Media type or explicit artifact format label. | Helps consumers choose readers without inspecting file contents. |
| `content_hash` | Optional `sha256:` hash of artifact bytes where practical. | Supports artifact integrity checks and stale-output review without forcing every first-slice projection to materialize a file. |

### Current Output Compatibility

The first Williams-fit slice should project canonical quantities into current output vocabulary through adapters:

- `filename` and `experiment_data` can be projected from `InputRecord`, `CrackTipFrame`, and source metadata.
- Current `Williams_fit_results` keys can be projected from `ResultQuantity.legacy_aliases`.
- Legacy text and current JSON sections are compatibility artifacts, not canonical schema.
- Adapter aliases must remain explicit enough that old tests, scripts, and readers can be supported during migration.

Long-lived first-adapter aliases follow [[decision-log#2026-06-05-first-williams-fit-adapter-uses-current-section-aliases]]. They are limited to current text and JSON `Williams_fit_results` output:

- `error_xy` / text row `Error_xy`;
- `error_z` / text row `Error_z`;
- `K_I`;
- `K_II`;
- `K_III`;
- `T`;
- `a_{n}`, `b_{n}`, and `c_{n}` for every resolved Williams coefficient term.

Current internal attributes such as `williams_fit_res`, `williams_fit_a_n`, `williams_fit_b_n`, and `williams_fit_c_n` are adapter extraction sources, not canonical public schema names.

### Compact KG Statement-Bundle Projection

The compact KG projection is an adapter over the envelope. It is not the internal result model and does not require CrackPy core records to become RDF resources.

Bundle-level fields:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `bundle_schema_version` | Version of the compact statement-bundle export shape. | Lets KG importers distinguish export formats. |
| `uri_policy` | Exporter policy for whether and how subject URIs are included. | Keeps namespace and URI construction outside core records. |
| `descriptor_field_policy` | Statement of whether scalar facts are plain statements, RDF descriptor resources, or both. | Prevents `LiteralField` and related RDF constructs from leaking into core architecture. |
| `statements` | Flat list of compact metadata statements. | Gives importers a simple ingestion shape. |
| `groups` | Statements grouped by `related_to` or equivalent grouping key. | Supports compact query and ingestion without making grouping the core graph model. |

Required statement fields:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `subject_id` | Local subject identity selected by the export profile. | Gives each statement a concrete local subject even when no URI is minted. |
| `subject_uri` | Optional KG-facing URI for the subject. | Allows RDF import while keeping URI minting out of core records. |
| `key` | Statement key. | Names the exported property for compact metadata ingestion. |
| `value` | JSON-like statement value. | Carries the exported fact. |
| `data_type` | Normalized datatype label. | Avoids non-standard datatype names and supports predictable KG conversion. |
| `unit` | Normalized unit string, using `1` for unitless values. | Avoids missing or non-standard unit representation for scalar facts. |
| `description` | Plain-language meaning of the statement. | Keeps compact statements interpretable without consulting code. |
| `metadata_type` | Export grouping/type name such as `InputRecord`, `SoftwareConfiguration`, `AnalysisRun`, `FractureAnalysisResult`, `ResultQuantity`, or `OutputArtifact`. | Supports compact KG query and display without defining CrackPy core classes from KG ontology names. |
| `source` | Record or method ID that supplied the statement. | Supports audit and debugging of the export projection. |
| `related_to` | Owning domain subject used for grouping. | Keeps quantities, artifacts, and run facts linkable to their result or source record in compact form. |

Projection policy:

- Grouping policy: group compact statements by `related_to` for ingestion and query; do not treat group names as durable URI policy by themselves.
- Subject identity policy: use stable core IDs as `subject_id`; include `subject_uri` only when an exporter or KG importer profile chooses a URI policy.
- URI minting policy: keep base URI, namespace, escaping, and class/predicate choices in exporter or importer policy, not in core records.
- Descriptor-field policy: the first compact JSON projection should use statements. RDF resources such as `LiteralField`, `IdentityMetadata`, `ContextMetadata`, and `StateMetadata` may be downstream RDF rendering choices only.
- Datatype normalization policy: normalize JSON-like values to parseable categories such as `null`, `boolean`, `integer`, `float`, `string`, `list`, and `object`; RDF/XSD mapping belongs to the RDF exporter.
- Unit normalization policy: use explicit physical units where known and `1` for unitless values; current compatibility unit labels may be adapted at writer boundaries.
- Angle-unit policy: compact KG angle statements should use `degree`; current `grad` output remains an adapter concern.
- Content policy: export query, audit, and re-analysis facts. Keep detailed process provenance, RDF graph expansion, and debug-level traces in optional projections.

### Graph Visualization Kit Boundary

The graph visualization kit is a downstream adapter over the first-slice envelope. It should consume the canonical records and dependency edges first, then optionally consume compact KG statements, RDF, Turtle, or graph explorer artifacts as secondary views.

Primary visualization input:

- `InputRecord`;
- `CrackTipEstimateResult`;
- `CrackTipFrame`;
- `AnalysisRun`;
- `ResultRecord`;
- `ResultQuantity`;
- `ArtifactRef`;
- `DependencyEdge`.

The first useful graph view should show stable IDs, node types, result quantities, artifact references, and dependency roles such as `used_input`, `used_configuration`, `used_crack_tip_estimate`, `used_crack_tip_frame`, `was_generated_by`, and `has_quantity`.

Visualization concerns remain outside the core record model:

- layout coordinates, colors, expanded or collapsed UI state, and graph explorer HTML;
- RDF namespaces, URI expansion, Turtle serialization, and KG importer policy;
- descriptor resources such as `LiteralField`, `IdentityMetadata`, `ContextMetadata`, or `StateMetadata`.

This boundary follows [[decision-log#2026-06-05-graph-visualization-kit-consumes-the-canonical-envelope-first]]. The preserved RDF-stack prototype can guide a later adapter, but it is not the source of truth for core result/provenance fields.

### Definition And Logic Split

The next Williams-fit refactor should make the first slice spec-driven. Stable per-slice definitions belong in a versioned [[glossary#Provenance slice spec]], preferably YAML-backed and loaded through typed Python validation. Runtime extraction from current objects belongs in Python [[glossary#Source adapter]] code. Envelope construction, hashing, canonical JSON normalization, and file writing remain Python logic.

The Williams-fit provenance slice spec should define:

- method IDs, method revisions, display names, implementation references, and reference IDs;
- schema-version strings for the envelope, result record, normalized configuration, compact KG bundle, and graph visualization profile;
- result quantity symbols, descriptions, units, Williams coefficient-series rules, and legacy aliases;
- dependency roles and target record types;
- compact KG statement keys, descriptions, grouping policy, URI policy, descriptor-field policy, datatype policy, and unit policy;
- graph node labels, graph node types, graph edge labels, and graph edge roles.

The spec should not define:

- how to read attributes from `FractureAnalysis`;
- Williams numerical fitting behavior;
- unit calculation logic such as coefficient units that depend on Williams term order;
- hash implementation details beyond naming the schema and inclusion policy;
- output paths, writer side effects, UI layout, RDF namespaces, Turtle serialization, or graph explorer HTML.

This split follows the same-day accepted planning decision in [[decision-log]]. It is intended to make CJP, line-integral, crack-tip-estimate, KG, and graph variants additive rather than forcing edits to a hard-coded Williams builder.

Coefficient quantity definitions are optional. Williams fitting uses them for repeated `a`, `b`, and `c` coefficient series; scalar-only methods should rely on ordinary quantity definitions.

### Source Adapter And Minimal Source Snapshot

The generic builder should not consume `FractureAnalysis` directly. Current CrackPy objects should be translated by Python [[glossary#Source adapter]] code into a minimal immutable [[glossary#MethodResultSource]], then the builder should combine that source with the [[glossary#Provenance slice spec]].

The planned flow is:

```text
FractureAnalysis -> SourceAdapter -> MethodResultSource -> ProvenanceSliceSpec + builder -> ResultEnvelope
```

The first `MethodResultSource` shape should keep only these field groups:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `inputs` | One or more primary data anchors, such as a nodemap, displacement field, simulation field, or imported reference field. Each anchor should carry only the facts needed to create or link an `InputRecord`: `input_id`, `data_ref`, `source_metadata`, `source_label`, and optional `source_hash`. | Lets the builder create `InputRecord` values without depending on `InputData` or `FractureAnalysis`. |
| `dependencies` | Non-primary-input records or resolved entities the method relied on, such as a crack-tip estimate, crack-tip frame, model artifact, calibration record, or future material record. | Lets each method expose only the dependencies it actually has, without treating them as plain parameters or primary input data. |
| `parameters` | Resolved result-affecting settings plus parameter-origin labels. | Lets the builder create `NormalizedConfiguration` and hashes without reading mutable options objects. |
| `quantities` | Extracted scalar or small result values named by spec quantity name, with optional qualifiers. | Lets Williams, CJP, line-integral, and crack-tip-estimate adapters feed the same builder surface. |

`dependencies` includes both prior records and adapter-derived anchors when they deserve typed links. For example, a Williams-fit source can depend on a crack-tip estimate record and on the resolved `CrackTipFrame` used to interpret the local field. The frame should not be buried in `parameters` only because current code resolves it inside `FractureAnalysis`.

The first source dependency shape should stay constrained:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `dependency_name` | Spec-facing relationship name, such as `crack_tip_frame`, `crack_tip_estimate`, `model_artifact`, or `calibration_record`. It is not just the Python class name. | Lets the spec map the dependency to a final edge role such as `used_crack_tip_frame`, and distinguishes different roles that may use the same record type. |
| `record` | Full typed dependency record supplied by the adapter, such as a resolved `CrackTipFrame`. Mutually exclusive with `target_id`. | Preserves typed dependency data without forcing the builder to interpret loose dictionaries. |
| `target_id` | Stable ID of an already-existing dependency record. Mutually exclusive with `record`. | Lets future composed workflows reference records produced upstream, such as a crack-tip estimate result, without duplicating the record in the source snapshot. |

Exactly one of `record` or `target_id` should be present. Do not add generic `payload` or `values` fields to `SourceDependency`; if a dependency has data, it should be represented by a typed record. The `ProvenanceSliceSpec` should validate allowed `dependency_name` values and map them to final dependency edge roles and target record types.

The first source parameter shape should be one resolved snapshot, not one record per parameter:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `result_parameters` | Mapping of concrete result-affecting values after default resolution, such as material values and Williams optimization settings. | Defines the recomputation-relevant scope without passing mutable `OptimizationProperties` or broad `FractureAnalysis` objects into the builder. |
| `parameter_origins` | Mapping that explains where each result-affecting value came from, such as caller-provided, model default, derived default, or analysis object. | Makes default-driven result changes auditable and allows hashes to change when origin policy changes. |
| `adapter_policy` | Optional mapping for output/projection policy that should be recorded but should not by itself force scientific recomputation. | Keeps writer, alias, plotting, and export choices separate from result-affecting parameters. |

Current runtime configuration objects such as `OptimizationProperties` may feed `SourceParameters`, but they are not the canonical provenance shape. The adapter should extract resolved values from those objects, while the builder should create `NormalizedConfiguration` from `SourceParameters` and the `ProvenanceSliceSpec`.

The first source quantity shape should avoid separate top-level containers for Williams coefficient series, paths, or statistics:

| Field | Meaning | Why it exists |
| --- | --- | --- |
| `quantity_name` | Spec-facing quantity name, such as `K_I`, `error_xy`, `williams_coefficient`, `J`, or `crack_tip_x`. | Gives the spec a stable lookup name without baking legacy result sections into builder logic. |
| `value` | JSON-compatible scalar or small value. | Carries the result extracted from current objects. |
| `qualifiers` | Optional mapping for method dimensions such as `coefficient_series=a`, `term_order=-1`, `statistic=mean`, `path_index=0`, or `mode=mixed_mode`. | Supports Williams coefficients, CJP modes, and J-integral/path statistics without growing `MethodResultSource` fields. |

For Williams fitting, the source adapter should emit `williams_coefficient` quantities with `coefficient_series` and `term_order` qualifiers rather than separate `a_n`, `b_n`, and `c_n` containers. Literature and CrackPy's own theory notes usually describe in-plane Williams coefficients as `A_n` for the Mode I contribution and `B_n` for the Mode II contribution. Canonical source qualifiers should still use compact lower-case labels `a`, `b`, and `c`, matching current CrackPy result symbols and keeping legacy aliases direct. The provenance spec should map lower-case coefficient-series labels to display notation and aliases such as `Williams_fit_results.a_{n}`, `Williams_fit_results.b_{n}`, and `Williams_fit_results.c_{n}`.

For J-integral and path-based results, the source adapter should emit quantities with `statistic` and/or `path_index` qualifiers rather than separate `statistics` or `paths` containers.

The `ProvenanceSliceSpec` should validate which quantity names and qualifier names are allowed for a slice. If future methods need additional dimensions, extend the spec's allowed qualifiers before adding new top-level source fields.

### Williams Method Module Refactor Notes

The Williams-fit refactor keeps generic source/spec/builder concepts under `crackpy.results.provenance` and moves Williams-specific parameters, result types, numerical runner, provenance construction, envelope wrapper, and spec files under `crackpy.fracture_analysis.methods.williams_fit`.

The retained seams are:

- `run_williams_fit()`: current Williams numerical fitting method to typed `WilliamsFitResult`;
- `source_from_result()`: typed `WilliamsFitResult` plus `WilliamsFitResultParameters` to `MethodResultSource`;
- `MethodResultEnvelopeBuilder`: shared provenance builder for input records, method metadata, normalized configurations, dependency edges, and source quantity projection;
- `build_williams_fit_envelope_from_source()`: Williams-specific wrapper that combines `MethodResultSource`, `ProvenanceSliceSpec`, Williams ID policy, the crack-tip estimate record, and Williams coefficient unit logic into a `ResultEnvelope`;
- `SourceDependency`: validates dependency-name plus `record`/`target_id` shape;
- `WilliamsFitResultParameters`: documents and validates Williams-specific result-affecting parameters without growing `MethodResultSource`;
- `load_williams_fit_spec()`: keeps Williams definitions close to the Williams builder while avoiding package import cycles.

One-time helper functions that do not name a domain operation or validation boundary should be inlined. This intentionally relaxes DRY when duplicated structure would make the vertical slice easier to read and easier to adapt for CJP or J-integral.

Method-specific parameter and result schemas can use Pydantic models with field descriptions. These models should describe the new method interface directly; legacy object traversal or current `FractureAnalysis` attribute mapping belongs only in temporary transition facades, not in the method parameter contract.

The Williams source adapter intentionally leaves optional `source_metadata` empty. Hard-coded extraction of legacy `InputData` attributes such as force, cycles, displacement, potential, crack length, or timestamp would turn unstable report metadata into adapter maintenance burden without improving the first provenance dependency chain.

The actual-data vertical slice uses `test_data/simulations` to verify that a real `FractureAnalysis` run can produce the canonical envelope and compact KG statement bundle, not only a synthetic fake-analysis object.

### Field Interpolation Workspace Candidate

Performance reuse should be handled by a method-execution workspace, not by provenance records. The current `Optimization` class already precomputes Williams/CJP interpolation grids once per analysis object, and `ReusableLinearInterpolator` already caches triangulation and barycentric weights for fixed evaluation points. Those are observed implementation facts, not yet a stable method interface.

A future `PreparedFieldData` or `FieldInterpolationWorkspace` module should own reusable interpolated field data across Williams fitting, CJP fitting, and J-integral/path methods. Its cache identity should be derived from input identity, crack-tip frame, transformed coordinate state, grid geometry, mask policy, and result-affecting method parameters. Provenance records may reference the resulting workspace/configuration identity or hash, but they should not own cache lifetime, eviction, interpolation arrays, or mutable numerical state.

This keeps `MethodResultSource` focused on result traceability while leaving room for performance work such as sharing Delaunay triangulation, interpolation weights, transformed displacement fields, and regular-grid samples between methods.

### Prototype Details Not Promoted

The preserved prototypes are evidence for the record split, not the target implementation. Do not promote these details into core CrackPy architecture without a separate decision:

- fake numerical Williams values, demo material constants, demo `stage-0042` IDs, and example timestamps;
- the `crackpy_result_spine` package layout, dataclass validation rules, and local namespace-prefix assertions;
- short prototype hash truncation as the final production hash policy;
- `https://example.invalid` URIs, FMO/DLR namespace choices, BFO-near class names, Turtle schema output, RDFLib, graph explorer HTML/JSON, and rendered TTL files;
- RDF descriptor resources such as `LiteralField` or descriptor categories such as `IdentityMetadata`, `ContextMetadata`, and `StateMetadata` as internal CrackPy records;
- demo RDF predicates as public CrackPy API commitments;
- production imports in the live-test proof path as evidence that the current package has already migrated.

### First-Slice Approval Gate

Before implementation, maintainers should approve or revise this first-slice specification and answer at least these points:

- confirm that the Williams-fit first-slice decision in [[decision-log#2026-06-05-williams-fit-is-the-first-result-provenance-implementation-slice]] still holds if new evidence appears during implementation.

The schema-version, angle-unit, quantity-boundary, hash-policy, and compatibility-alias questions are resolved for planning by same-day decisions in [[decision-log]].

## Current Knowledge Graph Assumptions

The provided microscope-DIC datapoint JSON is one concrete example of a more generic metadata statement bundle. It should not define CrackPy's internal architecture and should not be treated as an MDIC-only target. A comparable bundle could also describe FEM, synthetic benchmark data, imported reference fields, DVC, or another future source.

The observed bundle is grouped by entity-like subject keys such as `Experiment`, `Specimen`, `Crack`, `MachineConfiguration`, `AramisConfiguration`, `MicroscopeImage`, and `ExperimentProcedure`. Each subject contains a list of metadata statements with a regular shape:

```text
data_type
description
key
metadata_type
related_to
source
unit
value
```

The example does not expose a literal `grouped_by` field, but its top-level groups and repeated `related_to` values act like a grouped metadata statement bundle. If the knowledge-graph importer treats `related_to` as the grouping key or names this convention `grouped_by`, the compact exporter should follow that convention. This grouping identifies the subject category for a statement; it does not by itself define a durable URI for a concrete individual.

Generic statement-bundle pattern:

```text
MetadataBundle
  subject group:
    MetadataStatement
      key
      value
      data_type
      unit
      description
      metadata_type
      source
      related_to
```

For microscope DIC, subject groups may be `Aramis`, `MicroscopeImage`, `Specimen`, `Crack`, or `ExperimentProcedure`. For FEM, equivalent subject groups could be `Solver`, `SolverConfiguration`, `Mesh`, `MaterialModel`, `BoundaryCondition`, `LoadStep`, `ResultField`, `CrackDefinition`, or `SimulationProcedure`.

This suggests the existing graph is closer to a BFO-near or object/configuration-oriented model than a fully PROV-O-centered workflow graph. Software and procedure metadata are represented through entities and configuration/state metadata, not through a complete semantic activity chain.

CrackPy should target the generic metadata statement-bundle pattern for compact export, not the microscope-DIC-specific subject vocabulary. A separate exporter can map the same internal metadata records into a PROV-O-like process graph. URI minting should remain part of the exporter profile or KG import policy: CrackPy internal records should provide stable IDs and types, while the KG-facing adapter decides how those IDs become subject URIs.

The paired Turtle sample is not just the JSON statement bundle serialized differently. It materializes metadata statements as descriptor resources, such as `LiteralField` instances with descriptor predicates, and links them to concrete subject instances such as `Nodemap2D`, `ZeissCorrelateConfiguration`, `AramisExporter`, `DigitalImageCorrelationProcess`, and `MicroscopeImage`. That reinforces two boundaries:

- JSON grouping or `related_to` values are not enough to define durable subject identity.
- The KG exporter profile must define descriptor-field policy, subject identity policy, URI minting policy, datatype normalization, and unit normalization.

Source-specific ontology names such as `Aramis`, `ZeissCorrelateConfiguration`, `Nodemap2D`, or `MicroscopeImage` may appear in an exporter profile or source adapter. They should not become CrackPy core record types unless a future CrackPy method genuinely owns that concept.

The diagram sketch with `Prefect Orchestrator`, `Flow`, `CrackPy`, `GraphInsertion`, and `MetadataClass` is useful as an integration picture, but it is more ambitious than the first CrackPy boundary. External orchestrators, object stores, graph insertion clients, and RDF namespaces should remain outside the computational core. The code screenshot that directly constructs RDF triples with a hard-coded namespace and a hash of `str(graph_node)` should be treated as exporter-prototype evidence, not as the target core architecture.

For CrackPy, the likely compact target groups are:

- `Software`: `CrackPy`;
- `SoftwareConfiguration`: package version, Python version, dependency snapshot, repository URL, commit;
- `CrackPyAnalysis`: one analysis execution or result bundle;
- `CrackPyAnalysisConfiguration`: serialized analysis configuration and parameter values;
- `CrackDetectionConfiguration` or `CrackTipEstimateConfiguration`: detection model, side convention, window, offset, thresholds, correction settings, manual/import source handling;
- `FractureAnalysisConfiguration`: material, optimization, integral, path, and coordinate-system settings;
- `CrackTipEstimateResult` or `CrackDetectionResult`: crack-tip x/y, angle or frame, side compatibility label, detection/correction/import method, source estimate link for corrections, corrected estimate fields, correction delta fields, confidence or uncertainty values where available;
- `FractureAnalysisResult`: Williams fit, CJP, SIF, J-integral, T-stress, path and aggregate result metadata;
- `InputRecord` or current `Nodemap`/`InputDataset`: source file identity, hash, input ID, optional sequence index, source-specific stage metadata, force/cycle/load metadata, and minimal input/source provenance.

The main graph can keep this compact by storing one statement per relevant property, while a linked artifact can hold detailed process provenance if needed. The compact KG should be result-centric: its primary job is to say which result was produced from which input by CrackPy with which configuration and method metadata, not to describe every step inside CrackPy.

## Target Use Cases

- Reproduce how a result was produced from nodemap data, crack-tip information, configuration, and analysis methods.
- Let an external orchestrator identify which existing results may be stale after a code or configuration change.
- Query results by CrackPy version, method revision, method ID, literature reference, material, input hash, side/orientation convention, result schema version, or input metadata.
- Export CrackPy result metadata into the existing JSON/RDF shape without forcing CrackPy internals to mirror the external ontology directly.
- Preserve enough method metadata for software citation, method citation, and scientific review.
- Support future command-line, Model Context Protocol (MCP), and workflow-manager execution without relying on implicit `InputData` state.

## Core Requirements

Required compact KG metadata:

- software name and package version;
- repository URL and execution commit, when available;
- stable method ID, display name, category, method revision, implementation fingerprint, and method registry status;
- result schema version;
- execution timestamp and timezone policy;
- input identifiers and optional hashes;
- output identifiers and optional hashes;
- configuration identifier plus parameter or configuration hash;
- selected method and numerical options;
- literature/method reference identifiers;
- coordinate-system and side/orientation convention;
- input metadata such as source-specific stage labels, sequence index, force, cycle, and load where available;
- model provenance for neural detection, including model name, weights source, and hash when available.
- explicit result dependency roles such as `used_crack_tip_estimate` when one result consumes another result.

Detailed metadata that should be linked rather than expanded in the compact KG:

- full normalized configuration JSON;
- full dependency-scope manifests;
- detailed implementation references beyond stable method identity and fingerprints;
- full method-reference records when a method-reference registry can resolve the IDs;
- logs, intermediate arrays, transformation history, and helper-step provenance;
- full process-chain activities that belong in a PROV-O-like artifact.

Non-goals for the compact main model:

- representing every internal helper call as an RDF activity;
- making CrackPy's internal object model conform directly to the external RDF schema;
- storing large arrays or full result tables as graph properties;
- treating every dependency version as a first-class graph node unless a workflow requires it.

## Proposed Internal Metadata Model

CrackPy should own an internal metadata model first, then map it outward. A possible minimal model:

```python
MethodMetadata(
    method_id="crackpy.fracture.williams_fit",
    aliases=(),
    display_name="WilliamsFit",
    category="stress_intensity_factor_evaluation",
    implementation_ref="crackpy.fracture_analysis.optimization:Optimization.optimize_williams_displacements_xy",
    method_revision="1",
    status="active",
    references=["williams_1961", "kuna_williams_coefficients"],
    input_schema="williams_fit_input.v1",
    output_schema="williams_fit_output.v1",
    dependency_scope=[
        "crackpy/fracture_analysis/analysis.py",
        "crackpy/fracture_analysis/optimization.py",
        "crackpy/fracture_analysis/crack_tip.py",
        "crackpy/fracture_analysis/utils.py",
        "crackpy/results/write.py",
    ],
)
```

Execution metadata should be separate from static method metadata:

```python
AnalysisExecutionMetadata(
    run_id="...",
    method_id="crackpy.fracture.williams_fit",
    method_revision="1",
    crackpy_version="1.3.0",
    execution_commit="...",
    implementation_fingerprint="sha256:...",
    input_ids=["nodemap:..."],
    input_hashes={"nodemap": "..."},
    output_ids=["result:..."],
    parameter_hash="...",
    started_at="...",
    completed_at="...",
)
```

The internal model should distinguish:

- static method metadata: stable method identity, display name, category, references, schemas, implementation reference, revision, registry status, aliases, and dependency scope;
- execution metadata: run ID, timestamp, software version, commit, inputs, outputs;
- configuration metadata: parameter values, defaults, validation state, hash;
- result metadata: result ID, schema version, units, output artifacts;
- export metadata: mapping target, exporter version, generated artifact ID.

Input metadata should remain separate from processing provenance. A future `InputRecord` can pair data with attached source/user metadata, stable `input_id`, optional `sequence_index`, hashes, and minimal input/source provenance. Processing history, method identity, configuration snapshots, and result identity belong to execution or result records that consume input records.

Planning decisions for OQ-016 and OQ-017: the stable provenance value is `method_id`, a registry-owned method identity independent of current Python location. A separate `display_name` can stay human-readable, and `implementation_ref` records the module, class, function, or source reference that ran. `method_revision` is the maintainer-declared revision of the method's scientific, numerical, and output meaning. `implementation_fingerprint` is generated from the declared `dependency_scope` and should be checked during build or release validation so method changes cannot drift silently.

Useful split for planning:

- `InputRecord`: data plus attached metadata, stable identity, ordering hints, hashes, and minimal input/source provenance.
- `AnalysisRun`: one execution of a registered method over one or more input records and a configuration snapshot.
- `ResultRecord`: identity, schema, units, hashes, and artifact references for generated outputs.
- `ProvenanceRecord`: compact or detailed traceability envelope linking input records, analysis runs, result records, software, configuration, and export metadata.

Example future object sketch, not an implementation contract:

```python
@dataclass(frozen=True)
class InputRecord:
    """Concrete input data plus attached metadata.

    Fields:
    - input_id: durable record identity; used for matching, provenance links,
      result links, and targeted re-analysis even when files are reordered.
    - data_ref: path, URI, dataset key, or object-store ID; locates large data
      without embedding arrays in metadata.
    - metadata: attached source, user, experiment, simulation,
      coordinate-system, and preprocessing context; keeps CrackPy independent
      from one DIC, FEM, or knowledge-graph schema.
    - sequence_index: optional ordering key; replaces current stage-like
      ordering without pretending to be stable identity.
    - source_label: original external label, such as stage, image name, or
      solver step; preserves round-tripping to source tools.
    - source_hash: optional source artifact hash; detects changed inputs.
    - geometry_profile: declared spatial-domain profile; prevents methods from
      confusing planar, parameterized, 3D surface, and volumetric inputs.
    """

    input_id: str
    data_ref: str
    metadata: Mapping[str, object]
    sequence_index: int | None = None
    source_label: str | None = None
    source_hash: str | None = None
    geometry_profile: str | None = None


@dataclass(frozen=True)
class AnalysisRun:
    """One execution of one registered method.

    Fields:
    - run_id: durable execution identity; anchors logs, results, plots, and
      provenance exports.
    - method_id: stable registry-owned method ID; tells an orchestrator which
      method produced a result even after code moves.
    - method_revision: maintainer-declared method revision; changes when
      scientific meaning, numerical behavior, defaults, schemas, references, or
      result interpretation change.
    - input_ids: consumed input records; makes data dependencies explicit.
    - input_roles: role for each input ID; distinguishes primary field,
      representative crack-tip source, material, configuration, model weights,
      correction result, or post-processing input.
    - configuration_id: identity of the normalized configuration snapshot;
      lets runs share, compare, cache, and export parameter sets.
    - parameter_hash: hash of values and relevant defaults; supports stale
      result detection without deep object comparison.
    - started_at and completed_at: execution timestamps; support audit, ordering,
      failed-run detection, and knowledge-graph queries.
    - crackpy_version and execution_commit: package and source state; supports
      reproducibility and code-level traceability.
    - implementation_fingerprint: generated fingerprint over the declared
      dependency scope; flags unreviewed implementation changes.
    - method_reference_ids: literature or method references; keeps scientific
      method citation attached to the run.
    - model_ids: optional model artifacts; captures neural-network or surrogate
      dependencies that source-code commits alone cannot explain.
    """

    run_id: str
    method_id: str
    method_revision: str
    input_ids: tuple[str, ...]
    input_roles: Mapping[str, str]
    configuration_id: str
    parameter_hash: str
    started_at: str
    crackpy_version: str
    method_reference_ids: tuple[str, ...] = ()
    model_ids: tuple[str, ...] = ()
    completed_at: str | None = None
    execution_commit: str | None = None
    implementation_fingerprint: str | None = None


@dataclass(frozen=True)
class ResultRecord:
    """Generated result and its output artifacts.

    Fields:
    - result_id: durable result identity; lets downstream tools refer to the
      result independently of filenames.
    - run_id: producing execution; links results back to inputs, parameters,
      software, and methods.
    - result_schema_version: result contract version; tells readers whether
      public JSON keys, adapter projections, units, and nested structures are
      interpretable with the expected schema.
    - output_ids: generated artifact references; covers text, JSON, CSV rows,
      plots, RDF exports, and future artifacts.
    - output_roles: role for each output; distinguishes machine-readable data,
      human report, plot, flattened projection, or export artifact.
    - output_hashes: optional artifact hashes; support integrity checks,
      caching, and stale-result detection.
    - units: unit metadata for public values; prevents unsafe interpretation
      after flattening or RDF export.
    """

    result_id: str
    run_id: str
    result_schema_version: str
    output_ids: tuple[str, ...]
    output_roles: Mapping[str, str]
    output_hashes: Mapping[str, str]
    units: Mapping[str, str]


@dataclass(frozen=True)
class ProvenanceRecord:
    """Traceability envelope linking inputs, runs, results, and exports.

    Fields:
    - provenance_id: durable envelope identity; lets compact bundles, detailed
      graphs, and external knowledge graphs reference the same trace.
    - input_records: covered input records; keeps source identity and minimal
      input metadata with the traceability envelope.
    - analysis_runs: covered executions; connects inputs, configurations,
      software, methods, and outputs.
    - result_records: covered generated results; states which outputs the
      provenance facts apply to.
    - export_target: optional target representation; records whether the
      envelope was mapped to RDF/Jena, JSON, JSON-LD, RO-Crate, or another form.
    - exporter_version: exporter implementation version; tracks mapping changes
      separately from numerical analysis changes.
    - detailed_provenance_ref: optional detailed artifact link; keeps the
      compact graph small while preserving access to richer PROV-O-like detail.
    """

    provenance_id: str
    input_records: tuple[InputRecord, ...]
    analysis_runs: tuple[AnalysisRun, ...]
    result_records: tuple[ResultRecord, ...]
    export_target: str | None = None
    exporter_version: str | None = None
    detailed_provenance_ref: str | None = None
```

The important constraint is that links should carry semantic roles. A run should not only say that it used several records; it should say which record was the primary displacement field, representative crack-tip source, material definition, configuration, model weights, correction result, or post-processing input where applicable. This preserves enough meaning to export useful PROV-O later instead of a generic graph full of indistinguishable `used` edges.

## Method Interface

The future interface should make registered methods callable without relying on a live `InputData` pipeline object where possible. Candidate shapes:

Decorator style:

```python
@analysis_step(
    method_id="crackpy.fracture.williams_fit",
    method_revision="1",
    display_name="WilliamsFit",
    category="stress_intensity_factor_evaluation",
    references=["williams_1961", "sanford_2003"],
)
def run_williams_fit(inputs: WilliamsFitInput, config: WilliamsFitConfig) -> WilliamsFitOutput:
    ...
```

Class style:

```python
class WilliamsFit(AnalysisFunction[WilliamsFitInput, WilliamsFitConfig, WilliamsFitOutput]):
    metadata = MethodMetadata(
        method_id="crackpy.fracture.williams_fit",
        method_revision="1",
        display_name="WilliamsFit",
        category="stress_intensity_factor_evaluation",
        references=["williams_1961"],
    )

    def run(self, inputs: WilliamsFitInput, config: WilliamsFitConfig) -> WilliamsFitOutput:
        ...
```

Decorator style is lightweight and can wrap existing functions incrementally. Class style gives a stronger place for metadata, validation, versioning, and orchestration. A mixed approach is possible: a decorator registers simple functions into a method registry, while richer classes implement the same protocol.

The key interface requirement is explicit inputs and outputs. The future `WilliamsFit` interface should not require callers to know the entire [[glossary#Implicit InputData workflow]] if the computational inputs can be expressed as coordinate arrays, displacement arrays, material properties, crack-tip-centered coordinate metadata, and fit configuration.

## Configuration Model

Current configuration is distributed across objects such as `OptimizationProperties`, `IntegralProperties`, `PathProperties`, `CrackDetectionSetup`, `PlotSettings`, `Material`, and deep-learning setup structures. A provenance-capable architecture needs configuration snapshots that are:

- serializable;
- hashable after normalization;
- versioned;
- validated at the interface seam;
- explicit about defaults that were supplied by CrackPy rather than by the caller;
- stable enough for comparison by an orchestrator.

Pydantic is a candidate because it can produce JSON-serializable models and JSON Schema, which could support validation and external documentation. This should remain an evaluated option rather than an immediate dependency requirement. Dataclasses plus explicit serializers may be enough for early versions if dependency minimization is more important.

Configuration should preserve:

- raw caller-provided values;
- normalized values after explicit default resolution;
- value origin for result-affecting values, such as caller-provided, model default, or derived default;
- units and coordinate frame where relevant;
- parameter schema version;
- parameter hash for re-analysis decisions.

OQ-010 resolves the default boundary for this model. Result-affecting defaults and derived defaults belong in the normalized configuration and should be included in `parameter_hash` or `configuration_hash` after resolution. Computational methods should receive concrete values or reject ambiguous missing inputs. Method-selection switches are workflow composition settings, and output, plotting, progress, multiprocessing, or export choices belong to adapters unless they affect numerical results.

## Version and Commit Tracking

Four levels should be separated:

- package version: the installed CrackPy release, currently `crackpy.__version__`;
- execution commit: the repository commit used for a local editable or source checkout, if available;
- method revision: maintainer-declared revision of one registered method's scientific, numerical, and output meaning;
- implementation fingerprint: generated traceability value over the registered method's declared dependency scope.

Possible automation sources:

- `importlib.metadata.version("crackpy")` or `crackpy.__version__` for package version;
- `git rev-parse HEAD` for source-checkout execution commit;
- Git commits, source-range hashes, file hashes, artifact hashes, or packaged build metadata for implementation fingerprints;
- a build-time generated metadata file for installed wheels where `.git` is absent;
- manually maintained `method_revision` when method meaning changes.

Method-level tracking should not rely only on the top-level function body. Important changes may occur in helpers, defaults, config classes, model weights, constants, result-schema writers, or interpolation behavior. Each `MethodMetadata` record therefore needs a declared dependency scope:

```python
dependency_scope=[
    "crackpy/fracture_analysis/analysis.py",
    "crackpy/fracture_analysis/optimization.py",
    "crackpy/fracture_analysis/crack_tip.py",
    "crackpy/fracture_analysis/utils.py",
    "crackpy/structure_elements/material.py",
    "crackpy/results/write.py",
]
```

The scope should start coarse enough to avoid silent drift. A Williams-fit scope that watches only `optimize_williams_displacements_xy()` would miss changes in analytical Williams fields, interpolation helpers, material assumptions, default completion, or result writers. A crack-tip detection scope must include preprocessing and model artifacts, not only the Python class that calls the neural network.

The build or release process should generate a method manifest:

```json
{
  "method_id": "crackpy.fracture.williams_fit",
  "aliases": [],
  "method_revision": "1",
  "status": "active",
  "crackpy_version": "1.3.0",
  "source_commit": "abc123",
  "dependency_scope": [
    "crackpy/fracture_analysis/analysis.py",
    "crackpy/fracture_analysis/optimization.py",
    "crackpy/fracture_analysis/crack_tip.py",
    "crackpy/fracture_analysis/utils.py",
    "crackpy/results/write.py"
  ],
  "implementation_fingerprint": "sha256:...",
  "change_classification": "semantic"
}
```

Build validation should check:

- every registered method has a unique canonical `method_id`;
- aliases resolve one-to-one and do not collide with canonical IDs;
- `status` is one of `active`, `deprecated`, or `removed`;
- every dependency-scope entry resolves or is explicitly marked external;
- generated implementation fingerprints are reproducible;
- model, reference, and configuration IDs referenced by method metadata resolve or are explicitly external;
- a changed implementation fingerprint is classified before release.

Release validation should fail when a registered method's implementation fingerprint changed without either:

- a `method_revision` change, meaning the method's scientific, numerical, or output meaning changed; or
- an explicit non-semantic classification, meaning the implementation changed but the method meaning is intentionally unchanged.

Concrete examples:

| Method | Dependency-scope examples | Revision-changing cases | Fingerprint-only or review cases |
| --- | --- | --- | --- |
| `crackpy.fracture.williams_fit` | `analysis.py`, `optimization.py`, analytical Williams-field helpers in `crack_tip.py`, interpolation helpers, material behavior, result writer keys. | Changed default Williams terms, residual definition, fitting domain defaults, SIF/T-stress sign convention, output units, or exported result meaning. | Moving `_run_williams_optimization`, renaming implementation classes, formatting, or a behavior-preserving cleanup. |
| `crackpy.detection.unet_crack_tip_detection` | detection preprocessing, interpolation, mirroring/right-side convention, `UNet` architecture, `get_model()`, model weights, model source/hash. | Changed pixel-to-mm convention, preprocessing normalization, trained weights, model architecture, crack-tip coordinate convention, or output meaning. | Changing a download URL while the verified model hash is identical, or moving model-loading code without changing behavior. |
| `crackpy.fracture.bueckner_chen_integral` | line-integration code, integration path construction, Bueckner-Chen solver, interpolation helpers, unit conversion, aggregation, result writer keys. | Changed integral formulas, default Williams terms, path construction semantics, outlier aggregation, unit conversion, or public result tags. | Internal spelling cleanup from `buckner` to `bueckner` if formulas and outputs remain identical. |

Default handling needs special care. If `terms=None` in Williams fitting currently resolves to a default list, changing that default affects callers who did not provide terms. That should change the normalized parameter hash and usually the `method_revision`. If a caller explicitly provided the old terms, the parameter hash may remain comparable even though the implementation fingerprint changed.

Dependency-scope drift remains a risk. The validation target is not perfect inference; it is to make unreviewed changes visible. A future check can start by verifying declared paths, comparing generated fingerprints, and requiring change classification. Later checks could add import or call-graph audits to flag method code that starts touching CrackPy modules outside its declared scope.

Method ID migration should be explicit:

```python
# Abbreviated registry sketch; unchanged metadata fields omitted.
MethodMetadata(
    method_id="crackpy.fracture.bueckner_chen_integral",
    aliases=("crackpy.fracture.buckner_chen_integral",),
    status="active",
)
```

Aliases cover one-to-one renames. They are not enough for method splits, where one old ID maps to multiple possible successors:

```python
# Abbreviated registry sketch; unchanged metadata fields omitted.
MethodMetadata(
    method_id="crackpy.detection.crack_tip_detection",
    status="deprecated",
    successors=(
        "crackpy.detection.unet_crack_tip_detection",
        "crackpy.detection.line_intercept_crack_tip_detection",
        "crackpy.detection.manual_crack_tip_import",
    ),
)
```

New results should write only canonical `active` method IDs. Old results using aliases or deprecated IDs should remain readable. `removed` means the historical ID is known for provenance but no current implementation is available for direct recomputation.

For incremental re-analysis, the semantic rule is: a result should be recomputed if its producing `method_id`, `method_revision`, configuration schema version, parameter hash, input hash, model hash, or result schema version no longer matches the current expected value. If only the `implementation_fingerprint` changed, the result should be flagged for review or recomputed under a conservative policy.

## Result Update Logic / Orchestrator Use Case

An external orchestrator should be able to ask:

```text
Find results where:
  method_id == "crackpy.fracture.williams_fit"
  and (
    method_revision != current_method_revision
    or implementation_fingerprint != current_implementation_fingerprint
    or parameter_hash != current_parameter_hash
    or input_hash != current_input_hash
    or model_hash != current_model_hash
    or result_schema_version != current_result_schema_version
  )
```

The result metadata should therefore include:

- stable result ID;
- producing stable method ID;
- method revision;
- execution commit;
- implementation fingerprint;
- dependency-scope identifier or hash;
- input IDs and hashes;
- parameter hash;
- output schema version;
- execution timestamp.

This enables targeted refresh of affected Williams fits, crack-tip detections, SIF evaluations, interpolation steps, or preprocessing steps without re-running unrelated analyses.

The orchestrator should distinguish recomputation triggers from review triggers:

- Recompute when `method_revision`, normalized parameters, inputs, model hashes, configuration schema, or result schema changed.
- Flag for review, or recompute under a conservative policy, when only `implementation_fingerprint` changed.
- Keep `crackpy_version` and `execution_commit` for reproducibility, but do not treat a package-version change alone as proof that every method result is stale.

## Literature and Method References

CrackPy needs method-level references, not only package-level citation. The accepted planning direction for OQ-018 is a hybrid model:

- `CITATION.cff` remains package-level citation metadata for CrackPy as software.
- A small versioned YAML or JSON method-reference registry is the source of truth for method-level references.
- Python method metadata stores only stable method-reference IDs, such as `references=("williams_1961", "sanford_2003")`.
- BibTeX support can be added later as import/export tooling, but should not be the primary internal source of truth.

A reduced registry entry should be enough:

```yaml
williams_1961:
  authors: ["Williams, M. L."]
  title: "The Bending Stress Distribution at the Base of a Stationary Crack"
  year: 1961
  doi: null
  venue: "Journal of Applied Mechanics"
  url: null
  notes: "Williams-series basis for crack-tip field representation."
```

This keeps method entries compact while preserving scientific traceability:

```python
MethodMetadata(
    method_id="crackpy.fracture.williams_fit",
    method_revision="1",
    references=("williams_1961", "sanford_2003"),
    # Other metadata omitted.
)
```

Validation should check that every method-reference ID used by `MethodMetadata.references` exists in the registry and that each registry entry has the required reduced citation fields. A `method_revision` should change when reference changes alter the claimed scientific basis, assumptions, or interpretation of a method. Pure bibliography cleanup, such as correcting capitalization without changing the scientific basis, should not force a revision.

Exporters can map method-reference IDs into RDF/JSON statements, JSON-LD, RO-Crate, or documentation. BibTeX remains useful for paper writing and documentation export, but the YAML/JSON registry should remain the canonical CrackPy source so provenance export does not depend on parsing free-form bibliography syntax.

## Export to Existing RDF/JSON Format

The exporter should be an adapter. It should not define the internal CrackPy model.

Accepted OQ-019 planning boundary: the compact KG export is result-centric. It is the query and re-analysis index for the main graph. The full history of what happened inside CrackPy, including transformations and detailed process-chain steps, belongs in the optional detailed provenance artifact.

Conceptual crosswalk:

| CrackPy internal concept | Compact statement-bundle export | Optional PROV-O-like export |
| --- | --- | --- |
| `InputRecord` | `InputRecord`, `Nodemap`, `InputDataset`, `Mesh`, or source-specific input subject | `prov:Entity` |
| `AnalysisRun` | `run_id` and lightweight method/run facts attached to the result, or an optional `CrackPyAnalysis` summary subject if the KG profile requires it | `prov:Activity` |
| `ResultRecord` | `CrackPyAnalysisResult` as the compact anchor | generated `prov:Entity` |
| `ResultQuantity` | `ResultQuantity`, `FractureAnalysisQuantity`, or method-specific quantity subject linked to a result | generated `prov:Entity` or domain quantity entity |
| `ProvenanceRecord` | linked metadata bundle or export artifact subject | `prov:Bundle` or named graph |
| CrackPy software | `Software` | `prov:SoftwareAgent` |
| Configuration snapshot | `SoftwareConfiguration` or analysis-specific configuration subject | `prov:Entity` or `prov:Plan` |

The compact KG should link a result to:

- input identity and optional input hash;
- CrackPy as software, including CrackPy version;
- CrackPy configuration identity and parameter or configuration hash;
- method identity, method revision, and implementation fingerprint;
- result identity, result schema version, units, output artifact references, and output hashes where practical;
- `run_id` and `provenance_artifact_ref` for resolving the detailed process graph;
- method-reference IDs, not duplicated full citation records;
- model IDs and model or weights hashes when a method depends on trained artifacts.

The compact KG should not contain:

- every internal helper call;
- full normalized configuration JSON when a stable configuration ID and hash are enough for graph queries;
- full dependency-scope manifests;
- logs and intermediate arrays;
- large result tables, fields, or plotting payloads;
- PROV-O activity/entity/agent chains for every CrackPy step.

Accepted OQ-006 planning boundary: the canonical CrackPy result JSON should be a PROV-compatible graph-shaped bundle. It should not mirror the current result tags, and it should not be identical to the compact KG statement-bundle format. Current result names such as `Williams_fit_results`, `SIFs_integral`, `Path_SIFs`, `Bueckner_Chen_integral`, and `Path_Properties` are compatibility aliases for adapters.

The canonical graph bundle should carry typed nodes and explicit edges. A compact conceptual shape is:

```json
{
  "nodes": [
    {
      "id": "software:crackpy",
      "type": "Software",
      "prov_type": "prov:SoftwareAgent",
      "name": "CrackPy",
      "version": "0.x.y"
    },
    {
      "id": "config:crackpy:sha256:...",
      "type": "SoftwareConfiguration",
      "prov_type": "prov:Plan",
      "configuration_hash": "sha256:...",
      "configuration_schema_version": "crackpy.configuration.v1"
    },
    {
      "id": "run:williams-fit:example-001",
      "type": "AnalysisRun",
      "prov_type": "prov:Activity",
      "method_id": "crackpy.fracture.williams_fit",
      "method_revision": "1"
    },
    {
      "id": "result:fracture:example-001",
      "type": "FractureAnalysisResult",
      "prov_type": "prov:Entity",
      "result_schema_version": "crackpy.result_bundle.v1"
    },
    {
      "id": "quantity:sha256:...",
      "type": "ResultQuantity",
      "prov_type": "prov:Entity",
      "symbol": "K_I",
      "description": "Mode I stress intensity factor derived from Williams coefficient a_1.",
      "value": 1.99,
      "unit": "MPa*sqrt(m)",
      "method_id": "crackpy.fracture.williams_fit",
      "derived_from_quantity_ids": ["quantity:williams-a1"],
      "legacy_aliases": ["Williams_fit_results.K_I"]
    }
  ],
  "edges": [
    {
      "type": "wasAssociatedWith",
      "activity": "run:williams-fit:example-001",
      "agent": "software:crackpy",
      "plan": "config:crackpy:sha256:..."
    },
    {
      "type": "used",
      "activity": "run:williams-fit:example-001",
      "entity": "input:nodemap:example-001",
      "role": "primary_displacement_field"
    },
    {
      "type": "used",
      "activity": "run:williams-fit:example-001",
      "entity": "result:crack-tip-estimate:example-001",
      "role": "used_crack_tip_estimate"
    },
    {
      "type": "wasGeneratedBy",
      "entity": "result:fracture:example-001",
      "activity": "run:williams-fit:example-001"
    },
    {
      "type": "hasQuantity",
      "subject": "result:fracture:example-001",
      "object": "quantity:sha256:..."
    }
  ]
}
```

This shape preserves enough structure for a later PROV-O/JSON-LD exporter while still allowing a compact KG translator to flatten selected facts into the existing grouped statement-bundle style.

A physical `CrackTip` in the KG should be treated as a domain object, not as one object per computational method. Different crack-tip detection or correction methods may generate different computational estimates or results about the same physical crack tip. Those estimates belong in result data or detailed provenance unless the KG explicitly introduces an observation model.

Crack-tip estimates are dependencies, not configuration-only values. A `CrackTipEstimateResult` should have its own method metadata and configuration link, because a detector, correction routine, manual import, or future fusion method can depend on settings, model weights, thresholds, windows, coordinate conventions, and source metadata. A downstream `FractureAnalysisResult` should link to the estimate through a role such as `used_crack_tip_estimate` instead of burying the estimate inside `used_configuration`.

For correction-derived crack-tip estimates, the compact result vocabulary should distinguish the absolute corrected estimate from the relative correction delta. The corrected estimate is the primary value consumed by downstream fracture analysis; the delta is audit metadata that explains how far the correction moved the source estimate. A correction result should also link to `source_crack_tip_estimate_id` so provenance can reconstruct the estimate chain without interpreting a bare `dx`/`dy` value as a final crack-tip coordinate.

Mapping sketch to the generic statement-bundle style:

```text
Software:
  crackpy_name
  crackpy_version
  crackpy_repository_url

SoftwareConfiguration:
  crackpy_execution_commit
  crackpy_python_version
  crackpy_dependency_snapshot_hash
  crackpy_result_schema_version

CrackPyAnalysis:
  crackpy_analysis_run_id
  crackpy_method_id
  crackpy_method_revision
  crackpy_implementation_fingerprint
  crackpy_analysis_display_name
  crackpy_analysis_category
  crackpy_analysis_started_at
  crackpy_analysis_completed_at

CrackPyAnalysisConfiguration:
  crackpy_parameter_schema
  crackpy_parameter_hash
  crackpy_configuration_json

CrackTipEstimateResult:
  crackpy_result_id
  cracktip_estimate_id
  physical_crack_tip_id_optional
  source_cracktip_estimate_id_optional
  cracktip_estimate_source
  crackpy_input_id
  crackpy_configuration_id
  crackpy_method_id
  crackpy_method_revision
  cracktip_frame_id
  cracktip_x
  cracktip_y
  cracktip_z_optional
  corrected_cracktip_x_optional
  corrected_cracktip_y_optional
  corrected_cracktip_z_optional
  correction_delta_x_optional
  correction_delta_y_optional
  correction_delta_z_optional
  correction_delta_units_optional
  correction_delta_frame_id_optional
  cracktip_uncertainty_ref_optional

CrackPyAnalysisResult:
  crackpy_result_id
  crackpy_analysis_run_id
  crackpy_input_id
  crackpy_configuration_id
  crackpy_method_id
  crackpy_method_revision
  crackpy_implementation_fingerprint
  crackpy_result_schema_version
  crackpy_parameter_hash
  crackpy_input_hash
  crackpy_result_hash
  crackpy_provenance_artifact_ref
  crackpy_output_schema
  crackpy_output_hash
  crackpy_output_artifact_path

ResultQuantity:
  crackpy_quantity_id
  crackpy_result_id
  crackpy_quantity_symbol
  crackpy_quantity_description
  crackpy_quantity_value
  crackpy_quantity_unit
  crackpy_method_id
  crackpy_derived_from_quantity_ids_optional
  crackpy_statistic_optional
  crackpy_path_index_optional
  crackpy_legacy_aliases_optional
```

For a fracture-analysis result, the same compact result shape should include dependency roles when applicable:

```text
FractureAnalysisResult:
  crackpy_result_id
  crackpy_input_id
  crackpy_configuration_id
  crackpy_used_crack_tip_estimate_result_id
  crackpy_method_id
  crackpy_method_revision
  crackpy_result_schema_version
```

Each exported metadata statement can use the target record shape:

```json
{
  "data_type": "string",
  "description": "Stable ID of the CrackPy method that generated this result",
  "key": "crackpy_method_id",
  "metadata_type": "IdentityMetadata",
  "related_to": "CrackPyAnalysis",
  "source": "Code",
  "unit": "None",
  "value": "crackpy.fracture.williams_fit"
}
```

The exporter should normalize data types, units, and `source` values because the example datapoint mixes capitalization such as `String` / `string` and `User` / `user`.

The compact exporter should also define an explicit grouping and URI policy:

- grouping policy: whether statements are grouped by top-level subject keys, by `related_to`, or by a formal `grouped_by` field expected by the KG importer;
- subject identity policy: whether the compact bundle carries only local IDs such as `result_id` and `input_id`, or also a KG-facing `subject_uri`;
- URI minting policy: whether URIs are generated by the KG importer from subject type plus local ID, or by a CrackPy exporter profile configured with the KG namespace.
- descriptor-field policy: whether scalar facts are exported as plain statements, KG descriptor resources such as `LiteralField`, or both.

The computational core should not hard-code URI namespaces. It should provide stable IDs, subject types, and semantic roles so the exporter can produce conformal KG metadata.

For `SoftwareConfiguration`, URI minting can be content-addressed by a hash of the canonical normalized configuration payload. The hashed payload should include resolved defaults and `configuration_schema_version`; it should exclude volatile fields such as timestamps, output paths, run IDs, and temporary object IDs. The resulting hash can be stored as metadata and used by the KG exporter or importer to mint a URI such as `SoftwareConfiguration/<hash>` according to the configured namespace policy.

## Optional Detailed PROV-O-like Provenance Layer

The compact graph should remain practical. A second optional layer can be more PROV-O-like and exported separately as JSON-LD, Turtle, or another RDF artifact.

The proposed internal split is intentionally compatible with established provenance standards without forcing CrackPy internals to be named after those standards. `InputRecord` and `ResultRecord` map naturally to PROV-O entities, `AnalysisRun` maps to a PROV-O activity, and CrackPy, users, model providers, or external orchestrators map to PROV-O agents. This means CrackPy can later generate a standards-oriented process graph from the same internal records that also feed the compact metadata statement-bundle export.

Candidate mapping:

- `Activity`: one analysis execution, such as crack detection or Williams fit;
- `Entity`: nodemap file, crack-tip estimate, configuration object, result file, plot;
- `Agent`: CrackPy, user, external orchestrator, workflow manager;
- `used`: activity used input data, configuration, and crack-tip estimate where applicable;
- `wasGeneratedBy`: result entity was generated by activity;
- `wasAssociatedWith`: activity was associated with software/user/orchestrator;
- `wasDerivedFrom`: result derived from nodemap and crack-tip data.

Relevant process-chain activities may include:

- input loading and source-metadata binding;
- coordinate transformation, projection, or unwrapping;
- masking, filtering, interpolation, or resampling;
- crack-tip detection and crack-tip correction;
- displacement, strain, or stress evaluation;
- Williams fitting, line-integral evaluation, and optimization;
- result aggregation, schema projection, text/JSON writing, CSV flattening, plotting, or RDF/JSON export.

The detailed artifact should use a declared provenance granularity policy:

- `compact`: result-centric KG metadata only; normally this is not the PROV-O artifact.
- `standard`: major CrackPy analysis stages.
- `detailed`: major stages plus scientifically meaningful substeps.
- `debug`: low-level execution traces for development, not normal KG export.

This detailed layer should be optional because full provenance can become large and hard to query. The compact main graph should link to the detailed artifact through an artifact ID, URI, or file path.

## Candidate Standards and Concepts

Standards and tools worth evaluating:

- [W3C PROV-O](https://www.w3.org/TR/prov-o/) and [PROV-N](https://www.w3.org/TR/prov-n/): suitable vocabulary for optional detailed provenance, but too verbose as the main CrackPy/Jena representation.
- [JSON-LD 1.1](https://www.w3.org/TR/json-ld/): useful export serialization for RDF-compatible metadata while retaining JSON-friendly tooling.
- [CodeMeta](https://codemeta.github.io/jsonld/): useful for package-level software metadata and software citation crosswalks.
- [Citation File Format](https://citation-file-format.github.io/): already present as `CITATION.cff`; should remain package-level citation metadata.
- [RO-Crate](https://www.researchobject.org/ro-crate/technical_overview): useful if CrackPy later packages inputs, outputs, metadata, and provenance artifacts together.
- Parquet, HDF5, netCDF, and Zarr: useful possible export or storage profiles for tabular summaries, large arrays, or chunked scientific fields, but not the planned first canonical scalar-result artifact.
- [RDFLib](https://rdflib.readthedocs.io/en/7.1.1/index.html): mature Python RDF library for exporter prototypes; should be optional to avoid forcing RDF dependencies into the computational core.
- [Pydantic JSON Schema](https://pydantic.dev/docs/validation/2.5/concepts/json_schema): useful for typed internal metadata and configuration schemas if dependency cost is acceptable.
- [FAIR Digital Object Framework](https://fairdigitalobjectframework.org/): useful conceptual reference for persistent identifiers and metadata records, but currently more infrastructure-oriented than CrackPy needs.
- [FORCE11 Software Citation Principles](https://force11.org/info/software-citation-principles-published-2016/): supports the separation between citing CrackPy as software and recording execution provenance for specific results.
- Git line-history tools such as `git blame -L` and `git log -L`: useful as one source for implementation fingerprints, with the limitation that deleted/replaced code, helper dependencies, packaged wheels, and model artifacts need additional handling.

Candidate adoption stance:

- adopt compact internal metadata and result IDs early;
- use versioned graph-shaped JSON as the main future result output for scalar result records and traceability metadata;
- treat legacy text, flattened CSV, plots, Parquet-style tables, HDF5/netCDF/Zarr stores, and RO-Crate bundles as adapters or optional export profiles;
- make the canonical JSON PROV-compatible without requiring it to be literal PROV-O, JSON-LD, or RDF;
- keep literal PROV-O/JSON-LD/RDF export in the optional detailed layer;
- adapt CodeMeta/CFF for package-level citation, not method-level provenance metadata;
- avoid making RDFLib, Pydantic, or RO-Crate hard runtime dependencies in the numerical core until an exporter package or optional extra is designed.

## Open Design Questions

- OQ-015: resolved minimal traceability chain across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots;
- OQ-005: resolved future result files should use a required `result_schema_version`, with JSON as the main scalar-result output and legacy text/CSV/plots as adapters or helper projections;
- OQ-016: resolved stable registry-owned method identity;
- OQ-017: resolved method revision, implementation fingerprint, dependency-scope validation, aliases, successors, and method registry status;
- OQ-018: resolved method-level references use a hybrid model with package-level `CITATION.cff`, a YAML/JSON method-reference registry, Python reference IDs, and optional BibTeX import/export;
- OQ-019: resolved compact KG export is result-centric; detailed provenance is process-centric and uses a declared granularity policy.
- OQ-006: resolved canonical result JSON is a PROV-compatible graph-shaped bundle; current result tags and internal names are legacy adapter aliases.
- OQ-010: resolved result-affecting defaults and derived defaults must be explicit in normalized configuration before method execution.

Related existing questions:

- OQ-002: resolved stage/source metadata, sequence index, input identity, and mapping-policy vocabulary;
- OQ-007: crack-tip correction coordinate semantics;

## Implementation Sketch

Possible phased implementation, after planning approval:

1. Add internal metadata dataclasses or Pydantic models in a new provenance/result-metadata module.
2. Add a `MethodMetadata` registry and method-reference registry, then register a small number of pilot methods, starting with `WilliamsFit`, crack-tip detection, and SIF/integral evaluation.
3. Add `AnalysisExecutionMetadata` creation around analysis execution without changing numerical behavior.
4. Add build validation that generates a method manifest, computes implementation fingerprints, checks aliases/status values, and fails release builds on unclassified dependency-scope changes.
5. Make graph-shaped JSON the main scalar result/provenance output and extend it with package version, result schema version, execution commit, method metadata, parameter hash, input hash, explicit result quantities, semantic edges, and reference IDs.
6. Add a compact exporter from internal metadata records into the observed datapoint JSON shape.
7. Add an optional detailed PROV-O-like exporter behind an optional dependency group.
8. Teach the future orchestrator to compare result metadata with current metadata and mark stale results for targeted re-analysis.

Sketch of internal records:

```python
@dataclass(frozen=True)
class MethodReference:
    """Compact citation record for one scientific or numerical method.

    Fields:
    - key: stable method-reference ID; used by method metadata, analysis
      metadata, exports, and documentation without duplicating citation records.
    - authors, title, year: minimum human-readable citation; supports review
      without requiring a BibTeX parser in the core package.
    - doi, venue, url: optional resolution and publication context; improves
      RDF/export quality while staying lightweight.
    """

    key: str
    authors: tuple[str, ...]
    title: str
    year: int
    doi: str | None = None
    venue: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class MethodMetadata:
    """Static metadata carried by a registered CrackPy method.

    Fields:
    - method_id: stable canonical method ID; lets results survive Python
      refactors that move or rename implementation details.
    - aliases: one-to-one legacy or alternate IDs; keep old provenance records
      resolvable after naming cleanup without writing aliases for new results.
    - display_name: human-facing name; supports reports and documentation
      without becoming the durable provenance identity.
    - category: method family; supports grouping such as crack detection,
      Williams fitting, SIF evaluation, or preprocessing.
    - implementation_ref: current Python implementation location; lets
      maintainers and tooling connect metadata to code.
    - method_revision: maintainer-declared method revision; changes when
      scientific meaning, numerical behavior, schemas, defaults, model
      dependencies, or references change.
    - status: registry lifecycle state; controls whether new results may use
      the ID (`active`), only old results should use it (`deprecated`), or no
      current implementation exists (`removed`).
    - successors: replacement method IDs for one-to-many splits or removals;
      supports migrations that aliases cannot represent safely.
    - references: method-reference IDs; attaches scientific basis to results.
    - input_schema and output_schema: explicit contracts; support validation,
      CLI exposure, orchestration, and result interpretation.
    - dependency_scope: files, source ranges, helper modules, config/default
      providers, model artifacts, or result writers relevant for behavior;
      bounds implementation fingerprinting beyond a single top-level callable.
    """

    method_id: str
    aliases: tuple[str, ...]
    display_name: str
    category: str
    implementation_ref: str
    method_revision: str
    status: Literal["active", "deprecated", "removed"]
    successors: tuple[str, ...]
    references: tuple[str, ...]
    input_schema: str
    output_schema: str
    dependency_scope: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisExecutionMetadata:
    """Execution metadata for one run of a registered method.

    Fields:
    - run_id: durable execution identity; anchors produced results.
    - method_id: registered method ID; enables method-specific stale-result
      checks across Python refactors.
    - method_revision: revision used for the run; allows result compatibility
      checks below the package-version level.
    - crackpy_version and execution_commit: package and source state; support
      reproducibility when the run came from an installed wheel or checkout.
    - implementation_fingerprint: generated dependency-scope fingerprint used
      to flag unreviewed implementation changes.
    - parameter_hash: normalized parameter/default hash; detects configuration
      changes without comparing full objects.
    - input_hashes and output_hashes: data and artifact fingerprints; support
      integrity checks, caching, and re-analysis decisions.
    - started_at and completed_at: run timing; supports audit, ordering, and
      failed or incomplete run detection.
    """

    run_id: str
    method_id: str
    method_revision: str
    crackpy_version: str
    execution_commit: str | None
    implementation_fingerprint: str | None
    parameter_hash: str
    input_hashes: Mapping[str, str]
    output_hashes: Mapping[str, str]
    started_at: str
    completed_at: str | None
```

## Risks and Trade-Offs

- Too much provenance will make the graph noisy and harder to query.
- Too little provenance will not support targeted re-analysis after method changes.
- Implementation fingerprinting is only as good as the declared dependency scope; build validation and review gates are needed to reduce scope drift.
- Git history is not enough for method traceability when behavior depends on helper functions, defaults, model weights, packaged artifacts, or external dependencies.
- Pydantic improves validation and JSON Schema generation but adds a dependency and model-design burden.
- A class-based analysis interface is cleaner but requires more refactoring than decorator-based registration.
- RDF/JSON exporter requirements may distort the internal model if introduced too early.
- Hashing inputs and outputs improves traceability but may be expensive for large nodemaps or result artifacts.
- Backward compatibility with existing text/JSON tags must be handled carefully.
- Choosing JSON as the main scalar result output keeps the first design simple, but large field arrays or dense intermediate data may need optional HDF5, netCDF, Zarr, or similar storage profiles later.
- Copying the KG's resource-per-field `LiteralField` pattern into CrackPy internals would couple the computational core to one RDF export representation.
- Treating `GraphInsertion`, RDF clients, hard-coded namespaces, or Prefect flow nodes as core provenance objects would mix adapter/orchestrator concerns into result records.
- Hashing stringified Python objects for URI construction is unstable; content-addressed IDs should be based on canonical normalized payloads with explicit inclusion and exclusion rules.
- Making external descriptor categories such as `IdentityMetadata`, `StateMetadata`, and `ContextMetadata` mandatory internal classes too early would couple CrackPy to the current KG ontology.
- Locale-sensitive numeric formatting and non-standard RDF datatype names must be normalized by exporters rather than leaking into the canonical result model.

## Next Steps

- Decide whether `C-010` belongs with [[refactor-candidates/001-explicit-analysis-result]] as part of a future result model or remains a separate provenance feature.
- Review and approve or revise [[refactor-candidates/010-provenance-metadata-architecture#First Williams-Fit Slice Specification]] before touching production code.
- Use the Williams-fit first-slice decision in [[decision-log#2026-06-05-williams-fit-is-the-first-result-provenance-implementation-slice]] as the implementation target unless maintainers explicitly reverse it.
- Use the first-slice compact target export profile as the starting point for a future KG adapter specification, including grouping, subject identity, URI minting, descriptor-field, datatype, and unit normalization policy.
- Sketch the first YAML/JSON method-reference registry entries for Williams fitting, Bueckner-Chen, line integrals, and crack-tip detection.
- Keep this note in planning state until the refactor specification is approved.

## Decision State

Not decided. No implementation approved.

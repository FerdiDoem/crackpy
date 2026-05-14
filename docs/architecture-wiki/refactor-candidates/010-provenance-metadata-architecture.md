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
    - schema_version: result contract version; tells readers whether tags,
      columns, units, and JSON keys are interpretable with the expected schema.
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
    schema_version: str
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
- normalized values after default completion;
- units and coordinate frame where relevant;
- parameter schema version;
- parameter hash for re-analysis decisions.

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

The computational core should not hard-code URI namespaces. It should provide stable IDs, subject types, and semantic roles so the exporter can produce conformal KG metadata.

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
- [RDFLib](https://rdflib.readthedocs.io/en/7.1.1/index.html): mature Python RDF library for exporter prototypes; should be optional to avoid forcing RDF dependencies into the computational core.
- [Pydantic JSON Schema](https://pydantic.dev/docs/validation/2.5/concepts/json_schema): useful for typed internal metadata and configuration schemas if dependency cost is acceptable.
- [FAIR Digital Object Framework](https://fairdigitalobjectframework.org/): useful conceptual reference for persistent identifiers and metadata records, but currently more infrastructure-oriented than CrackPy needs.
- [FORCE11 Software Citation Principles](https://force11.org/info/software-citation-principles-published-2016/): supports the separation between citing CrackPy as software and recording execution provenance for specific results.
- Git line-history tools such as `git blame -L` and `git log -L`: useful as one source for implementation fingerprints, with the limitation that deleted/replaced code, helper dependencies, packaged wheels, and model artifacts need additional handling.

Candidate adoption stance:

- adopt compact internal metadata and result IDs early;
- adapt PROV-O concepts only for the optional detailed layer;
- adapt CodeMeta/CFF for package-level citation, not method-level provenance metadata;
- avoid making RDFLib, Pydantic, or RO-Crate hard runtime dependencies in the numerical core until an exporter package or optional extra is designed.

## Open Design Questions

- OQ-015: resolved minimal traceability chain across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots;
- OQ-016: resolved stable registry-owned method identity;
- OQ-017: resolved method revision, implementation fingerprint, dependency-scope validation, aliases, successors, and method registry status;
- OQ-018: resolved method-level references use a hybrid model with package-level `CITATION.cff`, a YAML/JSON method-reference registry, Python reference IDs, and optional BibTeX import/export;
- OQ-019: resolved compact KG export is result-centric; detailed provenance is process-centric and uses a declared granularity policy.

Related existing questions:

- OQ-002: resolved stage/source metadata, sequence index, input identity, and mapping-policy vocabulary;
- OQ-005: result schema or format version;
- OQ-006: public result names versus legacy implementation names;
- OQ-007: crack-tip correction coordinate semantics;
- OQ-010: public defaults versus incidental implementation defaults.

## Implementation Sketch

Possible phased implementation, after planning approval:

1. Add internal metadata dataclasses or Pydantic models in a new provenance/result-metadata module.
2. Add a `MethodMetadata` registry and method-reference registry, then register a small number of pilot methods, starting with `WilliamsFit`, crack-tip detection, and SIF/integral evaluation.
3. Add `AnalysisExecutionMetadata` creation around analysis execution without changing numerical behavior.
4. Add build validation that generates a method manifest, computes implementation fingerprints, checks aliases/status values, and fails release builds on unclassified dependency-scope changes.
5. Extend JSON result output with package version, result schema version, execution commit, method metadata, parameter hash, input hash, and reference IDs.
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

## Next Steps

- Decide whether `C-010` belongs with [[refactor-candidates/001-explicit-analysis-result]] as part of a future result model or remains a separate provenance feature.
- Prototype a metadata record for `WilliamsFit` on paper before touching production code.
- Define a compact target export profile using the generic metadata statement-bundle pattern observed in the provided microscope-DIC datapoint, including grouping, subject identity, and URI minting policy.
- Sketch the first YAML/JSON method-reference registry entries for Williams fitting, Bueckner-Chen, line integrals, and crack-tip detection.
- Keep this note in planning state until the refactor specification is approved.

## Decision State

Not decided. No implementation approved.

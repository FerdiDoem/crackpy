# CrackPy Provenance and Metadata Architecture

Status: proposed
Role: Future architecture candidate for internal provenance metadata, compact knowledge-graph export, and optional detailed process provenance. This is a planning note only; no implementation is approved.

Related: [[refactor-candidates/001-explicit-analysis-result]], [[refactor-candidates/002-input-loading-seam]], [[refactor-candidates/008-result-tag-schema]], [[refactor-candidates/009-sequence-index-vocabulary]], [[open-questions#Question Index]]

## Motivation

CrackPy should eventually emit enough provenance and metadata to make analysis results traceable, selectively refreshable, and exportable into the existing RDF / Apache Jena knowledge graph. The target is not to model every internal call as a semantic process in the main graph. The target is a compact, queryable representation that records which software, configuration, analysis function, inputs, parameters, methods, and outputs produced a result.

The current code already has useful fragments:

- `crackpy.__version__` defines the package version.
- `OutputWriter.write_json()` records `filename`, `evaluation_UTC_datetime`, `experiment_data`, result sections, `Path_Properties`, and `CrackPy_settings`.
- `CrackPy_settings` serializes selected `IntegralProperties`, `OptimizationProperties`, `CrackTipInfo`, and `Material` attributes.
- `InputData` parses nodemap header metadata such as force, cycles, displacement, potential, crack length, and time.
- `CITATION.cff` records package citation metadata.

Observed gaps are also clear:

- result files do not record the CrackPy version, repository commit, analysis-function version, input hash, result schema version, detection model identifier, model hash, dependency snapshot, or function-level method references;
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

CrackPy should target the generic metadata statement-bundle pattern for compact export, not the microscope-DIC-specific subject vocabulary. A separate exporter can map the same internal metadata records into a PROV-O-like process graph.

For CrackPy, the likely compact target groups are:

- `Software`: `CrackPy`;
- `SoftwareConfiguration`: package version, Python version, dependency snapshot, repository URL, commit;
- `CrackPyAnalysis`: one analysis execution or result bundle;
- `CrackPyAnalysisConfiguration`: serialized analysis configuration and parameter values;
- `CrackDetectionConfiguration`: detection model, side convention, window, offset, thresholds, correction settings;
- `FractureAnalysisConfiguration`: material, optimization, integral, path, and coordinate-system settings;
- `CrackDetectionResult`: crack-tip x/y, angle, side, detection/correction method, confidence or error values where available;
- `FractureAnalysisResult`: Williams fit, CJP, SIF, J-integral, T-stress, path and aggregate result metadata;
- `InputRecord` or current `Nodemap`/`InputDataset`: source file identity, hash, input ID, optional sequence index, source-specific stage metadata, force/cycle/load metadata, and minimal input/source provenance.

The main graph can keep this compact by storing one statement per relevant property, while a linked artifact can hold detailed process provenance if needed.

## Target Use Cases

- Reproduce how a result was produced from nodemap data, crack-tip information, configuration, and analysis methods.
- Let an external orchestrator identify which existing results may be stale after a code or configuration change.
- Query results by CrackPy version, function version, method, literature reference, material, input hash, side/orientation convention, result schema version, or input metadata.
- Export CrackPy result metadata into the existing JSON/RDF shape without forcing CrackPy internals to mirror the external ontology directly.
- Preserve enough method metadata for software citation, method citation, and scientific review.
- Support future command-line, Model Context Protocol (MCP), and workflow-manager execution without relying on implicit `InputData` state.

## Core Requirements

Required compact metadata:

- software name and package version;
- repository URL and execution commit, when available;
- analysis function identifier, category, function metadata version, and last function-relevant commit;
- result schema version;
- execution timestamp and timezone policy;
- input identifiers and optional hashes;
- output identifiers and optional hashes;
- explicit configuration object and parameter snapshot;
- selected method and numerical options;
- literature/method reference identifiers;
- coordinate-system and side/orientation convention;
- input metadata such as source-specific stage labels, sequence index, force, cycle, and load where available;
- model provenance for neural detection, including model name, weights source, and hash when available.

Non-goals for the compact main model:

- representing every internal helper call as an RDF activity;
- making CrackPy's internal object model conform directly to the external RDF schema;
- storing large arrays or full result tables as graph properties;
- treating every dependency version as a first-class graph node unless a workflow requires it.

## Proposed Internal Metadata Model

CrackPy should own an internal metadata model first, then map it outward. A possible minimal model:

```python
AnalysisMetadata(
    name="WilliamsFit",
    category="stress_intensity_factor_evaluation",
    implementation_ref="crackpy.fracture_analysis.optimization:Optimization.optimize_williams_displacements_xy",
    metadata_version="1",
    references=["williams_1961", "kuna_williams_coefficients"],
    input_schema="williams_fit_input.v1",
    output_schema="williams_fit_output.v1",
)
```

Execution metadata should be separate from static function metadata:

```python
AnalysisExecutionMetadata(
    run_id="...",
    function_name="WilliamsFit",
    function_metadata_version="1",
    crackpy_version="1.3.0",
    execution_commit="...",
    function_last_modified_commit="...",
    input_ids=["nodemap:..."],
    input_hashes={"nodemap": "..."},
    output_ids=["result:..."],
    parameter_hash="...",
    started_at="...",
    completed_at="...",
)
```

The internal model should distinguish:

- static function metadata: identity, category, references, schemas, owner module;
- execution metadata: run ID, timestamp, software version, commit, inputs, outputs;
- configuration metadata: parameter values, defaults, validation state, hash;
- result metadata: result ID, schema version, units, output artifacts;
- export metadata: mapping target, exporter version, generated artifact ID.

Input metadata should remain separate from processing provenance. A future `InputRecord` can pair data with attached source/user metadata, stable `input_id`, optional `sequence_index`, hashes, and minimal input/source provenance. Processing history, analysis-function identity, configuration snapshots, and result identity belong to execution or result records that consume input records.

Useful split for planning:

- `InputRecord`: data plus attached metadata, stable identity, ordering hints, hashes, and minimal input/source provenance.
- `AnalysisRun`: one execution of a registered analysis function over one or more input records and a configuration snapshot.
- `ResultRecord`: identity, schema, units, hashes, and artifact references for generated outputs.
- `ProvenanceRecord`: compact or detailed traceability envelope linking input records, analysis runs, result records, software, configuration, and export metadata.

Example future object sketch, not an implementation contract:

```python
@dataclass(frozen=True)
class InputRecord:
    """Concrete input data plus attached metadata.

    `input_id` is the durable identity for matching, result links, and
    re-analysis. `data_ref` locates the data without embedding large arrays.
    `metadata` keeps source, user, experiment, simulation, coordinate-system,
    and preprocessing context schema-neutral. `sequence_index` orders inputs
    without replacing identity. `source_label` preserves external labels such
    as a legacy stage or solver step. `source_hash` detects changed inputs.
    `geometry_profile` declares spatial assumptions for method compatibility.
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
    """One execution of one registered analysis function.

    The run ties function identity and metadata version to consumed inputs,
    explicit input roles, configuration identity, parameter hash, timestamps,
    CrackPy version, execution commit, method references, and optional model
    identities. This is the process anchor for targeted re-analysis and for
    later PROV-O activity export.
    """

    run_id: str
    function_name: str
    function_metadata_version: str
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


@dataclass(frozen=True)
class ResultRecord:
    """Generated result and its output artifacts.

    `result_id` gives downstream tools a stable result handle independent of
    filenames. `run_id` links the result to the producing execution.
    `schema_version`, output roles, hashes, and units make JSON, text, CSV,
    plot, and RDF exports interpretable and stale-result checks possible.
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

    The envelope can drive a compact metadata statement-bundle export while
    optionally pointing to a detailed PROV-O-like artifact. Export target and
    exporter version are tracked because export behavior can change
    independently from numerical analysis behavior.
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

## Analysis Function Interface

The future interface should make analysis functions callable without relying on a live `InputData` pipeline object where possible. Candidate shapes:

Decorator style:

```python
@analysis_step(
    name="WilliamsFit",
    category="stress_intensity_factor_evaluation",
    references=["williams_1961", "sanford_2003"],
)
def run_williams_fit(inputs: WilliamsFitInput, config: WilliamsFitConfig) -> WilliamsFitOutput:
    ...
```

Class style:

```python
class WilliamsFit(AnalysisFunction[WilliamsFitInput, WilliamsFitConfig, WilliamsFitOutput]):
    metadata = AnalysisMetadata(
        name="WilliamsFit",
        category="stress_intensity_factor_evaluation",
        references=["williams_1961"],
    )

    def run(self, inputs: WilliamsFitInput, config: WilliamsFitConfig) -> WilliamsFitOutput:
        ...
```

Decorator style is lightweight and can wrap existing functions incrementally. Class style gives a stronger place for metadata, validation, versioning, and orchestration. A mixed approach is possible: a decorator registers simple functions into an `AnalysisRegistry`, while richer classes implement the same protocol.

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

Three levels should be separated:

- package version: the installed CrackPy release, currently `crackpy.__version__`;
- execution commit: the repository commit used for a local editable or source checkout, if available;
- function-relevant commit: the latest commit that changed the registered analysis function or its declared dependency set.

Possible automation sources:

- `importlib.metadata.version("crackpy")` or `crackpy.__version__` for package version;
- `git rev-parse HEAD` for source-checkout execution commit;
- `git blame -L` or `git log -L` over registered source ranges for function-level changes;
- a build-time generated metadata file for installed wheels where `.git` is absent;
- manually maintained `metadata_version` when a semantic method change occurs without easy source-range detection.

Function-level tracking should not rely only on the function body. Important changes may occur in helpers, defaults, config classes, model weights, or constants. Each `AnalysisMetadata` record therefore needs a declared dependency scope:

```python
dependency_scope=[
    "crackpy/fracture_analysis/optimization.py",
    "crackpy/fracture_analysis/crack_tip.py",
    "crackpy/structure_elements/material.py",
]
```

For incremental re-analysis, the conservative rule is: a result may be stale if its producing function name, function metadata version, dependency-scope commit, configuration schema version, parameter hash, input hash, model hash, or result schema version no longer matches the current expected value.

## Result Update Logic / Orchestrator Use Case

An external orchestrator should be able to ask:

```text
Find results where:
  function_name == "WilliamsFit"
  and (
    function_last_modified_commit != current_function_last_modified_commit
    or function_metadata_version != current_function_metadata_version
    or parameter_hash != current_parameter_hash
    or input_hash != current_input_hash
    or result_schema_version != current_result_schema_version
  )
```

The result metadata should therefore include:

- stable result ID;
- producing analysis function;
- static metadata version;
- execution commit;
- last function-relevant commit;
- dependency-scope identifier or hash;
- input IDs and hashes;
- parameter hash;
- output schema version;
- execution timestamp.

This enables targeted refresh of affected Williams fits, crack-tip detections, SIF evaluations, interpolation steps, or preprocessing steps without re-running unrelated analyses.

## Literature and Method References

CrackPy needs method-level references, not only package-level citation. A reduced reference record should be enough:

```yaml
williams_1961:
  authors: ["Williams, M. L."]
  title: "The Bending Stress Distribution at the Base of a Stationary Crack"
  year: 1961
  doi: null
  venue: "Journal of Applied Mechanics"
```

Possible storage locations:

- Python metadata constants: easiest to package, but harder for documentation tooling;
- YAML or JSON registry: easy to validate and export;
- BibTeX-compatible file: useful for papers, but less direct for Python metadata;
- `CITATION.cff`: good for software citation, not sufficient for method-level references.

Recommendation for planning: use a small YAML/JSON method-reference registry as the internal source, and keep `CITATION.cff` for package citation. Exporters can map method reference IDs into RDF/JSON statements and documentation.

## Export to Existing RDF/JSON Format

The exporter should be an adapter. It should not define the internal CrackPy model.

Conceptual crosswalk:

| CrackPy internal concept | Compact statement-bundle export | Optional PROV-O-like export |
| --- | --- | --- |
| `InputRecord` | `InputRecord`, `Nodemap`, `InputDataset`, `Mesh`, or source-specific input subject | `prov:Entity` |
| `AnalysisRun` | `CrackPyAnalysis` | `prov:Activity` |
| `ResultRecord` | `CrackPyAnalysisResult` | generated `prov:Entity` |
| `ProvenanceRecord` | linked metadata bundle or export artifact subject | `prov:Bundle` or named graph |
| CrackPy software | `Software` | `prov:SoftwareAgent` |
| Configuration snapshot | `SoftwareConfiguration` or analysis-specific configuration subject | `prov:Entity` or `prov:Plan` |

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
  crackpy_analysis_function
  crackpy_analysis_category
  crackpy_analysis_started_at
  crackpy_analysis_completed_at

CrackPyAnalysisConfiguration:
  crackpy_parameter_schema
  crackpy_parameter_hash
  crackpy_configuration_json

CrackPyAnalysisResult:
  crackpy_result_id
  crackpy_output_schema
  crackpy_output_hash
  crackpy_output_artifact_path
```

Each exported metadata statement can use the target record shape:

```json
{
  "data_type": "string",
  "description": "Name of the CrackPy analysis function that generated this result",
  "key": "crackpy_analysis_function",
  "metadata_type": "IdentityMetadata",
  "related_to": "CrackPyAnalysis",
  "source": "Code",
  "unit": "None",
  "value": "WilliamsFit"
}
```

The exporter should normalize data types, units, and `source` values because the example datapoint mixes capitalization such as `String` / `string` and `User` / `user`.

## Optional Detailed PROV-O-like Provenance Layer

The compact graph should remain practical. A second optional layer can be more PROV-O-like and exported separately as JSON-LD, Turtle, or another RDF artifact.

The proposed internal split is intentionally compatible with established provenance standards without forcing CrackPy internals to be named after those standards. `InputRecord` and `ResultRecord` map naturally to PROV-O entities, `AnalysisRun` maps to a PROV-O activity, and CrackPy, users, model providers, or external orchestrators map to PROV-O agents. This means CrackPy can later generate a standards-oriented process graph from the same internal records that also feed the compact metadata statement-bundle export.

Candidate mapping:

- `Activity`: one analysis execution, such as crack detection or Williams fit;
- `Entity`: nodemap file, crack-tip info, configuration object, result file, plot;
- `Agent`: CrackPy, user, external orchestrator, workflow manager;
- `used`: activity used input data and configuration;
- `wasGeneratedBy`: result entity was generated by activity;
- `wasAssociatedWith`: activity was associated with software/user/orchestrator;
- `wasDerivedFrom`: result derived from nodemap and crack-tip data.

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
- Git line-history tools such as `git blame -L` and `git log -L`: useful for function-level change tracking, with the limitation that deleted/replaced code and helper dependencies need additional handling.

Candidate adoption stance:

- adopt compact internal metadata and result IDs early;
- adapt PROV-O concepts only for the optional detailed layer;
- adapt CodeMeta/CFF for package-level citation, not function-level method metadata;
- avoid making RDFLib, Pydantic, or RO-Crate hard runtime dependencies in the numerical core until an exporter package or optional extra is designed.

## Open Design Questions

- OQ-015: resolved minimal traceability chain across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots;
- OQ-016: How should CrackPy define an analysis-function identity and function-level version?
- OQ-017: Should function-relevant commits be computed automatically from Git history, declared manually, or generated at build time?
- OQ-018: Should method references live in Python metadata, YAML/JSON, BibTeX, or a hybrid registry?
- OQ-019: Which parts of provenance belong in the compact knowledge graph, and which belong only in an optional detailed artifact?

Related existing questions:

- OQ-002: resolved stage/source metadata, sequence index, input identity, and mapping-policy vocabulary;
- OQ-005: result schema or format version;
- OQ-006: public result names versus legacy implementation names;
- OQ-007: crack-tip correction coordinate semantics;
- OQ-010: public defaults versus incidental implementation defaults.

## Implementation Sketch

Possible phased implementation, after planning approval:

1. Add internal metadata dataclasses or Pydantic models in a new provenance/result-metadata module.
2. Add an `AnalysisMetadata` registry and register a small number of pilot functions, starting with `WilliamsFit`, crack-tip detection, and SIF/integral evaluation.
3. Add `AnalysisExecutionMetadata` creation around analysis execution without changing numerical behavior.
4. Extend JSON result output with package version, result schema version, execution commit, function metadata, parameter hash, input hash, and reference IDs.
5. Add a compact exporter from internal metadata records into the observed datapoint JSON shape.
6. Add an optional detailed PROV-O-like exporter behind an optional dependency group.
7. Teach the future orchestrator to compare result metadata with current metadata and mark stale results for targeted re-analysis.

Sketch of internal records:

```python
@dataclass(frozen=True)
class MethodReference:
    """Compact citation record for one scientific or numerical method.

    `key` is the stable identifier used by analysis metadata and exports.
    The remaining fields keep method references machine-readable without
    overloading package-level `CITATION.cff`.
    """

    key: str
    authors: tuple[str, ...]
    title: str
    year: int
    doi: str | None = None
    venue: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class AnalysisMetadata:
    """Static metadata carried by a registered analysis function.

    This describes what the function is, where it is implemented, which
    method references and schemas define it, and which source ranges or helper
    modules belong to its change-tracking scope. It is separate from any one
    execution.
    """

    name: str
    category: str
    implementation_ref: str
    metadata_version: str
    references: tuple[str, ...]
    input_schema: str
    output_schema: str
    dependency_scope: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisExecutionMetadata:
    """Execution metadata for one run of a registered analysis function.

    The record connects function identity, package and commit state,
    parameters, input/output hashes, and timestamps so an orchestrator can
    audit the run and decide whether existing results need re-analysis.
    """

    run_id: str
    function_name: str
    crackpy_version: str
    execution_commit: str | None
    function_last_modified_commit: str | None
    parameter_hash: str
    input_hashes: Mapping[str, str]
    output_hashes: Mapping[str, str]
    started_at: str
    completed_at: str | None
```

## Risks and Trade-Offs

- Too much provenance will make the graph noisy and harder to query.
- Too little provenance will not support targeted re-analysis after method changes.
- Function-level Git tracking is fragile when behavior depends on helper functions, defaults, model weights, or external dependencies.
- Pydantic improves validation and JSON Schema generation but adds a dependency and model-design burden.
- A class-based analysis interface is cleaner but requires more refactoring than decorator-based registration.
- RDF/JSON exporter requirements may distort the internal model if introduced too early.
- Hashing inputs and outputs improves traceability but may be expensive for large nodemaps or result artifacts.
- Backward compatibility with existing text/JSON tags must be handled carefully.

## Next Steps

- Decide whether `C-010` belongs with [[refactor-candidates/001-explicit-analysis-result]] as part of a future result model or remains a separate provenance feature.
- Resolve OQ-016 through OQ-019 enough to define the remaining metadata scope.
- Prototype a metadata record for `WilliamsFit` on paper before touching production code.
- Define a compact target export profile using the generic metadata statement-bundle pattern observed in the provided microscope-DIC datapoint.
- Decide whether method references should start as YAML/JSON registry entries.
- Keep this note in planning state until the refactor specification is approved.

## Decision State

Not decided. No implementation approved.

# Goal-Driven Refactoring Plan

Status: future architecture plan, not approved implementation
Role: Turn the current refactor candidates into goal-sized development targets with concrete Definition Of Done checks.

Related: [[refactor-roadmap]], [[refactor-notes]], [[refactor-candidates/index]], [[decision-log]], [[coupling-map]]

This plan is the working basis for future goal-driven Codex development. It does not approve production refactoring by itself. Each candidate still needs an explicit goal, a field-level specification for new records or adapters, and user approval before package code is changed.

## Plan Rules

- Keep observed reality, shared language, and future architecture separate.
- Use the existing candidate IDs `C-001` through `C-011` as stable goal references.
- Prefer deep Modules: small explicit Interfaces with substantial behavior behind them.
- Put each new seam where behavior really varies. One adapter means a hypothetical seam; two adapters make it real.
- Keep legacy behavior working through compatibility facades or adapters until a migration is approved.
- Treat docstrings, field descriptions, and decision-focused inline comments as part of the Interface.
- Run a limited-context documentation review for new or reshaped classes and functions before a candidate is called done.
- Do not extract private helpers only for DRY. Keep local duplication when it makes a method slice easier to inspect and test.
- Use object-oriented coding where the object owns lifecycle, invariants, state, adapter role, or domain meaning.

## Suggested Goal Order

| Order | Candidate | Why this order |
| --- | --- | --- |
| 1 | C-010: Provenance Metadata Architecture | The Williams-fit provenance slice already exists; audit it before extending the pattern. |
| 2 | C-011: Method Module Contract | Williams-fit and CJP-fit now prove enough repeated method-module shape to define a contract before copying it to integral methods. |
| 3 | C-001: Explicit Analysis Result | Result shape is the current high-coupling seam between analysis and outputs. |
| 4 | C-008: Result Tag Schema | Legacy writers/readers need a schema and alias map before broader output migration. |
| 5 | C-002: Input Loading Seam | Stable input identity is needed for provenance, mapping policy, and non-file inputs. |
| 6 | C-009: Sequence Index Vocabulary | Stage-to-input mapping should become explicit after input identity exists. |
| 7 | C-005: Side Orientation Module | Crack-tip frames need input identity and result/provenance roles to land cleanly. |
| 8 | C-007: Defaults And Options Cleanup | Normalized configuration should precede method registry, hashing, and runners. |
| 9 | C-003: Self-Contained Williams Fit Interface | The computational method seam should build on explicit configuration and crack-tip frame vocabulary. |
| 10 | C-006: Model Provider Seam | Detection methods need explicit model metadata before runner/facade migration. |
| 11 | C-004: Separate Orchestration From Adapters | Workflow runners compose the earlier result, input, configuration, orientation, and provider seams. |

## Global Definition Of Done

Every candidate-specific DoD extends these checks:

- The candidate has a short implementation spec before code changes, including new fields, parameters, invariants, units, side effects, and error modes.
- New public classes, dataclasses, Pydantic models, protocol-like Interfaces, and non-trivial functions have expressive docstrings.
- Pydantic fields use `Field(description=...)`; dataclasses without field metadata document field meaning in the class docstring or nearby comments.
- Inline comments record non-obvious decisions only, such as dependency direction, compatibility behavior, validation rules, naming choices, or scientific assumptions.
- Tests cover the new Interface rather than private implementation details.
- Existing legacy scripts, output files, and public import paths either keep working or have an approved compatibility facade.
- The relevant architecture-wiki note is updated in the same pass when code reality changes.
- `python docs\architecture-wiki\check_wiki.py` passes.
- Targeted tests for the touched package area pass. A full `pytest crackpy/tests` run is expected before broad or cross-package changes are considered complete.

## C-001: Explicit Analysis Result

Candidate note: [[refactor-candidates/001-explicit-analysis-result]]

### Goal

Turn `FractureAnalysis` from a broad mutable post-run result bag into a Module that returns or exposes an explicit analysis result Interface. `FractureAnalysis` may stay as a compatibility facade during migration, but new outputs and tests should depend on result records instead of dozens of mutable attributes.

### Main Files

- `crackpy/fracture_analysis/analysis.py`
- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/line_integration.py`
- `crackpy/results/result_data.py`
- `crackpy/results/write.py`
- `crackpy/results/plot.py`
- `crackpy/tests/test_fracture_analysis/*`

### Current Friction

The current Interface after `FractureAnalysis.run()` is nearly as complex as the implementation. Callers must know which mutable attributes exist after which methods ran, which attributes are absent when a method family is skipped, and which fields output modules inspect directly.

Deletion test: deleting `FractureAnalysis` result attributes today would push the same complexity into writers, plots, tests, and scripts. That means a deeper explicit result Module can earn its Interface.

Current implementation note: the first `crackpy.results.analysis_result` slice can collect named method envelopes and write their standard frontend/backend artifacts without constructing `FractureAnalysis`.
It is an additive artifact handoff, not a replacement for the broad post-run analysis attribute Interface.

### Target Shape

- A structured analysis result record or envelope collects method results, integral summaries, path metadata, artifact references, and compatibility aliases.
- `FractureAnalysis` delegates method execution and assembles the result record.
- Legacy result attributes remain readable for compatibility until an approved migration removes them.
- Output adapters consume the result Interface rather than a live `FractureAnalysis` object.

### Definition Of Done

- `FractureAnalysis` has a documented lifecycle contract: required inputs, required pre-run state, what `run()` populates, and which attributes are compatibility-only.
- A minimal test fixture can construct an analysis result without loading a full nodemap or running plotting code.
- Output artifact tests can exercise method-envelope artifact writing from an explicit analysis result fixture rather than a full `FractureAnalysis` instance.
- Output writer and plotter migration remain broader C-001 work because legacy text/current JSON and plots still inspect `FractureAnalysis` directly.
- Missing or skipped method families produce explicit absence or explicit errors, not accidental `AttributeError` behavior.
- Current text, current JSON, CSV, and plot behavior remain covered by compatibility tests.
- Existing Williams-fit provenance records still serialize the same semantic fields after the result Interface is introduced.

## C-002: Input Loading Seam

Candidate note: [[refactor-candidates/002-input-loading-seam]]

### Goal

Separate input loading and metadata extraction from the mutable numerical data carrier. The future Module should make stable input identity, source metadata, hashes, and optional ordering explicit without forcing all sources into the current nodemap file lifecycle.

### Main Files

- `crackpy/input/input_data.py`
- `crackpy/input/crack_tip_info.py`
- `crackpy/structure_elements/data_files.py`
- `crackpy/structure_elements/material.py`
- `crackpy/tests/test_fracture_analysis/test_data_processing.py`
- `crackpy/tests/test_crack_detection/test_data/*`

### Current Friction

`InputData` mixes file reading, metadata parsing, mutable field storage, mechanics helpers, transforms, masks, validation, and VTK export. Its Interface includes hidden call order: load, compute strains or stresses, transform coordinates, then analyze.

### Target Shape

- An `InputRecord` planning shape carries `input_id`, source label, optional `sequence_index`, source metadata, source reference, and optional source hash.
- Input adapters translate nodemap files, manual in-memory arrays, FEM-like records, and future external workflow inputs into the same loaded input Interface.
- `InputData` remains a compatibility carrier while loaders and future runners depend on the narrower input Interface.

### Definition Of Done

- Constructor modes are documented and tested: nodemap file load, header-only load, and manual/in-memory data.
- Methods that read files, mutate arrays, or require pre-existing fields say so in docstrings.
- `require_fields()` and shape validation have tests for missing fields, unequal array lengths, and optional fields.
- `transform_data()` tests prove which fields mutate when stresses exist and that missing optional stress fields do not crash.
- A future input adapter can provide data without pretending to be a `Nodemap` file.
- Input identity fields are available to provenance/result code without parsing `stage` from filenames.
- Existing nodemap parsing and metadata behavior remain covered by legacy tests.

## C-003: Self-Contained Williams Fit Interface

Candidate note: [[refactor-candidates/003-self-contained-williams-fit-interface]]

### Goal

Make Williams fitting a deep method Module with an explicit computational Interface. The Interface should accept resolved arrays, material data, crack-tip frame information, and fitting parameters, then return a typed Williams result without requiring callers to understand `Optimization` constructor side effects.

### Main Files

- `crackpy/fracture_analysis/methods/williams_fit/*`
- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/analysis.py`
- `crackpy/crack_detection/correction.py`
- `crackpy/tests/test_fracture_analysis/test_williams_method_module.py`
- `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`

### Current Friction

The current Williams method module is the cleanest vertical slice, but the runner still depends on the existing optimizer object and transformed `InputData` assumptions. Crack-tip correction still has its own bridge into Williams optimization and mostly returns relative deltas.

### Target Shape

- A computational Williams fit Interface receives explicit numerical inputs and resolved `WilliamsFitParameters`.
- An `InputData` adapter prepares that Interface from current mutable data.
- Correction code uses the same Williams fit Interface and returns a corrected crack-tip estimate plus correction delta.
- The method module owns Williams-specific parameter records, result records, source adapter, spec loading, and method-local provenance wrapper.

### Definition Of Done

- The public Williams runner can be tested from explicit arrays and material values without constructing a full `FractureAnalysis`.
- Existing `Optimization.optimize_williams_displacements_xy()` behavior is either delegated behind the runner or kept only as a compatibility implementation detail.
- Williams result units, coordinate-frame assumptions, selected terms, fit radii, and error metrics are documented at the Interface.
- Correction methods expose absolute corrected crack-tip estimates and audit deltas in tests, with legacy delta outputs preserved where required.
- Optimization failures propagate as clear exceptions at the method seam.
- Williams provenance source construction uses typed result data, not broad `FractureAnalysis` attribute probing, for the approved slice.

## C-004: Separate Orchestration From Adapters

Candidate note: [[refactor-candidates/004-separate-orchestration-from-adapters]]

### Goal

Split domain workflow runners from adapter policy. CrackPy should own scientific sequencing, while filesystem layout, text/current JSON writing, plotting, progress reporting, multiprocessing, model download/cache policy, VTK export, and KG/RDF export live behind adapters or compatibility facades.

### Main Files

- `crackpy/fracture_analysis/pipeline.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/results/write.py`
- `crackpy/results/plot.py`
- `crackpy/crack_detection/model.py`
- `crackpy/__init__.py`
- `crackpy/results/__init__.py`
- `crackpy/tests/test_crack_detection/test_pipeline/test_pipeline.py`

### Current Friction

The batch pipelines combine input selection, file reads, transformations, method execution, output writing, plotting, progress, directory creation, and multiprocessing. Reusing CrackPy from a CLI, MCP tool, notebook workflow, or graph orchestrator currently means inheriting these adapter policies.

### Target Shape

- Domain workflow runners return structured records and artifacts with minimal side effects.
- Compatibility facades preserve current pipeline constructors, scripts, folder layout, progress, and legacy outputs.
- Adapters satisfy explicit Interfaces for output writing, plotting, progress, execution policy, model provision, and optional export.
- Import-time side effects are audited and either moved behind explicit initialization/adapters or documented as compatibility behavior.

### Definition Of Done

- Mapping logic such as max-force stage selection, representative input mapping, and integral property selection is testable without launching worker processes or writing files.
- A runner test can execute one fracture-analysis or crack-detection workflow with null output/progress adapters.
- Compatibility facade tests prove current script-level behavior remains available.
- Plotting, progress, multiprocessing, and output-folder choices are no longer required knowledge for the domain runner Interface.
- Importing lightweight CrackPy modules for result/provenance records does not trigger plotting backend changes, network access, or broad pipeline initialization.
- Documentation clearly labels domain sequencing versus adapter policy.

## C-005: Side Orientation Module

Candidate note: [[refactor-candidates/005-side-orientation-module]]

### Goal

Replace repeated `left`/`right` orientation logic with a `CrackTipFrame` Module and compatibility adapters. The internal Interface should describe crack-tip identity, origin, local axes, geometry profile, detector convention, mirroring policy, and output labels without making `side` the mechanics model.

### Main Files

- `crackpy/input/crack_tip_info.py`
- `crackpy/crack_detection/detection.py`
- `crackpy/crack_detection/line_intercept.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/crack_detection/correction.py`
- `crackpy/fracture_analysis/methods/williams_fit/source_adapter.py`
- `crackpy/results/result_data.py`
- `crackpy/results/plot.py`

### Current Friction

Orientation is encoded through strings, sign flips, mirrored arrays, signed windows, output naming, and plot conventions. `side` bundles specimen geometry, crack-tip identity, crack-growth direction, detector training convention, mirroring policy, pipeline grouping, and result naming.

### Target Shape

- `CrackTipFrame` is the internal crack-tip orientation Interface.
- `side` and `left_or_right` remain compatibility labels at file, legacy call, plot, and result naming seams.
- Detector mirroring is an adapter policy over the detector's trained right-side convention.
- Method applicability declares geometry profile, such as `surface_planar`, without overclaiming 3D support.

### Definition Of Done

- Current `left` and `right` inputs round-trip through a compatibility adapter without changing legacy output labels.
- Detection, correction, fracture analysis, plotting, and provenance can reference the same frame identity for one workflow slice.
- Tests cover orientation conversion, mirroring policy, angle units, and compatibility labels.
- The Interface makes geometry profile explicit and documents that current methods remain `surface_planar` unless a method declares more.
- No new internal method accepts raw `side` when it needs orientation semantics; raw `side` is translated at the adapter seam.
- Existing crack-tip handoff files remain readable.

## C-006: Model Provider Seam

Candidate note: [[refactor-candidates/006-model-provider-seam]]

### Goal

Separate neural model construction and weights provision from detection algorithms. Detection should depend on a model provider Interface, while local cache, Zenodo download, test doubles, device placement, and future workflow-managed models live behind adapters.

### Main Files

- `crackpy/crack_detection/model.py`
- `crackpy/crack_detection/detection.py`
- `crackpy/crack_detection/deep_learning/*`
- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/tests/test_crack_detection/test_deep_learning/*`
- `crackpy/tests/test_crack_detection/test_pipeline/test_pipeline.py`

### Current Friction

`get_model()` combines model selector, model construction, weights file identity, cache folder policy, network download, state loading, and device behavior. Tests and future orchestration cannot vary those decisions independently.

### Target Shape

- A `ModelProvider` Interface returns a loaded model plus metadata such as model ID, role, architecture, weights ID, weights hash where available, and device.
- Adapters include local weights, Zenodo cache/download, test double, and future external provider.
- `UNetPath` and `ParallelNets` remain compatibility selectors and aliases.

### Definition Of Done

- Detection code can receive a model through the provider seam without knowing whether it came from local disk, download cache, or a test double.
- Unit tests for detection do not require network access or real pretrained weights.
- Provider tests cover cache hit, missing weights, unknown selector, and explicit no-download policy.
- Model metadata is available to future provenance records.
- Device placement behavior is documented and tested at the provider seam.
- Existing public selectors such as `UNetPath` keep working through compatibility aliases.

## C-007: Defaults And Options Cleanup

Candidate note: [[refactor-candidates/007-defaults-and-options-cleanup]]

### Goal

Make result-affecting configuration explicit and reproducible. Defaults should be resolved before method execution, recorded with origins, and separated from adapter policy such as output folders, progress, plotting, and multiprocessing.

### Main Files

- `crackpy/fracture_analysis/optimization.py`
- `crackpy/fracture_analysis/line_integration.py`
- `crackpy/fracture_analysis/analysis.py`
- `crackpy/structure_elements/data_files.py`
- `crackpy/structure_elements/material.py`
- `crackpy/provenance/source.py`
- `crackpy/results/result_data.py`

### Current Friction

Mutable default instances are used in public constructors and then mutated by default-normalization helpers. Result-affecting defaults, derived defaults, method selection, adapter choices, and incidental implementation defaults are mixed into the same object lifecycles.

### Target Shape

- Configuration builders resolve defaults per run.
- Method runners receive concrete result-affecting values or reject ambiguous missing values.
- `NormalizedConfiguration` records result parameters, parameter origins, adapter policy, parameter hash, and configuration hash.
- Mutable default objects are removed from touched constructor signatures.

### Definition Of Done

- No touched public constructor or function uses mutable object instances as default arguments.
- Tests prove each defaulted option object is independent per call.
- Result-affecting parameters are separated from adapter policy in at least one implemented method slice.
- Parameter-origin metadata is available for provenance and hash construction.
- Configuration hashes are deterministic for semantically equivalent resolved configuration payloads.
- Docstrings explain which settings affect scientific results, which are derived defaults, and which are adapter policy.

## C-008: Result Tag Schema

Candidate note: [[refactor-candidates/008-result-tag-schema]]

### Goal

Centralize result schema, legacy text tags, JSON keys, CSV columns, units, and aliases. The schema Module should provide one source of truth for output adapters and readers while the future canonical result graph remains the main scalar result Interface.

### Main Files

- `crackpy/results/result_data.py`
- `crackpy/results/write.py`
- `crackpy/results/read.py`
- `crackpy/results/plot.py`
- `crackpy/results/kg_statement_bundle.py`
- `crackpy/fracture_analysis/methods/williams_fit/spec.yaml`
- `crackpy/tests/test_fracture_analysis/test_read.py`
- `crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py`

### Current Friction

Result tags and sections are stringly typed across writer, reader, plotter, tests, and scripts. Current files lack a consistent explicit result schema version. Williams-fit aliases are the first partial slice, but other result families remain implicit.

Current implementation note: `crackpy.results.legacy_schema` can project Williams-fit and CJP current-style result sections from canonical envelopes.
It is an additive adapter for schema-backed tests and frontend/backend handoff, not a migration of legacy writers or readers.

### Target Shape

- Schema definitions carry schema version, result family, canonical quantity symbols, descriptions, units, legacy aliases, and adapter projection rules.
- Legacy text, current JSON sections, flattened CSV, and plots are adapters over schema-backed result records.
- The schema works with the provenance/result envelope rather than duplicating definitions.

### Definition Of Done

- Every currently written legacy scalar tag in the touched result family is listed in one schema or alias map with a description and unit policy.
- Envelope-backed legacy-section tests fail if a touched Williams/CJP alias is renamed without updating the schema.
- Writer and reader migration remains broader C-008 work because legacy text/current JSON and CSV still use older direct contracts.
- CSV flattening uses schema-backed columns for the touched result family.
- Compatibility tests prove old fixtures still read or have an explicit migration path.
- Schema versions appear in new canonical output artifacts.
- The schema module does not import `FractureAnalysis`, `Plotter`, or file-writing policy.

## C-009: Sequence Index Vocabulary

Candidate note: [[refactor-candidates/009-sequence-index-vocabulary]]

### Goal

Keep `stage` as source metadata while introducing stable `input_id`, optional `sequence_index`, and explicit mapping policies for representative inputs. This should make DIC workflows compatible with FEM load steps, synthetic fields, image sequences, and externally indexed data.

### Main Files

- `crackpy/input/input_data.py`
- `crackpy/structure_elements/data_files.py`
- `crackpy/crack_detection/pipeline/pipeline.py`
- `crackpy/fracture_analysis/pipeline.py`
- `crackpy/results/write.py`
- `crackpy/tests/test_crack_detection/test_pipeline/test_pipeline.py`

### Current Friction

`stage` currently acts as source label, ordering key, matching key, filename convention, and workflow state. Matching policies such as max-force or nearest-cycle assignment are represented as stage mappings rather than record mappings.

### Target Shape

- `stage` remains attached source metadata and compatibility output.
- `input_id` is the durable identity used by results, mappings, and provenance.
- `sequence_index` is an ordering hint, not identity.
- Mapping policies produce explicit `input_id -> representative_input_id` relationships and record the policy used.

### Definition Of Done

- Existing stage-based inputs still parse and produce the same compatibility labels.
- At least one mapping policy is tested using stable input IDs rather than only stage numbers.
- Max-force or nearest-cycle mapping tests cover missing metadata, tie cases, and filtered input sequences.
- Result/provenance records can link to `input_id` without parsing filenames.
- Documentation states when `stage` is source metadata and when `sequence_index` is the internal ordering value.
- No new internal runner uses `stage` as durable identity.

## C-010: Provenance Metadata Architecture

Candidate note: [[refactor-candidates/010-provenance-metadata-architecture]]

### Goal

Make provenance a first-class package seam that can build result/provenance envelopes from method-local source adapters and slice specs. The current Williams-fit slice should be audited, hardened, and used as the pattern only where it passes the deletion test.

### Main Files

- `crackpy/provenance/source.py`
- `crackpy/provenance/spec.py`
- `crackpy/provenance/builder.py`
- `crackpy/results/result_data.py`
- `crackpy/results/kg_statement_bundle.py`
- `crackpy/results/graph_visualization.py`
- `crackpy/fracture_analysis/methods/williams_fit/*`
- `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`
- `crackpy/tests/test_fracture_analysis/test_williams_provenance_actual_data.py`

### Current Friction

The first Williams-fit result/provenance slice exists, but broader provenance architecture is not approved. The risk is that early implementation details become accidental architecture for CJP, line integrals, crack-tip estimates, KG export, or graph visualization.

### Target Shape

- `crackpy.provenance` owns generic source snapshots, slice spec validation, and envelope projection.
- Method modules own method-specific adapters, parameters, result records, spec files, and method-specific wrapper logic.
- Compact KG statement-bundle and visualization graph are adapters over envelope records, not core method logic.
- Detailed process provenance remains optional and separate from the compact result-centric export.

### Definition Of Done

- The current Williams-fit implementation is audited against [[refactor-candidates/010-provenance-metadata-architecture#First Williams-Fit Slice Specification]], and every drift is either fixed, documented, or recorded as a new planning decision.
- `MethodResultSource`, `SourceDependency`, `SourceParameters`, and `ProvenanceSliceSpec` enforce their invariants with direct tests.
- Record classes that can be dependency targets expose explicit `provenance_id` behavior and document identity fields.
- KG statement-bundle and graph visualization tests prove they can be generated from envelope records without method-specific hard-coding outside adapter profiles.
- No generic provenance Module imports `FractureAnalysis`, plotting, file writers, or method-specific numerical code.
- A second method slice is not started until Williams-fit passes the audit and has a documented extension rule.
- The limited-context documentation review confirms that fixture authors can construct source snapshots, specs, envelopes, and adapter projections without reading the full stack.

## C-011: Method Module Contract

Candidate note: [[refactor-candidates/011-method-module-contract]]

### Goal

Define a lightweight method-module contract and verifier so Williams-fit, CJP-fit, and later integral methods expose the same essential seams without sharing premature inheritance.

### Main Files

- `crackpy/fracture_analysis/methods/williams_fit/*`
- `crackpy/fracture_analysis/methods/cjp_fit/*`
- `crackpy/provenance/source.py`
- `crackpy/provenance/spec.py`
- `crackpy/provenance/builder.py`
- `crackpy/results/result_data.py`
- `crackpy/results/envelope_artifacts.py`
- future `crackpy/methods/*` or test-support contract verifier module
- future `crackpy/tests/test_methods/*`

### Current Friction

Williams-fit and CJP-fit now share method-module shape, but the commonality is implicit.
Future integral methods could copy the shape inconsistently, especially around metadata, schema versions, aliases, source adapters, and envelope builders.
CJP shows that a method family may need variants and contextual result-symbol lookup, so a simple base class would be too rigid.

Current implementation note: the first `crackpy.methods.contract` verifier slice exists and is exercised by Williams-fit and CJP-fit fixtures.
It is a test-time helper, not a package-wide registry or release gate.

### Target Shape

- A protocol-like method-module Interface describes required files, public seams, spec loading, typed parameters, typed results, source adapters, runners, and envelope builders.
- A contract verifier checks method slices at test time and later build time.
- Shared runtime helpers cover configuration/run/result ID policy, imported crack-tip estimate projection, dependency edge construction, and standard artifact writing where Williams and CJP prove true duplication.
- Method-local modules keep numerical implementation, variant rules, coefficient conversion, quantity extraction, and source adapters.

### Definition Of Done

- The method-module contract is documented with Williams-fit and CJP-fit as examples.
- Contract tests verify spec loading, unique method IDs, alias uniqueness, quantity metadata, source snapshots, schema-indexable envelopes, and standard artifact construction.
- Repeated-symbol disambiguation and parameter snapshot expectations remain covered by the surrounding CJP/Williams provenance tests until the verifier owns those checks directly.
- CJP passes the contract while still producing separate mixed-mode and Mode-I runs/results.
- Williams passes the contract while still producing one analysis run/result.
- Shared runtime helpers remove repeated ID/configuration/imported-crack-tip-estimate plumbing without changing public artifact filenames or envelope semantics.
- The verifier can write standard envelope artifacts from a produced envelope without importing `FractureAnalysis`, plotting, or legacy result writers.
- No common base class is required for method modules.
- Integral method migration remains out of scope until the CJP/Williams contract is stable.

## Ready-To-Start Goal Template

Use this template when turning a candidate into a Codex goal:

```text
Goal ID:
Candidate:
User-approved scope:
Files in scope:
Files explicitly out of scope:
Compatibility behavior to preserve:
New or changed Interface:
Adapters involved:
Required tests:
Documentation/docstring review target:
Architecture-wiki notes to update:
Definition Of Done:
```

## Candidate Dependency Notes

- C-010 should be audited before extending C-001 or C-008 beyond Williams-fit because it proves the first result/provenance pattern.
- C-002 should precede broad C-009 work because mapping policies need stable input identity.
- C-005 should precede broad correction and detector migration because `side` compatibility must map into `CrackTipFrame` cleanly.
- C-007 should precede method registry and hash work because hashes are meaningful only after defaults are resolved explicitly.
- C-003 can proceed as a narrow Williams method slice, but broader correction migration should wait for C-005.
- C-011 should run after the current provenance slice audit and before using the Williams/CJP method-module shape as the template for integral methods.
- C-004 should be last among the broad candidates because workflow runners compose results, inputs, orientation, configuration, model providers, and adapters.

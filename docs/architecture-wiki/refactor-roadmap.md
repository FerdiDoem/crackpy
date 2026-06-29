# Refactor Roadmap

Status: future planning roadmap, not approved implementation
Role: Consolidate resolved planning decisions into a cross-candidate sequencing view. This note does not replace the candidate notes, does not create ADRs, and does not approve package-code refactoring.

Related: [[refactor-notes]], [[refactor-candidates/index]], [[decision-log]], [[open-questions]]

Goal-sized execution plan: [[goal-driven-refactoring-plan]]

## Roadmap Rules

- Keep observed-system notes as the baseline for current behavior.
- Treat this roadmap as sequencing guidance for future specifications, not as implementation approval.
- Keep future architecture grouped by initiative while detailed proposal content remains in candidate notes.
- Before production code changes, define field-level specifications for any proposed records, configuration objects, registries, adapters, or workflow runners.
- Treat human maintainability as an architecture constraint: important classes and functions should be self-explanatory through names, docstrings, field descriptions, and decision-focused inline comments.
- Use private helpers and object-oriented structure where they create real depth, locality, lifecycle control, invariant ownership, or adapter seams. Do not extract helpers or classes only to satisfy DRY when local readability would get worse.
- Before approving future architecture code changes, run a documentation-focused review on individual functions/classes with limited background context to check whether their purpose, inputs, side effects, invariants, and failure modes are understandable locally.
- Preserve compatibility behavior until an approved migration plan says otherwise.

## Initiative 1: Result And Provenance Spine

Primary candidates:

- C-001: [[refactor-candidates/001-explicit-analysis-result]]
- C-008: [[refactor-candidates/008-result-tag-schema]]
- C-010: [[refactor-candidates/010-provenance-metadata-architecture]]

Resolved decisions consolidated here:

- Future main scalar result output is JSON with an explicit `result_schema_version`.
- Canonical result JSON is a PROV-compatible graph bundle, not current writer tags.
- `ResultQuantity` keeps `symbol` and expressive `description` before structured descriptors.
- Provenance uses a minimal traceability chain: `InputRecord`, `AnalysisRun`, `ResultRecord`, and `ProvenanceRecord`.
- Compact knowledge-graph export is result-centric; detailed provenance is process-centric and optional.
- Crack-tip estimates are explicit result dependencies, not configuration-only values.

Planning direction:

Treat the explicit result model, result tag/schema cleanup, and provenance metadata model as one roadmap spine. The first specification should define the canonical result/provenance graph boundary before designing adapters for legacy text, current JSON sections, flattened CSV, plots, compact KG statement bundles, or optional detailed provenance artifacts.

Recent KG artifact and prototype review calibrates the first target: keep the adapter-first direction, but shrink the first specification. The first approved slice should define a minimal result/provenance envelope plus one compact KG projection for one real workflow, such as Williams fitting or crack-tip estimation. It should not attempt to land the full method registry, implementation fingerprinting, input identity model, crack-tip frame model, compact KG exporter, and optional PROV artifact in one step.

That first slice still needs enough export policy to avoid later rework: grouping policy, subject identity policy, URI minting policy, descriptor-field policy, datatype normalization, unit normalization, and compatibility aliases for current result tags. The external JSON/Turtle artifacts show that grouped metadata statements and RDF descriptor resources are KG export representations, not CrackPy core record types.

The field-level Williams-fit slice lives in [[refactor-candidates/010-provenance-metadata-architecture#First Williams-Fit Slice Specification]]. It folds the preserved `result_spine_package` prototype conclusions into planning notes. Current code now contains a partial implementation of this slice: shared provenance source/spec/builder modules, Williams-fit method-local typed records and source adapter, a YAML-backed Williams spec, a compact KG statement-bundle projection, a graph visualization projection, and an optional `OutputWriter.write_williams_fit_provenance_json()` hook.

The first-slice choice is accepted for planning in [[decision-log#2026-06-05-williams-fit-is-the-first-result-provenance-implementation-slice]]: Williams fitting is the first implementation target, with crack-tip estimates included as explicit dependencies.

The first-slice schema-version, angle-unit, required-quantity, hash, and compatibility-alias policies are now captured in [[decision-log]]. Production implementation should stay inside those boundaries unless new evidence forces another planning decision.

The graph visualization kit is accepted as a downstream adapter over the canonical envelope. It should consume envelope records and dependency edges first, with RDF/KG rendering as a secondary projection. Visualization layout and KG descriptor resources must not become core result/provenance fields.

Approval gate:

Do not broaden result writers, readers, CSV output, CJP results, line-integral results, Bueckner-Chen results, plot metadata, or KG/RDF export beyond the current Williams-fit slice until the next field-level result/provenance specification is approved, including node types, edge roles, schema-version policy, quantity fields, artifact references, and compatibility aliases for the affected current result tags.

## Initiative 2: Input Identity And Ordering

Primary candidates:

- C-002: [[refactor-candidates/002-input-loading-seam]]
- C-009: [[refactor-candidates/009-sequence-index-vocabulary]]
- C-010: [[refactor-candidates/010-provenance-metadata-architecture]]

Resolved decisions consolidated here:

- `stage` remains source-specific and compatibility vocabulary.
- Future internals should use stable `input_id` values and optional `sequence_index` values.
- `InputRecord` pairs data with attached metadata and minimal input/source provenance.
- Matching across loads, cycles, or representative records should use explicit mapping policies.

Planning direction:

Define the input identity model before changing loader behavior. The future input layer should separate durable identity, source labels, ordering hints, metadata, hashes, and mapping policies without forcing all sources into DIC `stage` vocabulary.

Approval gate:

Do not replace `InputData` loading or stage-based workflows until an `InputRecord` and mapping-policy specification is approved, including compatibility behavior for existing nodemap filename parsing, crack-detection stage selection, and fracture-analysis handoff files.

## Initiative 3: Crack-Tip Orientation And Estimate Flow

Primary candidates:

- C-003: [[refactor-candidates/003-self-contained-williams-fit-interface]]
- C-005: [[refactor-candidates/005-side-orientation-module]]
- C-010: [[refactor-candidates/010-provenance-metadata-architecture]]

Resolved decisions consolidated here:

- `side` is compatibility vocabulary, not a sustainable internal crack-orientation model.
- `CrackTipFrame` is the future internal crack-tip orientation planning target.
- Future planning should separate crack-tip identity, origin, local axes, geometry profile, detector convention, mirroring policy, specimen geometry, and output labels.
- Crack-tip correction should distinguish absolute corrected estimates from relative correction deltas.

Planning direction:

Specify crack-tip estimates and crack-tip frames before changing Williams fitting, correction, or detector handoff behavior. The first planning target should describe how current `side`, `left_or_right`, crack-tip angle, mirrored detection inputs, correction deltas, and downstream fracture-analysis transforms map into explicit estimate records and `CrackTipFrame` values.

Approval gate:

Do not rename or remove current `side`/`left_or_right` compatibility paths until the `CrackTipFrame` and `CrackTipEstimateResult` specifications define migration behavior for files, APIs, plots, and result aliases.

## Initiative 4: Explicit Configuration And Method Registry

Primary candidates:

- C-006: [[refactor-candidates/006-model-provider-seam]]
- C-007: [[refactor-candidates/007-defaults-and-options-cleanup]]
- C-010: [[refactor-candidates/010-provenance-metadata-architecture]]
- C-011: [[refactor-candidates/011-method-module-contract]]

Resolved decisions consolidated here:

- Result-affecting defaults must be explicit before method execution.
- Future provenance should use stable registry-owned `method_id` values.
- `method_revision` is maintainer-declared; `implementation_fingerprint` is generated from declared `dependency_scope`.
- Method references should live in a hybrid registry: package-level `CITATION.cff`, method-reference YAML/JSON as source of truth, and Python metadata storing reference IDs.
- `UNetPath` remains compatibility vocabulary while future model metadata splits model ID, role, architecture, weights, and aliases.

Planning direction:

Specify normalized configuration, method metadata, method-reference registry, model metadata, and fingerprint validation together. This keeps stale-result checks tied to resolved result-affecting values rather than to incidental output paths, plotting choices, or Python file locations.

The method-module contract should be specified before migrating additional method families.
Williams-fit and CJP-fit are the first two contract examples because they prove both single-result and multi-variant result shapes.
The contract should use protocol-like conformance and build-time verification rather than forcing method modules through a shared base class.

Approval gate:

Do not introduce a method registry or configuration hash into production paths until the normalized configuration boundary is approved, including default-origin recording, hash inclusion/exclusion rules, method lifecycle states, alias rules, successor rules, and dependency-scope validation.
Do not apply the method-module contract broadly to integral methods until Williams-fit and CJP-fit pass the contract verifier without changing their public result artifact shape.

## Initiative 5: Domain Workflow Runners And Compatibility Facades

Primary candidates:

- C-004: [[refactor-candidates/004-separate-orchestration-from-adapters]]
- C-003: [[refactor-candidates/003-self-contained-williams-fit-interface]]
- C-006: [[refactor-candidates/006-model-provider-seam]]
- C-008: [[refactor-candidates/008-result-tag-schema]]

Resolved decisions consolidated here:

- CrackPy should keep package-owned scientific workflow logic where sequencing is domain-specific.
- Current `CrackDetectionPipeline` and `FractureAnalysisPipeline` should become compatibility facades during a future migration.
- Adapter policy includes file layout, text/current JSON/future JSON writing, CSV export, plot generation, progress reporting, multiprocessing, model download/cache behavior, VTK export, and KG/RDF export.

Planning direction:

After the record, configuration, and result/provenance boundaries are specified, choose one vertical slice as a paper design before code changes. A likely pilot is a Williams-fit or crack-tip-estimate flow that returns explicit records while a compatibility facade preserves current files and plots.

Approval gate:

Do not restructure current pipelines until a runner/adapter specification identifies which behavior remains CrackPy-owned scientific sequencing and which behavior moves behind adapters or compatibility facades.

## Initiative 6: Bounded Terminology And Compatibility Cleanup

Primary candidates:

- C-005: [[refactor-candidates/005-side-orientation-module]]
- C-006: [[refactor-candidates/006-model-provider-seam]]
- C-007: [[refactor-candidates/007-defaults-and-options-cleanup]]
- C-009: [[refactor-candidates/009-sequence-index-vocabulary]]

Resolved decisions consolidated here:

- Detection grid terminology uses explicit window extent, input resolution, endpoint-inclusive spacing, and unit-bearing names.
- Line-intercept `window_size` means minimum consecutive strain-exceedance count.
- Future implementation vocabulary should use `bueckner_chen_*`; current `buckner_*` is legacy spelling.
- Fixture names such as `Dummy2`, `EBr10`, and `Aramis_in_line` are not domain vocabulary.

Planning direction:

Keep terminology cleanup subordinate to the larger record, configuration, runner, and adapter plans. Use aliases, wrappers, and deprecation notes where public or file-facing names are involved.

Approval gate:

Do not perform broad renames until compatibility aliases, public documentation impact, and result/file migration behavior are specified.

## Suggested Specification Order

1. Approve or revise this roadmap grouping.
2. Audit the current Williams-fit provenance implementation against [[refactor-candidates/010-provenance-metadata-architecture#First Williams-Fit Slice Specification]] and record any drift as a decision or follow-up candidate.
3. Expand the result/provenance spine only after that audit, including canonical result graph nodes, output artifact roles, provenance edge roles, and legacy adapter aliases for the next result family.
4. Specify input identity and ordering, including `InputRecord`, `input_id`, `sequence_index`, and mapping policies.
5. Specify crack-tip estimate and `CrackTipFrame` records.
6. Specify normalized configuration, method registry, method references, model metadata, and fingerprint validation.
7. Specify one vertical runner/adapter pilot and its compatibility facade.
8. Only then consider package-code refactoring.

## Candidate Grouping Summary

| Initiative | Candidate IDs | Main purpose |
| --- | --- | --- |
| Result and provenance spine | C-001, C-008, C-010 | Define canonical result/provenance model before adapters. |
| Input identity and ordering | C-002, C-009, C-010 | Replace stage-as-internal-ordering with stable input identity and explicit mapping policy. |
| Crack-tip orientation and estimate flow | C-003, C-005, C-010 | Replace side-coupled internals with crack-tip frames and estimate records. |
| Configuration and method registry | C-006, C-007, C-010 | Make result-affecting configuration, method identity, references, and model metadata explicit. |
| Method module contract | C-003, C-010, C-011 | Define method-local seams and build-time verification before copying the pattern to integral methods. |
| Workflow runners and facades | C-003, C-004, C-006, C-008 | Separate domain sequencing from side-effect adapters while preserving current behavior. |
| Terminology and compatibility cleanup | C-005, C-006, C-007, C-009 | Rename or deprecate only after compatibility plans exist. |

## Follow-Up Planning Questions

The resolved `OQ-*` set is sufficient to draft this roadmap. New open questions may be useful during implementation planning, but they should be added only when code inspection reveals a real architecture decision not covered by the first-slice specification. Likely areas are:

- whether the result/provenance spine is one specification or split into result schema, provenance records, and KG exporter specifications;
- how strict the first method-registry validation should be during development versus release builds.

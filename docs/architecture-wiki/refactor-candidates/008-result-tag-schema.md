# Candidate 008: Result Tag Schema

Status: proposed, with Williams-fit aliases and contextual CJP symbol lookup partially implemented
Role: Architecture candidate for centralizing result JSON keys, legacy text tags, and tabular output schema.

## Observed Evidence

- [[results-io-workflows]] documents current result modules and output tags.
- [[terminology-report]] records result naming inconsistencies.
- [[coupling-map]] records direct dependency from result I/O to analysis internals.

## Problem

Text tags and output keys are stringly typed across writers, readers, tests, and scripts. Current result files do not carry an explicit result schema version.

## Future Direction

Centralize result JSON schema, legacy text tags, and column schemas. Future planning treats versioned JSON as the main CrackPy result output for scalar result values and traceability metadata. Text output, flattened CSV, plots, and heavier scientific-storage formats should be adapters or helper projections over the structured result model.

Accepted OQ-006 boundary: the canonical result JSON should be a PROV-compatible graph-shaped bundle, not a set of method-section keys copied from current writer tags. The public schema should define typed nodes and edges:

- `Software`: CrackPy package identity, version, and source/build traceability.
- `SoftwareConfiguration`: normalized and hashable CrackPy configuration snapshot, including resolved defaults and configuration schema version.
- `InputRecord`: input identity, source metadata, hashes, and geometry profile.
- `AnalysisRun`: one execution of a registered method with method ID, method revision, configuration, inputs, timestamps, and implementation fingerprint.
- `ResultRecord`: generated result identity, schema version, artifact references, and hashes.
- `ResultQuantity`: scalar scientific output such as a stress intensity factor, T-stress value, Williams coefficient, J value, fit error, or path statistic.
- `ProvenanceRecord`: envelope linking inputs, runs, results, software, configuration, compact KG export metadata, and optional detailed provenance.

Current names such as `Williams_fit_results`, `SIFs_integral`, `Path_SIFs`, `Bueckner_Chen_integral`, `Path_Properties`, `mean_wo_outliers`, and `rej_out_mean` should remain visible as legacy aliases for adapters and compatibility readers, not as canonical public schema.

A scalar result should have its own quantity identity instead of being represented only by a flattened key:

```json
{
  "quantity_id": "quantity:sha256:...",
  "result_id": "result:fracture:example-001",
  "symbol": "K_I",
  "description": "Mode I stress intensity factor derived from Williams coefficient a_1.",
  "value": 1.99,
  "unit": "MPa*sqrt(m)",
  "method_id": "crackpy.fracture.williams_fit",
  "derived_from_quantity_ids": ["quantity:williams-a1"],
  "legacy_aliases": ["Williams_fit_results.K_I"]
}
```

This quantity can then be translated into the compact KG statement-bundle format as a `ResultQuantity` subject linked to its `FractureAnalysisResult`, while a PROV-O-like exporter can keep it as a generated entity or domain quantity linked to the generating activity.

Accepted OQ-011 boundary: keep current scientific symbols such as `K_I`, `K_II`, `K_F`, `K_R`, `T`, `a_1`, and `J_I` as the primary quantity labels for now. Use an expressive `description` string to explain scientific meaning and derivation context. Do not introduce mandatory structured descriptor fields such as `fracture_mode`, `component`, `series`, or `term_index` until the result ontology boundary is clearer.

Result schema metadata should align with [[refactor-candidates/010-provenance-metadata-architecture]] so provenance exporters can identify result format versions reliably.

## Seams / Interfaces / Adapters

- Interface: result schema, JSON result envelope, and tag/column definitions.
- Main output: versioned graph-shaped JSON result/provenance artifact.
- Adapters: legacy text writer, CSV flattening, plotting, optional future table or array exports.
- Translators: compact KG grouped metadata statement-bundle exporter and optional PROV-O/JSON-LD exporter.
- Existing implementation: `OutputWriter`, `OutputReader`, and fixture expectations.

## Consequences

- Reader/writer consistency becomes local.
- Graph-shaped JSON becomes the source of truth for scalar result records and traceability metadata.
- CSV generation can be validated against the schema.
- Existing files and tests need compatibility handling if schema names change.
- Current result names become legacy alias mappings instead of public ontology.

## Open Questions

- OQ-005: resolved; future main result output is versioned JSON, with legacy text/CSV/plots treated as adapters or helper projections.
- OQ-006: resolved; canonical result JSON is graph-shaped and current result tags are legacy aliases.
- OQ-011: resolved; future quantity records keep `symbol` plus expressive `description` for now, while structured mode/component/term descriptors are deferred.
- OQ-015: resolved; provenance metadata uses the `InputRecord`, `AnalysisRun`, `ResultRecord`, and `ProvenanceRecord` split.

## Decision State

OQ-005, OQ-006, and OQ-011 planning boundaries accepted. The Williams-fit slice now defines scalar quantity aliases in `crackpy.fracture_analysis.methods.williams_fit/spec.yaml`, projects them into canonical result quantities, and exposes an envelope-derived `ResultSchemaIndex` for resolving canonical symbols, units, descriptions, schema versions, and legacy aliases. The CJP slice now proves that a scientific symbol is not a stable global key by itself: `error` appears in both mixed-mode and Mode-I result records, so `ResultSchemaIndex` supports one-to-many symbol lookup plus contextual lookup by `result_id` or `method_id`. The broader concrete schema still needs future design, validation rules, and compatibility strategy for current JSON sections, text tags, CSV output, line-integral, Bueckner-Chen, path, and plot result families.

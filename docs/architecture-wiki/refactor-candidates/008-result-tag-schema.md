# Candidate 008: Result Tag Schema

Status: proposed
Role: Future architecture candidate for centralizing result JSON keys, legacy text tags, and tabular output schema.

## Observed Evidence

- [[results-io-workflows]] documents current result modules and output tags.
- [[terminology-report]] records result naming inconsistencies.
- [[coupling-map]] records direct dependency from result I/O to analysis internals.

## Problem

Text tags and output keys are stringly typed across writers, readers, tests, and scripts. Current result files do not carry an explicit result schema version.

## Future Direction

Centralize result JSON keys, legacy text tags, and column schemas. Future planning treats versioned JSON as the main CrackPy result output for scalar result values and traceability metadata. Text output, flattened CSV, plots, and heavier scientific-storage formats should be adapters or helper projections over the structured result model.

Result schema metadata should align with [[refactor-candidates/010-provenance-metadata-architecture]] so provenance exporters can identify result format versions reliably.

## Seams / Interfaces / Adapters

- Interface: result schema, JSON result envelope, and tag/column definitions.
- Main output: versioned JSON result artifact.
- Adapters: legacy text writer, CSV flattening, plotting, optional future table or array exports.
- Existing implementation: `OutputWriter`, `OutputReader`, and fixture expectations.

## Consequences

- Reader/writer consistency becomes local.
- JSON becomes the source of truth for scalar result records and traceability metadata.
- CSV generation can be validated against the schema.
- Existing files and tests need compatibility handling if schema names change.

## Open Questions

- OQ-005: resolved; future main result output is versioned JSON, with legacy text/CSV/plots treated as adapters or helper projections.
- OQ-006: Which result names are public schema and which are legacy implementation names?
- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

OQ-005 planning boundary accepted. No implementation approved. OQ-006 still blocks the concrete public result-name schema.

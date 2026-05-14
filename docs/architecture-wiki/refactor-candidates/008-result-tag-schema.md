# Candidate 008: Result Tag Schema

Status: proposed
Role: Future architecture candidate for centralizing result text/JSON tag names and tabular output schema.

## Observed Evidence

- [[results-io-workflows]] documents current result modules and output tags.
- [[terminology-report]] records result naming inconsistencies.
- [[coupling-map]] records direct dependency from result I/O to analysis internals.

## Problem

Text tags and output keys are stringly typed across writers, readers, tests, and scripts.

## Future Direction

Centralize result tag definitions and column schemas. Treat text output as an adapter over structured results. Result schema metadata should align with [[refactor-candidates/010-provenance-metadata-architecture]] so provenance exporters can identify result format versions reliably.

## Seams / Interfaces / Adapters

- Interface: result schema and tag definitions.
- Adapters: text writer, JSON writer, CSV flattening, plotting.
- Existing implementation: `OutputWriter`, `OutputReader`, and fixture expectations.

## Consequences

- Reader/writer consistency becomes local.
- CSV generation can be validated against the schema.
- Existing files and tests need compatibility handling if schema names change.

## Open Questions

- OQ-005: Should result files receive an explicit schema or format version?
- OQ-006: Which result names are public schema and which are legacy implementation names?
- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

Not decided. No implementation approved.

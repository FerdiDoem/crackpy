# Candidate 002: Input Loading Seam

Status: proposed
Role: Future architecture candidate for separating file loading from the central mutable data carrier.

## Observed Evidence

- [[data-model-input]] documents `InputData`, nodemap parsing, metadata handling, material coupling, and VTK export.
- [[system-map]] identifies `crackpy.input` as the owner of nodemap import and transformation behavior.
- [[coupling-map]] records `InputData` as a high-coupling module.

## Problem

`InputData` currently acts as file adapter, schema, mutable container, transform module, and mechanics helper. Callers must know file format and field lifecycle details.

## Future Direction

Create a loading seam around nodemap file loading, manual/in-memory loading, metadata extraction, and FEM-vs-DIC interpretation.

Candidate adapters:

- nodemap file adapter;
- in-memory/test adapter;
- future uploaded-file or workflow-manager adapter.

## Seams / Interfaces / Adapters

- Seam: input loading and metadata extraction.
- Interface: loaded measurement data plus metadata and source identifiers.
- Adapters: nodemap file, in-memory data, future external workflow input.

## Consequences

- Nodemap format quirks and metadata parsing become local.
- External orchestration can provide data without pretending to be a nodemap file.
- The current `InputData` lifecycle must be preserved during migration.

## Open Questions

- OQ-001: Should `side` remain a public term or split into smaller concepts?
- OQ-002: Should `stage` remain public vocabulary or become adapter-specific acquisition metadata?
- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

Not decided. No implementation approved.

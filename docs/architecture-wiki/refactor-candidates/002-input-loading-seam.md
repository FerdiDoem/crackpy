# Candidate 002: Input Loading Seam

Status: proposed, with first SourceInput and InputRecord projection slices implemented
Role: Future architecture candidate for separating file loading from the central mutable data carrier.

## Observed Evidence

- [[data-model-input]] documents `InputData`, nodemap parsing, metadata handling, material coupling, and VTK export.
- [[system-map]] identifies `crackpy.input` as the owner of nodemap import and transformation behavior.
- [[coupling-map]] records `InputData` as a high-coupling module.

## Problem

`InputData` currently acts as file adapter, schema, mutable container, transform module, and mechanics helper. Callers must know file format and field lifecycle details.

## Future Direction

Create a loading seam around nodemap file loading, manual/in-memory loading, metadata extraction, and FEM-vs-DIC interpretation.

Planning vocabulary from [[decision-log#2026-05-14-stage-is-source-metadata-sequence-index-is-internal-ordering]] points toward an [[glossary#InputRecord]] concept: data plus attached [[glossary#Input metadata]], minimal input/source provenance, a stable [[glossary#Input ID]], and an optional [[glossary#Sequence index]] for ordered inputs.

Candidate adapters:

- nodemap file adapter;
- in-memory/test adapter;
- future uploaded-file or workflow-manager adapter.

## Seams / Interfaces / Adapters

- Seam: input loading and metadata extraction.
- Interface: loaded measurement data plus metadata, source identifiers, stable input identity, and optional sequence ordering.
- Adapters: nodemap file, in-memory data, future external workflow input.

## Consequences

- Nodemap format quirks and metadata parsing become local.
- External orchestration can provide data without pretending to be a nodemap file.
- The current `InputData` lifecycle must be preserved during migration.

## Open Questions

- OQ-001: Resolved in [[decision-log#2026-05-14-side-is-not-a-sustainable-internal-crack-orientation-model]].
- OQ-002: Resolved in [[decision-log#2026-05-14-stage-is-source-metadata-sequence-index-is-internal-ordering]].
- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

The first narrow implementation slice is now present: `InputData.source_input()` projects already-loaded input identity and source metadata into a `SourceInput`, and `SourceInput`/`InputRecord` carry optional `sequence_index` as an ordering hint.

The second narrow implementation slice is now present: `crackpy.provenance.input_records.input_record_from_source_input()` converts `SourceInput` snapshots into canonical `InputRecord` records, and `input_records_from_source_inputs()` rejects duplicate primary input IDs.

`MethodResultEnvelopeBuilder.input_records()` delegates to this adapter so method envelopes, graph payloads, KG bundles, and frontend/backend fixtures share the same input-record projection rules.

This does not approve a broader `InputData` rewrite; nodemap parsing, manual data injection, transforms, mechanics helpers, VTK export, masking, and legacy stage handling remain compatibility behavior.

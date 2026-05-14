# Candidate 009: Sequence Index Vocabulary

Status: proposed
Role: Future architecture candidate for generalizing the current `Stage` concept without rewriting observed current behavior.

## Observed Evidence

- [[glossary]] defines `Stage` as the current DIC source label and filename-derived ordering key.
- [[terminology-report]] records `stage` as overloaded and potentially workflow-specific.
- [[crack-detection]] documents stage selection and force metadata handling.
- [[data-model-input]] documents nodemap filename and metadata coupling.

## Problem

`Stage` is the current CrackPy term for the maintainers' DIC source label and filename-derived ordering key. It is useful for the existing nodemap workflow, but it is not a universal concept. Future inputs may be FEM load steps, synthetic fields, image sequences, video frames, externally indexed measurements, or acquisition systems that do not use the word stage.

## Future Direction

Keep `stage` as source-specific metadata for current nodemap filenames and headers. Use [[glossary#Sequence index]] as the generic future ordering key and [[glossary#Input ID]] as the durable identity. A future [[glossary#InputRecord]] can pair data with attached metadata and minimal input/source provenance without making that metadata part of pipeline state.

Matching between records should be a separate [[glossary#Mapping policy]]. For example, max-load or nearest-cycle matching should produce mappings such as `input_id -> representative_input_id` instead of depending on `stage -> stage` as the internal representation.

## Seams / Interfaces / Adapters

- Seam: input metadata, including source identifiers that future provenance export may need to map into [[refactor-candidates/010-provenance-metadata-architecture]].
- Interface: ordered input record with stable identity, sequence index, attached metadata, and optional source-specific labels such as `stage`.
- Adapter: current stage suffix parsed from nodemap filenames.
- Helper: mapping policy over metadata for representative max-load or nearest-cycle assignments.

## Consequences

- The interface becomes clearer for non-DIC or non-ZEISS/GOM acquisition sources.
- Current stage-based workflows can remain supported through an adapter.
- Matching logic becomes explicit and record-based instead of being hidden inside stage dictionaries.
- Processing provenance remains outside the input record, while minimal input/source provenance can stay attached to the input.

## Open Questions

- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

Planning vocabulary accepted in [[decision-log#2026-05-14-stage-is-source-metadata-sequence-index-is-internal-ordering]]. No implementation approved.

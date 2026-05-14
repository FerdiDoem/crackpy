# Candidate 009: Acquisition Index Vocabulary

Status: proposed
Role: Future architecture candidate for generalizing the current `Stage` concept without rewriting observed current behavior.

## Observed Evidence

- [[glossary]] defines `Stage` as the current DIC acquisition-order index.
- [[terminology-report]] records `stage` as overloaded and potentially workflow-specific.
- [[crack-detection]] documents stage selection and force metadata handling.
- [[data-model-input]] documents nodemap filename and metadata coupling.

## Problem

`Stage` is the current CrackPy term for the maintainers' DIC acquisition-order index. It is useful for the existing nodemap workflow, but it is not a universal concept. Future inputs may be image sequences, video frames, externally indexed measurements, or acquisition systems that do not use the word stage.

## Future Direction

Keep `stage` as an adapter-level field for current nodemap filenames, but consider a more general internal concept such as `measurement_index`, `acquisition_index`, or `acquisition_point`. A richer `AcquisitionPoint` could group the ordering index with load/force, cycle count, source filename/frame, and optional sub-cycle position.

## Seams / Interfaces / Adapters

- Seam: acquisition metadata, including source identifiers that future provenance export may need to map into [[refactor-candidates/010-provenance-metadata-architecture]].
- Interface: ordered acquisition point with source identifier and metadata.
- Adapter: current stage suffix parsed from nodemap filenames.

## Consequences

- The interface becomes clearer for non-DIC or non-ZEISS/GOM acquisition sources.
- Current stage-based workflows can remain supported through an adapter.
- Needs a terminology decision before implementation.

## Open Questions

- OQ-002: Should `stage` remain public vocabulary or become adapter-specific acquisition metadata?

## Decision State

Not decided. No implementation approved.

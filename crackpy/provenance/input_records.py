"""Input identity adapters for canonical result/provenance records."""
from __future__ import annotations

from collections.abc import Iterable

from crackpy.provenance.source import SourceInput
from crackpy.results.result_data import InputRecord


def input_record_from_source_input(source_input: SourceInput) -> InputRecord:
    """Project a source input snapshot into a canonical `InputRecord`.

    The adapter keeps input identity projection out of method-specific envelope
    builders. `SourceInput` remains the method-source Interface, while
    `InputRecord` is the canonical result/provenance record consumed by graph,
    KG, frontend, and future output adapters.
    """
    return InputRecord(
        input_id=source_input.input_id,
        data_ref=source_input.data_ref,
        source_metadata=source_input.source_metadata,
        source_label=source_input.source_label,
        sequence_index=source_input.sequence_index,
        source_hash=source_input.source_hash,
    )


def input_records_from_source_inputs(source_inputs: Iterable[SourceInput]) -> tuple[InputRecord, ...]:
    """Project source inputs into canonical records and reject duplicate IDs.

    Duplicate `input_id` values make dependency edges ambiguous, so the adapter
    fails before an envelope, graph, or frontend payload can contain two primary
    input records with the same identity.
    """
    records = tuple(input_record_from_source_input(source_input) for source_input in source_inputs)
    seen: set[str] = set()
    duplicates: list[str] = []
    for record in records:
        if record.input_id in seen:
            duplicates.append(record.input_id)
        seen.add(record.input_id)
    if duplicates:
        joined = ", ".join(repr(input_id) for input_id in sorted(set(duplicates)))
        raise ValueError(f"Duplicate input_id values in source inputs: {joined}.")
    return records

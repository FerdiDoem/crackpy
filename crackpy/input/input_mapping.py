"""Input identity mapping policies used by legacy stage-based workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class InputSequenceRecord:
    """Minimal input record consumed by input mapping policies.

    `input_id` is the durable identity used in mapping results. `cycle` is the
    current crack-growth acquisition coordinate used by nearest-cycle mapping.
    `sequence_index` is only a deterministic ordering hint and must not replace
    `input_id` as identity. `source_label` and `source_metadata` preserve
    source-specific vocabulary such as the current DIC `stage`.
    """

    input_id: str
    cycle: float | int | str | None = None
    sequence_index: int | None = None
    source_label: str | None = None
    source_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.input_id:
            raise ValueError("InputSequenceRecord requires a non-empty input_id.")
        if self.cycle is not None:
            try:
                object.__setattr__(self, "cycle", float(self.cycle))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Input {self.input_id!r} has non-numeric cycle metadata.") from exc


@dataclass(frozen=True)
class InputMappingResult:
    """Result of applying an input mapping policy.

    `policy_name` records the policy that produced the mapping.
    `input_id_to_representative_input_id` is the stable identity mapping.
    `skipped_input_ids` lists inputs that could not be mapped because required
    metadata was absent, for example missing cycle metadata.
    """

    policy_name: str
    input_id_to_representative_input_id: Mapping[str, str]
    skipped_input_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.policy_name:
            raise ValueError("InputMappingResult requires a non-empty policy_name.")


@dataclass(frozen=True)
class NearestCycleInputMappingPolicy:
    """Map inputs to representative inputs by nearest cycle metadata.

    The policy is intentionally independent of DIC stage numbers. Callers pass
    stable input IDs and optional source metadata; compatibility adapters may
    still translate legacy stages into input records before crossing this seam.
    Ties are resolved by representative `sequence_index` and then input ID so
    filtered input sequences remain deterministic.
    """

    policy_name: str = "nearest_cycle"

    def map_to_representatives(
            self,
            records: Sequence[InputSequenceRecord],
            representative_input_ids: Sequence[str],
    ) -> InputMappingResult:
        """Return an `input_id -> representative_input_id` nearest-cycle mapping.

        Args:
            records: Input records that may need a representative.
            representative_input_ids: Stable IDs of records eligible as representatives.

        Raises:
            ValueError: If input IDs are duplicated, no representatives are provided,
                a representative is unknown, or a representative has no cycle metadata.
        """
        records_by_id = self._records_by_id(records)
        representative_records = self._representative_records(records_by_id, representative_input_ids)

        mapping: dict[str, str] = {}
        skipped_input_ids: list[str] = []
        for record in records:
            if record.cycle is None:
                skipped_input_ids.append(record.input_id)
                continue
            mapping[record.input_id] = self._closest_representative(record, representative_records).input_id

        return InputMappingResult(
            policy_name=self.policy_name,
            input_id_to_representative_input_id=mapping,
            skipped_input_ids=tuple(skipped_input_ids),
        )

    @staticmethod
    def _records_by_id(records: Sequence[InputSequenceRecord]) -> dict[str, InputSequenceRecord]:
        records_by_id: dict[str, InputSequenceRecord] = {}
        for record in records:
            if record.input_id in records_by_id:
                raise ValueError(f"Duplicate input_id in input mapping records: {record.input_id!r}")
            records_by_id[record.input_id] = record
        return records_by_id

    @staticmethod
    def _representative_records(
            records_by_id: Mapping[str, InputSequenceRecord],
            representative_input_ids: Sequence[str],
    ) -> tuple[InputSequenceRecord, ...]:
        if not representative_input_ids:
            raise ValueError("Nearest-cycle input mapping requires at least one representative input.")

        representatives: list[InputSequenceRecord] = []
        for input_id in representative_input_ids:
            try:
                record = records_by_id[input_id]
            except KeyError as exc:
                raise ValueError(f"Unknown representative input_id: {input_id!r}") from exc
            if record.cycle is None:
                raise ValueError(f"Representative input {input_id!r} requires cycle metadata.")
            representatives.append(record)
        return tuple(representatives)

    @staticmethod
    def _closest_representative(
            record: InputSequenceRecord,
            representatives: Sequence[InputSequenceRecord],
    ) -> InputSequenceRecord:
        assert record.cycle is not None
        return min(
            representatives,
            key=lambda representative: (
                abs(representative.cycle - record.cycle),  # type: ignore[operator]
                representative.sequence_index is None,
                representative.sequence_index if representative.sequence_index is not None else 0,
                representative.input_id,
            ),
        )


def stage_input_id(stage: int | str) -> str:
    """Return the compatibility input ID for a legacy DIC stage label."""
    return f"stage:{stage}"


def map_stage_cycles_to_representative_stages(
        stage_to_cycle: Mapping[int, float],
        representative_cycle_to_stage: Mapping[float, int],
        *,
        policy: NearestCycleInputMappingPolicy | None = None,
) -> tuple[dict[int, int], InputMappingResult]:
    """Map legacy stages through stable input IDs and return compatibility stages.

    `stage` stays source metadata at this adapter seam. The returned
    `InputMappingResult` is the canonical policy output and uses input IDs; the
    first returned dictionary exists only so current pipelines can keep their
    public `stage -> representative_stage` behavior during migration.
    """
    policy = policy or NearestCycleInputMappingPolicy()
    records = tuple(
        InputSequenceRecord(
            input_id=stage_input_id(stage),
            cycle=cycle,
            sequence_index=stage,
            source_label=str(stage),
            source_metadata={"stage": stage},
        )
        for stage, cycle in sorted(stage_to_cycle.items())
    )
    stage_by_input_id = {record.input_id: record.source_metadata["stage"] for record in records}
    representative_input_ids = tuple(
        stage_input_id(stage)
        for _, stage in sorted(representative_cycle_to_stage.items())
    )

    mapping_result = policy.map_to_representatives(records, representative_input_ids)
    stage_mapping = {
        stage_by_input_id[input_id]: stage_by_input_id[representative_input_id]
        for input_id, representative_input_id in mapping_result.input_id_to_representative_input_id.items()
    }
    return stage_mapping, mapping_result

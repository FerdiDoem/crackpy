import pytest

from crackpy.input.input_mapping import (
    InputSequenceRecord,
    NearestCycleInputMappingPolicy,
    map_stage_cycles_to_representative_stages,
    stage_input_id,
)


def test_nearest_cycle_mapping_returns_stable_input_ids():
    records = (
        InputSequenceRecord(input_id="input:1", cycle=10.0, sequence_index=1),
        InputSequenceRecord(input_id="input:2", cycle=18.0, sequence_index=2),
        InputSequenceRecord(input_id="input:3", cycle=22.0, sequence_index=3),
    )

    result = NearestCycleInputMappingPolicy().map_to_representatives(
        records,
        representative_input_ids=("input:1", "input:3"),
    )

    assert result.policy_name == "nearest_cycle"
    assert result.input_id_to_representative_input_id == {
        "input:1": "input:1",
        "input:2": "input:3",
        "input:3": "input:3",
    }


def test_nearest_cycle_mapping_skips_inputs_without_cycle_metadata():
    records = (
        InputSequenceRecord(input_id="input:missing-cycle", sequence_index=1),
        InputSequenceRecord(input_id="input:representative", cycle=4.0, sequence_index=2),
    )

    result = NearestCycleInputMappingPolicy().map_to_representatives(
        records,
        representative_input_ids=("input:representative",),
    )

    assert result.input_id_to_representative_input_id == {
        "input:representative": "input:representative",
    }
    assert result.skipped_input_ids == ("input:missing-cycle",)


def test_nearest_cycle_mapping_tie_uses_sequence_index_before_input_id():
    records = (
        InputSequenceRecord(input_id="input:later", cycle=20.0, sequence_index=20),
        InputSequenceRecord(input_id="input:target", cycle=15.0, sequence_index=15),
        InputSequenceRecord(input_id="input:earlier", cycle=10.0, sequence_index=10),
    )

    result = NearestCycleInputMappingPolicy().map_to_representatives(
        records,
        representative_input_ids=("input:later", "input:earlier"),
    )

    assert result.input_id_to_representative_input_id["input:target"] == "input:earlier"


def test_nearest_cycle_mapping_handles_filtered_sequence_gaps():
    records = (
        InputSequenceRecord(input_id="input:stage-10", cycle="100.0", sequence_index=10),
        InputSequenceRecord(input_id="input:stage-40", cycle="135.0", sequence_index=40),
        InputSequenceRecord(input_id="input:stage-80", cycle="180.0", sequence_index=80),
    )

    result = NearestCycleInputMappingPolicy().map_to_representatives(
        records,
        representative_input_ids=("input:stage-80",),
    )

    assert result.input_id_to_representative_input_id == {
        "input:stage-10": "input:stage-80",
        "input:stage-40": "input:stage-80",
        "input:stage-80": "input:stage-80",
    }


def test_nearest_cycle_mapping_rejects_invalid_representatives():
    records = (
        InputSequenceRecord(input_id="input:1", cycle=1.0),
        InputSequenceRecord(input_id="input:no-cycle"),
    )

    with pytest.raises(ValueError, match="requires cycle metadata"):
        NearestCycleInputMappingPolicy().map_to_representatives(
            records,
            representative_input_ids=("input:no-cycle",),
        )


def test_stage_cycle_adapter_preserves_stage_labels_as_metadata():
    stage_mapping, input_mapping = map_stage_cycles_to_representative_stages(
        stage_to_cycle={52: 888983.0, 53: 901098.0, 54: 901099.0, 55: 901100.0},
        representative_cycle_to_stage={888983.0: 52, 901100.0: 55},
    )

    assert stage_mapping == {
        52: 52,
        53: 55,
        54: 55,
        55: 55,
    }
    assert input_mapping.input_id_to_representative_input_id[stage_input_id(53)] == stage_input_id(55)

import pytest

from crackpy.input.input_data import InputData
from crackpy.provenance import (
    MethodResultSource,
    SourceInput,
    SourceParameters,
    input_record_from_source_input,
    input_records_from_source_inputs,
)
from crackpy.provenance.builder import MethodResultEnvelopeBuilder
from crackpy.provenance.spec import ProvenanceSliceSpec


def test_source_input_projects_to_canonical_input_record():
    source_input = SourceInput(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_metadata={"force": 100.0, "stage": 53},
        source_label="DemoNodemap",
        sequence_index=7,
        source_hash="sha256:demo",
    )

    input_record = input_record_from_source_input(source_input)

    assert input_record.input_id == "input:demo"
    assert input_record.provenance_id == "input:demo"
    assert input_record.data_ref == "DemoNodemap.txt"
    assert input_record.source_metadata == {"force": 100.0, "stage": 53}
    assert input_record.source_label == "DemoNodemap"
    assert input_record.sequence_index == 7
    assert input_record.source_hash == "sha256:demo"


def test_input_data_source_input_projects_through_record_adapter():
    data = InputData()
    data.nodemap_file = r"C:\data\DemoNodemap.txt"
    data.force = 100.0
    data.cycles = 4

    input_record = input_record_from_source_input(data.source_input(sequence_index=4))

    assert input_record.input_id == "input:DemoNodemap"
    assert input_record.data_ref == r"C:\data\DemoNodemap.txt"
    assert input_record.source_metadata == {"force": 100.0, "cycles": 4}
    assert input_record.sequence_index == 4


def test_input_record_collection_rejects_duplicate_input_ids():
    source_inputs = (
        SourceInput(input_id="input:demo", data_ref="DemoNodemap.txt"),
        SourceInput(input_id="input:demo", data_ref="OtherNodemap.txt"),
    )

    with pytest.raises(ValueError, match="Duplicate input_id"):
        input_records_from_source_inputs(source_inputs)


def test_method_envelope_builder_uses_shared_input_record_projection():
    source = MethodResultSource(
        inputs=(SourceInput(input_id="input:demo", data_ref="DemoNodemap.txt", sequence_index=3),),
        dependencies=(),
        parameters=SourceParameters(result_parameters={}, parameter_origins={}),
        quantities=(),
    )
    spec = ProvenanceSliceSpec.model_validate(
        {
            "schemas": {
                "envelope": "crackpy.result_envelope.demo.v1",
                "result": "crackpy.result_record.demo.v1",
                "configuration": "crackpy.configuration.demo.v1",
                "kg_statement_bundle": "crackpy.kg_statement_bundle.demo.v1",
            },
            "methods": {
                "analysis": {
                    "method_id": "crackpy.demo.method",
                    "display_name": "Demo Method",
                    "kind": "analysis",
                    "method_revision": "1",
                    "implementation_ref": "crackpy.demo",
                }
            },
            "dependencies": {},
            "quantities": {},
        }
    )

    input_records = MethodResultEnvelopeBuilder(source, spec).input_records()

    assert len(input_records) == 1
    assert input_records[0].input_id == "input:demo"
    assert input_records[0].sequence_index == 3

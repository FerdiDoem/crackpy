from pathlib import Path
from inspect import signature
from types import SimpleNamespace

import pytest

from crackpy.results import result_data
from crackpy.results.result_data import (
    AnalysisRun,
    ArtifactRef,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    InputRecord,
    MethodMetadata,
    NormalizedConfiguration,
    ResultEnvelope,
    ResultQuantity,
    ResultRecord,
    ResultSchemaIndex,
    canonical_json_bytes,
    sha256_canonical_json,
    to_jsonable,
    write_json_file,
)
from crackpy.provenance import SourceDependency
from crackpy.fracture_analysis.methods.williams_fit.parameters import (
    RESOLVED_OPTIMIZATION_ORIGIN,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
)
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsCoefficientSet, WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec


def test_generic_provenance_types_are_available_from_deeper_module():
    from crackpy.provenance import MethodResultSource, SourceDependency, SourceParameters, SourceQuantity

    assert MethodResultSource.__name__ == "MethodResultSource"
    assert SourceDependency.__name__ == "SourceDependency"
    assert SourceParameters.__name__ == "SourceParameters"
    assert SourceQuantity.__name__ == "SourceQuantity"


def test_williams_fit_spec_loads_from_method_module():
    from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec

    spec = load_williams_fit_spec()

    assert spec.schemas.envelope == "crackpy.result_envelope.williams_fit.v1"
    assert spec.dependencies["crack_tip_frame"].role == "used_crack_tip_frame"


def test_generic_result_records_do_not_define_williams_schema_versions():
    assert not hasattr(result_data, "WILLIAMS_FIT_ENVELOPE_SCHEMA")
    assert not hasattr(result_data, "WILLIAMS_FIT_RESULT_SCHEMA")
    assert not hasattr(result_data, "WILLIAMS_FIT_CONFIGURATION_SCHEMA")
    assert not hasattr(result_data, "WILLIAMS_FIT_KG_BUNDLE_SCHEMA")


def test_canonical_json_hash_is_stable_for_key_order():
    left = {"b": 2, "a": {"y": 1.0, "x": [3, 2, 1]}}
    right = {"a": {"x": [3, 2, 1], "y": 1.0}, "b": 2}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_canonical_json(left) == sha256_canonical_json(right)
    assert sha256_canonical_json(left).startswith("sha256:")


def test_non_finite_numbers_become_json_null():
    payload = {"nan": float("nan"), "positive_inf": float("inf"), "negative_inf": float("-inf")}

    assert to_jsonable(payload) == {"nan": None, "positive_inf": None, "negative_inf": None}


def test_normalized_configuration_hash_scopes_are_separate():
    configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [-1, 1, 2], "angle_gap_deg": 20.0},
        parameter_origins={"terms": "caller-provided", "angle_gap_deg": "model default"},
        adapter_policy={"write_legacy_json": True},
    )
    changed_adapter = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [-1, 1, 2], "angle_gap_deg": 20.0},
        parameter_origins={"terms": "caller-provided", "angle_gap_deg": "model default"},
        adapter_policy={"write_legacy_json": False},
    )

    assert configuration.parameter_hash == changed_adapter.parameter_hash
    assert configuration.configuration_hash != changed_adapter.configuration_hash


def test_result_envelope_to_dict_contains_schema_and_nested_records(tmp_path):
    input_record = InputRecord(input_id="input:demo", data_ref="demo.txt")
    method = MethodMetadata(
        method_id="crackpy.fracture.williams_fit",
        display_name="Williams Fit",
        kind="analysis",
        method_revision="1",
        implementation_ref="crackpy.fracture_analysis.analysis.FractureAnalysis._run_williams_optimization",
    )
    configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [1, 2]},
        parameter_origins={"terms": "caller-provided"},
        adapter_policy={},
    )
    frame = CrackTipFrame(
        frame_id="frame:demo",
        tip_id="tip:demo",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=3.0,
        compatibility_side="right",
    )
    estimate = CrackTipEstimateResult(
        estimate_id="estimate:demo",
        input_id=input_record.input_id,
        method_id="crackpy.crack_tip.manual_import",
        configuration_id=configuration.configuration_id,
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm={"x": 1.0, "y": 2.0},
        corrected_mm={"x": 1.0, "y": 2.0},
    )
    run = AnalysisRun(
        run_id="run:demo",
        method_id=method.method_id,
        method_revision=method.method_revision,
        input_ids=[input_record.input_id],
        configuration_id=configuration.configuration_id,
        parameter_hash=configuration.parameter_hash,
        dependencies=[
            DependencyEdge(source_id="run:demo", target_id="input:demo", role="used_input", target_type="InputRecord")
        ],
        crackpy_version="test",
    )
    quantity = ResultQuantity(
        quantity_id="quantity:demo:K_I",
        result_id="result:demo",
        symbol="K_I",
        description="Mode I stress intensity factor derived from Williams coefficient a_1.",
        value=12.5,
        unit="MPa*m^{1/2}",
        method_id=method.method_id,
        legacy_aliases=["Williams_fit_results.K_I"],
    )
    result = ResultRecord(
        result_id="result:demo",
        run_id=run.run_id,
        result_schema_version="crackpy.result_record.williams_fit.v1",
        quantities=[quantity],
        artifacts=[ArtifactRef(artifact_id="artifact:demo", role="canonical_envelope", path="demo.json")],
    )
    envelope = ResultEnvelope(
        input_records=[input_record],
        methods=[method],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=[run],
        results=[result],
        envelope_schema_version=load_williams_fit_spec().schemas.envelope,
    )

    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == load_williams_fit_spec().schemas.envelope
    assert payload["results"][0]["quantities"][0]["legacy_aliases"] == ["Williams_fit_results.K_I"]

    target = tmp_path / "envelope.json"
    write_json_file(payload, target)
    assert target.read_text(encoding="utf-8").startswith("{")


def test_provenance_records_expose_explicit_identity_properties():
    input_record = InputRecord(input_id="input:demo", data_ref="demo.txt")
    frame = CrackTipFrame(
        frame_id="frame:demo",
        tip_id="tip:demo",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=3.0,
    )
    estimate = CrackTipEstimateResult(
        estimate_id="estimate:demo",
        input_id=input_record.input_id,
        method_id="crackpy.crack_tip.manual_import",
        configuration_id="configuration:demo",
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm={"x": 1.0, "y": 2.0},
        corrected_mm={"x": 1.0, "y": 2.0},
    )

    assert input_record.provenance_id == "input:demo"
    assert frame.provenance_id == "frame:demo"
    assert estimate.provenance_id == "estimate:demo"


def test_provenance_spec_models_document_all_fields():
    from crackpy.provenance import spec as spec_models
    from crackpy.fracture_analysis.methods.williams_fit import spec_loader as williams_spec_models

    for model in (
        spec_models.SchemaVersions,
        spec_models.MethodSpec,
        spec_models.DependencySpec,
        spec_models.QuantitySpec,
        spec_models.ProvenanceSliceSpec,
        williams_spec_models.WilliamsCoefficientQuantitySpec,
        williams_spec_models.WilliamsFitSliceSpec,
    ):
        missing_descriptions = [
            field_name
            for field_name, model_field in model.model_fields.items()
            if not model_field.description
        ]
        assert missing_descriptions == []


def test_provenance_slice_spec_rejects_key_name_drift():
    from crackpy.provenance.spec import ProvenanceSliceSpec

    payload = {
        "schemas": {
            "envelope": "crackpy.result_envelope.williams_fit.v1",
            "result": "crackpy.result_record.williams_fit.v1",
            "configuration": "crackpy.configuration.williams_fit.v1",
            "kg_statement_bundle": "crackpy.kg_statement_bundle.williams_fit.v1",
        },
        "methods": {
            "analysis": {
                "method_id": "crackpy.fracture.williams_fit",
                "display_name": "Williams Fit",
                "kind": "analysis",
                "method_revision": "1",
                "implementation_ref": "crackpy.fracture_analysis.methods.williams_fit",
            }
        },
        "dependencies": {
            "crack_tip_frame": {
                "dependency_name": "wrong_dependency_name",
                "role": "used_crack_tip_frame",
                "target_type": "CrackTipFrame",
            }
        },
        "quantities": {
            "K_I": {
                "quantity_name": "wrong_quantity_name",
                "symbol": "K_I",
                "description": "Mode I stress intensity factor.",
                "unit": "MPa*m^{1/2}",
            }
        },
    }

    with pytest.raises(ValueError, match="dependencies\\['crack_tip_frame'\\]"):
        ProvenanceSliceSpec.model_validate(payload)

    payload["dependencies"]["crack_tip_frame"]["dependency_name"] = "crack_tip_frame"
    with pytest.raises(ValueError, match="quantities\\['K_I'\\]"):
        ProvenanceSliceSpec.model_validate(payload)


def test_generic_provenance_contains_no_coefficient_specific_schema_or_builder_api():
    from crackpy.provenance import MethodResultEnvelopeBuilder
    from crackpy.provenance import spec as spec_models

    assert not hasattr(spec_models, "CoefficientQuantitySpec")
    assert "coefficient_quantity" not in spec_models.ProvenanceSliceSpec.model_fields
    assert "coefficient_unit" not in signature(MethodResultEnvelopeBuilder.result_quantity_from_source).parameters


def test_generic_provenance_contains_no_method_specific_vocabulary():
    from crackpy import provenance

    forbidden_terms = ("williams", "coefficient")
    offenders = []
    for path in Path(provenance.__file__).parent.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            if term in text:
                offenders.append(f"{path.name}:{term}")

    assert offenders == []


def test_source_dependency_record_requires_explicit_provenance_identity():
    class UnidentifiedRecord:
        frame_id = "frame:legacy-shape"

    with pytest.raises(TypeError, match="provenance_id"):
        SourceDependency(dependency_name="crack_tip_frame", record=UnidentifiedRecord())


from crackpy.fracture_analysis.methods.williams_fit import (
    build_williams_fit_envelope_from_analysis,
    build_williams_fit_envelope_from_result,
    source_from_analysis,
)


def _fake_analysis():
    data = SimpleNamespace(
        force=100.0,
        cycles=200.0,
        displacement=0.3,
        potential=None,
        cracklength=4.5,
        time=None,
    )
    crack_tip = SimpleNamespace(
        crack_tip_x=1.5,
        crack_tip_y=2.5,
        crack_tip_angle=12.0,
        left_or_right="right",
    )
    material = SimpleNamespace(
        name="AA2024-T3",
        E=72000,
        nu_xy=0.33,
        sig_yield=350,
        plane_strain=False,
        G=27067.66917293233,
        kappa=2.007518796992481,
    )
    optimization_properties = SimpleNamespace(
        angle_gap=20,
        min_radius=0.2,
        max_radius=1.0,
        tick_size=0.01,
        terms=[-1, 1, 2],
    )
    return SimpleNamespace(
        nodemap_file="DemoNodemap.txt",
        data=data,
        crack_tip=crack_tip,
        material=material,
        optimization_properties=optimization_properties,
        williams_fit_res={
            "Error_xy": 0.1,
            "Error_z": float("nan"),
            "K_I": 12.5,
            "K_II": -2.0,
            "K_III": float("nan"),
            "T": 4.0,
        },
        williams_fit_a_n={-1: 0.01, 1: 2.0, 2: 1.0},
        williams_fit_b_n={-1: 0.02, 1: -0.5, 2: 0.3},
        williams_fit_c_n={-1: float("nan"), 1: float("nan"), 2: float("nan")},
    )


def test_build_williams_fit_envelope_maps_current_result_section():
    envelope = build_williams_fit_envelope_from_analysis(_fake_analysis(), crackpy_version="test-version")
    payload = envelope.to_dict()

    assert payload["envelope_schema_version"] == "crackpy.result_envelope.williams_fit.v1"
    assert payload["input_records"][0]["input_id"] == "input:DemoNodemap"
    assert payload["crack_tip_frames"][0]["angle_deg"] == 12.0
    assert payload["crack_tip_frames"][0]["compatibility_side"] == "right"
    assert payload["analysis_runs"][0]["dependencies"][0]["role"] == "used_input"
    assert payload["analysis_runs"][0]["crackpy_version"] == "test-version"

    result = payload["results"][0]
    quantities = {quantity["symbol"]: quantity for quantity in result["quantities"]}
    assert quantities["K_I"]["legacy_aliases"] == ["Williams_fit_results.K_I"]
    assert quantities["error_xy"]["legacy_aliases"] == ["Williams_fit_results.error_xy", "Error_xy"]
    assert quantities["a_-1"]["legacy_aliases"] == ["Williams_fit_results.a_-1"]
    assert quantities["c_1"]["value"] is None


def _typed_williams_envelope() -> ResultEnvelope:
    frame = CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    parameters = WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=WilliamsOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, terms=(-1, 1, 2)),
    )
    result = WilliamsFitResult(
        error_xy=0.1,
        error_z=float("nan"),
        K_I=12.5,
        K_II=-2.0,
        K_III=float("nan"),
        T=4.0,
        coefficients=WilliamsCoefficientSet(
            a={-1: 0.01, 1: 2.0, 2: 1.0},
            b={-1: 0.02, 1: -0.5, 2: 0.3},
            c={-1: float("nan"), 1: float("nan"), 2: float("nan")},
        ),
    )
    return build_williams_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
        crackpy_version="test-version",
    )


def test_source_dependency_requires_record_or_target_id_exclusively():
    with pytest.raises(ValueError, match="exactly one"):
        SourceDependency(dependency_name="crack_tip_frame")

    frame = CrackTipFrame(
        frame_id="frame:demo",
        tip_id="tip:demo",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=3.0,
    )

    with pytest.raises(ValueError, match="exactly one"):
        SourceDependency(dependency_name="crack_tip_frame", record=frame, target_id=frame.frame_id)


def test_williams_fit_source_snapshot_uses_dependencies_parameters_and_quantities():
    source = source_from_analysis(_fake_analysis())

    assert source.inputs[0].input_id == "input:DemoNodemap"
    assert "crack_tip_frame" not in source.parameters.result_parameters
    assert source.parameters.result_parameters["optimization"]["terms"] == [-1, 1, 2]

    frame_dependencies = [dependency for dependency in source.dependencies if dependency.dependency_name == "crack_tip_frame"]
    assert len(frame_dependencies) == 1
    assert isinstance(frame_dependencies[0].record, CrackTipFrame)
    assert frame_dependencies[0].target_id is None

    coefficient_quantities = [
        quantity
        for quantity in source.quantities
        if quantity.quantity_name == "williams_coefficient" and quantity.qualifiers["term_order"] == -1
    ]
    assert {quantity.qualifiers["coefficient_series"] for quantity in coefficient_quantities} == {"a", "b", "c"}


def test_williams_fit_source_from_analysis_requires_input_identity():
    analysis = _fake_analysis()
    del analysis.nodemap_file

    with pytest.raises(AttributeError, match="nodemap_file"):
        source_from_analysis(analysis)


def test_williams_fit_parameter_model_documents_explicit_method_fields():
    parameters = WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=WilliamsOptimizationParameters(angle_gap_deg=20, terms=(-1, 1, 2)),
    )

    assert parameters.result_parameters()["material"]["E_MPa"] == 72000
    assert parameters.result_parameters()["optimization"]["angle_gap_deg"] == 20
    assert parameters.result_parameters()["optimization"]["terms"] == [-1, 1, 2]
    assert parameters.parameter_origins()["angle_gap_deg"] == RESOLVED_OPTIMIZATION_ORIGIN
    assert WilliamsMaterialParameters.model_fields["E_MPa"].description
    assert WilliamsOptimizationParameters.model_fields["angle_gap_deg"].description


def test_williams_fit_spec_defines_quantities_dependencies_and_lower_case_series():
    spec = load_williams_fit_spec()

    assert spec.schemas.configuration == "crackpy.configuration.williams_fit.v1"
    assert spec.dependencies["crack_tip_frame"].role == "used_crack_tip_frame"
    assert spec.quantities["K_I"].legacy_aliases == ("Williams_fit_results.K_I",)
    assert spec.coefficient_quantity.quantity_name == "williams_coefficient"
    assert spec.coefficient_quantity.allowed_coefficient_series == ("a", "b", "c")


def test_build_williams_fit_envelope_uses_normalized_source_parameters():
    envelope = build_williams_fit_envelope_from_analysis(_fake_analysis(), crackpy_version="test-version")
    configuration = envelope.configurations[0]

    assert "crack_tip_frame" not in configuration.result_parameters
    assert configuration.result_parameters["material"]["name"] == "AA2024-T3"
    assert configuration.result_parameters["optimization"]["angle_gap_deg"] == 20


def test_build_williams_fit_envelope_rejects_missing_williams_results():
    analysis = _fake_analysis()
    analysis.williams_fit_res = None

    with pytest.raises(ValueError, match="Williams fit results"):
        build_williams_fit_envelope_from_analysis(analysis, crackpy_version="test-version")


from crackpy.results.write import OutputWriter
from crackpy.results.write import write_williams_fit_provenance_artifacts


def test_output_writer_writes_new_provenance_artifacts_without_changing_legacy_json(tmp_path):
    analysis = _fake_analysis()
    writer = OutputWriter(path=tmp_path, fracture_analysis=analysis)

    written = writer.write_williams_fit_provenance_artifacts(path=tmp_path)

    assert set(written) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    assert written["envelope"].name.endswith("_williams_fit_envelope.json")
    assert written["kg_statement_bundle"].name.endswith("_williams_fit_kg_statement_bundle.json")
    assert written["visualization_graph"].name.endswith("_williams_fit_graph.json")
    assert written["visualization_graph_html"].name.endswith("_williams_fit_graph.html")
    assert written["envelope"].exists()
    assert written["kg_statement_bundle"].exists()
    assert written["visualization_graph"].exists()
    assert written["visualization_graph_html"].exists()


def test_legacy_williams_fit_provenance_json_writer_keeps_artifact_behavior(tmp_path):
    analysis = _fake_analysis()
    writer = OutputWriter(path=tmp_path, fracture_analysis=analysis)

    written = writer.write_williams_fit_provenance_json(path=tmp_path)

    assert "visualization_graph_html" in written


def test_williams_provenance_artifact_writer_accepts_explicit_result_envelope(tmp_path):
    envelope = _typed_williams_envelope()

    written = write_williams_fit_provenance_artifacts(envelope, path=tmp_path, stem="explicit_result")

    assert set(written) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    assert written["envelope"].name == "explicit_result_williams_fit_envelope.json"
    assert written["kg_statement_bundle"].exists()
    assert written["visualization_graph"].exists()
    assert written["visualization_graph_html"].exists()


def test_result_schema_index_exposes_williams_legacy_aliases_from_envelope():
    envelope = _typed_williams_envelope()

    schema_index = ResultSchemaIndex.from_envelope(envelope)
    k_i = schema_index.entry_for_legacy_alias("Williams_fit_results.K_I")
    coefficient = schema_index.entry_for_symbol("a_-1")

    assert k_i.symbol == "K_I"
    assert k_i.unit == "MPa*m^{1/2}"
    assert k_i.result_schema_version == "crackpy.result_record.williams_fit.v1"
    assert k_i.envelope_schema_version == "crackpy.result_envelope.williams_fit.v1"
    assert coefficient.legacy_aliases == ("Williams_fit_results.a_-1",)


def test_result_schema_index_rejects_duplicate_legacy_aliases():
    quantity = ResultQuantity(
        quantity_id="quantity:demo:K_I",
        result_id="result:demo",
        symbol="K_I",
        description="Mode I stress intensity factor.",
        value=12.5,
        unit="MPa*m^{1/2}",
        method_id="crackpy.fracture.williams_fit",
        legacy_aliases=["Williams_fit_results.K_I"],
    )
    duplicate = ResultQuantity(
        quantity_id="quantity:demo:duplicate",
        result_id="result:demo",
        symbol="K_I_duplicate",
        description="Duplicate alias for validation.",
        value=12.5,
        unit="MPa*m^{1/2}",
        method_id="crackpy.fracture.williams_fit",
        legacy_aliases=["Williams_fit_results.K_I"],
    )
    envelope = ResultEnvelope(
        input_records=[],
        methods=[],
        configurations=[],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[],
        results=[
            ResultRecord(
                result_id="result:demo",
                run_id="run:demo",
                result_schema_version="crackpy.result_record.williams_fit.v1",
                quantities=[quantity, duplicate],
            )
        ],
        envelope_schema_version="crackpy.result_envelope.williams_fit.v1",
    )

    with pytest.raises(ValueError, match="Duplicate legacy result alias"):
        ResultSchemaIndex.from_envelope(envelope)

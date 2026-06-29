from pathlib import Path
from types import SimpleNamespace

from crackpy.results.result_data import CrackTipFrame, ResultEnvelope, ResultSchemaIndex


def _typed_cjp_inputs():
    from crackpy.fracture_analysis.methods.cjp_fit import (
        CjpFitResultParameters,
        CjpMaterialParameters,
        CjpOptimizationParameters,
        cjp_mode_i_outputs_from_coefficients,
        cjp_mixed_mode_outputs_from_coefficients,
    )

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    parameters = CjpFitResultParameters(
        material=CjpMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=CjpOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, max_radius_mm=1.0),
    )
    result = {
        "mixed_mode": cjp_mixed_mode_outputs_from_coefficients(
            [2.0, -0.5, 0.25, 30.0, 0.75],
            error=0.125,
        ),
        "mode_i": cjp_mode_i_outputs_from_coefficients(
            [3.0, -1.0, 25.0, 0.5, 12.0],
            error=0.25,
        ),
    }
    return frame, parameters, result


def _typed_cjp_result():
    from crackpy.fracture_analysis.methods.cjp_fit import CjpFitResult

    _, _, parts = _typed_cjp_inputs()
    return CjpFitResult(mixed_mode=parts["mixed_mode"], mode_i=parts["mode_i"])


def test_build_cjp_fit_envelope_from_typed_result_has_two_methods_runs_and_results():
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result

    frame, parameters, _ = _typed_cjp_inputs()
    result = _typed_cjp_result()

    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
        crackpy_version="test-version",
    )
    payload = envelope.to_dict()

    assert payload["envelope_schema_version"] == "crackpy.result_envelope.cjp_fit.v1"
    assert payload["input_records"][0]["input_id"] == "input:demo"
    assert len(payload["configurations"]) == 1
    assert len(payload["analysis_runs"]) == 2
    assert len(payload["results"]) == 2
    assert {method["method_id"] for method in payload["methods"]} == {
        "crackpy.fracture.cjp_mixed_mode_fit",
        "crackpy.fracture.cjp_mode_i_fit",
        "crackpy.crack_tip.manual_import",
    }
    assert {result_record["run_id"] for result_record in payload["results"]} == {
        payload["analysis_runs"][0]["run_id"],
        payload["analysis_runs"][1]["run_id"],
    }


def test_build_cjp_fit_envelope_splits_quantities_by_variant():
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result

    frame, parameters, _ = _typed_cjp_inputs()
    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=_typed_cjp_result(),
        crackpy_version="test-version",
    )
    runs_by_id = {run.run_id: run for run in envelope.analysis_runs}
    results_by_method = {runs_by_id[result.run_id].method_id: result for result in envelope.results}
    mixed_symbols = {quantity.symbol for quantity in results_by_method["crackpy.fracture.cjp_mixed_mode_fit"].quantities}
    mode_i_symbols = {quantity.symbol for quantity in results_by_method["crackpy.fracture.cjp_mode_i_fit"].quantities}

    assert {"A_r", "B_i", "K_II", "T"} <= mixed_symbols
    assert "T_y" not in mixed_symbols
    assert {"A", "F", "K_F", "T_y"} <= mode_i_symbols
    assert "K_II" not in mode_i_symbols


def test_result_schema_index_resolves_cjp_duplicate_symbols_with_context():
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result

    frame, parameters, _ = _typed_cjp_inputs()
    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=_typed_cjp_result(),
        crackpy_version="test-version",
    )

    schema_index = ResultSchemaIndex.from_envelope(envelope)
    error_entries = schema_index.entries_for_symbol("error")
    mixed_error = schema_index.entry_for_symbol_for_method("error", "crackpy.fracture.cjp_mixed_mode_fit")
    mode_i_error = schema_index.entry_for_legacy_alias("CJP_modeI_results.error")

    assert len(error_entries) == 2
    assert mixed_error.legacy_aliases == ("CJP_results.error", "CJP_results.Error")
    assert mode_i_error.method_id == "crackpy.fracture.cjp_mode_i_fit"
    assert mode_i_error.result_id != mixed_error.result_id


def test_result_schema_index_requires_context_for_ambiguous_cjp_symbol():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result

    frame, parameters, _ = _typed_cjp_inputs()
    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=_typed_cjp_result(),
        crackpy_version="test-version",
    )

    schema_index = ResultSchemaIndex.from_envelope(envelope)

    with pytest.raises(ValueError, match="ambiguous.*result IDs"):
        schema_index.entry_for_symbol("error")


def test_build_cjp_fit_envelope_accepts_direct_source_fixture():
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_source
    from crackpy.provenance import MethodResultSource, SourceDependency, SourceInput, SourceParameters, SourceQuantity

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:direct:right",
        tip_id="crack_tip:direct:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    source = MethodResultSource(
        inputs=(
            SourceInput(
                input_id="input:direct",
                data_ref="DirectNodemap.txt",
                source_label="direct",
                sequence_index=3,
            ),
        ),
        dependencies=(SourceDependency("crack_tip_frame", record=frame),),
        parameters=SourceParameters(
            result_parameters={"optimization": {"angle_gap_deg": 20.0}, "material": {"E_MPa": 72000}},
            parameter_origins={"angle_gap_deg": "direct fixture", "material": "direct fixture"},
            adapter_policy={"test_fixture": True},
        ),
        quantities=(
            SourceQuantity("mixed_mode.K_II", 1.25, {"variant": "mixed_mode"}),
            SourceQuantity("mode_i.T_y", -12.0, {"variant": "mode_i"}),
        ),
    )

    envelope = build_cjp_fit_envelope_from_source(source, crackpy_version="test-version")

    assert envelope.input_records[0].input_id == "input:direct"
    assert envelope.input_records[0].sequence_index == 3
    assert envelope.configurations[0].adapter_policy["test_fixture"] is True
    assert len(envelope.analysis_runs) == 2
    assert {dependency.role for run in envelope.analysis_runs for dependency in run.dependencies} >= {
        "used_input",
        "used_configuration",
        "used_crack_tip_frame",
        "used_crack_tip_estimate",
    }


def test_build_cjp_fit_envelope_rejects_undeclared_quantity_qualifier():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_source
    from crackpy.provenance import MethodResultSource, SourceDependency, SourceInput, SourceParameters, SourceQuantity

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:direct:right",
        tip_id="crack_tip:direct:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    source = MethodResultSource(
        inputs=(SourceInput(input_id="input:direct", data_ref="DirectNodemap.txt", source_label="direct"),),
        dependencies=(SourceDependency("crack_tip_frame", record=frame),),
        parameters=SourceParameters(result_parameters={}, parameter_origins={}),
        quantities=(SourceQuantity("mixed_mode.K_II", 1.25, {"variant": "mixed_mode", "path_index": 0}),),
    )

    with pytest.raises(ValueError, match="Unsupported qualifiers.*path_index"):
        build_cjp_fit_envelope_from_source(source, crackpy_version="test-version")


def test_build_cjp_fit_envelope_requires_variant_qualifier():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_source
    from crackpy.provenance import MethodResultSource, SourceDependency, SourceInput, SourceParameters, SourceQuantity

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:direct:right",
        tip_id="crack_tip:direct:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    source = MethodResultSource(
        inputs=(SourceInput(input_id="input:direct", data_ref="DirectNodemap.txt", source_label="direct"),),
        dependencies=(SourceDependency("crack_tip_frame", record=frame),),
        parameters=SourceParameters(result_parameters={}, parameter_origins={}),
        quantities=(SourceQuantity("mixed_mode.K_II", 1.25),),
    )

    with pytest.raises(ValueError, match="requires variant qualifier"):
        build_cjp_fit_envelope_from_source(source, crackpy_version="test-version")


def test_cjp_envelope_builder_requires_stable_input_identity():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result

    frame, parameters, _ = _typed_cjp_inputs()

    with pytest.raises(ValueError, match="data_ref"):
        build_cjp_fit_envelope_from_result(
            input_id="input:demo",
            data_ref="",
            source_label=None,
            crack_tip_frame=frame,
            parameters=parameters,
            result=_typed_cjp_result(),
        )


def test_cjp_provenance_artifact_writer_accepts_explicit_result_envelope(tmp_path):
    from crackpy.results.write import write_cjp_fit_provenance_artifacts

    envelope = ResultEnvelope(
        input_records=[],
        methods=[],
        configurations=[],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[],
        results=[],
        envelope_schema_version="crackpy.result_envelope.cjp_fit.v1",
    )

    written = write_cjp_fit_provenance_artifacts(envelope, path=tmp_path, stem="explicit_result")

    assert set(written) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    assert written["envelope"].name == "explicit_result_cjp_fit_envelope.json"
    assert written["kg_statement_bundle"].name == "explicit_result_cjp_fit_kg_statement_bundle.json"
    assert written["visualization_graph"].name == "explicit_result_cjp_fit_graph.json"
    assert written["visualization_graph_html"].name == "explicit_result_cjp_fit_graph.html"
    assert written["envelope"].exists()
    assert written["kg_statement_bundle"].exists()
    assert written["visualization_graph"].exists()
    assert written["visualization_graph_html"].exists()


def _fake_cjp_analysis():
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
    )
    return SimpleNamespace(
        nodemap_file="DemoNodemap.txt",
        crack_tip=crack_tip,
        material=material,
        optimization_properties=optimization_properties,
        cjp_coeffs_mm=[2.0, -0.5, 0.25, 30.0, 0.75],
        cjp_res_mm={"Error": 0.125, "K_F": -0.1, "K_R": -0.2, "K_S": -0.3, "K_II": 0.4, "T": -30.0},
        cjp_coeffs_m1=[3.0, -1.0, 25.0, 0.5, 12.0],
        cjp_res_m1={"Error": 0.25, "K_F": 0.5, "K_R": -0.6, "K_S": 0.7, "T_x": -25.0, "T_y": -12.0},
    )


def test_output_writer_writes_cjp_provenance_artifacts_from_current_analysis_shape(tmp_path):
    from crackpy.results.write import OutputWriter

    writer = OutputWriter(path=tmp_path, fracture_analysis=_fake_cjp_analysis())

    written = writer.write_cjp_fit_provenance_artifacts(path=tmp_path)

    assert set(written) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    assert written["envelope"].name.endswith("_cjp_fit_envelope.json")
    assert written["kg_statement_bundle"].name.endswith("_cjp_fit_kg_statement_bundle.json")
    assert written["visualization_graph"].name.endswith("_cjp_fit_graph.json")
    assert written["visualization_graph_html"].name.endswith("_cjp_fit_graph.html")
    assert written["envelope"].exists()

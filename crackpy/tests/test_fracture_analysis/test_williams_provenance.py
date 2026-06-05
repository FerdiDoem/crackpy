from pathlib import Path
from types import SimpleNamespace

import pytest

from crackpy.results.result_data import (
    WILLIAMS_FIT_ENVELOPE_SCHEMA,
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
    canonical_json_bytes,
    sha256_canonical_json,
    to_jsonable,
    write_json_file,
)


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
    )

    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == WILLIAMS_FIT_ENVELOPE_SCHEMA
    assert payload["results"][0]["quantities"][0]["legacy_aliases"] == ["Williams_fit_results.K_I"]

    target = tmp_path / "envelope.json"
    write_json_file(payload, target)
    assert target.read_text(encoding="utf-8").startswith("{")

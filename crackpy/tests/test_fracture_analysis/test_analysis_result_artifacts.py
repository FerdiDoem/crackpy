from pathlib import Path

import pytest

from crackpy.results.analysis_result import (
    AnalysisResult,
    AnalysisResultArtifactPaths,
    MethodEnvelopeArtifactPlan,
    write_analysis_result_artifacts,
)
from crackpy.results.envelope_artifacts import ResultEnvelopeArtifactPaths
from crackpy.results.result_data import (
    AnalysisRun,
    MethodMetadata,
    NormalizedConfiguration,
    ResultEnvelope,
    ResultQuantity,
    ResultRecord,
)


def _method_envelope(method_key: str, *, symbol: str = "K_I") -> ResultEnvelope:
    method_id = f"crackpy.fracture.{method_key}"
    configuration_id = f"configuration:{method_key}:demo"
    run_id = f"run:{method_key}:demo"
    result_id = f"result:{method_key}:demo"
    configuration = NormalizedConfiguration.create(
        configuration_id=configuration_id,
        schema_version=f"crackpy.configuration.{method_key}.v1",
        result_parameters={"fixture": True},
        parameter_origins={"fixture": "test"},
    )
    return ResultEnvelope(
        input_records=[],
        methods=[
            MethodMetadata(
                method_id=method_id,
                display_name=f"{method_key} demo",
                kind="analysis",
                method_revision="1",
                implementation_ref=f"crackpy.demo.{method_key}",
            )
        ],
        configurations=[configuration],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[
            AnalysisRun(
                run_id=run_id,
                method_id=method_id,
                method_revision="1",
                input_ids=[],
                configuration_id=configuration.configuration_id,
                parameter_hash=configuration.parameter_hash,
                dependencies=[],
                crackpy_version="test-version",
            )
        ],
        results=[
            ResultRecord(
                result_id=result_id,
                run_id=run_id,
                result_schema_version=f"crackpy.result_record.{method_key}.v1",
                quantities=[
                    ResultQuantity(
                        quantity_id=f"quantity:{method_key}:{symbol}",
                        result_id=result_id,
                        symbol=symbol,
                        description=f"Demo quantity for {method_key}.",
                        value=1.25,
                        unit="MPa*m^{1/2}",
                        method_id=method_id,
                    )
                ],
            )
        ],
        envelope_schema_version=f"crackpy.result_envelope.{method_key}.v1",
    )


def test_analysis_result_writes_method_artifacts_without_fracture_analysis(tmp_path):
    analysis_result = AnalysisResult(
        analysis_result_id="analysis_result:demo",
        source_label="DemoNodemap",
        method_artifacts=(
            MethodEnvelopeArtifactPlan(
                method_key="williams_fit",
                envelope=_method_envelope("williams_fit", symbol="K_I"),
                artifact_stem="demo_williams_fit",
                graph_title="Williams Fit Result Graph",
            ),
            MethodEnvelopeArtifactPlan(
                method_key="cjp_fit",
                envelope=_method_envelope("cjp_fit", symbol="K_II"),
                artifact_stem="demo_cjp_fit",
                graph_title="CJP Fit Result Graph",
            ),
        ),
    )

    written = write_analysis_result_artifacts(analysis_result, tmp_path)

    assert isinstance(written, AnalysisResultArtifactPaths)
    assert set(written.method_artifacts) == {"williams_fit", "cjp_fit"}
    assert all(isinstance(paths, ResultEnvelopeArtifactPaths) for paths in written.method_artifacts.values())
    assert written.method_artifacts["williams_fit"].envelope == tmp_path / "demo_williams_fit_envelope.json"
    assert written.method_artifacts["cjp_fit"].visualization_graph == tmp_path / "demo_cjp_fit_graph.json"
    assert all(path.exists() for paths in written.as_dict().values() for path in paths.values())


def test_analysis_result_artifact_paths_preserve_nested_dictionary_shape():
    williams_paths = ResultEnvelopeArtifactPaths(
        envelope=Path("williams_envelope.json"),
        kg_statement_bundle=Path("williams_kg.json"),
        visualization_graph=Path("williams_graph.json"),
        visualization_graph_html=Path("williams_graph.html"),
    )
    written = AnalysisResultArtifactPaths(
        analysis_result_id="analysis_result:demo",
        method_artifacts={"williams_fit": williams_paths},
    )

    assert written.as_dict() == {"williams_fit": williams_paths.as_dict()}


def test_analysis_result_rejects_ambiguous_artifact_plans():
    plan = MethodEnvelopeArtifactPlan(
        method_key="williams_fit",
        envelope=_method_envelope("williams_fit"),
        artifact_stem="demo",
        graph_title="Williams Fit Result Graph",
    )

    with pytest.raises(ValueError, match="unique method_key"):
        AnalysisResult(analysis_result_id="analysis_result:demo", method_artifacts=(plan, plan))

    duplicate_stem = MethodEnvelopeArtifactPlan(
        method_key="cjp_fit",
        envelope=_method_envelope("cjp_fit"),
        artifact_stem="demo",
        graph_title="CJP Fit Result Graph",
    )
    with pytest.raises(ValueError, match="unique artifact_stem"):
        AnalysisResult(analysis_result_id="analysis_result:demo", method_artifacts=(plan, duplicate_stem))

    with pytest.raises(ValueError, match="at least one method artifact plan"):
        AnalysisResult(analysis_result_id="analysis_result:empty", method_artifacts=())


def test_method_envelope_artifact_plan_requires_a_real_result_envelope():
    envelope_without_results = ResultEnvelope(
        input_records=[],
        methods=[],
        configurations=[],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[],
        results=[],
        envelope_schema_version="crackpy.result_envelope.empty.v1",
    )

    with pytest.raises(ValueError, match="at least one result record"):
        MethodEnvelopeArtifactPlan(
            method_key="empty",
            envelope=envelope_without_results,
            artifact_stem="empty",
            graph_title="Empty Graph",
        )

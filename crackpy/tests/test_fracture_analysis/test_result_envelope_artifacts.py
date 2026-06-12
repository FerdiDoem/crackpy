from pathlib import Path

from crackpy.results.envelope_artifacts import ResultEnvelopeArtifactPaths, write_result_envelope_artifacts
from crackpy.results.result_data import ResultEnvelope


def _empty_envelope(schema_version: str = "crackpy.result_envelope.demo.v1") -> ResultEnvelope:
    return ResultEnvelope(
        input_records=[],
        methods=[],
        configurations=[],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[],
        results=[],
        envelope_schema_version=schema_version,
    )


def test_result_envelope_artifact_writer_uses_explicit_envelope_interface(tmp_path):
    envelope = _empty_envelope()

    written = write_result_envelope_artifacts(
        envelope=envelope,
        path=tmp_path,
        stem="explicit_result",
        graph_title="Explicit Result Graph",
    )

    assert isinstance(written, ResultEnvelopeArtifactPaths)
    assert written.envelope == tmp_path / "explicit_result_envelope.json"
    assert written.kg_statement_bundle == tmp_path / "explicit_result_kg_statement_bundle.json"
    assert written.visualization_graph == tmp_path / "explicit_result_graph.json"
    assert written.visualization_graph_html == tmp_path / "explicit_result_graph.html"
    assert all(path.exists() for path in written.as_dict().values())


def test_result_envelope_artifact_paths_preserve_legacy_dictionary_shape():
    paths = ResultEnvelopeArtifactPaths(
        envelope=Path("result_envelope.json"),
        kg_statement_bundle=Path("result_kg_statement_bundle.json"),
        visualization_graph=Path("result_graph.json"),
        visualization_graph_html=Path("result_graph.html"),
    )

    assert paths.as_dict() == {
        "envelope": Path("result_envelope.json"),
        "kg_statement_bundle": Path("result_kg_statement_bundle.json"),
        "visualization_graph": Path("result_graph.json"),
        "visualization_graph_html": Path("result_graph.html"),
    }

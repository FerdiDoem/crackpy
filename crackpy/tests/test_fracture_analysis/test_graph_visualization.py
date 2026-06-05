from crackpy.results.graph_visualization import envelope_to_visualization_graph
from crackpy.fracture_analysis.methods.williams_fit import build_williams_fit_envelope_from_analysis
from crackpy.tests.test_fracture_analysis.test_williams_provenance import _fake_analysis


def test_visualization_graph_consumes_envelope_records_and_dependency_edges():
    envelope = build_williams_fit_envelope_from_analysis(_fake_analysis(), crackpy_version="test-version")
    graph = envelope_to_visualization_graph(envelope)
    payload = graph.to_dict()

    node_types = {node["type"] for node in payload["nodes"]}
    assert "InputRecord" in node_types
    assert "CrackTipEstimateResult" in node_types
    assert "CrackTipFrame" in node_types
    assert "AnalysisRun" in node_types
    assert "ResultRecord" in node_types
    assert "ResultQuantity" in node_types

    roles = {edge["role"] for edge in payload["edges"]}
    assert "used_input" in roles
    assert "used_configuration" in roles
    assert "used_crack_tip_estimate" in roles
    assert "used_crack_tip_frame" in roles
    assert "was_generated_by" in roles
    assert "has_quantity" in roles

    assert all("subject_uri" not in node["data"] for node in payload["nodes"])

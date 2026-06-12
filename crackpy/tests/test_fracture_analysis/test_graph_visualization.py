from crackpy.results.graph_visualization import (
    envelope_to_visualization_graph,
    render_visualization_graph_html,
    write_visualization_graph_html,
)
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
    assert "MethodMetadata" in node_types
    assert "AnalysisRun" in node_types
    assert "ResultRecord" in node_types
    assert "ResultQuantity" in node_types

    method_nodes = {
        node["id"]: node
        for node in payload["nodes"]
        if node["type"] == "MethodMetadata"
    }
    assert set(method_nodes) == {
        "crackpy.fracture.williams_fit",
        "crackpy.crack_tip.manual_import",
    }
    assert method_nodes["crackpy.fracture.williams_fit"]["label"] == "Williams Fit"

    roles = {edge["role"] for edge in payload["edges"]}
    assert "used_input" in roles
    assert "used_configuration" in roles
    assert "used_crack_tip_estimate" in roles
    assert "used_crack_tip_frame" in roles
    assert "used_method" in roles
    assert "was_generated_by" in roles
    assert "has_quantity" in roles

    method_edges = {
        (edge["source"], edge["target"])
        for edge in payload["edges"]
        if edge["role"] == "used_method"
    }
    assert any(
        source.startswith("run:williams_fit:DemoNodemap:right:")
        and target == "crackpy.fracture.williams_fit"
        for source, target in method_edges
    )
    assert ("crack_tip_estimate:DemoNodemap:right", "crackpy.crack_tip.manual_import") in method_edges

    assert all("subject_uri" not in node["data"] for node in payload["nodes"])


def test_visualization_graph_writes_standalone_html(tmp_path):
    envelope = build_williams_fit_envelope_from_analysis(_fake_analysis(), crackpy_version="test-version")
    graph = envelope_to_visualization_graph(envelope)

    html = render_visualization_graph_html(graph, title="Probe <Result>")
    target = write_visualization_graph_html(graph, tmp_path / "graph.html", title="Probe <Result>")

    assert target.read_text(encoding="utf-8") == html
    assert "<title>Probe &lt;Result&gt;</title>" in html
    assert f"Nodes: {len(graph.nodes)}" in html
    assert f"Edges: {len(graph.edges)}" in html
    assert "const graph =" in html
    assert "<script>alert" not in html

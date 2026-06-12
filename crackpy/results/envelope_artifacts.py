"""Artifact writing for explicit result/provenance envelopes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crackpy.results.graph_visualization import envelope_to_visualization_graph, write_visualization_graph_html
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.results.result_data import ResultEnvelope, write_json_file


@dataclass(frozen=True, slots=True)
class ResultEnvelopeArtifactPaths:
    """Filesystem paths written for one `ResultEnvelope` projection.

    `envelope` points to the canonical graph-shaped result/provenance JSON.
    `kg_statement_bundle` points to the compact KG statement-bundle projection.
    `visualization_graph` points to the frontend-facing graph JSON.
    `visualization_graph_html` points to the standalone HTML graph viewer.
    The `as_dict()` adapter preserves the existing writer return shape while
    giving new code a typed Interface.
    """

    envelope: Path
    kg_statement_bundle: Path
    visualization_graph: Path
    visualization_graph_html: Path

    def as_dict(self) -> dict[str, Path]:
        """Return the legacy dictionary shape used by current writer callers."""
        return {
            "envelope": self.envelope,
            "kg_statement_bundle": self.kg_statement_bundle,
            "visualization_graph": self.visualization_graph,
            "visualization_graph_html": self.visualization_graph_html,
        }


def write_result_envelope_artifacts(
    *,
    envelope: ResultEnvelope,
    path: str | Path,
    stem: str,
    graph_title: str,
) -> ResultEnvelopeArtifactPaths:
    """Write standard artifact projections from an explicit result envelope.

    `envelope` is the result Interface. This writer intentionally does not know
    `FractureAnalysis`, method-local source adapters, or legacy text/current-JSON
    sections. Method-specific wrappers decide filename stems and graph titles.
    """
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)

    kg_statement_bundle = envelope_to_kg_statement_bundle(envelope)
    visualization_graph = envelope_to_visualization_graph(envelope)

    return ResultEnvelopeArtifactPaths(
        envelope=write_json_file(envelope.to_dict(), output_path / f"{stem}_envelope.json"),
        kg_statement_bundle=write_json_file(
            kg_statement_bundle.to_dict(),
            output_path / f"{stem}_kg_statement_bundle.json",
        ),
        visualization_graph=write_json_file(
            visualization_graph.to_dict(),
            output_path / f"{stem}_graph.json",
        ),
        visualization_graph_html=write_visualization_graph_html(
            visualization_graph,
            output_path / f"{stem}_graph.html",
            title=graph_title,
        ),
    )

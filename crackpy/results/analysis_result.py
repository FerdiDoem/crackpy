"""Explicit analysis-result records and artifact adapters.

This Module is the first C-001 seam above individual method envelopes.
It collects method-level `ResultEnvelope` records for one analysis workflow and
writes their standard artifacts without importing `FractureAnalysis`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from crackpy.results.envelope_artifacts import ResultEnvelopeArtifactPaths, write_result_envelope_artifacts
from crackpy.results.result_data import ResultEnvelope


@dataclass(frozen=True, slots=True)
class MethodEnvelopeArtifactPlan:
    """Artifact-writing plan for one method envelope inside an analysis result.

    `method_key` is the stable local key used in the returned artifact map.
    `envelope` is the canonical method result/provenance payload.
    `artifact_stem` controls filenames and is explicit because file naming is
    adapter policy.
    `graph_title` controls the generated standalone graph viewer title and is
    explicit because display labels should not be guessed from method IDs.
    """

    method_key: str
    envelope: ResultEnvelope
    artifact_stem: str
    graph_title: str

    def __post_init__(self) -> None:
        if not self.method_key:
            raise ValueError("MethodEnvelopeArtifactPlan requires a non-empty method_key.")
        if not isinstance(self.envelope, ResultEnvelope):
            raise TypeError("MethodEnvelopeArtifactPlan.envelope must be a ResultEnvelope.")
        if not self.envelope.results:
            raise ValueError("MethodEnvelopeArtifactPlan requires an envelope with at least one result record.")
        if not self.artifact_stem:
            raise ValueError("MethodEnvelopeArtifactPlan requires a non-empty artifact_stem.")
        if not self.graph_title:
            raise ValueError("MethodEnvelopeArtifactPlan requires a non-empty graph_title.")


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Explicit result Interface for one fracture-analysis workflow.

    `analysis_result_id` is the stable identity for this collected result.
    `method_artifacts` lists method envelopes that should be exposed through
    standard artifact projections.
    `source_label` is optional workflow-facing context, such as a nodemap stem.
    `metadata` carries non-canonical notes for adapters and should not replace
    method-envelope provenance records.
    """

    analysis_result_id: str
    method_artifacts: tuple[MethodEnvelopeArtifactPlan, ...]
    source_label: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.analysis_result_id:
            raise ValueError("AnalysisResult requires a non-empty analysis_result_id.")
        if not self.method_artifacts:
            raise ValueError("AnalysisResult requires at least one method artifact plan.")
        method_keys = [plan.method_key for plan in self.method_artifacts]
        if len(set(method_keys)) != len(method_keys):
            raise ValueError("AnalysisResult method_artifacts must use unique method_key values.")
        artifact_stems = [plan.artifact_stem for plan in self.method_artifacts]
        if len(set(artifact_stems)) != len(artifact_stems):
            raise ValueError("AnalysisResult method_artifacts must use unique artifact_stem values.")


@dataclass(frozen=True, slots=True)
class AnalysisResultArtifactPaths:
    """Artifacts written from one explicit `AnalysisResult`.

    `analysis_result_id` identifies the source result Interface.
    `method_artifacts` maps each method key to the standard envelope, KG
    bundle, graph JSON, and graph HTML paths written for that method envelope.
    """

    analysis_result_id: str
    method_artifacts: Mapping[str, ResultEnvelopeArtifactPaths]

    def as_dict(self) -> dict[str, dict[str, Path]]:
        """Return a nested dictionary for compatibility with simple callers."""
        return {
            method_key: artifact_paths.as_dict()
            for method_key, artifact_paths in self.method_artifacts.items()
        }


def write_analysis_result_artifacts(
    analysis_result: AnalysisResult,
    path: str | Path,
) -> AnalysisResultArtifactPaths:
    """Write standard method-envelope artifacts from an explicit analysis result.

    This adapter is intentionally envelope-driven.
    It does not inspect `FractureAnalysis`, legacy result tags, plots, or method
    numerical implementations.
    """
    written = {
        plan.method_key: write_result_envelope_artifacts(
            envelope=plan.envelope,
            path=path,
            stem=plan.artifact_stem,
            graph_title=plan.graph_title,
        )
        for plan in analysis_result.method_artifacts
    }
    return AnalysisResultArtifactPaths(
        analysis_result_id=analysis_result.analysis_result_id,
        method_artifacts=written,
    )

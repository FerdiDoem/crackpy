# Candidate 001: Explicit Analysis Result

Status: proposed, with Williams-fit/CJP-fit result-envelope artifact slices and the first explicit analysis-result artifact slice partially implemented
Role: Architecture candidate for separating fracture-analysis computation from result storage and output adapters.

## Observed Evidence

- [[fracture-analysis]] documents that `FractureAnalysis` mutates many result attributes after `run()`.
- [[results-io-workflows]] documents that `OutputWriter` and `Plotter` consume `FractureAnalysis` internals directly.
- [[coupling-map]] records the broad post-run interface and the results/analysis coupling.

## Problem

`FractureAnalysis.run()` mutates many attributes, and output modules know those attributes directly. This makes the interface broad and contributes to the `fracture_analysis <-> results` import cycle.

## Future Direction

Introduce an explicit result module that records optimization results, line-integral results, path metadata, method availability, and provenance links. `OutputWriter` and `Plotter` would consume the result interface rather than a live `FractureAnalysis` object.

Accepted OQ-006 boundary: the future result interface should feed the graph-shaped main JSON result/provenance model described in [[refactor-candidates/008-result-tag-schema]] and [[refactor-candidates/010-provenance-metadata-architecture]]. Legacy text, current JSON sections, CSV, and plots are adapters over this result interface.

## First Explicit Analysis-Result Slice

`crackpy.results.analysis_result.AnalysisResult` is the first implemented result Interface above method-level envelopes.

It currently collects named `ResultEnvelope` records through `MethodEnvelopeArtifactPlan`.

`MethodEnvelopeArtifactPlan.method_key` is the stable local key used by callers and frontend handoff code.

`MethodEnvelopeArtifactPlan.envelope` is the canonical method result/provenance payload.

`MethodEnvelopeArtifactPlan.artifact_stem` is explicit because filename policy belongs to the adapter.

`MethodEnvelopeArtifactPlan.graph_title` is explicit because display labels should not be inferred from method IDs.

`write_analysis_result_artifacts()` projects each method envelope into the existing standard artifact set without importing `FractureAnalysis`.

This proves a workflow-level output adapter can depend on an explicit result Interface while legacy writer behavior remains untouched.

The slice does not yet model line-integral results, path metadata, plot artifacts, or legacy text/current JSON compatibility sections.

## Seams / Interfaces / Adapters

- New interface: structured analysis result.
- Existing implementation to adapt: `FractureAnalysis`.
- Output adapters: text writer, JSON writer, CSV reader/exporter, plotter.

## Consequences

- Higher locality for result shape.
- Smaller test surface for output modules.
- Better contract for command-line interface (CLI), Model Context Protocol (MCP), and workflow orchestration.
- Clearer path to a versioned main JSON result artifact.
- Clearer path to a graph-shaped result/provenance artifact that can be translated to compact KG metadata or optional PROV-O-like provenance.
- Requires careful compatibility with current text/JSON result tags as legacy aliases.

## Open Questions

- OQ-005: resolved; future main result output is versioned JSON.
- OQ-006: resolved; canonical result JSON is graph-shaped and current result tags are legacy aliases.
- OQ-015: resolved; provenance metadata uses the `InputRecord`, `AnalysisRun`, `ResultRecord`, and `ProvenanceRecord` split.

## Decision State

OQ-005 and OQ-006 planning boundaries accepted.

Williams-fit and CJP-fit result/provenance envelopes are partially implemented through `crackpy.results.result_data`, method-local source adapters, and shared provenance builders.

`crackpy.results.envelope_artifacts.write_result_envelope_artifacts()` can consume an explicit `ResultEnvelope` and write envelope JSON, compact KG statement bundle, graph JSON, and graph HTML without constructing `FractureAnalysis`.

`crackpy.results.analysis_result.write_analysis_result_artifacts()` can now consume an explicit `AnalysisResult` and write the same standard artifact set for multiple named method envelopes.

`FractureAnalysis` still exposes the broad mutable post-run attribute interface, legacy text/current JSON/CSV/plot outputs still inspect it directly, and broader analysis-result separation is not approved.

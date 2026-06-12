# Candidate 001: Explicit Analysis Result

Status: proposed, with Williams-fit result/provenance slice partially implemented
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

OQ-005 and OQ-006 planning boundaries accepted. The first Williams-fit result/provenance envelope is partially implemented through `crackpy.results.result_data` and `crackpy.fracture_analysis.methods.williams_fit`, but `FractureAnalysis` still exposes the broad mutable post-run attribute interface and broader analysis-result separation is not approved.

# Candidate 001: Explicit Analysis Result

Status: proposed
Role: Future architecture candidate for separating fracture-analysis computation from result storage and output adapters.

## Observed Evidence

- [[fracture-analysis]] documents that `FractureAnalysis` mutates many result attributes after `run()`.
- [[results-io-workflows]] documents that `OutputWriter` and `Plotter` consume `FractureAnalysis` internals directly.
- [[coupling-map]] records the broad post-run interface and the results/analysis coupling.

## Problem

`FractureAnalysis.run()` mutates many attributes, and output modules know those attributes directly. This makes the interface broad and contributes to the `fracture_analysis <-> results` import cycle.

## Future Direction

Introduce an explicit `AnalysisResult` module that records optimization results, line-integral results, path metadata, and method availability. `OutputWriter` and `Plotter` would consume the result interface rather than a live `FractureAnalysis` object. Provenance and execution metadata need coordination with [[refactor-candidates/010-provenance-metadata-architecture]].

## Seams / Interfaces / Adapters

- New interface: structured analysis result.
- Existing implementation to adapt: `FractureAnalysis`.
- Output adapters: text writer, JSON writer, CSV reader/exporter, plotter.

## Consequences

- Higher locality for result shape.
- Smaller test surface for output modules.
- Better contract for command-line interface (CLI), Model Context Protocol (MCP), and workflow orchestration.
- Requires careful compatibility with current text/JSON result tags.

## Open Questions

- OQ-005: Should result files receive an explicit schema or format version?
- OQ-006: Which result names are public schema and which are legacy implementation names?
- OQ-015: Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots?

## Decision State

Not decided. No implementation approved.

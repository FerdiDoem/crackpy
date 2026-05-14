# Candidate 004: Separate Orchestration From Adapters

Status: proposed
Role: Future architecture candidate for separating computational job orchestration from filesystem, plotting, progress, and execution adapters.

## Observed Evidence

- [[system-map]] shows primary runtime flow through detection, analysis, and results.
- [[fracture-analysis]] documents batch pipeline responsibilities.
- [[crack-detection]] documents batch detection responsibilities and side effects.
- [[results-io-workflows]] documents scripts, output folders, result writers, and plots.

## Problem

Pipelines combine algorithm orchestration with filesystem, plotting, progress, multiprocessing, and result-writing policy.

This makes it hard to reuse CrackPy's scientific workflow logic from a command-line interface, Model Context Protocol (MCP) tool, workflow manager, or graph orchestrator without also inheriting legacy output folders, plots, progress bars, text formats, multiprocessing choices, and model download behavior.

## Future Direction

Split pipeline behavior into:

- domain workflow runner returning structured records;
- output adapters for text, JSON, CSV, and plots;
- progress adapters such as rich, null, or MCP progress;
- execution adapters such as serial or process pool.

Accepted OQ-008 boundary: CrackPy should keep bundled domain workflow runners for sequencing that belongs to the package, but those runners should be side-effect-light and record-oriented. Current `CrackDetectionPipeline` and `FractureAnalysisPipeline` should be treated as compatibility facades during a future migration, not as the target architecture.

CrackPy-owned workflow logic includes operations such as transforming input data into a crack-tip-centered frame, computing stresses before line integrals, running detection/correction/analysis in a valid order, constructing or auto-detecting integration paths, aggregating path results, and attaching method/configuration/provenance metadata.

Adapter policy includes legacy text writing, current JSON writing, future canonical result JSON writing, old `crack_info_by_nodemap.txt` import/export, flattened CSV export, plots, folder layout, progress reporting, multiprocessing choice, neural-network model download/cache policy, VTK export, and RDF/knowledge-graph export.

## Seams / Interfaces / Adapters

- Seam: job orchestration.
- Interfaces: job input, workflow result, progress reporting, output writing, execution policy, model provisioning.
- Domain workflow runner: package-owned sequencing of scientific steps that returns explicit records and artifacts.
- Adapters: filesystem output, plotting, text/JSON/CSV output, VTK output, compact KG export, rich progress, null progress, serial/process execution, model provider/cache/download policy.
- Compatibility facades: current side-effect-heavy pipelines that preserve existing script behavior by composing future runners with adapters.

## Consequences

- Graph execution and CLI/MCP access can reuse the same computational runner without inheriting file/plot/progress behavior.
- Existing scripts can remain reproducible through compatibility facades while new orchestration surfaces depend on explicit runners and adapters.
- Legacy artifacts such as tagged text, current JSON sections, flattened CSV, plots, and `crack_info_by_nodemap.txt` become adapter or compatibility vocabulary rather than core workflow contracts.
- The distinction protects useful CrackPy-owned workflow knowledge from being pushed into external orchestrators.
- Requires clear compatibility rules for existing scripts, pipeline outputs, and model-cache behavior.

## Open Questions

- None.

## Decision State

OQ-008 is accepted for planning. No production pipeline migration is approved.

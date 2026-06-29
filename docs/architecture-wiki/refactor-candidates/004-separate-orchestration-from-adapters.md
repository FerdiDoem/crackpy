# Candidate 004: Separate Orchestration From Adapters

Status: proposed, with first single-nodemap fracture workflow runner slice implemented
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

## First Single-Nodemap Workflow Runner Slice

`crackpy.fracture_analysis.workflow.FractureWorkflowInput` is the first implemented C-004 workflow input Interface.
It carries one nodemap run's file anchor, material, crack-tip coordinates, explicit `crack_tip_id`, optional `compatibility_side`, nodemap structure, and optional method properties.
The `crack_tip_id` field is the durable identity for the crack tip.
The `compatibility_side` field preserves current `left`/`right` handoff behavior without making side the workflow identity.

`FractureWorkflowInput.from_legacy_pipeline_row()` is the compatibility adapter for current crack-info CSV rows.
It reads `Filename`, `Crack Tip x [mm]`, `Crack Tip y [mm]`, `Crack Angle`, and `Side`.
It preserves a future `Crack Tip ID` column when present.
When that column is absent, it derives `crack_tip:<filename-stem>:<side>` as a deterministic compatibility ID.

`run_fracture_analysis_workflow()` is the first domain workflow runner.
It owns the CrackPy-specific scientific sequence for one nodemap: create the `Nodemap`, load `InputData`, calculate stresses, transform into crack-tip-centered coordinates, build `FractureAnalysis`, and call `run()`.
It returns `FractureWorkflowResult`, including the prepared `FractureAnalysis` instance for legacy output adapters.
It deliberately does not write text/current JSON files, create plots, create output folders, choose multiprocessing policy, or own progress UI.

`FractureAnalysisPipeline.single_run()` now acts as the compatibility facade for one submitted job.
It delegates the scientific run to `run_fracture_analysis_workflow()` and then applies legacy `OutputWriter` and `Plotter` policy.
The broader pipeline still owns input CSV reading, automatic integral-property propagation, rich progress display, and process-pool execution.

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

OQ-008 is accepted for planning.
The first production slice is implemented for a single fracture-analysis nodemap run.
Broader pipeline migration remains unapproved.
Crack-detection workflow runners, line-integral result records, CSV adapters, plot adapters, progress adapters, process-pool adapters, and full compatibility-facade decomposition remain future work.

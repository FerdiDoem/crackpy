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

## Future Direction

Split pipeline behavior into:

- job runner returning structured results;
- output adapters for text, JSON, CSV, and plots;
- progress adapters such as rich, null, or MCP progress;
- execution adapters such as serial or process pool.

## Seams / Interfaces / Adapters

- Seam: job orchestration.
- Interfaces: job input, job result, progress reporting, output writing, execution policy.
- Adapters: filesystem output, plotting, text/JSON/CSV output, rich progress, null progress, serial/process execution.

## Consequences

- Graph execution and CLI/MCP access can reuse the same computational runner without inheriting file/plot/progress behavior.
- Requires clear compatibility rules for existing scripts and pipeline outputs.

## Open Questions

- OQ-008: Which pipeline side effects are user-facing behavior and which are adapter policy?

## Decision State

Not decided. No implementation approved.

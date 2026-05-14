# Candidate 003: Self-Contained Williams Fit Interface

Status: proposed
Role: Future architecture candidate for exposing Williams fitting as an explicit computational interface.

## Observed Evidence

- [[fracture-analysis]] documents Williams fitting behavior and assumptions.
- [[crack-detection]] documents crack-tip correction methods that call Williams optimization.
- [[coupling-map]] records implicit interfaces around transformed `InputData`.

## Problem

Williams fitting is reusable, but its current interface depends on transformed `InputData`, mutable option defaults, and `Optimization` constructor side effects.

## Future Direction

Expose a computational interface that accepts explicit arrays, material parameters, terms, and fitting-domain settings, then returns coefficients and residual metrics. Pipeline classes can adapt `InputData` into that interface.

## Seams / Interfaces / Adapters

- Interface: Williams fit input arrays, material data, fitting-domain settings, and coefficient result.
- Adapter: `InputData` to Williams fit input.
- Existing implementation: `Optimization.optimize_williams_displacements_xy()` and related methods.

## Consequences

- Williams fitting becomes easier to call from CLI, MCP, tests, crack-tip correction, and graph-based workflows.
- Current unit conventions and transformed-coordinate assumptions must remain explicit.
- Correction methods need a compatibility path during migration.

## Open Questions

- OQ-007: Should correction return values consistently mean relative shifts or absolute corrected crack-tip coordinates?

## Decision State

Not decided. No implementation approved.

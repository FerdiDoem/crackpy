# Candidate 003: Self-Contained Williams Fit Interface

Status: proposed, with typed runner and correction-result wrapper partially implemented
Role: Architecture candidate for exposing Williams fitting as an explicit computational interface.

## Observed Evidence

- [[fracture-analysis]] documents Williams fitting behavior and assumptions.
- [[crack-detection]] documents crack-tip correction methods that call Williams optimization.
- [[coupling-map]] records implicit interfaces around transformed `InputData`.

## Problem

Williams fitting is reusable, but its current interface depends on transformed `InputData`, mutable option defaults, and `Optimization` constructor side effects.

## Future Direction

Expose a computational interface that accepts explicit arrays, material parameters, terms, and fitting-domain settings, then returns coefficients and residual metrics. Pipeline classes can adapt `InputData` into that interface.

Correction interfaces built on this fitting layer should emit an absolute corrected crack-tip estimate plus an audit correction delta. Compatibility adapters can translate existing delta-returning correction APIs during migration.

## Seams / Interfaces / Adapters

- Interface: Williams fit input arrays, material data, fitting-domain settings, and coefficient result.
- Adapter: `InputData` to Williams fit input.
- Existing implementation: `Optimization.optimize_williams_displacements_xy()` and related methods.

## Consequences

- Williams fitting becomes easier to call from CLI, MCP, tests, crack-tip correction, and graph-based workflows.
- Current unit conventions and transformed-coordinate assumptions must remain explicit.
- Correction methods need a compatibility path during migration.

## Open Questions

- None for the current planning state.

## Resolved Planning Constraints

- OQ-007: Crack-tip correction should expose a corrected crack-tip estimate as the primary result and retain the correction delta for audit, comparison, and legacy compatibility.

## Decision State

Planning vocabulary accepted.
A typed Williams-fit runner, result model, parameter model, source adapter, and provenance builder wrapper now exist under `crackpy.fracture_analysis.methods.williams_fit`.
The runner now includes an explicit array-based slice: `WilliamsFitDisplacementField` carries resolved crack-tip-centered displacement grids and material data, `fit_williams_displacement_field()` performs the least-squares fit without constructing `Optimization`, and `run_williams_fit_from_coefficients()` assembles typed results from explicit coefficient vectors.
The first crack-tip-correction slice now exposes `CrackTipCorrectionResult` wrappers so correction callers can consume an absolute corrected crack-tip estimate plus the legacy correction delta.
The full candidate remains open because crack-tip correction still uses its own Williams optimization bridge internally and the production `FractureAnalysis` path still enters through the legacy optimizer adapter.

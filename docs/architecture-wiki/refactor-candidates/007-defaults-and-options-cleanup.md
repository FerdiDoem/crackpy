# Candidate 007: Defaults And Options Cleanup

Status: proposed
Role: Future architecture candidate for making configuration object lifecycles explicit and testable.

## Observed Evidence

- [[fracture-analysis]] documents fitting and integral property objects.
- [[data-model-input]] documents material and nodemap structures.
- [[coupling-map]] records hidden shared state and constructor work.

## Problem

Mutable default objects are instantiated at function-definition time and then mutated by default-normalization helpers. Current code also mixes result-affecting method defaults, derived defaults, method-selection switches, adapter settings, and incidental implementation defaults in the same object lifecycles.

## Future Direction

Use explicit construction per call, dataclasses or Pydantic models where appropriate, and default builders for method-specific options. Future registered methods should receive fully resolved, explicit result-affecting configuration at method entry. Defaults may be applied by user-facing configuration builders, but computational methods should either receive concrete values or reject ambiguous missing values.

Planning split accepted by OQ-010:

- result-affecting method defaults belong in normalized configuration;
- derived defaults are resolved before execution and stored as concrete values with value origin;
- method selection is workflow composition, not method configuration;
- output, plotting, progress, multiprocessing, and export choices are adapter or execution policy;
- mutable default objects and hidden random initialization are migration debt, not future public behavior.

## Seams / Interfaces / Adapters

- Interface: explicit options passed to analysis, optimization, and line-integral modules.
- Implementation: current `OptimizationProperties`, `IntegralProperties`, `PathProperties`, `NodemapStructure`, and `Material` behavior.
- Configuration seam: future normalized configuration builders that complete or reject missing result-affecting values before method execution.
- Workflow seam: composition settings that decide which registered methods run.
- Adapter seam: output folders, legacy text/JSON writing, plotting, progress, multiprocessing, and export policy.

## Consequences

- Removes hidden shared state.
- Makes option lifecycle easier to test.
- Makes provenance and configuration hashes meaningful because resolved result-affecting defaults are explicit.
- Requires compatibility with current default behavior through builders or compatibility facades, not hidden method defaults.
- Requires future reproducibility handling for random optimizer initialization if it can affect results.

## Open Questions

None.

## Decision State

OQ-010 accepted for planning. No implementation approved.

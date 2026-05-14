# Candidate 007: Defaults And Options Cleanup

Status: proposed
Role: Future architecture candidate for making configuration object lifecycles explicit and testable.

## Observed Evidence

- [[fracture-analysis]] documents fitting and integral property objects.
- [[data-model-input]] documents material and nodemap structures.
- [[coupling-map]] records hidden shared state and constructor work.

## Problem

Mutable default objects are instantiated at function-definition time and then mutated by default-normalization helpers.

## Future Direction

Use explicit construction per call, dataclasses where appropriate, and default builders for method-specific options.

## Seams / Interfaces / Adapters

- Interface: explicit options passed to analysis, optimization, and line-integral modules.
- Implementation: current `OptimizationProperties`, `IntegralProperties`, `PathProperties`, `NodemapStructure`, and `Material` behavior.

## Consequences

- Removes hidden shared state.
- Makes option lifecycle easier to test.
- Requires compatibility with current default behavior.

## Open Questions

- OQ-010: Which current option defaults are public behavior and which are incidental implementation defaults?

## Decision State

Not decided. No implementation approved.

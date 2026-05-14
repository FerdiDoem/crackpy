# Candidate 005: Side Orientation Module

Status: proposed
Role: Future architecture candidate for replacing left/right orientation coupling with an explicit `CrackTipFrame` model and compatibility adapters.

## Observed Evidence

- [[glossary]] defines current `Side` and `Coordinate system` terminology.
- [[crack-detection]] documents the right-side crack convention and left-side mirroring.
- [[terminology-report]] records `side` as overloaded.
- [[coupling-map]] records repeated orientation and side-handling patterns.

## Problem

Left/right orientation is encoded repeatedly through strings, sign flips, mirrored arrays, signed window sizes, and coordinate conversion logic.

The current `side` concept also bundles several ideas that should be separated before redesign: physical specimen geometry, crack-tip identity, notch or crack origin, crack propagation direction, algorithmic mirroring, pipeline grouping, and output naming. Middle Tension specimens, CT specimens, bending samples, multiple-crack-tip cases, and future 3D crack-front or 3D-surface cases do not share one universal left/right model. OQ-001 resolved that `side` may remain compatibility vocabulary at file, legacy API, detector setup, and result-naming boundaries, but should not remain the internal mechanics model.

## Future Direction

Create a broader crack-tip geometry/orientation module that owns a `CrackTipFrame`. The internal model should describe crack-tip identity, position, local axes, geometry profile, and, when needed, compatibility labels such as the current `left`/`right` side value. Current `left`/`right` side handling should become a compatibility adapter around that model.

The planning target is a general frame concept with declared geometry profiles. Current CrackPy methods remain `surface_planar` unless explicitly extended. `surface_parameterized` is a plausible future DIC-surface extension; `surface_3d` and `volumetric_field` are future capability profiles, not current guarantees.

## Seams / Interfaces / Adapters

- Seam: `CrackTipFrame`.
- Interface: orientation and geometry-profile data needed by detection, training, plotting, fracture analysis, provenance, and output naming.
- Adapters: current `left`/`right` side convention, current right-side detector convention, future specimen-specific geometry conventions.

## Consequences

- Higher leverage and locality for one domain concept used by detection, training, plotting, fracture analysis, provenance, and output.
- Requires careful treatment of the trained right-side crack convention.
- Requires a compatibility story for current result files and scripts using `Side`.
- Requires method-level applicability declarations so 3D coordinates in nodemaps are not mistaken for general 3D fracture-mechanics support.

## Open Questions

- OQ-001: resolved; `side` remains boundary compatibility vocabulary, while future internal interfaces should use explicit crack-tip frame concepts.
- OQ-003: resolved; specimen geometry, crack-tip identity, crack-growth direction, detector convention, mirroring policy, pipeline grouping, and output labels should become separate vocabulary.
- OQ-020: resolved; `CrackTipFrame` is the canonical planning target, with geometry profiles separating current surface-planar support from future parameterized-surface, 3D-surface, or volumetric capabilities.

## Decision State

Planning direction accepted for OQ-001 and OQ-020. Candidate remains proposed; no implementation approved.

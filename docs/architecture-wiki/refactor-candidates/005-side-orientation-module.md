# Candidate 005: Side Orientation Module

Status: proposed
Role: Future architecture candidate for replacing left/right orientation coupling with an explicit crack-tip coordinate-system model and compatibility adapters.

## Observed Evidence

- [[glossary]] defines current `Side` and `Coordinate system` terminology.
- [[crack-detection]] documents the right-side crack convention and left-side mirroring.
- [[terminology-report]] records `side` as overloaded.
- [[coupling-map]] records repeated orientation and side-handling patterns.

## Problem

Left/right orientation is encoded repeatedly through strings, sign flips, mirrored arrays, signed window sizes, and coordinate conversion logic.

The current `side` concept also bundles several ideas that should be separated before redesign: physical specimen geometry, crack-tip identity, notch or crack origin, crack propagation direction, algorithmic mirroring, pipeline grouping, and output naming. Middle Tension specimens, CT specimens, bending samples, multiple-crack-tip cases, and future 3D crack-front or 3D-surface cases do not share one universal left/right model. OQ-001 resolved that `side` may remain compatibility vocabulary at file, legacy API, detector setup, and result-naming boundaries, but should not remain the internal mechanics model.

## Future Direction

Create a broader crack-tip geometry/orientation module that owns a crack-tip coordinate system or crack-tip frame. The internal model should describe crack-tip position, crack-extension direction, crack-opening direction, and, when needed, crack-front or surface-normal direction. Current `left`/`right` side handling should become a compatibility adapter around that model.

For the current 2D package, this can start as a local 2D pose: origin at the crack tip and rotation by crack angle. For future work, it should be able to extend toward 3D crack-tip frames.

## Seams / Interfaces / Adapters

- Seam: crack-tip coordinate system or crack-tip frame.
- Interface: orientation data needed by detection, training, plotting, fracture analysis, provenance, and output naming.
- Adapters: current `left`/`right` side convention, current right-side detector convention, future specimen-specific geometry conventions.

## Consequences

- Higher leverage and locality for one domain concept used by detection, training, plotting, fracture analysis, provenance, and output.
- Requires careful treatment of the trained right-side crack convention.
- Requires a compatibility story for current result files and scripts using `Side`.
- Needs a minimal crack-tip coordinate-system decision before implementation.

## Open Questions

- OQ-001: resolved; `side` remains boundary compatibility vocabulary, while future internal interfaces should use explicit crack-tip frame concepts.
- OQ-003: Which meanings currently bundled into `side` must become separate vocabulary?
- OQ-020: What is the minimal internal crack-tip coordinate-system model needed to support arbitrary 2D cracks, multiple crack tips, tilted cracks, top-to-bottom cracks, and future 3D crack fronts?

## Decision State

Not decided. No implementation approved.

# Decision Log

Status: lightweight planning decisions
Role: Record accepted or rejected planning decisions that are not architecture decision records. ADRs are deferred until explicitly requested.

## 2026-05-14: Architecture Wiki Is Planning Memory

Status: accepted

Decision:

`docs/architecture-wiki/` functions as the shared working memory for CrackPy architectural mapping and future refactor planning.

Rationale:

The current phase is exploration and planning only. The notes need to preserve observed reality, shared language, unresolved terminology, and future candidates without implying that production code has changed.

Consequences:

- Observed-system notes describe current behavior only.
- Future architecture candidates live in [[refactor-notes]] and [[refactor-candidates/index]].
- Open terminology and architecture questions live in [[open-questions]].
- Stable vocabulary lives in [[glossary]].
- No ADRs are created in this phase.

## 2026-05-14: ADRs Deferred

Status: accepted

Decision:

Do not create `docs/adr/` or ADR records during this consolidation pass.

Rationale:

No architecture decision has been approved yet. The current task is to consolidate working memory, not to make durable architecture decisions.

Consequences:

- `decision-log.md` records lightweight planning decisions.
- Future ADRs can be introduced after explicit approval.

## 2026-05-14: Side Is Not A Sustainable Internal Crack-Orientation Model

Status: accepted for planning

Decision:

`side` should not be treated as the long-term internal representation of crack orientation, crack-tip pose, or crack-growth direction. It remains an observed compatibility term in the current package and handoff files, but future architecture planning should split the meanings currently bundled into `side`.

Rationale:

The current `left`/`right` vocabulary assumes at most two default crack tips whose nominal growth directions align with the package x-axis convention. This is too restrictive for multiple crack tips, tilted initial cracks, top-to-bottom crack growth, bending samples, 3D surfaces, and future crack-front descriptions.

The internal package model should move toward a crack-tip-centered coordinate system or crack-tip frame. In that frame, local x is the crack-extension direction, local y is the crack-opening direction for mode I, and local z is aligned with the crack front or, for the current straight-surface approximation, the surface normal.

Consequences:

- Current `side`, `sides`, and `left_or_right` stay documented as observed compatibility vocabulary.
- `side` remains acceptable at file, legacy API, detector setup, and result-naming boundaries, but new internal interfaces should treat it as adapter input that maps to an explicit crack-tip frame.
- Future planning should separate specimen geometry, crack-tip identity, crack-growth direction, detector model convention, mirroring policy, and output labels.
- The current 2D shift-and-rotation behavior in `InputData.transform_data(x_shift, y_shift, angle)` is an existing partial crack-tip-centered transform, not a complete orientation model.
- A new open question tracks the minimal internal crack-tip coordinate-system model before implementation.

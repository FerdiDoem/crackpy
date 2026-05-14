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

The internal package model should move toward `CrackTipFrame` as the canonical crack-tip orientation concept. In that frame, local x is the crack-extension direction, local y is the crack-opening direction for mode I, and local z is profile-specific: for current planar DIC workflows it is usually the assumed surface normal or out-of-plane direction, while true 3D crack-front workflows would need an explicit crack-front or surface-frame definition.

Consequences:

- Current `side`, `sides`, and `left_or_right` stay documented as observed compatibility vocabulary.
- `side` remains acceptable at file, legacy API, detector setup, and result-naming boundaries, but new internal interfaces should treat it as adapter input that maps to an explicit crack-tip frame.
- Future planning should separate specimen geometry, crack-tip identity, crack-growth direction, detector model convention, mirroring policy, and output labels.
- The current 2D shift-and-rotation behavior in `InputData.transform_data(x_shift, y_shift, angle)` is an existing partial crack-tip-centered transform, not a complete orientation model.
- OQ-020 resolves the minimal internal crack-tip coordinate-system planning target as `CrackTipFrame` with declared geometry profiles.

## 2026-05-14: CrackTipFrame Is The Planning Target For Internal Crack-Tip Orientation

Status: accepted for planning

Decision:

Use `CrackTipFrame` as the canonical future internal concept for crack-tip orientation and position. Do not use a permanently 2D-only term as the canonical model. A `CrackTipFrame` should carry a crack-tip identity, origin, local axes, geometry profile, and optional compatibility labels such as current `side`.

Rationale:

CrackPy currently targets digital image correlation (DIC) surface data. Nodemaps can contain `coor_z` and `disp_z`, but current detection, interpolation, line integrals, and `InputData.transform_data(x_shift, y_shift, angle)` are planar or surface-based methods. The architecture should be able to describe a crack-tip frame in 3D coordinates when surface data has 3D embedding, while avoiding a false promise that current methods support digital volume correlation (DVC), volumetric finite element method (FEM), or general 3D crack-front fracture mechanics.

Consequences:

- `CrackTipFrame` is the planning target for future internal orientation interfaces.
- Methods should declare a geometry profile such as `surface_planar`, `surface_parameterized`, `surface_3d`, or `volumetric_field`.
- Current CrackPy methods should be documented as `surface_planar` unless a method explicitly supports more.
- `surface_parameterized` is a plausible future extension for derived 2D surface coordinates after a defined parameterization, projection, or unwrapping step.
- `surface_3d` and `volumetric_field` are future capability profiles, not current guarantees.
- 3D coordinates in nodemaps do not imply general 3D fracture-mechanics support.

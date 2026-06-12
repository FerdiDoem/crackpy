# CJP Fit Result/Provenance Design

Status: approved field-level planning spec
Date: 2026-06-13
Scope: next result/provenance slice after Williams fitting

## Goal

Implement a CJP fitting result/provenance slice that treats the current mixed-mode and Mode-I CJP outputs with the same result/provenance discipline as the Williams-fit slice, while preserving existing text, current JSON, CSV, and plot behavior.

The slice covers the current CJP optimization outputs and fitted coefficients. It does not introduce a package-wide method registry, uncertainty model, symbolic formula engine, unit engine, RDF exporter, or pipeline refactor.

## Approved Boundary

In scope:

- Method-local package `crackpy.fracture_analysis.methods.cjp_fit`.
- Two CJP method identities in one implementation slice:
  - `crackpy.fracture.cjp_mixed_mode_fit`
  - `crackpy.fracture.cjp_mode_i_fit`
- A CJP slice spec loaded from YAML through Pydantic validation.
- Typed CJP result records for mixed-mode and Mode-I outputs.
- Fitted CJP coefficients as canonical result quantities.
- Derived CJP outputs as canonical result quantities.
- Tested Python conversion functions from fitted coefficients to derived outputs.
- Result/provenance envelope construction using the existing `MethodResultSource` and `MethodResultEnvelopeBuilder`.
- Artifact projection analogous to Williams fitting:
  - `_cjp_fit_envelope.json`
  - `_cjp_fit_kg_statement_bundle.json`
  - `_cjp_fit_graph.json`
  - `_cjp_fit_graph.html`
- An `OutputWriter` compatibility bridge that can write CJP provenance artifacts from current `FractureAnalysis` state.
- An actual-data proof if the existing CJP test fixture can run deterministically enough for the scoped verification.

Out of scope:

- Changing legacy `CJP_results` or `CJP_modeI_results` text/current-JSON output.
- CSV reader/exporter migration.
- Plot metadata changes.
- J-integral, interaction-integral, Bueckner-Chen, path-statistics, or Williams changes beyond shared reuse.
- RDF/Turtle export.
- SymPy, Pint, unyt, QUDT, or any new unit/formula dependency.
- Method trustworthiness, maturity, uncertainty, or validation-profile metadata.
- Broad `FractureAnalysis`, `Optimization`, or pipeline restructuring.

## Method Identities

The CJP slice must not model mixed-mode and Mode-I as only quantity variants under one method ID. They use different fitted formula systems, coefficient sets, derived quantities, and scientific evidence. They therefore require separate method identities while still belonging to one CJP implementation slice.

### `crackpy.fracture.cjp_mixed_mode_fit`

Meaning: mixed-mode CJP displacement fit using the current CrackPy implementation based on the mixed-mode CJP extension formulas.

Current implementation references:

- `crackpy.fracture_analysis.optimization.Optimization.optimize_cjp_displacements_mixedmode`
- `crackpy.fracture_analysis.crack_tip.cjp_displ_field_mixedmode`
- `crackpy.fracture_analysis.analysis.FractureAnalysis._run_cjp_optimization_mixedmode`

Legacy alias scope:

- `CJP_results`

### `crackpy.fracture.cjp_mode_i_fit`

Meaning: Mode-I CJP displacement fit using the current CrackPy implementation based on the Mode-I CJP formulas.

Current implementation references:

- `crackpy.fracture_analysis.optimization.Optimization.optimize_cjp_displacements_modeI`
- `crackpy.fracture_analysis.crack_tip.cjp_displ_field_modeI`
- `crackpy.fracture_analysis.analysis.FractureAnalysis._run_cjp_optimization_modeI`

Legacy alias scope:

- `CJP_modeI_results`

## Canonical Quantities

The canonical CJP envelope must expose fitted coefficients and derived quantities. Coefficients are included because the CJP-derived stress-intensity-like values are calculated through non-obvious formulas. Without the coefficients, the provenance record would expose only final values and hide the scientific evidence chain.

### Mixed-Mode Coefficients

Each coefficient quantity uses qualifier `variant=mixed_mode`.

| Quantity | Canonical unit | Meaning |
| --- | --- | --- |
| `A_r` | `MPa*m^{1/2}` | Mixed-mode CJP singular coefficient fitted by the optimizer. |
| `B_r` | `MPa*m^{1/2}` | Mixed-mode CJP singular coefficient fitted by the optimizer. |
| `B_i` | `MPa*m^{1/2}` | Mixed-mode CJP singular coefficient fitted by the optimizer. |
| `C` | `MPa` | Mixed-mode non-singular stress coefficient fitted by the optimizer. |
| `E` | `MPa*m^{1/2}` | Mixed-mode CJP singular/logarithmic coefficient fitted by the optimizer. |

### Mixed-Mode Derived Outputs

Each derived quantity uses qualifier `variant=mixed_mode`.

| Quantity | Canonical unit | Legacy alias |
| --- | --- | --- |
| `error` | `1` | `CJP_results.error`, `CJP_results.Error` |
| `K_F` | `MPa*m^{1/2}` | `CJP_results.K_F` |
| `K_R` | `MPa*m^{1/2}` | `CJP_results.K_R` |
| `K_S` | `MPa*m^{1/2}` | `CJP_results.K_S` |
| `K_II` | `MPa*m^{1/2}` | `CJP_results.K_II` |
| `T` | `MPa` | `CJP_results.T` |

### Mode-I Coefficients

Each coefficient quantity uses qualifier `variant=mode_i`.

| Quantity | Canonical unit | Meaning |
| --- | --- | --- |
| `A` | `MPa*m^{1/2}` | Mode-I CJP singular coefficient fitted by the optimizer. |
| `B` | `MPa*m^{1/2}` | Mode-I CJP singular coefficient fitted by the optimizer. |
| `C` | `MPa` | Mode-I CJP non-singular stress coefficient fitted by the optimizer. |
| `E` | `MPa*m^{1/2}` | Mode-I CJP singular/logarithmic coefficient fitted by the optimizer. |
| `F` | `MPa` | Mode-I CJP non-singular stress coefficient fitted by the optimizer. |

### Mode-I Derived Outputs

Each derived quantity uses qualifier `variant=mode_i`.

| Quantity | Canonical unit | Legacy alias |
| --- | --- | --- |
| `error` | `1` | `CJP_modeI_results.error`, `CJP_modeI_results.Error` |
| `K_F` | `MPa*m^{1/2}` | `CJP_modeI_results.K_F` |
| `K_R` | `MPa*m^{1/2}` | `CJP_modeI_results.K_R` |
| `K_S` | `MPa*m^{1/2}` | `CJP_modeI_results.K_S` |
| `T_x` | `MPa` | `CJP_modeI_results.T_x` |
| `T_y` | `MPa` | `CJP_modeI_results.T_y` |

## Unit Policy

The optimizer currently fits against CrackPy fields where radial distance `r` is in millimeters. In the implemented stress/displacement formulas, singular CJP coefficients have dimension `stress * sqrt(length)`. Native optimizer coefficients for `A_r`, `B_r`, `B_i`, `E`, `A`, and `B` are therefore in `MPa*mm^{1/2}`.

The canonical result/provenance envelope should expose singular CJP coefficients in `MPa*m^{1/2}` to match the derived `K_*` values already emitted by current writers. The conversion is:

```text
coefficient_MPa_sqrt_m = coefficient_MPa_sqrt_mm / sqrt(1000)
```

The non-singular coefficients `C` and `F`, and the derived stress terms `T`, `T_x`, and `T_y`, remain in `MPa`.

Raw optimizer coefficients may remain available inside method-local typed result objects for testing and debugging, but the canonical public quantities use the converted unit policy above.

## Formula Traceability

The first CJP slice must make derivations auditable without adding a symbolic math or unit engine.

Required implementation shape:

- The method module owns explicit Python conversion functions for mixed-mode and Mode-I derived outputs.
- Tests assert derived output values from known coefficient inputs.
- Quantity descriptions in the YAML spec mention the coefficient formula basis in human-readable language.
- Conversion functions document that singular coefficients are converted from `MPa*mm^{1/2}` to `MPa*m^{1/2}` for canonical export.

Deferred:

- SymPy formula registry.
- Pint, unyt, or another runtime unit system.
- QUDT/UCUM unit identifiers.
- LaTeX report generation from symbolic formulas.

These belong to a future formulas/units ecosystem gate so the numerical core can stay plain NumPy/SciPy and fast.

## Provenance Shape

The CJP source adapter should use the existing generic source model:

- `SourceInput`: primary nodemap/displacement-field input anchor.
- `SourceDependency`: crack-tip frame dependency.
- `SourceParameters`: resolved material and optimization parameters.
- `SourceQuantity`: fitted coefficients and derived outputs.

The source model must not gain top-level CJP-specific fields. CJP-specific dimensions belong in quantity qualifiers such as `variant=mixed_mode` or `variant=mode_i`.

The CJP envelope should contain:

- one input record;
- one shared crack-tip frame dependency;
- one configuration record unless implementation evidence shows the variants need separate normalized configurations;
- two method metadata records;
- two analysis runs and two result records, one for each method identity;
- result quantities for coefficients and derived outputs;
- the same compact KG and visualization graph projections used by Williams, if those projections accept the resulting envelope without method-specific branching.

## Compatibility Policy

Existing writer behavior stays unchanged:

- `OutputWriter.write_results()` still emits `CJP_results` and `CJP_modeI_results` as before.
- `OutputWriter.write_json()` still emits the current JSON sections as before.
- CSV flattening remains on the older reader/exporter contract.
- Existing tests for legacy CJP outputs remain valid.

New artifact writing should be additive through a named CJP provenance writer bridge. It must not change when current text/current-JSON/CSV/plot outputs appear.

## Method Evidence And Trustworthiness

No trustworthiness, maturity, validation, or uncertainty fields are added to method metadata in this slice.

Reason: method trustworthiness is not specific to CJP and should not be represented as two ad hoc fields. It belongs to a future method evidence or validation profile specification that can cover benchmark data, applicable regimes, limitations, validation references, maintainer review, and result-level uncertainty.

For this slice, scientific caution is represented only through:

- separate method identities for mixed-mode and Mode-I CJP;
- method references;
- explicit coefficient exposure;
- formula descriptions and tested conversion functions.

## Failure Policy

The CJP method-local runner and source adapter should follow the accepted scientific-code rule: fail early and fail visibly for unexpected data, missing identities, failed optimizations, or inconsistent outputs.

This means the new CJP method module should not silently convert optimization failures into valid-looking `NaN` result records. Legacy `FractureAnalysis` compatibility behavior may remain unchanged until a separate approved migration changes it.

## Documentation Expectations

New public classes, Pydantic models, dataclasses, protocol-like interfaces, and non-trivial functions must document:

- field meanings;
- why each field exists;
- unit assumptions;
- formula conversion policy;
- failure behavior;
- whether a value is native optimizer state, canonical result quantity, or compatibility alias.

Pydantic fields use `Field(description=...)`. Dataclasses without field-level metadata use class docstrings or nearby decision-focused comments.

## Verification Target

The implementation plan should require:

- direct unit tests for CJP coefficient-to-derived-output formulas;
- spec validation tests for method IDs, aliases, quantities, qualifiers, and units;
- direct `MethodResultSource` fixture tests without fake `FractureAnalysis` where possible;
- `FractureAnalysis` compatibility bridge tests for current CJP attributes;
- artifact writer tests for envelope, compact KG statement bundle, visualization graph, and HTML graph output;
- an actual-data CJP proof when the existing simulation fixture is deterministic enough for scoped assertions;
- architecture wiki validation with `python docs\architecture-wiki\check_wiki.py`.

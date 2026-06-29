# Candidate 011: Method Module Contract

Status: proposed
Role: Architecture candidate for defining a standard method-module Interface, its required seams, and build-time verification.

Related: [[refactor-candidates/003-self-contained-williams-fit-interface]], [[refactor-candidates/008-result-tag-schema]], [[refactor-candidates/010-provenance-metadata-architecture]], [[refactor-roadmap]]

## Observed Evidence

- `crackpy.fracture_analysis.methods.williams_fit` already has a method-local slice with `parameters.py`, `result.py`, `runner.py`, `source_adapter.py`, `builder.py`, `spec.yaml`, and `spec_loader.py`.
- `crackpy.fracture_analysis.methods.cjp_fit` now follows the same broad file shape, but it proves a more complex case because one method family has mixed-mode and Mode-I variants.
- CJP result quantities include repeated display symbols such as `error`, so result lookup needs `result_id` or `method_id` context rather than symbol-only lookup.
- [[refactor-candidates/010-provenance-metadata-architecture]] already defines `MethodResultSource`, `ProvenanceSliceSpec`, `MethodResultEnvelopeBuilder`, and `ResultEnvelope` as shared provenance/result infrastructure.
- [[results-io-workflows]] records that Williams-fit and CJP-fit provenance artifacts now use the same envelope, KG statement bundle, graph JSON, and graph HTML projection pattern.

## Problem

Williams-fit and CJP-fit are now similar enough to expose repeated method-module plumbing, but they are not identical enough to justify a broad base class.

Repeated plumbing currently includes method identity metadata, source snapshots, normalized configuration hashing, run/result ID policy, imported crack-tip estimate projection, dependency edges, envelope assembly, result artifact writing, and frontend-facing schema lookup.

Method-specific implementation still includes numerical runners, result containers, coefficient conversion, variant rules, source quantity extraction, unit rules, and result quantity mapping.

Without a declared method-module contract, future integral methods can copy the Williams/CJP structure inconsistently.

That would spread shallow duplication across J-integral, interaction integral, Bueckner-Chen, path SIF, path Williams coefficient, crack-tip correction, and detection result slices.

## Future Direction

Define a lightweight method-module contract as a protocol-like Interface plus build-time verifier.

The contract should verify method slices by behavior and exported seams rather than by inheritance.

The first production pilot should run the contract against Williams-fit and CJP-fit, because these two adapters prove both the one-result and multi-variant result shapes.

Future integral method modules should conform to the same contract only after the CJP/Williams contract exposes enough leverage.

The contract should be strict about seams and metadata, but permissive about method-local implementation.

For example, CJP may keep variant-specific result rules while Williams keeps coefficient-series rules.

Both should still expose a validated spec, typed parameters, typed results, a runner that can be tested without `FractureAnalysis`, a source adapter into `MethodResultSource`, and an envelope builder into `ResultEnvelope`.

## Draft Method-Module Shape

A conforming fracture-analysis method module should normally use this layout:

```text
crackpy/fracture_analysis/methods/<method_name>/
  __init__.py
  spec.yaml
  spec_loader.py
  parameters.py
  result.py
  runner.py
  source_adapter.py
  builder.py
```

`spec.yaml` defines stable method identity, schema versions, dependency roles, quantity records, legacy aliases, method references, and adapter policy.

`spec_loader.py` exposes a method-local loader such as `load_cjp_fit_spec()` and returns a validated spec object.

`parameters.py` defines result-affecting parameter models and exposes `result_parameters()` plus `parameter_origins()`.

`result.py` defines typed output records with field descriptions, unit meaning, and conversion helpers when the numerical implementation produces native coefficients or units.

`runner.py` exposes the computational method Interface and should be testable from explicit inputs without constructing a full `FractureAnalysis` object.

`source_adapter.py` translates either typed method results or legacy `FractureAnalysis` attributes into `MethodResultSource`.

`builder.py` translates `MethodResultSource` into `ResultEnvelope` and keeps method-local wrapper policy such as variant splitting and historical artifact stem choices.

## CJP Pilot Scope

CJP should be the next proving slice for the method-module contract because it is a stronger test than Williams.

It has one shared normalized configuration, one imported crack-tip estimate, two analysis runs, two result records, and method-specific variant routing.

The shared generic helper should own only the repeated runtime and provenance mechanics:

- deriving source stem and compatibility side from `SourceInput` and `CrackTipFrame`;
- creating deterministic configuration IDs from parameter hashes;
- constructing run IDs and result IDs from method key, optional variant, source stem, side, and short hash;
- projecting a manual/imported crack-tip estimate from a `CrackTipFrame`;
- adding dependency edges for configuration, input, crack-tip frame, and crack-tip estimate;
- writing standard `ResultEnvelope` artifacts;
- validating that a produced envelope can be indexed through `ResultSchemaIndex`.

CJP-local code should continue to own:

- mixed-mode and Mode-I variant definitions;
- CJP coefficient conversion formulas;
- CJP native and canonical coefficient records;
- CJP quantity extraction by variant;
- CJP-specific quantity validation;
- CJP method IDs and result schema versions declared in `spec.yaml`.

## Build-Time Verification

Add a method contract verifier that can be run from tests and later from build or release checks.

The verifier should receive a method module reference plus a small fixture factory.

The fixture factory is necessary because each method needs domain-specific numerical input, but the generic verifier can still validate the common Interface.

The first verifier should check:

- the expected module files exist;
- `spec.yaml` loads through the method-local loader;
- every `MethodSpec` has non-empty `method_id`, `display_name`, `kind`, `method_revision`, and `implementation_ref`;
- method IDs are unique inside the slice;
- legacy aliases are unique inside the slice;
- quantity records have stable quantity names, display symbols, descriptions, units, result schema versions, and legacy aliases where compatibility requires them;
- repeated display symbols are allowed only when result or method context can disambiguate them;
- parameter models expose `result_parameters()` and `parameter_origins()`;
- the method fixture can build a `MethodResultSource`;
- the method fixture can build a `ResultEnvelope`;
- the envelope passes `ResultSchemaIndex.from_envelope(envelope)`;
- standard envelope artifacts can be written from the envelope without importing `FractureAnalysis`, plotting, or legacy writers.

The verifier should not require a common base class.

It should treat the method module's public seam as the Interface and the numerical details as method-local implementation.

## Seams / Interfaces / Adapters

- Interface: method-module contract covering files, exported functions, specs, parameters, typed results, source snapshots, and envelope builders.
- Interface: method contract verifier used by tests and build checks.
- Interface: optional `MethodEnvelopePlan` or similar value object for shared run/result/configuration/estimate policy.
- Adapter: method-local `source_adapter.py` translating legacy `FractureAnalysis` or typed results into `MethodResultSource`.
- Adapter: method-local `builder.py` translating method sources into `ResultEnvelope`.
- Adapter: result artifact writer translating a `ResultEnvelope` into envelope JSON, KG statement bundle, graph JSON, and graph HTML.
- Existing implementations: `crackpy.fracture_analysis.methods.williams_fit` and `crackpy.fracture_analysis.methods.cjp_fit`.

## Consequences

- Future integral methods get a clear shape before code is copied across result families.
- The method-module contract becomes the test surface, which improves locality because verifier failures point to a specific seam.
- Generic runtime helpers can be extracted only where Williams and CJP prove real repeated behavior.
- CJP variant handling remains local instead of being flattened into a lowest-common-denominator generic runner.
- Build-time checks reduce the risk that one method slice forgets metadata, aliases, schema versions, or frontend-facing result context.
- Avoiding a base class keeps line-integral and detection methods from being forced into premature object-oriented inheritance.

## Open Questions

- Should the contract verifier live under `crackpy.methods`, `crackpy.provenance`, or a test-support module until more method families exist?
- Should method contract checks run only in tests first, or also in package build/release checks once the method registry exists?
- How much of `MethodEnvelopePlan` should be public production Interface versus internal helper for Williams/CJP-style provenance builders?
- Which integral method should be the first non-optimization pilot after CJP and Williams prove the contract: J-integral, interaction integral, or Bueckner-Chen?

## Definition Of Done

- A documented method-module contract exists and is linked from the refactor roadmap.
- Williams-fit and CJP-fit are used as the first contract examples.
- Contract tests verify method metadata, quantity metadata, alias uniqueness, contextual symbol lookup, parameter snapshots, source snapshots, and envelope construction.
- Shared runtime helpers remove repeated configuration/run/result ID and imported crack-tip estimate code from Williams/CJP builders without changing output shape.
- CJP still emits one mixed-mode run/result and one Mode-I run/result.
- Williams still emits one analysis run/result.
- Standard envelope artifact writing is reusable by both method slices.
- Method-local numerical runners, result containers, and source quantity extraction remain method-local.
- The architecture wiki records which parts are generic method infrastructure and which parts must stay method-specific until integral methods prove additional commonality.

## Decision State

Draft planning accepted for documentation only.

No package-wide method-module contract, build-time verifier, or generic method runtime helper is approved for implementation until a focused goal is explicitly started.

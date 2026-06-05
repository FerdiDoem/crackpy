# Williams Provenance Module Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the Williams-fit provenance slice into deeper, coherent modules while preserving the current public API, compact KG export, graph visualization output, and legacy result outputs.

**Architecture:** Keep the accepted source/spec split, but place generic provenance concepts under `crackpy/results/provenance/` and Williams-specific code under `crackpy/results/provenance/williams_fit/`. Prefer readable local code over one-time private helpers unless the helper names a real boundary, isolates validation, or creates a useful test seam.

**Tech Stack:** Python dataclasses, Pydantic v2, PyYAML, pytest, existing CrackPy fracture-analysis fixtures.

---

## Refactor Notes To Preserve

Record these notes during execution in `docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md` under a short "Williams Provenance Module Refactor Notes" subsection:

- Which one-time helpers were inlined and why readability improved.
- Which helpers remained because they are actual seams: source adapter, source-to-envelope builder, spec loader, and dependency validation.
- Whether the actual-data smoke slice found any difference between fake-analysis tests and real `FractureAnalysis` behavior.
- Any friction that future CJP or J-integral slices would hit when reusing `MethodResultSource`, `SourceDependency`, `SourceParameters`, `SourceQuantity`, or `ProvenanceSliceSpec`.

Do not promote CJP or J-integral abstractions during this refactor. Only write notes for reuse.

## Target File Layout

Create:

- `crackpy/results/provenance/__init__.py`: exports generic provenance source/spec types.
- `crackpy/results/provenance/source.py`: moves `MethodResultSource`, `SourceDependency`, `SourceInput`, `SourceParameters`, and `SourceQuantity`.
- `crackpy/results/provenance/spec.py`: moves `ProvenanceSliceSpec`, nested spec models, and generic YAML loader.
- `crackpy/results/provenance/williams_fit/__init__.py`: exports `build_williams_fit_envelope`, `build_williams_fit_envelope_from_source`, `williams_fit_source_from_analysis`, and `load_williams_fit_spec`.
- `crackpy/results/provenance/williams_fit/spec_loader.py`: loads the Williams-specific YAML resource without creating package import cycles.
- `crackpy/results/provenance/williams_fit/spec.yaml`: moves the Williams spec next to Williams-specific code.
- `crackpy/results/provenance/williams_fit/adapter.py`: current `FractureAnalysis` to `MethodResultSource` adapter.
- `crackpy/results/provenance/williams_fit/builder.py`: source/spec to `ResultEnvelope` builder.
- `crackpy/tests/test_fracture_analysis/test_williams_provenance_actual_data.py`: actual-data vertical-slice smoke test.

Modify:

- `crackpy/results/williams_provenance.py`: compatibility facade only.
- `crackpy/results/kg_statement_bundle.py`: import spec loader from the new package path.
- `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`: import from new package where useful, while keeping at least one compatibility import check.
- `crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py`: no behavior change expected; adjust imports only if needed.
- `crackpy/tests/test_fracture_analysis/test_graph_visualization.py`: no behavior change expected; adjust imports only if needed.
- `pyproject.toml`: package data path becomes `results/provenance/williams_fit/*.yaml`.
- `docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md`: add refactor notes after implementation.

Delete after move:

- `crackpy/results/provenance_source.py`
- `crackpy/results/provenance_spec.py`
- `crackpy/results/specs/williams_fit_provenance.yaml`

## Public API Contract

The following imports must continue to work:

```python
from crackpy.results.williams_provenance import build_williams_fit_envelope
from crackpy.results.williams_provenance import build_williams_fit_envelope_from_source
from crackpy.results.williams_provenance import williams_fit_source_from_analysis
```

The following new imports should work:

```python
from crackpy.results.provenance import MethodResultSource, SourceDependency, SourceParameters, SourceQuantity
from crackpy.results.provenance.williams_fit import build_williams_fit_envelope, load_williams_fit_spec
```

## Task 1: Move Generic Source And Spec Types

**Files:**
- Create: `crackpy/results/provenance/__init__.py`
- Create: `crackpy/results/provenance/source.py`
- Create: `crackpy/results/provenance/spec.py`
- Modify: `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`

- [ ] **Step 1: Write failing import tests**

Add this test to `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`:

```python
def test_generic_provenance_types_are_available_from_deeper_module():
    from crackpy.results.provenance import MethodResultSource, SourceDependency, SourceParameters, SourceQuantity

    assert MethodResultSource.__name__ == "MethodResultSource"
    assert SourceDependency.__name__ == "SourceDependency"
    assert SourceParameters.__name__ == "SourceParameters"
    assert SourceQuantity.__name__ == "SourceQuantity"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py::test_generic_provenance_types_are_available_from_deeper_module -q
```

Expected: FAIL because `crackpy.results.provenance` does not exist yet.

- [ ] **Step 3: Move generic source types**

Move the contents of `crackpy/results/provenance_source.py` into `crackpy/results/provenance/source.py`.

Create `crackpy/results/provenance/__init__.py`:

```python
"""Provenance source snapshots and spec models for result adapters."""
from crackpy.results.provenance.source import (
    MethodResultSource,
    SourceDependency,
    SourceInput,
    SourceParameters,
    SourceQuantity,
)
from crackpy.results.provenance.spec import (
    CoefficientQuantitySpec,
    DependencySpec,
    MethodSpec,
    ProvenanceSliceSpec,
    QuantitySpec,
    SchemaVersions,
    load_provenance_slice_spec,
)

__all__ = [
    "CoefficientQuantitySpec",
    "DependencySpec",
    "MethodResultSource",
    "MethodSpec",
    "ProvenanceSliceSpec",
    "QuantitySpec",
    "SchemaVersions",
    "SourceDependency",
    "SourceInput",
    "SourceParameters",
    "SourceQuantity",
    "load_provenance_slice_spec",
]
```

- [ ] **Step 4: Move generic spec models**

Move the contents of `crackpy/results/provenance_spec.py` into `crackpy/results/provenance/spec.py`, but remove `load_williams_fit_spec()` from the generic file. The generic file should expose only `load_provenance_slice_spec(path)`.

- [ ] **Step 5: Run focused test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py::test_generic_provenance_types_are_available_from_deeper_module -q
```

Expected: PASS.

## Task 2: Move Williams Slice Into A Deeper Module

**Files:**
- Create: `crackpy/results/provenance/williams_fit/__init__.py`
- Create: `crackpy/results/provenance/williams_fit/spec_loader.py`
- Create: `crackpy/results/provenance/williams_fit/spec.yaml`
- Create: `crackpy/results/provenance/williams_fit/adapter.py`
- Create: `crackpy/results/provenance/williams_fit/builder.py`
- Modify: `crackpy/results/williams_provenance.py`
- Modify: `crackpy/results/kg_statement_bundle.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing spec import test**

Add this test to `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`:

```python
def test_williams_fit_spec_loads_from_deeper_module():
    from crackpy.results.provenance.williams_fit import load_williams_fit_spec

    spec = load_williams_fit_spec()

    assert spec.schemas.envelope == "crackpy.result_envelope.williams_fit.v1"
    assert spec.dependencies["crack_tip_frame"].role == "used_crack_tip_frame"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py::test_williams_fit_spec_loads_from_deeper_module -q
```

Expected: FAIL because `crackpy.results.provenance.williams_fit` does not exist yet.

- [ ] **Step 3: Move `spec.yaml`**

Move `crackpy/results/specs/williams_fit_provenance.yaml` to `crackpy/results/provenance/williams_fit/spec.yaml`.

Create `crackpy/results/provenance/williams_fit/spec_loader.py`:

```python
"""Load the Williams-fit provenance slice specification."""
from importlib.resources import files

from crackpy.results.provenance.spec import ProvenanceSliceSpec, load_provenance_slice_spec


def load_williams_fit_spec() -> ProvenanceSliceSpec:
    spec_path = files("crackpy.results.provenance.williams_fit").joinpath("spec.yaml")
    return load_provenance_slice_spec(spec_path)
```

Create `crackpy/results/provenance/williams_fit/__init__.py`:

```python
"""Williams-fit provenance source adapter and envelope builder."""
from crackpy.results.provenance.williams_fit.adapter import williams_fit_source_from_analysis
from crackpy.results.provenance.williams_fit.builder import (
    build_williams_fit_envelope,
    build_williams_fit_envelope_from_source,
)
from crackpy.results.provenance.williams_fit.spec_loader import load_williams_fit_spec


__all__ = [
    "build_williams_fit_envelope",
    "build_williams_fit_envelope_from_source",
    "load_williams_fit_spec",
    "williams_fit_source_from_analysis",
]
```

- [ ] **Step 4: Move adapter code**

Move these functions from `crackpy/results/williams_provenance.py` into `crackpy/results/provenance/williams_fit/adapter.py`:

```text
_analysis_stem
_source_metadata
_material_parameters
_optimization_parameters
_parameter_origins
_source_quantities
williams_fit_source_from_analysis
```

Inline one-time mapping helpers only if the code remains readable. Keep `williams_fit_source_from_analysis()` as the public adapter seam.

- [ ] **Step 5: Move builder code**

Move envelope-building logic from `crackpy/results/williams_provenance.py` into `crackpy/results/provenance/williams_fit/builder.py`.

Keep:

```text
build_williams_fit_envelope_from_source
build_williams_fit_envelope
```

Collapse tiny one-time helpers inside `build_williams_fit_envelope_from_source()` when doing so makes the main flow clearer. Keep helpers only for:

```text
quantity projection from SourceQuantity to ResultQuantity
dependency validation or dependency edge construction
configuration construction and hash derivation if readability suffers inline
```

- [ ] **Step 6: Replace old module with compatibility facade**

Replace `crackpy/results/williams_provenance.py` with:

```python
"""Compatibility facade for the Williams-fit provenance adapter."""
from crackpy.results.provenance.williams_fit import (
    build_williams_fit_envelope,
    build_williams_fit_envelope_from_source,
    load_williams_fit_spec,
    williams_fit_source_from_analysis,
)

__all__ = [
    "build_williams_fit_envelope",
    "build_williams_fit_envelope_from_source",
    "load_williams_fit_spec",
    "williams_fit_source_from_analysis",
]
```

- [ ] **Step 7: Update package data**

Change `pyproject.toml` package data to:

```toml
[tool.setuptools.package-data]
crackpy = ["logging.yaml", "results/provenance/williams_fit/*.yaml"]
```

- [ ] **Step 8: Update imports**

Update imports in changed files:

```python
from crackpy.results.provenance import MethodResultSource, SourceDependency, SourceInput, SourceParameters, SourceQuantity
from crackpy.results.provenance.spec import MethodSpec, ProvenanceSliceSpec
from crackpy.results.provenance.williams_fit.spec_loader import load_williams_fit_spec
```

`kg_statement_bundle.py` should import `ProvenanceSliceSpec` from `crackpy.results.provenance.spec` and `load_williams_fit_spec` from `crackpy.results.provenance.williams_fit.spec_loader`.

- [ ] **Step 9: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_kg_statement_bundle.py crackpy\tests\test_fracture_analysis\test_graph_visualization.py -q
```

Expected: PASS.

## Task 3: Add Actual-Data Vertical Slice Smoke Test

**Files:**
- Create: `crackpy/tests/test_fracture_analysis/test_williams_provenance_actual_data.py`

- [ ] **Step 1: Write actual-data characterization smoke test**

Create `crackpy/tests/test_fracture_analysis/test_williams_provenance_actual_data.py`:

```python
from pathlib import Path

from crackpy.fracture_analysis.analysis import FractureAnalysis
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.results.provenance.williams_fit import build_williams_fit_envelope
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material


def test_williams_provenance_vertical_slice_on_simulation_fixture():
    project_root = Path(__file__).resolve().parents[3]
    nodemap = Nodemap(
        name="File_F_10000.0_a_0.5_B_200.0_H_200.0.txt",
        folder=project_root / "test_data" / "simulations" / "Nodemaps",
    )
    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    crack_tip = CrackTipInfo(50, 0, 0, "right")
    data = InputData(nodemap=nodemap)
    data.calc_stresses(material)
    data.transform_data(crack_tip.crack_tip_x, crack_tip.crack_tip_y, crack_tip.crack_tip_angle)

    analysis = FractureAnalysis(
        material=material,
        nodemap=nodemap,
        data=data,
        crack_tip_info=crack_tip,
        integral_properties=None,
        optimization_properties=OptimizationProperties(
            angle_gap=10,
            min_radius=5,
            max_radius=10,
            tick_size=0.01,
            terms=[-1, 0, 1, 2, 3, 4, 5],
        ),
    )
    analysis.run()

    envelope = build_williams_fit_envelope(analysis, crackpy_version="test-version")
    payload = envelope.to_dict()
    bundle = envelope_to_kg_statement_bundle(envelope).to_dict()

    assert payload["input_records"][0]["input_id"] == "input:File_F_10000.0_a_0.5_B_200.0_H_200.0"
    assert payload["configurations"][0]["parameter_hash"].startswith("sha256:")
    assert any(quantity["symbol"] == "K_I" for quantity in payload["results"][0]["quantities"])
    assert any(quantity["symbol"] == "a_-1" for quantity in payload["results"][0]["quantities"])
    assert "ResultQuantity" in bundle["groups"]
```

- [ ] **Step 2: Run test to verify the real fixture path passes**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance_actual_data.py -q
```

Expected: PASS in roughly 15 seconds on the current simulation fixture. The existing `FractureAnalysis.run()` path also attempts CJP optimizers when optimization properties are present; this smoke keeps `integral_properties=None` so it does not exercise line-integral work.

- [ ] **Step 3: Keep the test narrow**

Do not assert exact `K_I` values in this smoke test. Existing numerical tests cover specific fracture values. This test protects the vertical provenance path over real fixture data: current objects -> adapter -> source -> spec -> envelope -> KG bundle.

## Task 4: Slim The Builder For Coherence

**Files:**
- Modify: `crackpy/results/provenance/williams_fit/adapter.py`
- Modify: `crackpy/results/provenance/williams_fit/builder.py`

- [ ] **Step 1: Remove one-time helpers that do not create a seam**

Inline helpers when they are only used once and do not isolate validation. Candidates from the current flat module:

```text
_method_metadata
_dependency_edge
_configuration_from_source
```

Keep helper functions only when they preserve a useful boundary:

```text
williams_fit_source_from_analysis
build_williams_fit_envelope_from_source
_quantity_from_source
_source_quantities
SourceDependency validation
```

- [ ] **Step 2: Annotate complex blocks instead of extracting trivial helpers**

Use short comments for blocks such as:

```python
# Create the first-slice manual-import crack-tip estimate from the resolved frame.
```

Do not add comments that repeat field assignments.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_williams_provenance_actual_data.py -q
```

Expected: PASS.

## Task 5: Preserve Notes For Future Method Slices

**Files:**
- Modify: `docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md`

- [ ] **Step 1: Add implementation notes**

Add this subsection after the current `Source Adapter And Minimal Source Snapshot` section:

```markdown
### Williams Provenance Module Refactor Notes

The Williams-fit provenance refactor keeps generic source/spec concepts under `crackpy.results.provenance` and Williams-specific adapter, builder, and spec files under `crackpy.results.provenance.williams_fit`.

The retained seams are:

- `williams_fit_source_from_analysis()`: current `FractureAnalysis` to `MethodResultSource`;
- `build_williams_fit_envelope_from_source()`: `MethodResultSource` plus `ProvenanceSliceSpec` to `ResultEnvelope`;
- `SourceDependency`: validates dependency-name plus `record`/`target_id` shape;
- `load_williams_fit_spec()`: keeps Williams definitions close to the Williams builder while avoiding package import cycles.

One-time helper functions that do not name a domain operation or validation boundary should be inlined. This intentionally relaxes DRY when duplicated structure would make the vertical slice easier to read and easier to adapt for CJP or J-integral.

The actual-data vertical slice uses `test_data/simulations` to verify that a real `FractureAnalysis` run can produce the canonical envelope and compact KG statement bundle, not only a synthetic fake-analysis object.
```

- [ ] **Step 2: Run wiki check**

Run:

```powershell
.venv\Scripts\python.exe -B docs\architecture-wiki\check_wiki.py
```

Expected: PASS.

## Task 6: Remove Old Files And Verify Packaging

**Files:**
- Delete: `crackpy/results/provenance_source.py`
- Delete: `crackpy/results/provenance_spec.py`
- Delete: `crackpy/results/specs/williams_fit_provenance.yaml`

- [ ] **Step 1: Delete old files after imports are migrated**

Use `apply_patch` delete hunks for only these moved files. Do not touch unrelated dirty docs.

- [ ] **Step 2: Search for stale imports**

Run:

```powershell
rg -n "provenance_source|provenance_spec|results/specs|williams_fit_provenance.yaml" crackpy pyproject.toml docs/architecture-wiki
```

Expected: no stale references in code, package data, or architecture-wiki notes.

- [ ] **Step 3: Run package-data sanity check**

Run:

```powershell
@'
from importlib.resources import files
path = files("crackpy.results.provenance.williams_fit").joinpath("spec.yaml")
print(path)
print(path.read_text(encoding="utf-8").splitlines()[0])
'@ | .venv\Scripts\python.exe -
```

Expected output includes a readable `spec.yaml` path and first line `schemas:`.

## Task 7: Final Verification

**Files:**
- No edits unless a verification failure reveals a scoped issue.

- [ ] **Step 1: Run focused provenance tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_williams_provenance_actual_data.py crackpy\tests\test_fracture_analysis\test_kg_statement_bundle.py crackpy\tests\test_fracture_analysis\test_graph_visualization.py -q
```

Expected: PASS.

- [ ] **Step 2: Run fracture-analysis subset**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis -q
```

Expected: PASS. Existing NumPy warnings from data-processing tests are acceptable if unchanged.

- [ ] **Step 3: Run wiki check**

Run:

```powershell
.venv\Scripts\python.exe -B docs\architecture-wiki\check_wiki.py
```

Expected: PASS.

- [ ] **Step 4: Run diff check**

Run:

```powershell
git diff --check -- crackpy pyproject.toml docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md
```

Expected: no whitespace errors. LF/CRLF warnings are acceptable on this Windows checkout.

- [ ] **Step 5: Inspect dirty files before reporting**

Run:

```powershell
git status --short
```

Expected: only files in this plan plus previously dirty files. Do not claim ownership of unrelated dirty files.

## Self-Review

Spec coverage:

- Deeper module layout: covered by Tasks 1 and 2.
- Slimming one-time helpers: covered by Task 4.
- Notes for future versions: covered by Task 5.
- Vertical slice on actual data: covered by Task 3.
- Preserve existing outputs/API: covered by Public API Contract and Tasks 2, 7.

Placeholder scan:

- No placeholder tokens or unspecified "add tests" steps.
- Every command has an expected outcome.
- The actual-data test contains concrete fixture paths and code.

Scope:

- This plan does not add CJP, J-integral, RDF rendering, PROV-O export, or a method registry.
- It refactors the Williams provenance slice only and keeps the old public import facade.

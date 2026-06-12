# CJP Fit Result/Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved CJP mixed-mode and Mode-I result/provenance slice while preserving legacy CJP output behavior.

**Architecture:** Add a method-local `crackpy.fracture_analysis.methods.cjp_fit` package that mirrors the Williams slice boundary: typed result models, tested formula conversions, YAML-owned stable definitions, a source adapter, and a builder that reuses `crackpy.provenance.MethodResultEnvelopeBuilder`. Generic provenance code stays method-neutral; CJP-specific quantity variants and coefficient mapping stay in the CJP package.

**Tech Stack:** Python 3.12+, Pydantic v2, PyYAML, NumPy/SciPy optimizer results, existing CrackPy result/provenance dataclasses, pytest.

---

## Files

- Create: `crackpy/fracture_analysis/methods/cjp_fit/__init__.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/result.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/parameters.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/runner.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/spec.yaml`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/spec_loader.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/source_adapter.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/builder.py`
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_method_module.py`
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_provenance.py`
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_provenance_actual_data.py`
- Modify: `pyproject.toml` package data to include `fracture_analysis/methods/cjp_fit/*.yaml`
- Modify: `crackpy/results/write.py` to add additive CJP artifact writers and import the CJP builder lazily or narrowly
- Modify: `docs/architecture-wiki/decision-log.md` only if implementation evidence changes the approved design

## Task 1: Formula And Typed Result Models

**Files:**
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_method_module.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/result.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/runner.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/__init__.py`

- [ ] **Step 1: Write failing tests for coefficient conversion and runner API**

Add tests that import:

```python
from types import SimpleNamespace

import numpy as np
from scipy.optimize import OptimizeResult

from crackpy.fracture_analysis.methods.cjp_fit import (
    CjpModeIResult,
    CjpMixedModeResult,
    CjpOptimizer,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
    run_cjp_fit,
)
```

Assert:

```python
mixed = cjp_mixed_mode_outputs_from_coefficients([2.0, -0.5, 0.25, 30.0, 0.75], error=0.125)
assert mixed.error == 0.125
assert mixed.K_F == np.sqrt(np.pi / 2) * (2.0 - 3 * -0.5 - 8 * 0.75) / np.sqrt(1000)
assert mixed.K_R == -4 * np.sqrt(np.pi / 2) * (2 * 0.25 + 0.75 * np.pi) / np.sqrt(1000)
assert mixed.K_S == -np.sqrt(np.pi / 2) * (2.0 + -0.5) / np.sqrt(1000)
assert mixed.K_II == 2 * np.sqrt(2 * np.pi) * 0.25 / np.sqrt(1000)
assert mixed.T == -30.0
assert mixed.coefficients.A_r == 2.0 / np.sqrt(1000)
assert mixed.native_coefficients_MPa_sqrt_mm.A_r == 2.0
```

Assert:

```python
mode_i = cjp_mode_i_outputs_from_coefficients([3.0, -1.0, 25.0, 0.5, 12.0], error=0.25)
assert mode_i.error == 0.25
assert mode_i.K_F == np.sqrt(np.pi / 2) * (3.0 - 3 * -1.0 - 8 * 0.5) / np.sqrt(1000)
assert mode_i.K_R == -((2 * np.pi) ** 1.5) * 0.5 / np.sqrt(1000)
assert mode_i.K_S == np.sqrt(np.pi / 2) * (3.0 + -1.0) / np.sqrt(1000)
assert mode_i.T_x == -25.0
assert mode_i.T_y == -12.0
assert mode_i.coefficients.A == 3.0 / np.sqrt(1000)
assert mode_i.native_coefficients_MPa_sqrt_mm.A == 3.0
```

Assert the public runner signature uses `CjpOptimizer`, not `Any`, and returns a container with both results:

```python
optimizer = SimpleNamespace(
    optimize_cjp_displacements_mixedmode=lambda: OptimizeResult(x=np.asarray([2.0, -0.5, 0.25, 30.0, 0.75]), cost=0.125),
    optimize_cjp_displacements_modeI=lambda: OptimizeResult(x=np.asarray([3.0, -1.0, 25.0, 0.5, 12.0]), cost=0.25),
)
result = run_cjp_fit(optimizer)
assert result.mixed_mode.K_II == cjp_mixed_mode_outputs_from_coefficients([2.0, -0.5, 0.25, 30.0, 0.75], error=0.125).K_II
assert result.mode_i.T_y == -12.0
```

- [ ] **Step 2: Run the new tests and confirm import failure**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py -q
```

Expected: fails because `crackpy.fracture_analysis.methods.cjp_fit` does not exist.

- [ ] **Step 3: Implement result models and conversion functions**

Create frozen Pydantic models with `Field(description=...)` for every field:

- `CjpMixedModeCoefficientSet` with canonical exported `A_r`, `B_r`, `B_i`, `C`, `E`.
- `CjpModeICoefficientSet` with canonical exported `A`, `B`, `C`, `E`, `F`.
- `CjpMixedModeResult` with `error`, `K_F`, `K_R`, `K_S`, `K_II`, `T`, `coefficients`, and `native_coefficients_MPa_sqrt_mm`.
- `CjpModeIResult` with `error`, `K_F`, `K_R`, `K_S`, `T_x`, `T_y`, `coefficients`, and `native_coefficients_MPa_sqrt_mm`.
- `CjpFitResult` with `mixed_mode` and `mode_i`.

Create conversion functions:

- `cjp_mixed_mode_outputs_from_coefficients(coefficients: npt.ArrayLike, *, error: float) -> CjpMixedModeResult`
- `cjp_mode_i_outputs_from_coefficients(coefficients: npt.ArrayLike, *, error: float) -> CjpModeIResult`

Both functions validate exactly five coefficients and raise `ValueError` otherwise. Singular coefficients are exported as `MPa*m^{1/2}` by dividing native optimizer values by `sqrt(1000)`; `C` and `F` remain `MPa`.

- [ ] **Step 4: Implement runner protocol**

Create:

```python
class CjpOptimizer(Protocol):
    def optimize_cjp_displacements_mixedmode(self) -> OptimizeResult: ...
    def optimize_cjp_displacements_modeI(self) -> OptimizeResult: ...
```

Create:

```python
def run_cjp_fit(optimizer: CjpOptimizer) -> CjpFitResult:
    mixed = optimizer.optimize_cjp_displacements_mixedmode()
    mode_i = optimizer.optimize_cjp_displacements_modeI()
    return CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(mixed.x, error=mixed.cost),
        mode_i=cjp_mode_i_outputs_from_coefficients(mode_i.x, error=mode_i.cost),
    )
```

Do not catch optimizer exceptions in this method-local runner.

- [ ] **Step 5: Run tests green and commit**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py -q
```

Expected: all tests pass.

Commit:

```powershell
git add crackpy\fracture_analysis\methods\cjp_fit crackpy\tests\test_fracture_analysis\test_cjp_method_module.py
git commit -m "feat: add CJP fit result models"
```

## Task 2: YAML Spec And Source Adapter

**Files:**
- Modify: `crackpy/tests/test_fracture_analysis/test_cjp_method_module.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/spec.yaml`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/spec_loader.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/parameters.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/source_adapter.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing tests for spec and source adapter**

Add a fixture with a `CrackTipFrame`, `CjpFitResult`, and `CjpFitResultParameters`. Assert:

- `load_cjp_fit_spec().methods["mixed_mode"].method_id == "crackpy.fracture.cjp_mixed_mode_fit"`
- `load_cjp_fit_spec().methods["mode_i"].method_id == "crackpy.fracture.cjp_mode_i_fit"`
- YAML declares aliases `CJP_results` and `CJP_modeI_results`
- quantity specs include qualifier `variant` values `mixed_mode` and `mode_i`
- `source_from_result(...)` returns one input, one `crack_tip_frame` dependency, normalized parameters, and all coefficient plus derived quantities
- each emitted `SourceQuantity` for CJP values has a `variant` qualifier

- [ ] **Step 2: Run the tests and confirm missing spec/adapter failure**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py -q
```

Expected: fails on missing `load_cjp_fit_spec`, parameter models, or `source_from_result`.

- [ ] **Step 3: Implement YAML-owned stable definitions**

Create `spec.yaml` with:

- schemas `crackpy.result_envelope.cjp_fit.v1`, `crackpy.result_record.cjp_fit.v1`, `crackpy.configuration.cjp_fit.v1`, `crackpy.kg_statement_bundle.cjp_fit.v1`
- methods `mixed_mode`, `mode_i`, and `crack_tip_import`
- dependency `crack_tip_frame`
- scalar quantity entries for every derived output and coefficient, with canonical units and aliases from the approved spec
- each quantity entry carries a `variant` field through a CJP-specific Pydantic `CjpQuantitySpec`

Add `fracture_analysis/methods/cjp_fit/*.yaml` to `pyproject.toml` package data.

- [ ] **Step 4: Implement Pydantic spec loader**

Create `CjpQuantitySpec(QuantitySpec)` with:

```python
variant: str = Field(description="CJP variant that owns this quantity: mixed_mode or mode_i.")
```

Create `CjpFitSliceSpec(ProvenanceSliceSpec)` with:

```python
quantities: dict[str, CjpQuantitySpec] = Field(description="Allowed CJP source quantities keyed by quantity name.")
```

Validate allowed variants in a model validator so misspelled YAML fails early.

- [ ] **Step 5: Implement parameter models and source adapter**

Create material and optimization parameter models analogous to Williams, with CJP-specific class names and full field descriptions. `source_from_result(...)` should build `SourceQuantity` instances directly from typed result model dumps and the loaded YAML quantity definitions. The adapter should fail if a quantity in YAML cannot be read from the matching typed result.

- [ ] **Step 6: Run tests green and commit**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py -q
```

Commit:

```powershell
git add pyproject.toml crackpy\fracture_analysis\methods\cjp_fit crackpy\tests\test_fracture_analysis\test_cjp_method_module.py
git commit -m "feat: add CJP provenance source adapter"
```

## Task 3: Envelope Builder

**Files:**
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_provenance.py`
- Create: `crackpy/fracture_analysis/methods/cjp_fit/builder.py`
- Modify: `crackpy/fracture_analysis/methods/cjp_fit/__init__.py`

- [ ] **Step 1: Write failing envelope tests**

Use a direct `MethodResultSource` fixture and a typed-result fixture. Assert the envelope has:

- one input record
- one crack-tip frame
- one normalized configuration
- two method metadata records for the two CJP method IDs, plus crack-tip import metadata if a crack-tip estimate is created
- two analysis runs
- two result records
- mixed-mode result quantities only in the mixed-mode result
- Mode-I result quantities only in the Mode-I result
- dependency edges for input, configuration, and crack-tip frame

- [ ] **Step 2: Run the tests and confirm missing builder failure**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q
```

Expected: fails because the CJP builder is not available.

- [ ] **Step 3: Implement CJP envelope builder**

Create:

- `build_cjp_fit_envelope_from_source(source, *, spec=None, crackpy_version=None, started_at=None, completed_at=None)`
- `build_cjp_fit_envelope_from_result(...)`
- `build_cjp_fit_envelope_from_analysis(...)`

Use the generic `MethodResultEnvelopeBuilder` for input records, dependency lookup, configuration hashing, method metadata, dependency edges, and scalar `ResultQuantity` projection. Keep CJP-specific split logic limited to grouping `SourceQuantity` objects by `variant` and selecting `mixed_mode` versus `mode_i` method metadata.

- [ ] **Step 4: Run tests green and commit**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q
```

Commit:

```powershell
git add crackpy\fracture_analysis\methods\cjp_fit crackpy\tests\test_fracture_analysis\test_cjp_provenance.py
git commit -m "feat: build CJP provenance envelopes"
```

## Task 4: Writer Bridge And Artifacts

**Files:**
- Modify: `crackpy/tests/test_fracture_analysis/test_cjp_provenance.py`
- Modify: `crackpy/results/write.py`

- [ ] **Step 1: Write failing artifact writer tests**

Assert:

- `write_cjp_fit_provenance_artifacts(envelope, path, stem)` writes `_cjp_fit_envelope.json`, `_cjp_fit_kg_statement_bundle.json`, `_cjp_fit_graph.json`, `_cjp_fit_graph.html`
- `OutputWriter.write_cjp_fit_provenance_artifacts(path=tmp_path)` writes the same four projections from a fake analysis carrying `cjp_res_mm`, `cjp_res_m1`, `cjp_coeffs_mm`, and `cjp_coeffs_m1`
- `OutputWriter.write_json()` legacy sections remain unchanged for CJP

- [ ] **Step 2: Run tests and confirm missing writer failure**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q
```

Expected: fails because the writer bridge is missing.

- [ ] **Step 3: Implement additive writer bridge**

Add a top-level `write_cjp_fit_provenance_artifacts(envelope, path, stem)` beside the Williams writer. Add `OutputWriter.write_cjp_fit_provenance_artifacts(self, path=None)` that builds the CJP envelope from `self.analysis`. Do not alter `write_results()` or the existing CJP block in `write_json()` except for imports needed by the new writer.

- [ ] **Step 4: Run tests green and commit**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q
```

Commit:

```powershell
git add crackpy\results\write.py crackpy\tests\test_fracture_analysis\test_cjp_provenance.py
git commit -m "feat: write CJP provenance artifacts"
```

## Task 5: Actual-Data Slice And Full Verification

**Files:**
- Create: `crackpy/tests/test_fracture_analysis/test_cjp_provenance_actual_data.py`
- Modify: `docs/architecture-wiki/decision-log.md` only if the deterministic proof changes an architectural assumption

- [ ] **Step 1: Write actual-data proof test**

Use the same simulation fixture pattern as Williams. Run `FractureAnalysis.run()` with optimization properties, build the CJP envelope from analysis, and assert structural facts:

- input ID starts with `input:File_F_10000.0_a_0.5_B_200.0_H_200.0`
- there are exactly two CJP result records
- result quantities include `K_II` under mixed-mode and `T_y` under Mode-I
- coefficient quantities include `A_r` under mixed-mode and `A` under Mode-I
- KG statement bundle contains `ResultQuantity`

Do not assert exact optimizer-dependent CJP values unless they are deterministic under the fixture.

- [ ] **Step 2: Run actual-data test and inspect determinism**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_provenance_actual_data.py -q
```

Expected: pass on structural assertions. If optimizer nondeterminism only affects values, keep structural assertions.

- [ ] **Step 3: Run complete scoped verification**

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py crackpy\tests\test_fracture_analysis\test_cjp_provenance.py crackpy\tests\test_fracture_analysis\test_cjp_provenance_actual_data.py crackpy\tests\test_fracture_analysis\test_williams_method_module.py crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_graph_visualization.py crackpy\tests\test_fracture_analysis\test_kg_statement_bundle.py -q
```

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe docs\architecture-wiki\check_wiki.py
```

Run:

```powershell
git diff --check
```

- [ ] **Step 4: Commit verification slice**

Commit any actual-data test or documentation update:

```powershell
git add crackpy\tests\test_fracture_analysis\test_cjp_provenance_actual_data.py docs\architecture-wiki\decision-log.md
git commit -m "test: prove CJP provenance on simulation data"
```

Skip the commit if no files changed in this task.

## Task 6: Merge Back To Main

**Files:**
- Current branch: `codex/cjp-fit-result-provenance`
- Target branch: `main`

- [ ] **Step 1: Verify branch is clean**

Run:

```powershell
git status --short --branch
```

Expected: clean `codex/cjp-fit-result-provenance`.

- [ ] **Step 2: Merge from the main worktree**

From `C:\Users\Admin\Documents\Coding-Projekte\crackpy`, run:

```powershell
git merge --no-ff codex/cjp-fit-result-provenance
```

Resolve conflicts only within files touched by this plan. Do not revert unrelated dirty files in the main checkout.

- [ ] **Step 3: Final verification on main**

Run from main:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe -m pytest crackpy\tests\test_fracture_analysis\test_cjp_method_module.py crackpy\tests\test_fracture_analysis\test_cjp_provenance.py crackpy\tests\test_fracture_analysis\test_cjp_provenance_actual_data.py crackpy\tests\test_fracture_analysis\test_williams_method_module.py crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_graph_visualization.py crackpy\tests\test_fracture_analysis\test_kg_statement_bundle.py -q
```

Run:

```powershell
C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe docs\architecture-wiki\check_wiki.py
```

Run:

```powershell
git status --short --branch
```

Expected: tests pass, wiki check passes, and only pre-existing unrelated dirty files remain unstaged.

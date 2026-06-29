# Generic Method Runtime Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce an importable generic method metadata and artifact-writing seam that can be reused by crack detection, Williams fit, CJP fit, and later method slices without inventing method-specific metadata shapes.

**Architecture:** Keep `crackpy.provenance.spec.MethodSpec` as the shared method metadata core because Williams-fit, CJP-fit, and crack-detection metadata now use that shape. Add only thin generic helpers around method definitions, runtime records, and envelope artifact writing after the repetition is visible in at least detection, Williams, and CJP. Keep method-specific source adapters and numerical runners method-local.

**Tech Stack:** Python 3.12, dataclasses, Pydantic `MethodSpec`, existing `ResultEnvelope`, `MethodResultEnvelopeBuilder`, pytest, architecture wiki.

---

## Current Evidence

- Williams-fit and CJP-fit specs already declare `MethodSpec` fields in YAML: `method_id`, `display_name`, `kind`, `method_revision`, `implementation_ref`, `aliases`, and `references`.
- Crack-detection metadata now carries the same `MethodSpec` shape, with detection-specific `detection_task`, `implementation_family`, optional `network_architecture`, and optional `weights_artifact_id`.
- `MethodResultSource` already describes runtime source snapshots generically: primary inputs, dependencies, resolved parameters, and source quantities.
- `MethodResultEnvelopeBuilder` already projects `MethodResultSource` plus `ProvenanceSliceSpec` into generic records.
- `ResultEnvelope`, `AnalysisRun`, `MethodMetadata`, `NormalizedConfiguration`, `ResultRecord`, and `ResultQuantity` already model the "what ran, with which method, on which inputs, with which configuration, producing which result" structure.
- `ResultSchemaIndex` now proves why reusable method metadata must carry context instead of relying on display labels: CJP has repeated `error` symbols across mixed-mode and Mode-I result records, while Williams currently has unique coefficient and SIF labels.
- The first generic method-definition slice now exists: `crackpy.methods.definition` defines `MethodDefinition` and `MethodArtifactDefinition`, and detection metadata can export generic definitions through `known_crack_detection_method_definitions()`.
- Williams-fit and CJP-fit currently duplicate configuration ID generation from parameter hash, run/result ID construction, dependency-edge assembly, and manual/imported crack-tip estimate projection.
- Williams-fit and CJP-fit also duplicate material and optimization parameter snapshot patterns, but method-specific parameters such as Williams terms or CJP variants should remain method-local until more methods prove the shared shape.
- Artifact writing is still duplicated by method-family wrappers: Williams and CJP have separate entry points that produce envelope, KG statement bundle, graph JSON, and graph HTML artifacts.

## Postpone Until More Methods Exist

Do not implement a package-wide method registry yet. Wait until at least one more non-fracture method has a result/provenance slice beyond detection metadata. A global registry would otherwise guess at fields before line-intercept output, crack-tip correction output, and line-integral output have proven their needs.

Postpone these until more method slices exist:

- method trustworthiness, maturity, validation profile, applicability, and uncertainty fields;
- formal method-reference registry enforcement;
- provider/cache/device policy for pretrained neural networks;
- build-time implementation fingerprint validation;
- a full runtime orchestrator that calls numerical methods;
- automatic discovery of method definitions across the package;
- full replacement of legacy text, current JSON, CSV, and plot writers;
- expansion of `MethodResultSource` beyond scalar or small quantities unless line-integral/path slices prove qualifiers are insufficient.

## File Structure

- Create `crackpy/methods/__init__.py`: lightweight package entry point for generic method metadata helpers.
- Create `crackpy/methods/definition.py`: generic `MethodDefinition`, `MethodArtifactDefinition`, and conversion helpers around `MethodSpec`.
- Create `crackpy/methods/runtime.py`: generic helpers for method-run identity policy, normalized configuration IDs, run/result IDs, dependency edges, and manual crack-tip estimate projection.
- Create `crackpy/results/method_artifacts.py`: generic artifact writer for `ResultEnvelope` projections that can be reused by Williams and CJP wrappers.
- Modify `crackpy/fracture_analysis/methods/williams_fit/builder.py`: keep the public Williams entry point, delegate common artifact writing to `results.method_artifacts`.
- Modify `crackpy/fracture_analysis/methods/cjp_fit/builder.py`: keep the public CJP entry point, delegate common artifact writing to `results.method_artifacts`.
- Modify `crackpy/crack_detection/method_metadata.py`: optionally expose detection records as generic `MethodDefinition` after the helper exists.
- Test `crackpy/tests/test_methods/test_definition.py`: validate generic method definition behavior across Williams, CJP, and detection.
- Test `crackpy/tests/test_fracture_analysis/test_method_artifacts.py`: validate generic envelope/KG/graph artifact writing through existing Williams and CJP envelopes.
- Modify `docs/architecture-wiki/refactor-candidates/006-model-provider-seam.md`: link detection metadata to the shared method definition seam.
- Modify `docs/architecture-wiki/results-io-workflows.md`: document the generic artifact writer frontend handoff.
- Modify `docs/architecture-wiki/glossary.md`: add or refine "MethodDefinition" and "Method artifact writer" terms if implementation lands.

### Task 1: Characterize The Existing Shared Method Metadata Shape

Status: completed by `codex/generic-method-definitions`.

Implementation note: Williams-fit and CJP-fit intentionally share the `crackpy.crack_tip.manual_import` `MethodSpec`, so the completed characterization requires repeated method IDs to have identical specs rather than requiring every loaded slice to own globally unique IDs.

**Files:**
- Create: `crackpy/tests/test_methods/test_definition.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from crackpy.crack_detection.method_metadata import known_crack_detection_methods
from crackpy.fracture_analysis.methods.cjp_fit.spec_loader import load_cjp_fit_spec
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import load_williams_fit_spec
from crackpy.provenance.spec import MethodSpec


def test_detection_williams_and_cjp_expose_method_spec_records():
    detection_specs = [method.method_spec for method in known_crack_detection_methods()]
    williams_specs = list(load_williams_fit_spec().methods.values())
    cjp_specs = list(load_cjp_fit_spec().methods.values())

    all_specs = detection_specs + williams_specs + cjp_specs

    assert all(isinstance(method_spec, MethodSpec) for method_spec in all_specs)
    assert all(method_spec.method_id for method_spec in all_specs)
    assert all(method_spec.display_name for method_spec in all_specs)
    assert all(method_spec.kind for method_spec in all_specs)
    assert all(method_spec.method_revision for method_spec in all_specs)
    assert all(method_spec.implementation_ref for method_spec in all_specs)


def test_method_ids_are_unique_across_current_specs():
    detection_specs = [method.method_spec for method in known_crack_detection_methods()]
    williams_specs = list(load_williams_fit_spec().methods.values())
    cjp_specs = list(load_cjp_fit_spec().methods.values())

    method_ids = [method_spec.method_id for method_spec in detection_specs + williams_specs + cjp_specs]

    assert len(set(method_ids)) == len(method_ids)
```

- [ ] **Step 2: Run tests to verify they fail only because `crackpy/tests/test_methods` does not exist**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: FAIL before the test package and future helpers exist.

- [ ] **Step 3: Create the test package**

Create `crackpy/tests/test_methods/__init__.py` as an empty file.

- [ ] **Step 4: Run the characterization tests**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: PASS once the C-006 detection metadata slice is present.

- [ ] **Step 5: Commit**

```bash
git add crackpy/tests/test_methods
git commit -m "test: characterize shared method metadata shape"
```

### Task 2: Introduce A Generic MethodDefinition Helper

Status: completed by `codex/generic-method-definitions`.

**Files:**
- Create: `crackpy/methods/__init__.py`
- Create: `crackpy/methods/definition.py`
- Modify: `crackpy/tests/test_methods/test_definition.py`

- [ ] **Step 1: Write the failing tests**

```python
from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition


def test_method_definition_wraps_generic_method_spec_with_domain_tasks():
    detection_method = known_crack_detection_methods()[0]

    definition = MethodDefinition(
        method_spec=detection_method.method_spec,
        domain="crack_detection",
        tasks=(detection_method.detection_task,),
        artifacts=(
            MethodArtifactDefinition(
                artifact_id=detection_method.weights_artifact_id,
                role="pretrained_weights",
                required=True,
            ),
        ),
    )

    assert definition.method_id == detection_method.method_id
    assert definition.display_name == detection_method.display_name
    assert definition.domain == "crack_detection"
    assert definition.tasks == ("crack_tip_localization",)
    assert definition.artifacts[0].role == "pretrained_weights"


def test_method_definition_rejects_empty_tasks():
    detection_method = known_crack_detection_methods()[0]

    with pytest.raises(ValueError, match="at least one task"):
        MethodDefinition(
            method_spec=detection_method.method_spec,
            domain="crack_detection",
            tasks=(),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'crackpy.methods'`.

- [ ] **Step 3: Implement `crackpy/methods/definition.py`**

```python
"""Generic method definitions shared by detection and analysis methods."""
from __future__ import annotations

from dataclasses import dataclass

from crackpy.provenance.spec import MethodSpec


@dataclass(frozen=True, slots=True)
class MethodArtifactDefinition:
    """Artifact dependency or output declared by a method definition.

    `artifact_id` names the artifact when it is known, such as `UNetPath.pth`.
    `role` explains why the artifact matters, such as `pretrained_weights` or
    `result_envelope`. `required` tells orchestration or validation whether the
    method can run without it.
    """

    artifact_id: str | None
    role: str
    required: bool = True

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("MethodArtifactDefinition requires a non-empty role.")
        if self.required and not self.artifact_id:
            raise ValueError("Required method artifacts need a non-empty artifact_id.")


@dataclass(frozen=True, slots=True)
class MethodDefinition:
    """Shared importable method definition.

    `method_spec` is the generic method metadata core also used in provenance
    specs. `domain` names the package area that owns the method. `tasks` names
    output or workflow tasks at the method level. `artifacts` records declared
    method assets or output artifact roles without embedding writer policy.
    """

    method_spec: MethodSpec
    domain: str
    tasks: tuple[str, ...]
    artifacts: tuple[MethodArtifactDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("MethodDefinition requires a non-empty domain.")
        if not self.tasks:
            raise ValueError("MethodDefinition requires at least one task.")

    @property
    def method_id(self) -> str:
        return self.method_spec.method_id

    @property
    def display_name(self) -> str:
        return self.method_spec.display_name
```

- [ ] **Step 4: Implement `crackpy/methods/__init__.py`**

```python
from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition

__all__ = ["MethodArtifactDefinition", "MethodDefinition"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crackpy/methods crackpy/tests/test_methods/test_definition.py
git commit -m "feat: add generic method definitions"
```

### Task 3: Let Detection Metadata Export Generic MethodDefinitions

Status: completed by `codex/generic-method-definitions`.

**Files:**
- Modify: `crackpy/crack_detection/method_metadata.py`
- Modify: `crackpy/tests/test_crack_detection/test_method_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
def test_detection_metadata_exports_generic_method_definitions():
    definitions = known_crack_detection_method_definitions()

    by_id = {definition.method_id: definition for definition in definitions}
    parallel_nets = by_id["crackpy.detection.parallel_nets_crack_tip_localization"]

    assert parallel_nets.domain == "crack_detection"
    assert parallel_nets.tasks == ("crack_tip_localization",)
    assert parallel_nets.artifacts[0].artifact_id == "ParallelNets.pth"
    assert parallel_nets.artifacts[0].role == "pretrained_weights"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_crack_detection\test_method_metadata.py::test_detection_metadata_exports_generic_method_definitions -q`

Expected: FAIL with `NameError` or import failure for `known_crack_detection_method_definitions`.

- [ ] **Step 3: Implement the export helper**

```python
from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition


def known_crack_detection_method_definitions() -> tuple[MethodDefinition, ...]:
    """Return detection methods in the generic importable method-definition shape."""
    definitions: list[MethodDefinition] = []
    for metadata in KNOWN_CRACK_DETECTION_METHODS:
        artifacts: tuple[MethodArtifactDefinition, ...] = ()
        if metadata.weights_artifact_id is not None:
            artifacts = (
                MethodArtifactDefinition(
                    artifact_id=metadata.weights_artifact_id,
                    role="pretrained_weights",
                    required=True,
                ),
            )
        definitions.append(
            MethodDefinition(
                method_spec=metadata.method_spec,
                domain="crack_detection",
                tasks=(metadata.detection_task,),
                artifacts=artifacts,
            )
        )
    return tuple(definitions)
```

- [ ] **Step 4: Update `__all__`**

Add `"known_crack_detection_method_definitions"` to `crackpy/crack_detection/method_metadata.py`.

- [ ] **Step 5: Run tests**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_crack_detection\test_method_metadata.py crackpy\tests\test_methods\test_definition.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crackpy/crack_detection/method_metadata.py crackpy/tests/test_crack_detection/test_method_metadata.py
git commit -m "feat: expose detection method definitions"
```

### Task 4: Introduce Generic Method Runtime Identity Helpers

**Files:**
- Create: `crackpy/methods/runtime.py`
- Modify: `crackpy/methods/__init__.py`
- Modify: `crackpy/tests/test_methods/test_definition.py`

- [ ] **Step 1: Write the failing tests**

```python
from crackpy.methods.runtime import (
    MethodRunIdentityPolicy,
    build_manual_crack_tip_estimate,
)
from crackpy.provenance import MethodResultEnvelopeBuilder
from crackpy.results.result_data import CrackTipFrame


def test_method_run_identity_policy_derives_ids_from_parameter_hash():
    policy = MethodRunIdentityPolicy(method_key="williams_fit")

    assert policy.configuration_id("sha256:abcdef1234567890") == "configuration:williams_fit:abcdef123456"
    assert policy.run_id(stem="Dummy2", side="right", short_hash="abcdef123456") == (
        "run:williams_fit:Dummy2:right:abcdef123456"
    )
    assert policy.result_id(stem="Dummy2", side="right", short_hash="abcdef123456") == (
        "result:williams_fit:Dummy2:right:abcdef123456"
    )


def test_method_run_identity_policy_supports_variant_ids():
    policy = MethodRunIdentityPolicy(method_key="cjp_fit")

    assert policy.run_id(stem="Dummy2", side="right", short_hash="abcdef123456", variant="mode_i") == (
        "run:cjp_fit:mode_i:Dummy2:right:abcdef123456"
    )
    assert policy.result_id(stem="Dummy2", side="right", short_hash="abcdef123456", variant="mode_i") == (
        "result:cjp_fit:mode_i:Dummy2:right:abcdef123456"
    )


def test_manual_crack_tip_estimate_projection_is_shared():
    frame = CrackTipFrame.from_legacy_side(
        stem="Dummy2",
        side="right",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=0.0,
    )

    estimate = build_manual_crack_tip_estimate(
        stem="Dummy2",
        side="right",
        input_id="input:Dummy2",
        method_id="crackpy.crack_tip.manual_import",
        configuration_id="configuration:williams_fit:abcdef123456",
        frame=frame,
    )

    assert estimate.estimate_id == "crack_tip_estimate:Dummy2:right"
    assert estimate.observed_mm == {"x": 1.0, "y": 2.0}
    assert estimate.corrected_mm == {"x": 1.0, "y": 2.0}
    assert estimate.correction_delta_mm == {"x": 0.0, "y": 0.0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: FAIL with `ModuleNotFoundError` for `crackpy.methods.runtime`.

- [ ] **Step 3: Implement `crackpy/methods/runtime.py`**

```python
"""Reusable method-run identity helpers.

These helpers own generic ID and imported-crack-tip projection policy. They do
not call numerical methods and do not expand method-specific quantities.
"""
from __future__ import annotations

from dataclasses import dataclass

from crackpy.results.result_data import CrackTipEstimateResult, CrackTipFrame


@dataclass(frozen=True, slots=True)
class MethodRunIdentityPolicy:
    """Deterministic ID policy for method run, result, and configuration records."""

    method_key: str

    def __post_init__(self) -> None:
        if not self.method_key:
            raise ValueError("MethodRunIdentityPolicy requires a non-empty method_key.")

    def short_hash(self, parameter_hash: str) -> str:
        return parameter_hash.removeprefix("sha256:")[:12]

    def configuration_id(self, parameter_hash: str) -> str:
        return f"configuration:{self.method_key}:{self.short_hash(parameter_hash)}"

    def run_id(self, *, stem: str, side: str, short_hash: str, variant: str | None = None) -> str:
        parts = ["run", self.method_key]
        if variant is not None:
            parts.append(variant)
        parts.extend([stem, side, short_hash])
        return ":".join(parts)

    def result_id(self, *, stem: str, side: str, short_hash: str, variant: str | None = None) -> str:
        parts = ["result", self.method_key]
        if variant is not None:
            parts.append(variant)
        parts.extend([stem, side, short_hash])
        return ":".join(parts)


def build_manual_crack_tip_estimate(
    *,
    stem: str,
    side: str,
    input_id: str,
    method_id: str,
    configuration_id: str,
    frame: CrackTipFrame,
) -> CrackTipEstimateResult:
    """Project a legacy/manual crack-tip frame into a shared estimate record."""
    return CrackTipEstimateResult(
        estimate_id=f"crack_tip_estimate:{stem}:{side}",
        input_id=input_id,
        method_id=method_id,
        configuration_id=configuration_id,
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm=frame.origin_mm,
        corrected_mm=frame.origin_mm,
        correction_delta_mm={"x": 0.0, "y": 0.0},
    )
```

- [ ] **Step 4: Export the helpers**

Update `crackpy/methods/__init__.py`:

```python
from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition
from crackpy.methods.runtime import MethodRunIdentityPolicy, build_manual_crack_tip_estimate

__all__ = [
    "MethodArtifactDefinition",
    "MethodDefinition",
    "MethodRunIdentityPolicy",
    "build_manual_crack_tip_estimate",
]
```

- [ ] **Step 5: Run tests**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_methods\test_definition.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crackpy/methods/runtime.py crackpy/methods/__init__.py crackpy/tests/test_methods/test_definition.py
git commit -m "feat: add generic method run identity helpers"
```

### Task 5: Introduce A Generic ResultEnvelope Artifact Writer

**Files:**
- Create: `crackpy/results/method_artifacts.py`
- Create: `crackpy/tests/test_fracture_analysis/test_method_artifacts.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from crackpy.fracture_analysis.methods.williams_fit.builder import build_williams_fit_envelope_from_result
from crackpy.results.method_artifacts import write_result_envelope_artifacts


def test_generic_writer_emits_envelope_kg_and_graph(tmp_path, williams_fit_result):
    envelope = build_williams_fit_envelope_from_result(williams_fit_result)

    written = write_result_envelope_artifacts(envelope=envelope, output_dir=tmp_path, stem="result")

    assert written.envelope_path == tmp_path / "result_envelope.json"
    assert written.kg_statement_bundle_path == tmp_path / "result_kg_statement_bundle.json"
    assert written.graph_path == tmp_path / "result_graph.json"
    assert written.html_graph_path == tmp_path / "result_graph.html"
    assert written.envelope_path.exists()
    assert written.kg_statement_bundle_path.exists()
    assert written.graph_path.exists()
    assert written.html_graph_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_fracture_analysis\test_method_artifacts.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'crackpy.results.method_artifacts'`.

- [ ] **Step 3: Implement `crackpy/results/method_artifacts.py`**

```python
"""Generic artifact writing for result/provenance envelopes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crackpy.results.graph_visualization import (
    envelope_to_visualization_graph,
    write_visualization_graph_html,
)
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.results.result_data import ResultEnvelope, write_json_file


@dataclass(frozen=True)
class WrittenEnvelopeArtifacts:
    """Paths written for one result/provenance envelope projection."""

    envelope_path: Path
    kg_statement_bundle_path: Path
    graph_path: Path
    html_graph_path: Path


def write_result_envelope_artifacts(
    *,
    envelope: ResultEnvelope,
    output_dir: str | Path,
    stem: str,
) -> WrittenEnvelopeArtifacts:
    """Write standard JSON, KG, graph JSON, and graph HTML artifacts for an envelope."""
    output_dir = Path(output_dir)
    envelope_path = write_json_file(envelope.to_dict(), output_dir / f"{stem}_envelope.json")

    kg_statement_bundle = envelope_to_kg_statement_bundle(envelope)
    kg_statement_bundle_path = write_json_file(
        kg_statement_bundle.to_dict(),
        output_dir / f"{stem}_kg_statement_bundle.json",
    )

    graph = envelope_to_visualization_graph(envelope)
    graph_path = write_json_file(graph.to_dict(), output_dir / f"{stem}_graph.json")
    html_graph_path = write_visualization_graph_html(graph, output_dir / f"{stem}_graph.html")

    return WrittenEnvelopeArtifacts(
        envelope_path=envelope_path,
        kg_statement_bundle_path=kg_statement_bundle_path,
        graph_path=graph_path,
        html_graph_path=html_graph_path,
    )
```

- [ ] **Step 4: Run the focused test**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_fracture_analysis\test_method_artifacts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crackpy/results/method_artifacts.py crackpy/tests/test_fracture_analysis/test_method_artifacts.py
git commit -m "feat: write generic envelope artifacts"
```

### Task 6: Delegate Williams And CJP Artifact Wrappers To The Generic Writer

**Files:**
- Modify: `crackpy/fracture_analysis/methods/williams_fit/builder.py`
- Modify: `crackpy/fracture_analysis/methods/cjp_fit/builder.py`
- Modify: existing Williams/CJP provenance tests if path-return types need adjustment.

- [ ] **Step 1: Write compatibility tests**

Add assertions to existing artifact-writer tests that the public Williams and CJP wrapper functions still write the historical filenames:

```python
def test_williams_wrapper_keeps_historical_artifact_names(tmp_path, williams_fit_result):
    envelope = build_williams_fit_envelope_from_result(williams_fit_result)

    written = write_williams_fit_provenance_artifacts(envelope, tmp_path, "sample")

    assert (tmp_path / "sample_williams_fit_envelope.json").exists()
    assert (tmp_path / "sample_williams_fit_kg_statement_bundle.json").exists()
    assert (tmp_path / "sample_williams_fit_graph.json").exists()
    assert (tmp_path / "sample_williams_fit_graph.html").exists()
```

- [ ] **Step 2: Run tests to verify current behavior before refactor**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q`

Expected: PASS before refactor.

- [ ] **Step 3: Replace duplicated artifact-writing code with the generic writer**

In each method builder, keep the method-specific public entry point and stem policy:

```python
from crackpy.results.method_artifacts import write_result_envelope_artifacts


def write_williams_fit_provenance_artifacts(envelope: ResultEnvelope, output_dir: str | Path, stem: str):
    return write_result_envelope_artifacts(
        envelope=envelope,
        output_dir=output_dir,
        stem=f"{stem}_williams_fit",
    )
```

Use the same pattern for CJP:

```python
def write_cjp_fit_provenance_artifacts(envelope: ResultEnvelope, output_dir: str | Path, stem: str):
    return write_result_envelope_artifacts(
        envelope=envelope,
        output_dir=output_dir,
        stem=f"{stem}_cjp_fit",
    )
```

- [ ] **Step 4: Run compatibility and generic writer tests**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' -m pytest crackpy\tests\test_fracture_analysis\test_method_artifacts.py crackpy\tests\test_fracture_analysis\test_williams_provenance.py crackpy\tests\test_fracture_analysis\test_cjp_provenance.py -q`

Expected: PASS with unchanged public artifact filenames.

- [ ] **Step 5: Commit**

```bash
git add crackpy/results/method_artifacts.py crackpy/fracture_analysis/methods/williams_fit/builder.py crackpy/fracture_analysis/methods/cjp_fit/builder.py crackpy/tests/test_fracture_analysis
git commit -m "refactor: share method envelope artifact writing"
```

### Task 7: Document The Reusable Method Metadata Seam

**Files:**
- Modify: `docs/architecture-wiki/results-io-workflows.md`
- Modify: `docs/architecture-wiki/refactor-candidates/006-model-provider-seam.md`
- Modify: `docs/architecture-wiki/glossary.md`

- [ ] **Step 1: Update `results-io-workflows.md`**

Add this observed note after the provenance artifact writer bullets:

```markdown
- `crackpy/results/method_artifacts.py`: generic artifact writer for `ResultEnvelope` projections. Method-local wrappers keep public filename policy, while the generic writer owns envelope JSON, compact KG bundle, graph JSON, and graph HTML projection.
```

- [ ] **Step 2: Update C-006**

Add this future/implemented distinction:

```markdown
The shared method metadata seam should use `MethodSpec` for method identity across detection and fracture-analysis methods. Detection-specific task and artifact fields are extensions, not replacements. Provider/cache/device policy remains outside this seam until more pretrained or external methods exist.
```

- [ ] **Step 3: Update glossary**

Add:

```markdown
#### MethodDefinition
Importable wrapper around shared `MethodSpec` plus domain, task, and artifact declarations. It exists to let methods such as crack-tip localization, Williams fit, and CJP fit expose common metadata without moving numerical runner code or source adapters out of method-local modules.

#### Method artifact writer
Reusable writer for standard `ResultEnvelope` projections. It writes envelope JSON, compact KG statement bundle, graph JSON, and graph HTML while method-local wrappers preserve public naming and compatibility policy.
```

- [ ] **Step 4: Run wiki check**

Run: `& 'C:\Users\Admin\Documents\Coding-Projekte\crackpy\.venv\Scripts\python.exe' docs\architecture-wiki\check_wiki.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture-wiki
git commit -m "docs: describe reusable method metadata seam"
```

## Definition Of Done

- Detection, Williams-fit, and CJP-fit method metadata all expose the same `MethodSpec` core.
- A generic `MethodDefinition` helper exists and is imported by detection metadata without moving numerical method code.
- A generic method-runtime helper owns deterministic configuration/run/result ID construction and manual crack-tip estimate projection for Williams/CJP-style envelopes.
- Result and quantity metadata lookup treats `symbol` as a readable method/result label and uses `quantity_id`, `result_id`, or `method_id` for stable identity and disambiguation.
- Generic envelope artifact writing exists in one Module and Williams/CJP public wrappers delegate to it without changing public artifact filenames.
- Tests prove the generic method metadata shape across detection, Williams, and CJP.
- Tests prove method-run identity and manual crack-tip estimate projection without constructing a full `FractureAnalysis` object.
- Tests prove the generic artifact writer emits envelope, KG bundle, graph JSON, and graph HTML from a `ResultEnvelope`.
- Existing Williams/CJP provenance tests still pass.
- Architecture wiki distinguishes observed implementation from deferred registry/provider/runtime-orchestrator work.

## Self-Review

- Spec coverage: The plan covers generic method metadata, runtime identity helpers, result-envelope artifacts, frontend handoff, and explicit postponement of global registry/provider work.
- Placeholder scan: The plan names concrete files, functions, commands, and expected outcomes; deferred items are explicitly listed as postponed scope.
- Type consistency: `MethodSpec`, `MethodDefinition`, `MethodArtifactDefinition`, `ResultEnvelope`, and `WrittenEnvelopeArtifacts` names are consistent across tasks.

# Williams Fit Result Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production Williams-fit result/provenance slice: canonical envelope records, deterministic hashes, compact KG statement-bundle projection, and a downstream graph visualization JSON kit, without restructuring existing pipelines.

**Architecture:** Keep the current `FractureAnalysis` and `OutputWriter.write_json()` behavior intact. Add pure result/provenance modules under `crackpy/results/` that extract from the current `FractureAnalysis` attributes, produce canonical JSON-friendly records, and expose optional writer methods for new artifacts. The graph visualization kit consumes the canonical envelope first; RDF, Turtle, namespaces, and HTML graph explorers stay out of core records.

**Tech Stack:** Python 3.12, dataclasses, standard-library `json` and `hashlib`, current CrackPy `FractureAnalysis`, `OutputWriter`, pytest/unittest test layout under `crackpy/tests/`.

---

## Execution Rules

- Execute autonomously from the saved plan.
- Do not refactor or restructure `FractureAnalysis`, `FractureAnalysisPipeline`, `InputData`, or current result writer output.
- Preserve current text and current JSON result compatibility.
- Commit after each task only after its listed tests pass.
- Use PowerShell commands from `C:\Users\Admin\Documents\Coding-Projekte\crackpy`.
- Prefer `.venv\Scripts\python.exe` when the virtual environment exists; otherwise use `python`.

## Planned File Structure

- Modify: `crackpy/results/result_data.py`
  - Core dataclasses, schema constants, canonical JSON normalization, deterministic SHA-256 helpers, JSON file writer.
- Create: `crackpy/results/williams_provenance.py`
  - Extract the Williams-fit slice from a current `FractureAnalysis` object into the canonical envelope.
- Create: `crackpy/results/kg_statement_bundle.py`
  - Project a canonical envelope into the compact statement-bundle export shape.
- Create: `crackpy/results/graph_visualization.py`
  - Convert the envelope into lightweight visualization graph JSON nodes and edges.
- Modify: `crackpy/results/write.py`
  - Add optional new writer method for Williams-fit provenance artifacts without changing existing `write_results()` or `write_json()`.
- Create: `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`
  - Tests for dataclasses, deterministic hashes, quantity extraction, envelope builder, and writer integration.
- Create: `crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py`
  - Tests for compact KG projection.
- Create: `crackpy/tests/test_fracture_analysis/test_graph_visualization.py`
  - Tests for graph visualization JSON projection.

## Task 1: Core Result/Provenance Records And Hashes

**Files:**
- Modify: `crackpy/results/result_data.py`
- Test: `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`

- [ ] **Step 1: Write the failing tests for canonical JSON, hashes, and core record serialization**

Create `crackpy/tests/test_fracture_analysis/test_williams_provenance.py` with this initial content:

```python
from pathlib import Path
from types import SimpleNamespace

import pytest

from crackpy.results.result_data import (
    WILLIAMS_FIT_ENVELOPE_SCHEMA,
    AnalysisRun,
    ArtifactRef,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    InputRecord,
    MethodMetadata,
    NormalizedConfiguration,
    ResultEnvelope,
    ResultQuantity,
    ResultRecord,
    canonical_json_bytes,
    sha256_canonical_json,
    to_jsonable,
    write_json_file,
)


def test_canonical_json_hash_is_stable_for_key_order():
    left = {"b": 2, "a": {"y": 1.0, "x": [3, 2, 1]}}
    right = {"a": {"x": [3, 2, 1], "y": 1.0}, "b": 2}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_canonical_json(left) == sha256_canonical_json(right)
    assert sha256_canonical_json(left).startswith("sha256:")


def test_non_finite_numbers_become_json_null():
    payload = {"nan": float("nan"), "positive_inf": float("inf"), "negative_inf": float("-inf")}

    assert to_jsonable(payload) == {"nan": None, "positive_inf": None, "negative_inf": None}


def test_normalized_configuration_hash_scopes_are_separate():
    configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [-1, 1, 2], "angle_gap_deg": 20.0},
        parameter_origins={"terms": "caller-provided", "angle_gap_deg": "model default"},
        adapter_policy={"write_legacy_json": True},
    )
    changed_adapter = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [-1, 1, 2], "angle_gap_deg": 20.0},
        parameter_origins={"terms": "caller-provided", "angle_gap_deg": "model default"},
        adapter_policy={"write_legacy_json": False},
    )

    assert configuration.parameter_hash == changed_adapter.parameter_hash
    assert configuration.configuration_hash != changed_adapter.configuration_hash


def test_result_envelope_to_dict_contains_schema_and_nested_records(tmp_path):
    input_record = InputRecord(input_id="input:demo", data_ref="demo.txt")
    method = MethodMetadata(
        method_id="crackpy.fracture.williams_fit",
        display_name="Williams Fit",
        kind="analysis",
        method_revision="1",
        implementation_ref="crackpy.fracture_analysis.analysis.FractureAnalysis._run_williams_optimization",
    )
    configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:test",
        schema_version="crackpy.configuration.williams_fit.v1",
        result_parameters={"terms": [1, 2]},
        parameter_origins={"terms": "caller-provided"},
        adapter_policy={},
    )
    frame = CrackTipFrame(
        frame_id="frame:demo",
        tip_id="tip:demo",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=3.0,
        compatibility_side="right",
    )
    estimate = CrackTipEstimateResult(
        estimate_id="estimate:demo",
        input_id=input_record.input_id,
        method_id="crackpy.crack_tip.manual_import",
        configuration_id=configuration.configuration_id,
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm={"x": 1.0, "y": 2.0},
        corrected_mm={"x": 1.0, "y": 2.0},
    )
    run = AnalysisRun(
        run_id="run:demo",
        method_id=method.method_id,
        method_revision=method.method_revision,
        input_ids=[input_record.input_id],
        configuration_id=configuration.configuration_id,
        parameter_hash=configuration.parameter_hash,
        dependencies=[
            DependencyEdge(source_id="run:demo", target_id="input:demo", role="used_input", target_type="InputRecord")
        ],
        crackpy_version="test",
    )
    quantity = ResultQuantity(
        quantity_id="quantity:demo:K_I",
        result_id="result:demo",
        symbol="K_I",
        description="Mode I stress intensity factor derived from Williams coefficient a_1.",
        value=12.5,
        unit="MPa*m^{1/2}",
        method_id=method.method_id,
        legacy_aliases=["Williams_fit_results.K_I"],
    )
    result = ResultRecord(
        result_id="result:demo",
        run_id=run.run_id,
        result_schema_version="crackpy.result_record.williams_fit.v1",
        quantities=[quantity],
        artifacts=[ArtifactRef(artifact_id="artifact:demo", role="canonical_envelope", path="demo.json")],
    )
    envelope = ResultEnvelope(
        input_records=[input_record],
        methods=[method],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=[run],
        results=[result],
    )

    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == WILLIAMS_FIT_ENVELOPE_SCHEMA
    assert payload["results"][0]["quantities"][0]["legacy_aliases"] == ["Williams_fit_results.K_I"]

    target = tmp_path / "envelope.json"
    write_json_file(payload, target)
    assert target.read_text(encoding="utf-8").startswith("{")
```

- [ ] **Step 2: Run tests and verify they fail because the result records do not exist yet**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py -q
```

Expected: FAIL with import errors for names from `crackpy.results.result_data`.

- [ ] **Step 3: Implement `crackpy/results/result_data.py`**

Replace the empty file with:

```python
"""Canonical result/provenance records for CrackPy result adapters."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping

WILLIAMS_FIT_ENVELOPE_SCHEMA = "crackpy.result_envelope.williams_fit.v1"
WILLIAMS_FIT_RESULT_SCHEMA = "crackpy.result_record.williams_fit.v1"
WILLIAMS_FIT_CONFIGURATION_SCHEMA = "crackpy.configuration.williams_fit.v1"
WILLIAMS_FIT_KG_BUNDLE_SCHEMA = "crackpy.kg_statement_bundle.williams_fit.v1"


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses and common scientific values to strict JSON values."""
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return to_jsonable(value.item())
    return value


def canonical_json_bytes(payload: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashable payloads."""
    return json.dumps(
        to_jsonable(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical_json(payload: Any) -> str:
    """Hash canonical JSON bytes with the production `sha256:` prefix."""
    return "sha256:" + sha256(canonical_json_bytes(payload)).hexdigest()


def write_json_file(payload: Any, path: str | Path) -> Path:
    """Write strict, stable, indented JSON and return the target path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as outfile:
        json.dump(to_jsonable(payload), outfile, indent=4, sort_keys=True, allow_nan=False)
        outfile.write("\n")
    return target


@dataclass(frozen=True)
class InputRecord:
    input_id: str
    data_ref: str
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    source_label: str | None = None
    source_hash: str | None = None


@dataclass(frozen=True)
class MethodMetadata:
    method_id: str
    display_name: str
    kind: str
    method_revision: str
    implementation_ref: str
    aliases: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizedConfiguration:
    configuration_id: str
    schema_version: str
    result_parameters: Mapping[str, Any]
    parameter_origins: Mapping[str, str]
    adapter_policy: Mapping[str, Any] = field(default_factory=dict)
    parameter_hash: str = ""
    configuration_hash: str = ""

    @classmethod
    def create(
        cls,
        configuration_id: str,
        schema_version: str,
        result_parameters: Mapping[str, Any],
        parameter_origins: Mapping[str, str],
        adapter_policy: Mapping[str, Any] | None = None,
    ) -> "NormalizedConfiguration":
        adapter_policy = adapter_policy or {}
        parameter_payload = {
            "schema_version": schema_version,
            "result_parameters": result_parameters,
            "parameter_origins": parameter_origins,
        }
        configuration_payload = {
            **parameter_payload,
            "adapter_policy": adapter_policy,
        }
        return cls(
            configuration_id=configuration_id,
            schema_version=schema_version,
            result_parameters=result_parameters,
            parameter_origins=parameter_origins,
            adapter_policy=adapter_policy,
            parameter_hash=sha256_canonical_json(parameter_payload),
            configuration_hash=sha256_canonical_json(configuration_payload),
        )


@dataclass(frozen=True)
class CrackTipFrame:
    frame_id: str
    tip_id: str
    origin_mm: Mapping[str, float | None]
    angle_deg: float | None
    compatibility_side: str | None = None


@dataclass(frozen=True)
class CrackTipEstimateResult:
    estimate_id: str
    input_id: str
    method_id: str
    configuration_id: str
    frame_id: str
    source: str
    observed_mm: Mapping[str, float | None]
    corrected_mm: Mapping[str, float | None]
    correction_delta_mm: Mapping[str, float | None] | None = None
    source_estimate_id: str | None = None


@dataclass(frozen=True)
class DependencyEdge:
    source_id: str
    target_id: str
    role: str
    target_type: str


@dataclass(frozen=True)
class AnalysisRun:
    run_id: str
    method_id: str
    method_revision: str
    input_ids: list[str]
    configuration_id: str
    parameter_hash: str
    dependencies: list[DependencyEdge]
    crackpy_version: str
    started_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class ResultQuantity:
    quantity_id: str
    result_id: str
    symbol: str
    description: str
    value: Any
    unit: str
    method_id: str
    derived_from_quantity_ids: list[str] = field(default_factory=list)
    statistic: str | None = None
    path_index: int | None = None
    legacy_aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    role: str
    path: str
    schema_version: str | None = None
    content_hash: str | None = None


@dataclass(frozen=True)
class ResultRecord:
    result_id: str
    run_id: str
    result_schema_version: str
    quantities: list[ResultQuantity]
    artifacts: list[ArtifactRef] = field(default_factory=list)


@dataclass(frozen=True)
class ResultEnvelope:
    input_records: list[InputRecord]
    methods: list[MethodMetadata]
    configurations: list[NormalizedConfiguration]
    crack_tip_frames: list[CrackTipFrame]
    crack_tip_estimates: list[CrackTipEstimateResult]
    analysis_runs: list[AnalysisRun]
    results: list[ResultRecord]
    envelope_schema_version: str = WILLIAMS_FIT_ENVELOPE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class KGStatement:
    subject_id: str
    key: str
    value: Any
    data_type: str
    unit: str
    description: str
    metadata_type: str
    source: str
    related_to: str
    subject_uri: str | None = None


@dataclass(frozen=True)
class KGStatementBundle:
    bundle_schema_version: str
    uri_policy: str
    descriptor_field_policy: str
    statements: list[KGStatement]
    groups: Mapping[str, list[KGStatement]]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class VisualizationNode:
    id: str
    type: str
    label: str
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualizationEdge:
    source: str
    target: str
    role: str
    label: str


@dataclass(frozen=True)
class VisualizationGraph:
    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)
```

- [ ] **Step 4: Run the tests for Task 1**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py -q
```

Expected: PASS for the four Task 1 tests.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add crackpy/results/result_data.py crackpy/tests/test_fracture_analysis/test_williams_provenance.py
git commit -m "feat: add Williams fit provenance records"
```

## Task 2: Williams-Fit Envelope Builder

**Files:**
- Create: `crackpy/results/williams_provenance.py`
- Modify: `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`

- [ ] **Step 1: Extend tests with a fake analysis object and envelope-builder assertions**

Append this content to `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`:

```python
from crackpy.results.williams_provenance import build_williams_fit_envelope


def _fake_analysis():
    data = SimpleNamespace(
        force=100.0,
        cycles=200.0,
        displacement=0.3,
        potential=None,
        cracklength=4.5,
        time=None,
    )
    crack_tip = SimpleNamespace(
        crack_tip_x=1.5,
        crack_tip_y=2.5,
        crack_tip_angle=12.0,
        left_or_right="right",
    )
    material = SimpleNamespace(
        name="AA2024-T3",
        E=72000,
        nu_xy=0.33,
        sig_yield=350,
        plane_strain=False,
        G=27067.66917293233,
        kappa=2.007518796992481,
    )
    optimization_properties = SimpleNamespace(
        angle_gap=20,
        min_radius=0.2,
        max_radius=1.0,
        tick_size=0.01,
        terms=[-1, 1, 2],
    )
    return SimpleNamespace(
        nodemap_file="DemoNodemap.txt",
        data=data,
        crack_tip=crack_tip,
        material=material,
        optimization_properties=optimization_properties,
        williams_fit_res={
            "Error_xy": 0.1,
            "Error_z": float("nan"),
            "K_I": 12.5,
            "K_II": -2.0,
            "K_III": float("nan"),
            "T": 4.0,
        },
        williams_fit_a_n={-1: 0.01, 1: 2.0, 2: 1.0},
        williams_fit_b_n={-1: 0.02, 1: -0.5, 2: 0.3},
        williams_fit_c_n={-1: float("nan"), 1: float("nan"), 2: float("nan")},
    )


def test_build_williams_fit_envelope_maps_current_result_section():
    envelope = build_williams_fit_envelope(_fake_analysis(), crackpy_version="test-version")
    payload = envelope.to_dict()

    assert payload["envelope_schema_version"] == "crackpy.result_envelope.williams_fit.v1"
    assert payload["input_records"][0]["input_id"] == "input:DemoNodemap"
    assert payload["crack_tip_frames"][0]["angle_deg"] == 12.0
    assert payload["crack_tip_frames"][0]["compatibility_side"] == "right"
    assert payload["analysis_runs"][0]["dependencies"][0]["role"] == "used_input"
    assert payload["analysis_runs"][0]["crackpy_version"] == "test-version"

    result = payload["results"][0]
    quantities = {quantity["symbol"]: quantity for quantity in result["quantities"]}
    assert quantities["K_I"]["legacy_aliases"] == ["Williams_fit_results.K_I"]
    assert quantities["error_xy"]["legacy_aliases"] == ["Williams_fit_results.error_xy", "Error_xy"]
    assert quantities["a_-1"]["legacy_aliases"] == ["Williams_fit_results.a_-1"]
    assert quantities["c_1"]["value"] is None


def test_build_williams_fit_envelope_rejects_missing_williams_results():
    analysis = _fake_analysis()
    analysis.williams_fit_res = None

    with pytest.raises(ValueError, match="Williams fit results"):
        build_williams_fit_envelope(analysis, crackpy_version="test-version")
```

- [ ] **Step 2: Run tests and verify they fail because the builder does not exist**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `crackpy.results.williams_provenance`.

- [ ] **Step 3: Implement `crackpy/results/williams_provenance.py`**

Create `crackpy/results/williams_provenance.py`:

```python
"""Williams-fit adapter for canonical result/provenance envelopes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import crackpy

from crackpy.fracture_analysis.crack_tip import unit_of_williams_coefficients
from crackpy.results.result_data import (
    WILLIAMS_FIT_CONFIGURATION_SCHEMA,
    WILLIAMS_FIT_RESULT_SCHEMA,
    AnalysisRun,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    InputRecord,
    MethodMetadata,
    NormalizedConfiguration,
    ResultEnvelope,
    ResultQuantity,
    ResultRecord,
    to_jsonable,
)

WILLIAMS_METHOD_ID = "crackpy.fracture.williams_fit"
CRACK_TIP_IMPORT_METHOD_ID = "crackpy.crack_tip.manual_import"
WILLIAMS_IMPLEMENTATION_REF = "crackpy.fracture_analysis.analysis.FractureAnalysis._run_williams_optimization"


def _analysis_stem(analysis: Any) -> str:
    return Path(str(getattr(analysis, "nodemap_file", "unknown_input"))).stem or "unknown_input"


def _source_metadata(data: Any) -> dict[str, Any]:
    mapping = {
        "force": "force_N",
        "cycles": "cycles",
        "displacement": "displacement_mm",
        "potential": "potential_V",
        "cracklength": "cracklength_dcpd_mm",
        "time": "timestamp_s",
    }
    metadata: dict[str, Any] = {}
    for attr, key in mapping.items():
        value = getattr(data, attr, None)
        if value is not None:
            metadata[key] = value
    return metadata


def _material_parameters(material: Any) -> dict[str, Any]:
    return {
        "name": getattr(material, "name", None),
        "E_MPa": getattr(material, "E", None),
        "nu_xy": getattr(material, "nu_xy", None),
        "sig_yield_MPa": getattr(material, "sig_yield", None),
        "plane_strain": getattr(material, "plane_strain", None),
        "G_MPa": getattr(material, "G", None),
        "kappa": getattr(material, "kappa", None),
    }


def _optimization_parameters(options: Any) -> dict[str, Any]:
    return {
        "angle_gap_deg": getattr(options, "angle_gap", None),
        "min_radius_mm": getattr(options, "min_radius", None),
        "max_radius_mm": getattr(options, "max_radius", None),
        "tick_size_mm": getattr(options, "tick_size", None),
        "terms": list(getattr(options, "terms", []) or []),
    }


def _parameter_origins(options: Any) -> dict[str, str]:
    return {
        "material": "analysis object",
        "crack_tip_frame": "analysis crack_tip",
        "angle_gap_deg": "resolved optimization property",
        "min_radius_mm": "resolved optimization property",
        "max_radius_mm": "resolved optimization property",
        "tick_size_mm": "resolved optimization property",
        "terms": "resolved optimization property",
    }


def _quantity(
    result_id: str,
    symbol: str,
    description: str,
    value: Any,
    unit: str,
    aliases: list[str],
) -> ResultQuantity:
    return ResultQuantity(
        quantity_id=f"quantity:{result_id}:{symbol}",
        result_id=result_id,
        symbol=symbol,
        description=description,
        value=to_jsonable(value),
        unit=unit,
        method_id=WILLIAMS_METHOD_ID,
        legacy_aliases=aliases,
    )


def _williams_quantities(analysis: Any, result_id: str) -> list[ResultQuantity]:
    if getattr(analysis, "williams_fit_res", None) is None:
        raise ValueError("Williams fit results are missing; run Williams optimization before building provenance.")

    fit_res = analysis.williams_fit_res
    quantities = [
        _quantity(result_id, "error_xy", "Williams fit residual for in-plane displacement components.", fit_res["Error_xy"], "1", ["Williams_fit_results.error_xy", "Error_xy"]),
        _quantity(result_id, "error_z", "Williams fit residual for out-of-plane displacement component.", fit_res["Error_z"], "1", ["Williams_fit_results.error_z", "Error_z"]),
        _quantity(result_id, "K_I", "Mode I stress intensity factor derived from Williams coefficient a_1.", fit_res["K_I"], "MPa*m^{1/2}", ["Williams_fit_results.K_I"]),
        _quantity(result_id, "K_II", "Mode II stress intensity factor derived from Williams coefficient b_1.", fit_res["K_II"], "MPa*m^{1/2}", ["Williams_fit_results.K_II"]),
        _quantity(result_id, "K_III", "Mode III stress intensity factor derived from Williams coefficient c_1.", fit_res["K_III"], "MPa*m^{1/2}", ["Williams_fit_results.K_III"]),
        _quantity(result_id, "T", "T-stress derived from Williams coefficient a_2.", fit_res["T"], "MPa", ["Williams_fit_results.T"]),
    ]

    for family, values in (
        ("a", getattr(analysis, "williams_fit_a_n", {}) or {}),
        ("b", getattr(analysis, "williams_fit_b_n", {}) or {}),
        ("c", getattr(analysis, "williams_fit_c_n", {}) or {}),
    ):
        for term, value in values.items():
            symbol = f"{family}_{term}"
            quantities.append(
                _quantity(
                    result_id,
                    symbol,
                    f"Williams coefficient {symbol}.",
                    value,
                    unit_of_williams_coefficients(term),
                    [f"Williams_fit_results.{symbol}"],
                )
            )
    return quantities


def build_williams_fit_envelope(
    analysis: Any,
    *,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    """Build the first-slice Williams-fit result/provenance envelope."""
    stem = _analysis_stem(analysis)
    side = getattr(analysis.crack_tip, "left_or_right", None) or "unknown_side"

    input_id = f"input:{stem}"
    frame_id = f"crack_tip_frame:{stem}:{side}"
    tip_id = f"crack_tip:{stem}:{side}"
    estimate_id = f"crack_tip_estimate:{stem}:{side}"

    result_parameters = {
        "material": _material_parameters(analysis.material),
        "optimization": _optimization_parameters(analysis.optimization_properties),
        "crack_tip_frame": {
            "origin_mm": {
                "x": getattr(analysis.crack_tip, "crack_tip_x", None),
                "y": getattr(analysis.crack_tip, "crack_tip_y", None),
            },
            "angle_deg": getattr(analysis.crack_tip, "crack_tip_angle", None),
            "compatibility_side": getattr(analysis.crack_tip, "left_or_right", None),
        },
    }
    parameter_origins = _parameter_origins(analysis.optimization_properties)
    provisional_configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:pending",
        schema_version=WILLIAMS_FIT_CONFIGURATION_SCHEMA,
        result_parameters=result_parameters,
        parameter_origins=parameter_origins,
        adapter_policy={"legacy_alias_scope": "Williams_fit_results"},
    )
    short_hash = provisional_configuration.parameter_hash.removeprefix("sha256:")[:12]
    configuration = NormalizedConfiguration.create(
        configuration_id=f"configuration:williams_fit:{short_hash}",
        schema_version=WILLIAMS_FIT_CONFIGURATION_SCHEMA,
        result_parameters=result_parameters,
        parameter_origins=parameter_origins,
        adapter_policy={"legacy_alias_scope": "Williams_fit_results"},
    )

    run_id = f"run:williams_fit:{stem}:{side}:{short_hash}"
    result_id = f"result:williams_fit:{stem}:{side}:{short_hash}"

    input_record = InputRecord(
        input_id=input_id,
        data_ref=str(getattr(analysis, "nodemap_file", "")),
        source_metadata=_source_metadata(analysis.data),
        source_label=stem,
    )
    method = MethodMetadata(
        method_id=WILLIAMS_METHOD_ID,
        display_name="Williams Fit",
        kind="analysis",
        method_revision="1",
        implementation_ref=WILLIAMS_IMPLEMENTATION_REF,
        aliases=["Williams_fit_results"],
        references=[],
    )
    import_method = MethodMetadata(
        method_id=CRACK_TIP_IMPORT_METHOD_ID,
        display_name="Manual Crack-Tip Import",
        kind="crack_tip_estimate",
        method_revision="1",
        implementation_ref="crackpy.input.crack_tip_info.CrackTipInfo",
        aliases=["crack_info_by_nodemap.txt"],
        references=[],
    )
    frame = CrackTipFrame(
        frame_id=frame_id,
        tip_id=tip_id,
        origin_mm={
            "x": getattr(analysis.crack_tip, "crack_tip_x", None),
            "y": getattr(analysis.crack_tip, "crack_tip_y", None),
        },
        angle_deg=getattr(analysis.crack_tip, "crack_tip_angle", None),
        compatibility_side=getattr(analysis.crack_tip, "left_or_right", None),
    )
    estimate = CrackTipEstimateResult(
        estimate_id=estimate_id,
        input_id=input_id,
        method_id=CRACK_TIP_IMPORT_METHOD_ID,
        configuration_id=configuration.configuration_id,
        frame_id=frame_id,
        source="manual import",
        observed_mm=frame.origin_mm,
        corrected_mm=frame.origin_mm,
        correction_delta_mm={"x": 0.0, "y": 0.0},
    )
    run = AnalysisRun(
        run_id=run_id,
        method_id=WILLIAMS_METHOD_ID,
        method_revision="1",
        input_ids=[input_id],
        configuration_id=configuration.configuration_id,
        parameter_hash=configuration.parameter_hash,
        dependencies=[
            DependencyEdge(run_id, input_id, "used_input", "InputRecord"),
            DependencyEdge(run_id, configuration.configuration_id, "used_configuration", "NormalizedConfiguration"),
            DependencyEdge(run_id, estimate_id, "used_crack_tip_estimate", "CrackTipEstimateResult"),
            DependencyEdge(run_id, frame_id, "used_crack_tip_frame", "CrackTipFrame"),
        ],
        crackpy_version=crackpy_version or getattr(crackpy, "__version__", "unknown"),
        started_at=started_at,
        completed_at=completed_at,
    )
    result = ResultRecord(
        result_id=result_id,
        run_id=run_id,
        result_schema_version=WILLIAMS_FIT_RESULT_SCHEMA,
        quantities=_williams_quantities(analysis, result_id),
        artifacts=[],
    )

    return ResultEnvelope(
        input_records=[input_record],
        methods=[method, import_method],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=[run],
        results=[result],
    )
```

- [ ] **Step 4: Run the Williams provenance tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add crackpy/results/williams_provenance.py crackpy/tests/test_fracture_analysis/test_williams_provenance.py
git commit -m "feat: build Williams fit provenance envelope"
```

## Task 3: Compact KG Statement Bundle Projection

**Files:**
- Create: `crackpy/results/kg_statement_bundle.py`
- Create: `crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py`

- [ ] **Step 1: Write the failing compact KG projection tests**

Create `crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py`:

```python
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.tests.test_fracture_analysis.test_williams_provenance import _fake_analysis
from crackpy.results.williams_provenance import build_williams_fit_envelope


def test_envelope_to_kg_statement_bundle_exports_result_and_quantity_statements():
    envelope = build_williams_fit_envelope(_fake_analysis(), crackpy_version="test-version")
    bundle = envelope_to_kg_statement_bundle(envelope)
    payload = bundle.to_dict()

    assert payload["bundle_schema_version"] == "crackpy.kg_statement_bundle.williams_fit.v1"
    assert payload["uri_policy"] == "local IDs only; URI minting belongs to exporter or KG importer policy"
    assert "ResultQuantity" in payload["groups"]

    statements = payload["statements"]
    keys = {(item["metadata_type"], item["key"]) for item in statements}
    assert ("CrackPyAnalysisResult", "crackpy_result_schema_version") in keys
    assert ("CrackPyAnalysis", "crackpy_method_id") in keys
    assert ("ResultQuantity", "crackpy_quantity_symbol") in keys
    assert any(item["value"] == "K_I" and item["unit"] == "1" for item in statements)
    assert all(item["subject_uri"] is None for item in statements)
```

- [ ] **Step 2: Run tests and verify they fail because the KG module does not exist**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `crackpy.results.kg_statement_bundle`.

- [ ] **Step 3: Implement `crackpy/results/kg_statement_bundle.py`**

Create `crackpy/results/kg_statement_bundle.py`:

```python
"""Compact KG statement-bundle projection for CrackPy result envelopes."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from crackpy.results.result_data import (
    WILLIAMS_FIT_KG_BUNDLE_SCHEMA,
    KGStatement,
    KGStatementBundle,
    ResultEnvelope,
    to_jsonable,
)


def _data_type(value: Any) -> str:
    value = to_jsonable(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "string"


def _statement(
    statements: list[KGStatement],
    *,
    subject_id: str,
    key: str,
    value: Any,
    unit: str,
    description: str,
    metadata_type: str,
    source: str,
    related_to: str,
) -> None:
    statements.append(
        KGStatement(
            subject_id=subject_id,
            key=key,
            value=to_jsonable(value),
            data_type=_data_type(value),
            unit=unit,
            description=description,
            metadata_type=metadata_type,
            source=source,
            related_to=related_to,
            subject_uri=None,
        )
    )


def envelope_to_kg_statement_bundle(envelope: ResultEnvelope) -> KGStatementBundle:
    """Project a canonical envelope into compact grouped KG statements."""
    statements: list[KGStatement] = []

    for method in envelope.methods:
        _statement(
            statements,
            subject_id=method.method_id,
            key="crackpy_method_id",
            value=method.method_id,
            unit="1",
            description="Stable CrackPy method identity.",
            metadata_type="CrackPyMethod",
            source="Code",
            related_to="CrackPyMethod",
        )
        _statement(
            statements,
            subject_id=method.method_id,
            key="crackpy_method_revision",
            value=method.method_revision,
            unit="1",
            description="Maintainer-controlled method semantic revision.",
            metadata_type="CrackPyMethod",
            source="Code",
            related_to="CrackPyMethod",
        )

    for configuration in envelope.configurations:
        _statement(
            statements,
            subject_id=configuration.configuration_id,
            key="crackpy_parameter_hash",
            value=configuration.parameter_hash,
            unit="1",
            description="SHA-256 hash of result-affecting parameters and origins.",
            metadata_type="CrackPyAnalysisConfiguration",
            source="Code",
            related_to="CrackPyAnalysisConfiguration",
        )
        _statement(
            statements,
            subject_id=configuration.configuration_id,
            key="crackpy_configuration_hash",
            value=configuration.configuration_hash,
            unit="1",
            description="SHA-256 hash of result-affecting parameters, origins, and adapter policy.",
            metadata_type="CrackPyAnalysisConfiguration",
            source="Code",
            related_to="CrackPyAnalysisConfiguration",
        )

    for run in envelope.analysis_runs:
        _statement(
            statements,
            subject_id=run.run_id,
            key="crackpy_analysis_run_id",
            value=run.run_id,
            unit="1",
            description="Stable ID for one Williams-fit analysis execution.",
            metadata_type="CrackPyAnalysis",
            source="Code",
            related_to="CrackPyAnalysis",
        )
        _statement(
            statements,
            subject_id=run.run_id,
            key="crackpy_method_id",
            value=run.method_id,
            unit="1",
            description="Method ID executed by the analysis run.",
            metadata_type="CrackPyAnalysis",
            source="Code",
            related_to="CrackPyAnalysis",
        )
        _statement(
            statements,
            subject_id=run.run_id,
            key="crackpy_version",
            value=run.crackpy_version,
            unit="1",
            description="CrackPy version used for the analysis run.",
            metadata_type="CrackPyAnalysis",
            source="Code",
            related_to="CrackPyAnalysis",
        )

    for result in envelope.results:
        _statement(
            statements,
            subject_id=result.result_id,
            key="crackpy_result_id",
            value=result.result_id,
            unit="1",
            description="Stable ID of the Williams-fit result record.",
            metadata_type="CrackPyAnalysisResult",
            source="Code",
            related_to="CrackPyAnalysisResult",
        )
        _statement(
            statements,
            subject_id=result.result_id,
            key="crackpy_result_schema_version",
            value=result.result_schema_version,
            unit="1",
            description="Schema version of the canonical Williams-fit result record.",
            metadata_type="CrackPyAnalysisResult",
            source="Code",
            related_to="CrackPyAnalysisResult",
        )
        for quantity in result.quantities:
            _statement(
                statements,
                subject_id=quantity.quantity_id,
                key="crackpy_quantity_symbol",
                value=quantity.symbol,
                unit="1",
                description="Domain-facing symbol of a Williams-fit result quantity.",
                metadata_type="ResultQuantity",
                source=quantity.method_id,
                related_to="ResultQuantity",
            )
            _statement(
                statements,
                subject_id=quantity.quantity_id,
                key="crackpy_quantity_value",
                value=quantity.value,
                unit=quantity.unit,
                description=quantity.description,
                metadata_type="ResultQuantity",
                source=quantity.method_id,
                related_to="ResultQuantity",
            )

    groups: dict[str, list[KGStatement]] = defaultdict(list)
    for statement in statements:
        groups[statement.related_to].append(statement)

    return KGStatementBundle(
        bundle_schema_version=WILLIAMS_FIT_KG_BUNDLE_SCHEMA,
        uri_policy="local IDs only; URI minting belongs to exporter or KG importer policy",
        descriptor_field_policy="plain statements only; RDF descriptor resources are downstream rendering choices",
        statements=statements,
        groups=dict(groups),
    )
```

- [ ] **Step 4: Run compact KG tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add crackpy/results/kg_statement_bundle.py crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py
git commit -m "feat: project Williams provenance to KG statements"
```

## Task 4: Graph Visualization JSON Kit

**Files:**
- Create: `crackpy/results/graph_visualization.py`
- Create: `crackpy/tests/test_fracture_analysis/test_graph_visualization.py`

- [ ] **Step 1: Write graph visualization tests**

Create `crackpy/tests/test_fracture_analysis/test_graph_visualization.py`:

```python
from crackpy.results.graph_visualization import envelope_to_visualization_graph
from crackpy.results.williams_provenance import build_williams_fit_envelope
from crackpy.tests.test_fracture_analysis.test_williams_provenance import _fake_analysis


def test_visualization_graph_consumes_envelope_records_and_dependency_edges():
    envelope = build_williams_fit_envelope(_fake_analysis(), crackpy_version="test-version")
    graph = envelope_to_visualization_graph(envelope)
    payload = graph.to_dict()

    node_types = {node["type"] for node in payload["nodes"]}
    assert "InputRecord" in node_types
    assert "CrackTipEstimateResult" in node_types
    assert "CrackTipFrame" in node_types
    assert "AnalysisRun" in node_types
    assert "ResultRecord" in node_types
    assert "ResultQuantity" in node_types

    roles = {edge["role"] for edge in payload["edges"]}
    assert "used_input" in roles
    assert "used_configuration" in roles
    assert "used_crack_tip_estimate" in roles
    assert "used_crack_tip_frame" in roles
    assert "was_generated_by" in roles
    assert "has_quantity" in roles

    assert all("subject_uri" not in node["data"] for node in payload["nodes"])
```

- [ ] **Step 2: Run tests and verify they fail because the graph module does not exist**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_graph_visualization.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `crackpy.results.graph_visualization`.

- [ ] **Step 3: Implement `crackpy/results/graph_visualization.py`**

Create `crackpy/results/graph_visualization.py`:

```python
"""Envelope-first graph visualization adapter for CrackPy results."""
from __future__ import annotations

from crackpy.results.result_data import (
    ResultEnvelope,
    VisualizationEdge,
    VisualizationGraph,
    VisualizationNode,
)


def _node(node_id: str, node_type: str, label: str, **data: object) -> VisualizationNode:
    return VisualizationNode(id=node_id, type=node_type, label=label, data=data)


def envelope_to_visualization_graph(envelope: ResultEnvelope) -> VisualizationGraph:
    """Convert canonical envelope records into graph nodes and semantic edges."""
    nodes: list[VisualizationNode] = []
    edges: list[VisualizationEdge] = []

    for input_record in envelope.input_records:
        nodes.append(_node(input_record.input_id, "InputRecord", input_record.source_label or input_record.input_id))

    for configuration in envelope.configurations:
        nodes.append(
            _node(
                configuration.configuration_id,
                "NormalizedConfiguration",
                configuration.configuration_id,
                parameter_hash=configuration.parameter_hash,
                configuration_hash=configuration.configuration_hash,
            )
        )

    for frame in envelope.crack_tip_frames:
        nodes.append(
            _node(
                frame.frame_id,
                "CrackTipFrame",
                frame.frame_id,
                angle_deg=frame.angle_deg,
                compatibility_side=frame.compatibility_side,
            )
        )

    for estimate in envelope.crack_tip_estimates:
        nodes.append(_node(estimate.estimate_id, "CrackTipEstimateResult", estimate.estimate_id, source=estimate.source))

    for run in envelope.analysis_runs:
        nodes.append(_node(run.run_id, "AnalysisRun", run.run_id, method_id=run.method_id))
        for dependency in run.dependencies:
            edges.append(
                VisualizationEdge(
                    source=dependency.source_id,
                    target=dependency.target_id,
                    role=dependency.role,
                    label=dependency.role,
                )
            )

    for result in envelope.results:
        nodes.append(_node(result.result_id, "ResultRecord", result.result_id, schema=result.result_schema_version))
        edges.append(
            VisualizationEdge(
                source=result.result_id,
                target=result.run_id,
                role="was_generated_by",
                label="was generated by",
            )
        )
        for quantity in result.quantities:
            nodes.append(
                _node(
                    quantity.quantity_id,
                    "ResultQuantity",
                    quantity.symbol,
                    value=quantity.value,
                    unit=quantity.unit,
                )
            )
            edges.append(
                VisualizationEdge(
                    source=result.result_id,
                    target=quantity.quantity_id,
                    role="has_quantity",
                    label="has quantity",
                )
            )
        for artifact in result.artifacts:
            nodes.append(_node(artifact.artifact_id, "ArtifactRef", artifact.role, path=artifact.path))
            edges.append(
                VisualizationEdge(
                    source=result.result_id,
                    target=artifact.artifact_id,
                    role="has_artifact",
                    label="has artifact",
                )
            )

    return VisualizationGraph(nodes=nodes, edges=edges)
```

- [ ] **Step 4: Run graph visualization tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_graph_visualization.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add crackpy/results/graph_visualization.py crackpy/tests/test_fracture_analysis/test_graph_visualization.py
git commit -m "feat: add Williams provenance graph visualization data"
```

## Task 5: Optional OutputWriter Integration

**Files:**
- Modify: `crackpy/results/write.py`
- Modify: `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`

- [ ] **Step 1: Add writer integration test**

Append this test to `crackpy/tests/test_fracture_analysis/test_williams_provenance.py`:

```python
from crackpy.results.write import OutputWriter


def test_output_writer_writes_new_provenance_artifacts_without_changing_legacy_json(tmp_path):
    analysis = _fake_analysis()
    writer = OutputWriter(path=tmp_path, fracture_analysis=analysis)

    written = writer.write_williams_fit_provenance_json(path=tmp_path)

    assert set(written) == {"envelope", "kg_statement_bundle", "visualization_graph"}
    assert written["envelope"].name.endswith("_williams_fit_envelope.json")
    assert written["kg_statement_bundle"].name.endswith("_williams_fit_kg_statement_bundle.json")
    assert written["visualization_graph"].name.endswith("_williams_fit_graph.json")
    assert written["envelope"].exists()
    assert written["kg_statement_bundle"].exists()
    assert written["visualization_graph"].exists()
```

- [ ] **Step 2: Run the writer test and verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py::test_output_writer_writes_new_provenance_artifacts_without_changing_legacy_json -q
```

Expected: FAIL with `AttributeError` because `OutputWriter.write_williams_fit_provenance_json` does not exist.

- [ ] **Step 3: Add imports to `crackpy/results/write.py`**

Near the existing imports in `crackpy/results/write.py`, add:

```python
from crackpy.results.graph_visualization import envelope_to_visualization_graph
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.results.result_data import write_json_file
from crackpy.results.williams_provenance import build_williams_fit_envelope
```

- [ ] **Step 4: Add the optional writer method to `OutputWriter`**

Inside class `OutputWriter`, after `write_json`, add:

```python
    def write_williams_fit_provenance_json(self, path=None) -> dict[str, Path]:
        """Write canonical Williams-fit provenance artifacts without changing legacy outputs."""
        output_path = self._make_path(path if path is not None else self.path)
        stem = Path(self.filename).stem

        envelope = build_williams_fit_envelope(self.analysis)
        kg_statement_bundle = envelope_to_kg_statement_bundle(envelope)
        visualization_graph = envelope_to_visualization_graph(envelope)

        written = {
            "envelope": write_json_file(envelope.to_dict(), output_path / f"{stem}_williams_fit_envelope.json"),
            "kg_statement_bundle": write_json_file(
                kg_statement_bundle.to_dict(),
                output_path / f"{stem}_williams_fit_kg_statement_bundle.json",
            ),
            "visualization_graph": write_json_file(
                visualization_graph.to_dict(),
                output_path / f"{stem}_williams_fit_graph.json",
            ),
        }
        return written
```

- [ ] **Step 5: Run writer integration tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

Run:

```powershell
git add crackpy/results/write.py crackpy/tests/test_fracture_analysis/test_williams_provenance.py
git commit -m "feat: write Williams fit provenance artifacts"
```

## Task 6: Regression Coverage

**Files:**
- Test: existing and new fracture-analysis tests

- [ ] **Step 1: Keep package-level result imports unchanged unless tests prove they are needed**

Run:

```powershell
git diff -- crackpy/results/__init__.py
```

Expected: no diff. The package `results.__init__` is already eager, and the new modules should remain directly importable without adding more package import side effects.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py crackpy/tests/test_fracture_analysis/test_graph_visualization.py -q
```

Expected: PASS.

- [ ] **Step 3: Run current result reader regression test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_read.py -q
```

Expected: PASS. This confirms current result tags and CSV flattening still work.

- [ ] **Step 4: Commit Task 6 only if this task produced an intentional edit**

Run this only if Step 1 proved `crackpy/results/__init__.py` must be changed:

```powershell
git add crackpy/results/__init__.py
git commit -m "feat: expose Williams provenance result modules"
```

## Task 7: Documentation Alignment

**Files:**
- Modify only if implementation revealed a mismatch: `docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md`
- Modify only if implementation revealed a mismatch: `docs/architecture-wiki/decision-log.md`

- [ ] **Step 1: Check whether implementation changed planned field names or scope**

Run:

```powershell
git diff -- crackpy/results/result_data.py crackpy/results/williams_provenance.py crackpy/results/kg_statement_bundle.py crackpy/results/graph_visualization.py crackpy/results/write.py
```

Expected: review output shows the implementation still uses:

- `crackpy.result_envelope.williams_fit.v1`
- `crackpy.result_record.williams_fit.v1`
- `crackpy.configuration.williams_fit.v1`
- `crackpy.kg_statement_bundle.williams_fit.v1`
- `degree` for canonical angle unit through `angle_deg`
- compatibility aliases limited to `Williams_fit_results`
- graph visualization consuming the envelope, not RDF or KG namespaces

- [ ] **Step 2: If no mismatch exists, leave docs unchanged**

Run:

```powershell
git status --short docs/architecture-wiki
```

Expected: no required documentation changes from implementation. If implementation field names or scope changed, update the architecture wiki immediately before continuing.

- [ ] **Step 3: Run architecture wiki validation**

Run:

```powershell
.venv\Scripts\python.exe -B docs\architecture-wiki\check_wiki.py
```

Expected: PASS.

- [ ] **Step 4: Commit documentation only when it changed**

Run this only if Step 2 required wiki edits:

```powershell
git add docs/architecture-wiki
git commit -m "docs: align Williams provenance implementation notes"
```

## Task 8: Final Verification

**Files:**
- No new edits unless verification finds a defect.

- [ ] **Step 1: Run focused provenance and visualization tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py crackpy/tests/test_fracture_analysis/test_graph_visualization.py -q
```

Expected: PASS.

- [ ] **Step 2: Run fracture-analysis test subset**

Run:

```powershell
.venv\Scripts\python.exe -m pytest crackpy/tests/test_fracture_analysis -q
```

Expected: PASS, or only known pre-existing failures unrelated to this branch. Investigate any failure in `test_williams_provenance.py`, `test_kg_statement_bundle.py`, `test_graph_visualization.py`, or `test_read.py` before continuing.

- [ ] **Step 3: Run wiki validation**

Run:

```powershell
.venv\Scripts\python.exe -B docs\architecture-wiki\check_wiki.py
```

Expected: PASS.

- [ ] **Step 4: Run diff whitespace validation**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 5: Inspect final repository state**

Run:

```powershell
git status --short
```

Expected: clean worktree after all task commits, or only explicitly intentional uncommitted files created by the active execution environment.

## Task 9: Completion Criteria

The `/goal` is complete when all of the following are true:

- `crackpy/results/result_data.py` defines the canonical envelope records and deterministic SHA-256 canonical JSON helpers.
- `crackpy/results/williams_provenance.py` builds a Williams-fit envelope from current `FractureAnalysis` attributes.
- `crackpy/results/kg_statement_bundle.py` exports a compact statement bundle from the envelope.
- `crackpy/results/graph_visualization.py` exports graph visualization JSON from the envelope without RDF or UI concepts in core records.
- `OutputWriter.write_williams_fit_provenance_json()` writes the new artifacts without altering `write_results()` or `write_json()`.
- New tests pass.
- Existing result reader regression tests pass.
- Architecture wiki validation passes.
- `git diff --check` passes.

Final message should include:

```text
Implemented the Williams-fit result/provenance slice and graph visualization JSON adapter.
Verified with:
- pytest crackpy/tests/test_fracture_analysis/test_williams_provenance.py crackpy/tests/test_fracture_analysis/test_kg_statement_bundle.py crackpy/tests/test_fracture_analysis/test_graph_visualization.py -q
- pytest crackpy/tests/test_fracture_analysis -q
- python -B docs/architecture-wiki/check_wiki.py
- git diff --check
```

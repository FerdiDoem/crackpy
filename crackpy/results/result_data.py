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

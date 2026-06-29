"""Canonical result/provenance records for CrackPy result adapters."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping

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
    """Canonical provenance record for one primary input.

    `input_id` is the stable identity used in dependency edges. `data_ref`
    points to the input data. `source_metadata` carries optional source-system
    facts. `source_label` is a human/workflow label. `sequence_index` is an
    ordering hint for input series and must not replace `input_id` as identity.
    `source_hash` identifies input content when available.
    """

    input_id: str
    data_ref: str
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    source_label: str | None = None
    sequence_index: int | None = None
    source_hash: str | None = None

    @property
    def provenance_id(self) -> str:
        return self.input_id


@dataclass(frozen=True)
class MethodMetadata:
    """Metadata for a registered method used by a result envelope.

    `method_id` is the stable method identity. `display_name` is report-facing.
    `kind` classifies the method. `method_revision` tracks semantic method
    changes. `implementation_ref` points to the current code. `aliases` and
    `references` connect legacy names and scientific sources.
    """

    method_id: str
    display_name: str
    kind: str
    method_revision: str
    implementation_ref: str
    aliases: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    @property
    def provenance_id(self) -> str:
        return self.method_id


@dataclass(frozen=True)
class NormalizedConfiguration:
    """Resolved configuration and hashes for one method run.

    `configuration_id` is the stable envelope identity. `schema_version`
    identifies the configuration shape. `result_parameters` and
    `parameter_origins` define the recomputation-relevant payload.
    `adapter_policy` records projection policy. `parameter_hash` and
    `configuration_hash` are deterministic SHA-256 hashes over those scopes.
    """

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

    @property
    def provenance_id(self) -> str:
        return self.configuration_id


@dataclass(frozen=True)
class CrackTipFrame:
    """Resolved crack-tip coordinate frame used by a method.

    `frame_id` is the provenance identity. `tip_id` names the crack-tip entity.
    `origin_mm` stores the frame origin in millimetres. `angle_deg` stores the
    in-plane local crack-extension direction in degrees. `compatibility_side`
    preserves legacy left/right vocabulary when available. `geometry_profile`
    declares the spatial assumptions of the frame so current planar-surface
    methods are not mistaken for general 3D crack-front support.
    """

    frame_id: str
    tip_id: str
    origin_mm: Mapping[str, float | None]
    angle_deg: float | None
    compatibility_side: str | None = None
    geometry_profile: str = "surface_planar"

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("CrackTipFrame requires a non-empty frame_id.")
        if not self.tip_id:
            raise ValueError("CrackTipFrame requires a non-empty tip_id.")
        if not self.geometry_profile:
            raise ValueError("CrackTipFrame requires a non-empty geometry_profile.")

    @classmethod
    def from_legacy_side(
            cls,
            *,
            stem: str,
            side: str,
            origin_mm: Mapping[str, float | None],
            angle_deg: float | None,
            geometry_profile: str = "surface_planar",
            tip_id: str | None = None,
    ) -> "CrackTipFrame":
        """Create a frame from the current left/right compatibility label.

        This adapter is the first C-005 seam: legacy `side` remains a file and
        output label, while the returned frame carries explicit provenance
        identity and geometry-profile metadata for downstream records. `tip_id`
        lets newer workflow callers carry a stable crack-tip identity through
        this compatibility adapter without making `side` the tip identity.
        """
        if not stem:
            raise ValueError("CrackTipFrame.from_legacy_side() requires a non-empty stem.")
        if side not in {"left", "right", "l", "r"}:
            raise ValueError("Legacy crack-tip side must be one of 'left', 'right', 'l', or 'r'.")
        if tip_id is not None and not tip_id:
            raise ValueError("CrackTipFrame.from_legacy_side() tip_id must be non-empty when provided.")
        return cls(
            frame_id=f"crack_tip_frame:{stem}:{side}",
            tip_id=tip_id or f"crack_tip:{stem}:{side}",
            origin_mm=origin_mm,
            angle_deg=angle_deg,
            compatibility_side=side,
            geometry_profile=geometry_profile,
        )

    @property
    def provenance_id(self) -> str:
        return self.frame_id


@dataclass(frozen=True)
class CrackTipEstimateResult:
    """Crack-tip estimate record linked into an analysis run.

    `estimate_id` is the provenance identity. `input_id`, `method_id`,
    `configuration_id`, and `frame_id` link the estimate to its producing
    context. `source` describes where the estimate came from. `observed_mm`,
    `corrected_mm`, and optional `correction_delta_mm` carry the positions.
    `source_estimate_id` links to an upstream estimate when one exists.
    """

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

    @property
    def provenance_id(self) -> str:
        return self.estimate_id


@dataclass(frozen=True)
class DependencyEdge:
    """Directed dependency edge inside an analysis run.

    `source_id` is the run or record using another record. `target_id` is the
    depended-on provenance identity. `role` describes the relationship.
    `target_type` records the expected target record class for projections.
    """

    source_id: str
    target_id: str
    role: str
    target_type: str


@dataclass(frozen=True)
class AnalysisRun:
    """One execution of a registered method over input records.

    `run_id` is the run identity. `method_id` and `method_revision` identify the
    method semantics. `input_ids`, `configuration_id`, and `dependencies` link
    the run context. `parameter_hash` supports stale-result checks.
    `crackpy_version`, `started_at`, and `completed_at` record execution facts.
    """

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

    @property
    def provenance_id(self) -> str:
        return self.run_id


@dataclass(frozen=True)
class ResultQuantity:
    """Canonical scalar or small result quantity.

    `quantity_id` is the quantity identity. `result_id` links to the containing
    result record. `symbol`, `description`, `value`, and `unit` define the
    scientific output. Optional relationship, statistic, path, and legacy alias
    fields support derived quantities and compatibility projections.
    """

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

    @property
    def provenance_id(self) -> str:
        return self.quantity_id


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to a produced artifact.

    `artifact_id` is the artifact identity. `role` describes its purpose.
    `path` points to the artifact. Optional `schema_version` and `content_hash`
    identify the artifact shape and bytes when available.
    """

    artifact_id: str
    role: str
    path: str
    schema_version: str | None = None
    content_hash: str | None = None

    @property
    def provenance_id(self) -> str:
        return self.artifact_id


@dataclass(frozen=True)
class ResultRecord:
    """Record for one method result.

    `result_id` is the result identity. `run_id` links to the producing run.
    `result_schema_version` identifies the quantity/artifact shape.
    `quantities` carries canonical values. `artifacts` links optional outputs.
    """

    result_id: str
    run_id: str
    result_schema_version: str
    quantities: list[ResultQuantity]
    artifacts: list[ArtifactRef] = field(default_factory=list)

    @property
    def provenance_id(self) -> str:
        return self.result_id


@dataclass(frozen=True)
class ResultEnvelope:
    """Top-level result/provenance envelope.

    Lists group the input, method, configuration, crack-tip, run, and result
    records that belong together. `envelope_schema_version` names the envelope
    shape for serialization and downstream projections.
    """

    input_records: list[InputRecord]
    methods: list[MethodMetadata]
    configurations: list[NormalizedConfiguration]
    crack_tip_frames: list[CrackTipFrame]
    crack_tip_estimates: list[CrackTipEstimateResult]
    analysis_runs: list[AnalysisRun]
    results: list[ResultRecord]
    envelope_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ResultSchemaEntry:
    """Schema-facing metadata for one canonical result quantity.

    `symbol`, `description`, `unit`, and `legacy_aliases` describe the public
    quantity contract that writers, readers, CSV adapters, and frontends can
    share. `result_schema_version` and `envelope_schema_version` keep the entry
    tied to the canonical result artifact version that produced it.
    """

    symbol: str
    description: str
    unit: str
    legacy_aliases: tuple[str, ...]
    result_schema_version: str
    envelope_schema_version: str
    method_id: str
    result_id: str
    quantity_id: str


@dataclass(frozen=True)
class ResultSchemaIndex:
    """Lookup table for schema-backed quantities in a result envelope.

    The index is intentionally built from `ResultEnvelope` records instead of
    writer code. That keeps the schema seam independent from `FractureAnalysis`,
    plotting, filesystem policy, and legacy text/CSV adapters. A quantity symbol
    can appear more than once in an envelope, for example CJP mixed-mode and
    Mode-I `error` quantities. Use `entry_for_symbol()` only for symbols that
    are unique in this envelope, or provide `result_id`/`method_id` context.
    """

    entries: tuple[ResultSchemaEntry, ...]
    _by_symbol: Mapping[str, tuple[ResultSchemaEntry, ...]] = field(init=False, repr=False)
    _by_legacy_alias: Mapping[str, ResultSchemaEntry] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        by_symbol: dict[str, list[ResultSchemaEntry]] = {}
        by_legacy_alias: dict[str, ResultSchemaEntry] = {}
        for entry in self.entries:
            by_symbol.setdefault(entry.symbol, []).append(entry)

            for alias in entry.legacy_aliases:
                if alias in by_legacy_alias:
                    raise ValueError(f"Duplicate legacy result alias in schema index: {alias!r}")
                by_legacy_alias[alias] = entry

        # The maps are derived from entries so callers cannot bypass index invariants.
        object.__setattr__(
            self,
            "_by_symbol",
            {symbol: tuple(symbol_entries) for symbol, symbol_entries in by_symbol.items()},
        )
        object.__setattr__(self, "_by_legacy_alias", by_legacy_alias)

    @classmethod
    def from_envelope(cls, envelope: ResultEnvelope) -> "ResultSchemaIndex":
        """Build an index and reject duplicate legacy alias mappings."""
        entries: list[ResultSchemaEntry] = []

        for result in envelope.results:
            for quantity in result.quantities:
                entries.append(
                    ResultSchemaEntry(
                        symbol=quantity.symbol,
                        description=quantity.description,
                        unit=quantity.unit,
                        legacy_aliases=tuple(quantity.legacy_aliases),
                        result_schema_version=result.result_schema_version,
                        envelope_schema_version=envelope.envelope_schema_version,
                        method_id=quantity.method_id,
                        result_id=result.result_id,
                        quantity_id=quantity.quantity_id,
                    )
                )

        return cls(entries=tuple(entries))

    def entry_for_symbol(self, symbol: str) -> ResultSchemaEntry:
        """Return the schema entry for a symbol that is unique in this envelope.

        Raises:
            KeyError: If the symbol is unknown.
            ValueError: If the symbol exists in multiple result contexts. Use
                `entry_for_symbol_in_result()` or `entry_for_symbol_for_method()`
                when the symbol is intentionally reused.
        """
        entries = self.entries_for_symbol(symbol)
        if len(entries) > 1:
            result_ids = ", ".join(entry.result_id for entry in entries)
            raise ValueError(
                f"Result symbol {symbol!r} is ambiguous across result IDs: {result_ids}. "
                "Use result_id or method_id context."
            )
        return entries[0]

    def entries_for_symbol(self, symbol: str) -> tuple[ResultSchemaEntry, ...]:
        """Return all schema entries for a canonical result symbol."""
        try:
            return self._by_symbol[symbol]
        except KeyError as exc:
            raise KeyError(f"Unknown result symbol: {symbol!r}") from exc

    def entry_for_symbol_in_result(self, symbol: str, result_id: str) -> ResultSchemaEntry:
        """Return the schema entry for `symbol` inside one result record."""
        matches = [entry for entry in self.entries_for_symbol(symbol) if entry.result_id == result_id]
        if not matches:
            raise KeyError(f"Unknown result symbol {symbol!r} for result_id {result_id!r}")
        if len(matches) > 1:
            raise ValueError(f"Duplicate result symbol {symbol!r} for result_id {result_id!r}")
        return matches[0]

    def entry_for_symbol_for_method(self, symbol: str, method_id: str) -> ResultSchemaEntry:
        """Return the schema entry for `symbol` produced by one method."""
        matches = [entry for entry in self.entries_for_symbol(symbol) if entry.method_id == method_id]
        if not matches:
            raise KeyError(f"Unknown result symbol {symbol!r} for method_id {method_id!r}")
        if len(matches) > 1:
            raise ValueError(f"Duplicate result symbol {symbol!r} for method_id {method_id!r}")
        return matches[0]

    def entry_for_legacy_alias(self, alias: str) -> ResultSchemaEntry:
        """Return the schema entry for a legacy writer or reader alias."""
        try:
            return self._by_legacy_alias[alias]
        except KeyError as exc:
            raise KeyError(f"Unknown legacy result alias: {alias!r}") from exc


@dataclass(frozen=True)
class KGStatement:
    """Compact knowledge-graph statement derived from an envelope.

    `subject_id`, `key`, and `value` form the statement. `data_type`, `unit`,
    `description`, `metadata_type`, `source`, and `related_to` make the compact
    projection queryable. `subject_uri` is optional URI materialization.
    """

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
    """Compact KG statement collection.

    `bundle_schema_version` identifies the bundle shape. URI and descriptor
    policies document projection choices. `statements` is the flat statement
    list, while `groups` provides grouped views over the same statements.
    """

    bundle_schema_version: str
    uri_policy: str
    descriptor_field_policy: str
    statements: list[KGStatement]
    groups: Mapping[str, list[KGStatement]]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class VisualizationNode:
    """Graph visualization node.

    `id` is the rendered node identity. `type` classifies the node. `label` is
    the visible graph label. `data` carries optional node details for the UI.
    """

    id: str
    type: str
    label: str
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualizationEdge:
    """Graph visualization edge.

    `source` and `target` identify connected nodes. `role` is the semantic edge
    role from provenance. `label` is the visible graph edge label.
    """

    source: str
    target: str
    role: str
    label: str


@dataclass(frozen=True)
class VisualizationGraph:
    """Graph visualization payload.

    `nodes` and `edges` are the renderable graph projection derived from a
    result/provenance envelope.
    """

    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

"""Minimal source snapshots consumed by provenance builders."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ProvenanceIdentified(Protocol):
    """Record that exposes its stable provenance identity explicitly."""

    @property
    def provenance_id(self) -> str:
        """Stable identifier used as a dependency target ID."""
        ...


@dataclass(frozen=True)
class SourceInput:
    """Primary data anchor consumed by a method.

    `input_id` is the stable provenance identity for the input. `data_ref`
    points to the source data or artifact. `source_metadata` carries optional
    source-system facts, not method parameters. `source_label` is a human or
    workflow label useful for deterministic IDs. `sequence_index` is an
    ordering hint for input series and must not replace `input_id` as identity.
    `source_hash` identifies the input content when available.
    """

    input_id: str
    data_ref: str
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    source_label: str | None = None
    sequence_index: int | None = None
    source_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.input_id:
            raise ValueError("SourceInput requires a non-empty input_id.")
        if not self.data_ref:
            raise ValueError("SourceInput requires a non-empty data_ref.")


@dataclass(frozen=True)
class SourceDependency:
    """Non-primary input dependency used by a method result.

    `dependency_name` is the spec-facing relationship name, not a Python class
    name. `record` carries a full typed dependency record created by the adapter
    and must expose `provenance_id`. `target_id` links to an already-existing
    dependency record. Exactly one of `record` or `target_id` must be set so the
    dependency is never ambiguous.
    """

    dependency_name: str
    record: ProvenanceIdentified | None = None
    target_id: str | None = None

    def __post_init__(self) -> None:
        has_record = self.record is not None
        has_target_id = self.target_id is not None
        if has_record == has_target_id:
            raise ValueError("SourceDependency requires exactly one of 'record' or 'target_id'.")
        if not self.dependency_name:
            raise ValueError("SourceDependency requires a non-empty dependency_name.")
        if self.target_id is not None and not self.target_id:
            raise ValueError("SourceDependency target_id must be non-empty when provided.")
        if self.record is not None and not isinstance(self.record, ProvenanceIdentified):
            raise TypeError("SourceDependency record must expose a 'provenance_id' property.")


@dataclass(frozen=True)
class SourceParameters:
    """Resolved result-affecting configuration snapshot.

    `result_parameters` stores concrete values after defaults have been resolved.
    `parameter_origins` explains where those values came from for audit and
    stale-result checks. `adapter_policy` stores projection or writer policy
    that should be recorded but should not by itself force recomputation.
    """

    result_parameters: Mapping[str, Any]
    parameter_origins: Mapping[str, str]
    adapter_policy: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceQuantity:
    """Scalar or small result value extracted by a method source adapter.

    `quantity_name` is the spec-facing quantity key. `value` is the extracted
    scientific value. `qualifiers` carries method dimensions such as term
    order, path index, statistic, component, or mode without growing
    method-specific top-level source fields.
    """

    quantity_name: str
    value: Any
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.quantity_name:
            raise ValueError("SourceQuantity requires a non-empty quantity_name.")


@dataclass(frozen=True)
class MethodResultSource:
    """Minimal immutable snapshot consumed by a provenance builder.

    `inputs` are primary data anchors. `dependencies` are non-primary records
    or links the method relied on. `parameters` is the normalized configuration
    snapshot. `quantities` are extracted result values named by the slice spec.
    The source intentionally contains no method definitions, writer behavior, or
    graph/KG projection rules.
    """

    inputs: tuple[SourceInput, ...]
    dependencies: tuple[SourceDependency, ...]
    parameters: SourceParameters
    quantities: tuple[SourceQuantity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "quantities", tuple(self.quantities))
        if not self.inputs:
            raise ValueError("MethodResultSource requires at least one input.")

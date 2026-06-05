"""Minimal source snapshots consumed by provenance builders."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SourceInput:
    input_id: str
    data_ref: str
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    source_label: str | None = None
    source_hash: str | None = None


@dataclass(frozen=True)
class SourceDependency:
    dependency_name: str
    record: Any | None = None
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


@dataclass(frozen=True)
class SourceParameters:
    result_parameters: Mapping[str, Any]
    parameter_origins: Mapping[str, str]
    adapter_policy: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceQuantity:
    quantity_name: str
    value: Any
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.quantity_name:
            raise ValueError("SourceQuantity requires a non-empty quantity_name.")


@dataclass(frozen=True)
class MethodResultSource:
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

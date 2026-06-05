"""Typed provenance slice specifications loaded from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SchemaVersions(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: str
    result: str
    configuration: str
    kg_statement_bundle: str


class MethodSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    method_id: str
    display_name: str
    kind: str
    method_revision: str
    implementation_ref: str
    aliases: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


class DependencySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    dependency_name: str
    role: str
    target_type: str


class QuantitySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    quantity_name: str
    symbol: str
    description: str
    unit: str
    legacy_aliases: tuple[str, ...] = ()


class CoefficientQuantitySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    quantity_name: str
    symbol_template: str
    description_template: str
    legacy_alias_template: str
    allowed_coefficient_series: tuple[str, ...] = Field(default=("a", "b", "c"))


class ProvenanceSliceSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    schemas: SchemaVersions
    methods: dict[str, MethodSpec]
    adapter_policy: dict[str, Any] = Field(default_factory=dict)
    dependencies: dict[str, DependencySpec]
    quantities: dict[str, QuantitySpec]
    coefficient_quantity: CoefficientQuantitySpec


def load_provenance_slice_spec(path: str | Path) -> ProvenanceSliceSpec:
    with Path(path).open(encoding="utf-8") as spec_file:
        payload = yaml.safe_load(spec_file)
    return ProvenanceSliceSpec.model_validate(payload)

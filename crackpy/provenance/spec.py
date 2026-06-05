"""Typed provenance slice specifications loaded from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SchemaVersions(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: str = Field(description="Schema version for the complete result/provenance envelope.")
    result: str = Field(description="Schema version for result records emitted by this slice.")
    configuration: str = Field(description="Schema version for normalized configuration records.")
    kg_statement_bundle: str = Field(description="Schema version for the compact KG statement bundle projection.")


class MethodSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    method_id: str = Field(description="Stable registry-owned identity for the scientific or workflow method.")
    display_name: str = Field(description="Human-facing method label for reports and visualization.")
    kind: str = Field(description="Method category, such as analysis or crack_tip_estimate.")
    method_revision: str = Field(description="Maintainer-declared revision of the method's semantics.")
    implementation_ref: str = Field(description="Current Python implementation reference used for traceability.")
    aliases: tuple[str, ...] = Field(default=(), description="Legacy or compatibility names for this method.")
    references: tuple[str, ...] = Field(default=(), description="Method-reference IDs linked to scientific sources.")


class DependencySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    dependency_name: str = Field(description="Spec-facing dependency name used by source adapters.")
    role: str = Field(description="Semantic edge role written into dependency edges.")
    target_type: str = Field(description="Expected target record type for dependency graph projection.")


class QuantitySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    quantity_name: str = Field(description="Spec-facing name matched against SourceQuantity.quantity_name.")
    symbol: str = Field(description="Canonical result symbol written to ResultQuantity records.")
    description: str = Field(description="Human-readable meaning of the scientific quantity.")
    unit: str = Field(description="Canonical unit label for the quantity value.")
    legacy_aliases: tuple[str, ...] = Field(default=(), description="Legacy output keys that map to this quantity.")


class ProvenanceSliceSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    schemas: SchemaVersions = Field(description="Schema-version strings used by this result/provenance slice.")
    methods: dict[str, MethodSpec] = Field(description="Named method definitions referenced by the slice builder.")
    adapter_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Projection or writer policy recorded separately from result-affecting parameters.",
    )
    dependencies: dict[str, DependencySpec] = Field(description="Allowed source dependencies keyed by dependency name.")
    quantities: dict[str, QuantitySpec] = Field(description="Allowed scalar source quantities keyed by quantity name.")


def load_provenance_slice_spec(path: str | Path) -> ProvenanceSliceSpec:
    with Path(path).open(encoding="utf-8") as spec_file:
        payload = yaml.safe_load(spec_file)
    return ProvenanceSliceSpec.model_validate(payload)

"""Shared builders for result/provenance envelopes."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from crackpy.results.provenance.source import MethodResultSource, SourceQuantity
from crackpy.results.provenance.spec import DependencySpec, ProvenanceSliceSpec
from crackpy.results.result_data import (
    DependencyEdge,
    InputRecord,
    MethodMetadata,
    NormalizedConfiguration,
    ResultQuantity,
    to_jsonable,
)

RecordT = TypeVar("RecordT")


@dataclass(frozen=True)
class MethodResultEnvelopeBuilder:
    """Project a method source snapshot and slice spec into shared result records."""

    source: MethodResultSource
    spec: ProvenanceSliceSpec

    def record_id(self, record: Any) -> str:
        for attr in (
            "frame_id",
            "estimate_id",
            "input_id",
            "configuration_id",
            "result_id",
            "artifact_id",
            "method_id",
        ):
            value = getattr(record, attr, None)
            if value is not None:
                return str(value)
        raise ValueError(f"Dependency record of type {type(record).__name__} has no supported ID field.")

    def dependency_record(self, dependency_name: str, record_type: type[RecordT]) -> RecordT:
        for dependency in self.source.dependencies:
            if dependency.dependency_name == dependency_name and isinstance(dependency.record, record_type):
                return dependency.record
        raise ValueError(f"Missing {dependency_name!r} dependency record.")

    def dependency_spec(self, dependency_name: str) -> DependencySpec:
        dependency_spec = self.spec.dependencies.get(dependency_name)
        if dependency_spec is None:
            raise ValueError(f"Provenance spec is missing {dependency_name!r} dependency.")
        return dependency_spec

    def input_records(self) -> list[InputRecord]:
        return [
            InputRecord(
                input_id=source_input.input_id,
                data_ref=source_input.data_ref,
                source_metadata=source_input.source_metadata,
                source_label=source_input.source_label,
                source_hash=source_input.source_hash,
            )
            for source_input in self.source.inputs
        ]

    def method_metadata(self, method_name: str) -> MethodMetadata:
        method_spec = self.spec.methods[method_name]
        return MethodMetadata(
            method_id=method_spec.method_id,
            display_name=method_spec.display_name,
            kind=method_spec.kind,
            method_revision=method_spec.method_revision,
            implementation_ref=method_spec.implementation_ref,
            aliases=list(method_spec.aliases),
            references=list(method_spec.references),
        )

    def normalized_configuration(
        self,
        configuration_id: str,
        *,
        adapter_policy: Mapping[str, Any] | None = None,
    ) -> NormalizedConfiguration:
        return NormalizedConfiguration.create(
            configuration_id=configuration_id,
            schema_version=self.spec.schemas.configuration,
            result_parameters=self.source.parameters.result_parameters,
            parameter_origins=self.source.parameters.parameter_origins,
            adapter_policy=adapter_policy or {},
        )

    def dependency_edges(self, run_id: str, configuration_id: str) -> list[DependencyEdge]:
        dependencies = [
            DependencyEdge(run_id, source_input.input_id, "used_input", "InputRecord")
            for source_input in self.source.inputs
        ]
        dependencies.append(DependencyEdge(run_id, configuration_id, "used_configuration", "NormalizedConfiguration"))
        for source_dependency in self.source.dependencies:
            dependency_spec = self.dependency_spec(source_dependency.dependency_name)
            target_id = (
                source_dependency.target_id
                if source_dependency.target_id is not None
                else self.record_id(source_dependency.record)
            )
            dependencies.append(
                DependencyEdge(run_id, target_id, dependency_spec.role, dependency_spec.target_type)
            )
        return dependencies

    def result_quantity(
        self,
        *,
        result_id: str,
        method_id: str,
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
            method_id=method_id,
            legacy_aliases=aliases,
        )

    def result_quantity_from_source(
        self,
        *,
        result_id: str,
        method_id: str,
        source_quantity: SourceQuantity,
        coefficient_unit: Callable[[Any], str] | None = None,
    ) -> ResultQuantity:
        coefficient_quantity = self.spec.coefficient_quantity
        if coefficient_quantity is not None and source_quantity.quantity_name == coefficient_quantity.quantity_name:
            coefficient_series = str(source_quantity.qualifiers["coefficient_series"])
            if coefficient_series not in coefficient_quantity.allowed_coefficient_series:
                raise ValueError(f"Unsupported coefficient series: {coefficient_series!r}")
            if coefficient_unit is None:
                raise ValueError("Coefficient quantities require a coefficient_unit callback.")
            term_order = source_quantity.qualifiers["term_order"]
            symbol = coefficient_quantity.symbol_template.format(
                coefficient_series=coefficient_series,
                term_order=term_order,
            )
            return self.result_quantity(
                result_id=result_id,
                method_id=method_id,
                symbol=symbol,
                description=coefficient_quantity.description_template.format(symbol=symbol),
                value=source_quantity.value,
                unit=coefficient_unit(term_order),
                aliases=[coefficient_quantity.legacy_alias_template.format(symbol=symbol)],
            )

        quantity_spec = self.spec.quantities.get(source_quantity.quantity_name)
        if quantity_spec is None:
            raise ValueError(f"Unsupported quantity: {source_quantity.quantity_name!r}")
        return self.result_quantity(
            result_id=result_id,
            method_id=method_id,
            symbol=quantity_spec.symbol,
            description=quantity_spec.description,
            value=source_quantity.value,
            unit=quantity_spec.unit,
            aliases=list(quantity_spec.legacy_aliases),
        )

"""Legacy result-section projection from canonical result envelopes.

This Module is a C-008 adapter over `ResultEnvelope`.
It keeps legacy section/key knowledge derived from quantity aliases instead of
requiring output callers to inspect `FractureAnalysis` attributes directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from crackpy.results.result_data import ResultEnvelope, ResultSchemaEntry, ResultSchemaIndex, to_jsonable


@dataclass(frozen=True, slots=True)
class LegacyResultValue:
    """One canonical quantity projected into a legacy result section.

    `unit` and `result` preserve the current JSON writer's compact value shape.
    `description`, `method_id`, `result_id`, `quantity_id`,
    `result_schema_version`, and `envelope_schema_version` keep enough schema
    context for frontend tables, CSV adapters, and compatibility tests to avoid
    treating a legacy key as the canonical identity.
    """

    unit: str
    result: Any
    description: str
    method_id: str
    result_id: str
    quantity_id: str
    result_schema_version: str
    envelope_schema_version: str

    def as_legacy_dict(self) -> dict[str, Any]:
        """Return the current JSON-writer value shape for this quantity."""
        return {"unit": self.unit, "result": to_jsonable(self.result)}

    def as_schema_dict(self) -> dict[str, Any]:
        """Return the value plus schema context for new adapters."""
        return {
            **self.as_legacy_dict(),
            "description": self.description,
            "method_id": self.method_id,
            "result_id": self.result_id,
            "quantity_id": self.quantity_id,
            "result_schema_version": self.result_schema_version,
            "envelope_schema_version": self.envelope_schema_version,
        }


@dataclass(frozen=True, slots=True)
class LegacyResultSection:
    """Legacy writer section projected from canonical result quantities.

    `section_name` is a current output tag such as `Williams_fit_results`.
    `quantities` maps legacy keys such as `K_I` or `error` to schema-aware
    values derived from a `ResultEnvelope`.
    """

    section_name: str
    quantities: Mapping[str, LegacyResultValue]

    def as_legacy_dict(self) -> dict[str, dict[str, Any]]:
        """Return the current JSON-writer section shape."""
        return {
            key: value.as_legacy_dict()
            for key, value in self.quantities.items()
        }

    def as_schema_dict(self) -> dict[str, dict[str, Any]]:
        """Return the section with schema context on every quantity."""
        return {
            key: value.as_schema_dict()
            for key, value in self.quantities.items()
        }


@dataclass(frozen=True, slots=True)
class LegacyResultSections:
    """Collection of legacy sections derived from one canonical envelope.

    `sections` is keyed by legacy section/tag name.
    `as_legacy_dict()` preserves the current nested JSON section shape.
    `as_schema_dict()` keeps schema metadata for new adapters that need stable
    result identity, descriptions, and versions.
    """

    sections: Mapping[str, LegacyResultSection]

    def as_legacy_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return current-style nested sections for compatibility callers."""
        return {
            section_name: section.as_legacy_dict()
            for section_name, section in self.sections.items()
        }

    def as_schema_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return nested sections with canonical schema context retained."""
        return {
            section_name: section.as_schema_dict()
            for section_name, section in self.sections.items()
        }


def legacy_result_sections_from_envelope(envelope: ResultEnvelope) -> LegacyResultSections:
    """Project dotted legacy aliases from a canonical result envelope.

    Only aliases shaped as `section.key` become section entries.
    Unscoped aliases such as historical text labels are still available through
    `ResultSchemaIndex`, but they are not enough to decide a legacy section.

    Raises:
        ValueError: If two different quantities claim the same legacy
            `section.key` entry.
    """
    schema_index = ResultSchemaIndex.from_envelope(envelope)
    quantity_values = _quantity_values_by_id(envelope)
    section_values: dict[str, dict[str, LegacyResultValue]] = {}
    owners: dict[tuple[str, str], ResultSchemaEntry] = {}

    for entry in schema_index.entries:
        result_value = quantity_values[entry.quantity_id]
        for alias in entry.legacy_aliases:
            parsed = _parse_dotted_alias(alias)
            if parsed is None:
                continue
            section_name, key = parsed
            owner_key = (section_name, key)
            if owner_key in owners and owners[owner_key].quantity_id != entry.quantity_id:
                raise ValueError(
                    f"Legacy result alias {alias!r} is claimed by both "
                    f"{owners[owner_key].quantity_id!r} and {entry.quantity_id!r}."
                )
            owners[owner_key] = entry
            section_values.setdefault(section_name, {})[key] = LegacyResultValue(
                unit=entry.unit,
                result=result_value,
                description=entry.description,
                method_id=entry.method_id,
                result_id=entry.result_id,
                quantity_id=entry.quantity_id,
                result_schema_version=entry.result_schema_version,
                envelope_schema_version=entry.envelope_schema_version,
            )

    return LegacyResultSections(
        sections={
            section_name: LegacyResultSection(section_name=section_name, quantities=quantities)
            for section_name, quantities in section_values.items()
        }
    )


def _quantity_values_by_id(envelope: ResultEnvelope) -> dict[str, Any]:
    return {
        quantity.quantity_id: quantity.value
        for result in envelope.results
        for quantity in result.quantities
    }


def _parse_dotted_alias(alias: str) -> tuple[str, str] | None:
    if "." not in alias:
        return None
    section_name, key = alias.split(".", 1)
    if not section_name or not key:
        return None
    return section_name, key

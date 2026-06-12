"""Compact KG statement-bundle projection for CrackPy result envelopes."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from crackpy.provenance.spec import ProvenanceSliceSpec
from crackpy.results.result_data import (
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


def _kg_bundle_schema_from_envelope(envelope: ResultEnvelope) -> str:
    """Derive the compact KG bundle schema that belongs to an envelope schema.

    Method-local slice specs remain the source of truth when a caller passes
    `spec`. The fallback keeps generic artifact projection useful for envelopes
    that already carry the slice-specific envelope schema, without importing a
    particular method module such as Williams fitting.
    """
    prefix = "crackpy.result_envelope."
    if not envelope.envelope_schema_version.startswith(prefix):
        raise ValueError(
            f"Cannot infer KG statement-bundle schema from envelope schema "
            f"{envelope.envelope_schema_version!r}."
        )
    suffix = envelope.envelope_schema_version.removeprefix(prefix)
    return f"crackpy.kg_statement_bundle.{suffix}"


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


def envelope_to_kg_statement_bundle(
    envelope: ResultEnvelope,
    *,
    spec: ProvenanceSliceSpec | None = None,
) -> KGStatementBundle:
    """Project a canonical envelope into compact grouped KG statements."""
    bundle_schema_version = (
        spec.schemas.kg_statement_bundle
        if spec is not None
        else _kg_bundle_schema_from_envelope(envelope)
    )
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
            description="Stable ID for one CrackPy analysis execution.",
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
            description="Stable ID of the CrackPy result record.",
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
            description="Schema version of the canonical result record.",
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
                description="Domain-facing symbol of a CrackPy result quantity.",
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
        bundle_schema_version=bundle_schema_version,
        uri_policy="local IDs only; URI minting belongs to exporter or KG importer policy",
        descriptor_field_policy="plain statements only; RDF descriptor resources are downstream rendering choices",
        statements=statements,
        groups=dict(groups),
    )

"""Build canonical Williams-fit result/provenance envelopes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import crackpy

from crackpy.fracture_analysis.crack_tip import unit_of_williams_coefficients
from crackpy.fracture_analysis.methods.williams_fit.parameters import WilliamsFitResultParameters
from crackpy.fracture_analysis.methods.williams_fit.provenance import source_from_result
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import load_williams_fit_spec
from crackpy.results.provenance import MethodResultSource, SourceQuantity
from crackpy.results.provenance.spec import ProvenanceSliceSpec
from crackpy.results.result_data import (
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


def _record_id(record: Any) -> str:
    for attr in ("frame_id", "estimate_id", "input_id", "configuration_id", "result_id", "artifact_id", "method_id"):
        value = getattr(record, attr, None)
        if value is not None:
            return str(value)
    raise ValueError(f"Dependency record of type {type(record).__name__} has no supported ID field.")


def _source_dependency_record(
    source: MethodResultSource,
    dependency_name: str,
    record_type: type,
) -> Any:
    for dependency in source.dependencies:
        if dependency.dependency_name == dependency_name and isinstance(dependency.record, record_type):
            return dependency.record
    raise ValueError(f"Missing {dependency_name!r} dependency record.")


def _quantity(
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


def _quantity_from_source(
    result_id: str,
    method_id: str,
    source_quantity: SourceQuantity,
    spec: ProvenanceSliceSpec,
) -> ResultQuantity:
    if source_quantity.quantity_name == spec.coefficient_quantity.quantity_name:
        coefficient_series = str(source_quantity.qualifiers["coefficient_series"])
        if coefficient_series not in spec.coefficient_quantity.allowed_coefficient_series:
            raise ValueError(f"Unsupported Williams coefficient series: {coefficient_series!r}")
        term_order = source_quantity.qualifiers["term_order"]
        symbol = spec.coefficient_quantity.symbol_template.format(
            coefficient_series=coefficient_series,
            term_order=term_order,
        )
        return _quantity(
            result_id,
            method_id,
            symbol,
            spec.coefficient_quantity.description_template.format(symbol=symbol),
            source_quantity.value,
            unit_of_williams_coefficients(term_order),
            [spec.coefficient_quantity.legacy_alias_template.format(symbol=symbol)],
        )

    quantity_spec = spec.quantities.get(source_quantity.quantity_name)
    if quantity_spec is None:
        raise ValueError(f"Unsupported Williams quantity: {source_quantity.quantity_name!r}")
    return _quantity(
        result_id,
        method_id,
        quantity_spec.symbol,
        quantity_spec.description,
        source_quantity.value,
        quantity_spec.unit,
        list(quantity_spec.legacy_aliases),
    )


def build_williams_fit_envelope_from_source(
    source: MethodResultSource,
    *,
    spec: ProvenanceSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    """Build the first-slice Williams-fit result/provenance envelope from a source snapshot."""
    spec = spec or load_williams_fit_spec()
    primary_input = source.inputs[0]
    frame = _source_dependency_record(source, "crack_tip_frame", CrackTipFrame)
    side = frame.compatibility_side or "unknown_side"
    stem = primary_input.source_label or Path(primary_input.data_ref).stem or "unknown_input"

    adapter_policy = {**spec.adapter_policy, **dict(source.parameters.adapter_policy)}
    provisional_configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:pending",
        schema_version=spec.schemas.configuration,
        result_parameters=source.parameters.result_parameters,
        parameter_origins=source.parameters.parameter_origins,
        adapter_policy=adapter_policy,
    )
    short_hash = provisional_configuration.parameter_hash.removeprefix("sha256:")[:12]
    configuration = NormalizedConfiguration.create(
        configuration_id=f"configuration:williams_fit:{short_hash}",
        schema_version=spec.schemas.configuration,
        result_parameters=source.parameters.result_parameters,
        parameter_origins=source.parameters.parameter_origins,
        adapter_policy=adapter_policy,
    )

    run_id = f"run:williams_fit:{stem}:{side}:{short_hash}"
    result_id = f"result:williams_fit:{stem}:{side}:{short_hash}"
    estimate_id = f"crack_tip_estimate:{stem}:{side}"

    input_records = [
        InputRecord(
            input_id=source_input.input_id,
            data_ref=source_input.data_ref,
            source_metadata=source_input.source_metadata,
            source_label=source_input.source_label,
            source_hash=source_input.source_hash,
        )
        for source_input in source.inputs
    ]
    estimate = CrackTipEstimateResult(
        estimate_id=estimate_id,
        input_id=primary_input.input_id,
        method_id=spec.methods["crack_tip_import"].method_id,
        configuration_id=configuration.configuration_id,
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm=frame.origin_mm,
        corrected_mm=frame.origin_mm,
        correction_delta_mm={"x": 0.0, "y": 0.0},
    )

    crack_tip_estimate_dependency = spec.dependencies["crack_tip_estimate"]
    dependencies = [
        DependencyEdge(run_id, source_input.input_id, "used_input", "InputRecord") for source_input in source.inputs
    ]
    dependencies.append(
        DependencyEdge(run_id, configuration.configuration_id, "used_configuration", "NormalizedConfiguration")
    )
    dependencies.append(
        DependencyEdge(
            run_id,
            estimate.estimate_id,
            crack_tip_estimate_dependency.role,
            crack_tip_estimate_dependency.target_type,
        )
    )
    for source_dependency in source.dependencies:
        dependency_spec = spec.dependencies[source_dependency.dependency_name]
        target_id = (
            source_dependency.target_id
            if source_dependency.target_id is not None
            else _record_id(source_dependency.record)
        )
        dependencies.append(
            DependencyEdge(run_id, target_id, dependency_spec.role, dependency_spec.target_type)
        )

    analysis_method = spec.methods["analysis"]
    crack_tip_import_method = spec.methods["crack_tip_import"]
    run = AnalysisRun(
        run_id=run_id,
        method_id=analysis_method.method_id,
        method_revision=analysis_method.method_revision,
        input_ids=[source_input.input_id for source_input in source.inputs],
        configuration_id=configuration.configuration_id,
        parameter_hash=configuration.parameter_hash,
        dependencies=dependencies,
        crackpy_version=crackpy_version or getattr(crackpy, "__version__", "unknown"),
        started_at=started_at,
        completed_at=completed_at,
    )
    result = ResultRecord(
        result_id=result_id,
        run_id=run_id,
        result_schema_version=spec.schemas.result,
        quantities=[
            _quantity_from_source(result_id, analysis_method.method_id, source_quantity, spec)
            for source_quantity in source.quantities
        ],
        artifacts=[],
    )

    return ResultEnvelope(
        input_records=input_records,
        methods=[
            MethodMetadata(
                method_id=analysis_method.method_id,
                display_name=analysis_method.display_name,
                kind=analysis_method.kind,
                method_revision=analysis_method.method_revision,
                implementation_ref=analysis_method.implementation_ref,
                aliases=list(analysis_method.aliases),
                references=list(analysis_method.references),
            ),
            MethodMetadata(
                method_id=crack_tip_import_method.method_id,
                display_name=crack_tip_import_method.display_name,
                kind=crack_tip_import_method.kind,
                method_revision=crack_tip_import_method.method_revision,
                implementation_ref=crack_tip_import_method.implementation_ref,
                aliases=list(crack_tip_import_method.aliases),
                references=list(crack_tip_import_method.references),
            ),
        ],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=[run],
        results=[result],
        envelope_schema_version=spec.schemas.envelope,
    )


def build_williams_fit_envelope_from_result(
    *,
    input_id: str,
    data_ref: str,
    source_label: str | None,
    crack_tip_frame: CrackTipFrame,
    parameters: WilliamsFitResultParameters,
    result: WilliamsFitResult,
    spec: ProvenanceSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    source = source_from_result(
        input_id=input_id,
        data_ref=data_ref,
        source_label=source_label,
        crack_tip_frame=crack_tip_frame,
        parameters=parameters,
        result=result,
    )
    return build_williams_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )

"""Build canonical Williams-fit result/provenance envelopes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import crackpy

from crackpy.fracture_analysis.crack_tip import unit_of_williams_coefficients
from crackpy.fracture_analysis.methods.williams_fit.parameters import WilliamsFitResultParameters
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit.source_adapter import source_from_analysis, source_from_result
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import WilliamsFitSliceSpec, load_williams_fit_spec
from crackpy.provenance import MethodResultEnvelopeBuilder, MethodResultSource
from crackpy.results.result_data import (
    AnalysisRun,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    ResultEnvelope,
    ResultRecord,
)


def build_williams_fit_envelope_from_source(
    source: MethodResultSource,
    *,
    spec: WilliamsFitSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    """Build the first-slice Williams-fit result/provenance envelope from a source snapshot."""
    spec = spec or load_williams_fit_spec()
    builder = MethodResultEnvelopeBuilder(source, spec)
    primary_input = source.inputs[0]
    frame = builder.dependency_record("crack_tip_frame", CrackTipFrame)
    side = frame.compatibility_side or frame.frame_id
    stem = primary_input.source_label or Path(primary_input.data_ref).stem
    if not stem:
        raise ValueError("Williams-fit envelope requires source_label or data_ref with a filename stem.")

    adapter_policy = {**spec.adapter_policy, **dict(source.parameters.adapter_policy)}
    provisional_configuration = builder.normalized_configuration(
        "configuration:williams_fit:pending",
        adapter_policy=adapter_policy,
    )
    short_hash = provisional_configuration.parameter_hash.removeprefix("sha256:")[:12]
    configuration = builder.normalized_configuration(
        f"configuration:williams_fit:{short_hash}",
        adapter_policy=adapter_policy,
    )

    run_id = f"run:williams_fit:{stem}:{side}:{short_hash}"
    result_id = f"result:williams_fit:{stem}:{side}:{short_hash}"
    estimate_id = f"crack_tip_estimate:{stem}:{side}"

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
    dependencies = builder.dependency_edges(run_id, configuration.configuration_id)
    dependencies.append(
        DependencyEdge(
            run_id,
            estimate.estimate_id,
            crack_tip_estimate_dependency.role,
            crack_tip_estimate_dependency.target_type,
        )
    )

    analysis_method = spec.methods["analysis"]
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

    quantities = []
    coefficient_quantity = spec.coefficient_quantity
    for source_quantity in source.quantities:
        if source_quantity.quantity_name != coefficient_quantity.quantity_name:
            quantities.append(
                builder.result_quantity_from_source(
                    result_id=result_id,
                    method_id=analysis_method.method_id,
                    source_quantity=source_quantity,
                )
            )
            continue

        coefficient_series = str(source_quantity.qualifiers["coefficient_series"])
        if coefficient_series not in coefficient_quantity.allowed_coefficient_series:
            raise ValueError(f"Unsupported Williams coefficient series: {coefficient_series!r}")
        term_order = source_quantity.qualifiers["term_order"]
        symbol = coefficient_quantity.symbol_template.format(
            coefficient_series=coefficient_series,
            term_order=term_order,
        )
        quantities.append(
            builder.result_quantity(
                result_id=result_id,
                method_id=analysis_method.method_id,
                symbol=symbol,
                description=coefficient_quantity.description_template.format(symbol=symbol),
                value=source_quantity.value,
                unit=unit_of_williams_coefficients(term_order),
                aliases=[coefficient_quantity.legacy_alias_template.format(symbol=symbol)],
            )
        )

    result = ResultRecord(
        result_id=result_id,
        run_id=run_id,
        result_schema_version=spec.schemas.result,
        quantities=quantities,
        artifacts=[],
    )

    return ResultEnvelope(
        input_records=builder.input_records(),
        methods=[builder.method_metadata("analysis"), builder.method_metadata("crack_tip_import")],
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
    spec: WilliamsFitSliceSpec | None = None,
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
        spec=spec,
    )
    return build_williams_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )


def build_williams_fit_envelope_from_analysis(
    analysis: Any,
    *,
    spec: WilliamsFitSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    source = source_from_analysis(analysis)
    return build_williams_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )

"""Build canonical CJP-fit result/provenance envelopes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import crackpy

from crackpy.fracture_analysis.methods.cjp_fit.parameters import CjpFitResultParameters
from crackpy.fracture_analysis.methods.cjp_fit.result import CjpFitResult
from crackpy.fracture_analysis.methods.cjp_fit.source_adapter import source_from_analysis, source_from_result
from crackpy.fracture_analysis.methods.cjp_fit.spec_loader import CjpFitSliceSpec, load_cjp_fit_spec
from crackpy.provenance import MethodResultEnvelopeBuilder, MethodResultSource
from crackpy.results.result_data import (
    AnalysisRun,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    ResultEnvelope,
    ResultRecord,
)

VARIANT_METHOD_NAMES = {
    "mixed_mode": "mixed_mode",
    "mode_i": "mode_i",
}


def build_cjp_fit_envelope_from_source(
    source: MethodResultSource,
    *,
    spec: CjpFitSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    """Build a CJP result/provenance envelope from a method source snapshot."""
    spec = spec or load_cjp_fit_spec()
    builder = MethodResultEnvelopeBuilder(source, spec)
    builder.validate_source_quantities()
    for source_quantity in source.quantities:
        variant = source_quantity.qualifiers.get("variant")
        if variant not in VARIANT_METHOD_NAMES:
            raise ValueError(
                f"CJP source quantity {source_quantity.quantity_name!r} requires variant qualifier "
                f"{tuple(VARIANT_METHOD_NAMES)}."
            )
    primary_input = source.inputs[0]
    frame = builder.dependency_record("crack_tip_frame", CrackTipFrame)
    side = frame.compatibility_side or frame.frame_id
    stem = primary_input.source_label or Path(primary_input.data_ref).stem
    if not stem:
        raise ValueError("CJP-fit envelope requires source_label or data_ref with a filename stem.")

    adapter_policy = {**spec.adapter_policy, **dict(source.parameters.adapter_policy)}
    provisional_configuration = builder.normalized_configuration(
        "configuration:cjp_fit:pending",
        adapter_policy=adapter_policy,
    )
    short_hash = provisional_configuration.parameter_hash.removeprefix("sha256:")[:12]
    configuration = builder.normalized_configuration(
        f"configuration:cjp_fit:{short_hash}",
        adapter_policy=adapter_policy,
    )

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

    runs = []
    results = []
    for variant, method_name in VARIANT_METHOD_NAMES.items():
        analysis_method = spec.methods[method_name]
        run_id = f"run:cjp_fit:{variant}:{stem}:{side}:{short_hash}"
        result_id = f"result:cjp_fit:{variant}:{stem}:{side}:{short_hash}"
        dependencies = builder.dependency_edges(run_id, configuration.configuration_id)
        dependencies.append(
            DependencyEdge(
                run_id,
                estimate.estimate_id,
                crack_tip_estimate_dependency.role,
                crack_tip_estimate_dependency.target_type,
            )
        )
        runs.append(
            AnalysisRun(
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
        )
        quantities = [
            builder.result_quantity_from_source(
                result_id=result_id,
                method_id=analysis_method.method_id,
                source_quantity=source_quantity,
            )
            for source_quantity in source.quantities
            if source_quantity.qualifiers.get("variant") == variant
        ]
        results.append(
            ResultRecord(
                result_id=result_id,
                run_id=run_id,
                result_schema_version=spec.schemas.result,
                quantities=quantities,
                artifacts=[],
            )
        )

    return ResultEnvelope(
        input_records=builder.input_records(),
        methods=[
            builder.method_metadata("mixed_mode"),
            builder.method_metadata("mode_i"),
            builder.method_metadata("crack_tip_import"),
        ],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=runs,
        results=results,
        envelope_schema_version=spec.schemas.envelope,
    )


def build_cjp_fit_envelope_from_result(
    *,
    input_id: str,
    data_ref: str,
    source_label: str | None,
    crack_tip_frame: CrackTipFrame,
    parameters: CjpFitResultParameters,
    result: CjpFitResult,
    spec: CjpFitSliceSpec | None = None,
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
    return build_cjp_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )


def build_cjp_fit_envelope_from_analysis(
    analysis: Any,
    *,
    spec: CjpFitSliceSpec | None = None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    source = source_from_analysis(analysis)
    return build_cjp_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )

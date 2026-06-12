"""CJP-fit source adapter for provenance construction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from crackpy.fracture_analysis.methods.cjp_fit.parameters import (
    CjpFitResultParameters,
    CjpMaterialParameters,
    CjpOptimizationParameters,
)
from crackpy.fracture_analysis.methods.cjp_fit.result import (
    CjpFitResult,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
)
from crackpy.fracture_analysis.methods.cjp_fit.spec_loader import CjpFitSliceSpec, load_cjp_fit_spec
from crackpy.provenance import MethodResultSource, SourceDependency, SourceInput, SourceParameters, SourceQuantity
from crackpy.results.result_data import CrackTipFrame


def source_from_analysis(analysis: Any) -> MethodResultSource:
    """Translate current FractureAnalysis CJP outputs into a source snapshot."""
    if analysis.cjp_res_mm is None or analysis.cjp_res_m1 is None:
        raise ValueError("CJP results are missing; run CJP optimization before building provenance.")
    if analysis.cjp_coeffs_mm is None or analysis.cjp_coeffs_m1 is None:
        raise ValueError("CJP coefficients are missing; run CJP optimization before building provenance.")

    stem = Path(str(analysis.nodemap_file)).stem
    frame = CrackTipFrame.from_legacy_side(
        stem=stem,
        side=analysis.crack_tip.left_or_right,
        origin_mm={
            "x": analysis.crack_tip.crack_tip_x,
            "y": analysis.crack_tip.crack_tip_y,
        },
        angle_deg=analysis.crack_tip.crack_tip_angle,
    )
    material = analysis.material
    options = analysis.optimization_properties
    result = CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            analysis.cjp_coeffs_mm,
            error=analysis.cjp_res_mm["Error"],
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            analysis.cjp_coeffs_m1,
            error=analysis.cjp_res_m1["Error"],
        ),
    )

    return source_from_result(
        input_id=f"input:{stem}",
        data_ref=str(analysis.nodemap_file),
        source_label=stem,
        crack_tip_frame=frame,
        parameters=CjpFitResultParameters(
            material=CjpMaterialParameters(
                name=material.name,
                E_MPa=material.E,
                nu_xy=material.nu_xy,
                sig_yield_MPa=material.sig_yield,
                plane_strain=material.plane_strain,
                G_MPa=material.G,
                kappa=material.kappa,
            ),
            optimization=CjpOptimizationParameters(
                angle_gap_deg=options.angle_gap,
                min_radius_mm=options.min_radius,
                max_radius_mm=options.max_radius,
                tick_size_mm=options.tick_size,
            ),
        ),
        result=result,
    )


def source_from_result(
    *,
    input_id: str,
    data_ref: str,
    source_label: str | None,
    crack_tip_frame: CrackTipFrame,
    parameters: CjpFitResultParameters,
    result: CjpFitResult,
    spec: CjpFitSliceSpec | None = None,
) -> MethodResultSource:
    spec = spec or load_cjp_fit_spec()
    crack_tip_frame_dependency = "crack_tip_frame"
    if crack_tip_frame_dependency not in spec.dependencies:
        raise ValueError(f"CJP-fit provenance spec is missing {crack_tip_frame_dependency!r} dependency.")

    quantities = []
    for quantity_spec in spec.quantities.values():
        variant_result = getattr(result, quantity_spec.variant)
        value = _quantity_value(variant_result, quantity_spec.symbol)
        quantities.append(
            SourceQuantity(
                quantity_spec.quantity_name,
                value,
                {"variant": quantity_spec.variant},
            )
        )

    return MethodResultSource(
        inputs=(SourceInput(input_id=input_id, data_ref=data_ref, source_label=source_label),),
        dependencies=(SourceDependency(crack_tip_frame_dependency, record=crack_tip_frame),),
        parameters=SourceParameters(
            result_parameters=parameters.result_parameters(),
            parameter_origins=parameters.parameter_origins(),
        ),
        quantities=tuple(quantities),
    )


def _quantity_value(variant_result: Any, symbol: str) -> Any:
    if symbol in type(variant_result).model_fields:
        return getattr(variant_result, symbol)
    if symbol in type(variant_result.coefficients).model_fields:
        return getattr(variant_result.coefficients, symbol)
    raise ValueError(f"CJP result has no quantity symbol {symbol!r}.")

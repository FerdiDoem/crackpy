"""Williams-fit source adapter for provenance construction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from crackpy.fracture_analysis.methods.williams_fit.parameters import (
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
)
from crackpy.fracture_analysis.methods.parameter_snapshots import (
    material_parameters_from_analysis_material,
    optimization_parameters_from_analysis_options,
)
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsCoefficientSet, WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import WilliamsFitSliceSpec, load_williams_fit_spec
from crackpy.provenance import (
    MethodResultSource,
    SourceDependency,
    SourceInput,
    SourceParameters,
    SourceQuantity,
)
from crackpy.results.result_data import CrackTipFrame


def source_from_analysis(analysis: Any) -> MethodResultSource:
    """Translate the current FractureAnalysis Williams output into a source snapshot."""
    if analysis.williams_fit_res is None:
        raise ValueError("Williams fit results are missing; run Williams optimization before building provenance.")

    stem = Path(str(analysis.nodemap_file)).stem
    frame = CrackTipFrame.from_legacy_side(
        stem=stem,
        side=analysis.crack_tip.left_or_right,
        origin_mm={
            "x": analysis.crack_tip.crack_tip_x,
            "y": analysis.crack_tip.crack_tip_y,
        },
        angle_deg=analysis.crack_tip.crack_tip_angle,
        tip_id=getattr(analysis.crack_tip, "crack_tip_id", None),
    )
    fit_res = analysis.williams_fit_res
    result = WilliamsFitResult(
        error_xy=fit_res["Error_xy"],
        error_z=fit_res["Error_z"],
        K_I=fit_res["K_I"],
        K_II=fit_res["K_II"],
        K_III=fit_res["K_III"],
        T=fit_res["T"],
        coefficients=WilliamsCoefficientSet(
            a=analysis.williams_fit_a_n,
            b=analysis.williams_fit_b_n,
            c=analysis.williams_fit_c_n,
        ),
    )
    material = analysis.material
    options = analysis.optimization_properties
    return source_from_result(
        input_id=f"input:{stem}",
        data_ref=str(analysis.nodemap_file),
        source_label=stem,
        crack_tip_frame=frame,
        parameters=WilliamsFitResultParameters(
            material=material_parameters_from_analysis_material(material, WilliamsMaterialParameters),
            optimization=optimization_parameters_from_analysis_options(
                options,
                WilliamsOptimizationParameters,
                extra_values={"terms": tuple(options.terms)},
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
    parameters: WilliamsFitResultParameters,
    result: WilliamsFitResult,
    spec: WilliamsFitSliceSpec | None = None,
) -> MethodResultSource:
    spec = spec or load_williams_fit_spec()
    crack_tip_frame_dependency = "crack_tip_frame"
    if crack_tip_frame_dependency not in spec.dependencies:
        raise ValueError(f"Williams-fit provenance spec is missing {crack_tip_frame_dependency!r} dependency.")

    result_values = result.model_dump()
    quantities = []
    for quantity_spec in spec.quantities.values():
        if quantity_spec.quantity_name not in result_values:
            raise ValueError(f"Williams fit result has no field {quantity_spec.quantity_name!r}.")
        quantities.append(SourceQuantity(quantity_spec.quantity_name, result_values[quantity_spec.quantity_name]))

    coefficient_quantity = spec.coefficient_quantity
    for coefficient_series in coefficient_quantity.allowed_coefficient_series:
        coefficients = getattr(result.coefficients, coefficient_series, None)
        if coefficients is None:
            raise ValueError(f"Williams fit result has no coefficient series {coefficient_series!r}.")
        for term_order, value in coefficients.items():
            quantities.append(
                SourceQuantity(
                    coefficient_quantity.quantity_name,
                    value,
                    {"coefficient_series": coefficient_series, "term_order": term_order},
                )
            )

    return MethodResultSource(
        inputs=(
            SourceInput(
                input_id=input_id,
                data_ref=data_ref,
                source_label=source_label,
            ),
        ),
        dependencies=(SourceDependency(crack_tip_frame_dependency, record=crack_tip_frame),),
        parameters=SourceParameters(
            result_parameters=parameters.result_parameters(),
            parameter_origins=parameters.parameter_origins(),
        ),
        quantities=tuple(quantities),
    )

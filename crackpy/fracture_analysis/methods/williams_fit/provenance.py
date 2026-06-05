"""Williams-fit provenance source construction."""
from __future__ import annotations

from crackpy.fracture_analysis.methods.williams_fit.parameters import WilliamsFitResultParameters
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsFitResult
from crackpy.results.provenance import (
    MethodResultSource,
    SourceDependency,
    SourceInput,
    SourceParameters,
    SourceQuantity,
)
from crackpy.results.result_data import CrackTipFrame


def _source_quantities(result: WilliamsFitResult) -> tuple[SourceQuantity, ...]:
    quantities = [
        SourceQuantity("error_xy", result.error_xy),
        SourceQuantity("error_z", result.error_z),
        SourceQuantity("K_I", result.K_I),
        SourceQuantity("K_II", result.K_II),
        SourceQuantity("K_III", result.K_III),
        SourceQuantity("T", result.T),
    ]

    for coefficient_series, coefficients in (
        ("a", result.coefficients.a),
        ("b", result.coefficients.b),
        ("c", result.coefficients.c),
    ):
        for term_order, value in coefficients.items():
            quantities.append(
                SourceQuantity(
                    "williams_coefficient",
                    value,
                    {"coefficient_series": coefficient_series, "term_order": term_order},
                )
            )
    return tuple(quantities)


def source_from_result(
    *,
    input_id: str,
    data_ref: str,
    source_label: str | None,
    crack_tip_frame: CrackTipFrame,
    parameters: WilliamsFitResultParameters,
    result: WilliamsFitResult,
) -> MethodResultSource:
    return MethodResultSource(
        inputs=(
            SourceInput(
                input_id=input_id,
                data_ref=data_ref,
                source_label=source_label,
            ),
        ),
        dependencies=(SourceDependency("crack_tip_frame", record=crack_tip_frame),),
        parameters=SourceParameters(
            result_parameters=parameters.result_parameters(),
            parameter_origins=parameters.parameter_origins(),
        ),
        quantities=_source_quantities(result),
    )

"""Williams-fit provenance source construction."""
from __future__ import annotations

from crackpy.fracture_analysis.methods.williams_fit.parameters import WilliamsFitResultParameters
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import load_williams_fit_spec
from crackpy.results.provenance import (
    MethodResultSource,
    SourceDependency,
    SourceInput,
    SourceParameters,
    SourceQuantity,
)
from crackpy.results.provenance.spec import ProvenanceSliceSpec
from crackpy.results.result_data import CrackTipFrame


def source_from_result(
    *,
    input_id: str,
    data_ref: str,
    source_label: str | None,
    crack_tip_frame: CrackTipFrame,
    parameters: WilliamsFitResultParameters,
    result: WilliamsFitResult,
    spec: ProvenanceSliceSpec | None = None,
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
    if coefficient_quantity is None:
        raise ValueError("Williams-fit provenance spec is missing 'coefficient_quantity'.")
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

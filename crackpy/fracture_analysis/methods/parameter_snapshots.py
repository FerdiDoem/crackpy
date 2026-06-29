"""Shared provenance parameter snapshots for fracture-analysis methods."""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

MaterialParametersT = TypeVar("MaterialParametersT", bound=BaseModel)
OptimizationParametersT = TypeVar("OptimizationParametersT", bound=BaseModel)


def material_parameters_from_analysis_material(
    material: Any,
    parameter_type: type[MaterialParametersT],
) -> MaterialParametersT:
    """Build a method-local material snapshot from a legacy analysis material.

    `material` is the current `FractureAnalysis.material`-style object whose
    attributes use CrackPy's historical names and units. `parameter_type` is
    the method-local Pydantic parameter model that declares the provenance
    field descriptions and any method-specific validation.
    """
    return parameter_type(
        name=material.name,
        E_MPa=material.E,
        nu_xy=material.nu_xy,
        sig_yield_MPa=material.sig_yield,
        plane_strain=material.plane_strain,
        G_MPa=material.G,
        kappa=material.kappa,
    )


def optimization_parameters_from_analysis_options(
    options: Any,
    parameter_type: type[OptimizationParametersT],
    *,
    extra_values: dict[str, Any] | None = None,
) -> OptimizationParametersT:
    """Build a method-local optimization snapshot from legacy options.

    `options` is the current optimization-properties object shared by
    Williams-fit and CJP-fit adapters. `extra_values` carries method-specific
    parameters, such as Williams expansion terms, without forcing every
    fracture-analysis method to expose the same fields.
    """
    values: dict[str, Any] = {
        "angle_gap_deg": options.angle_gap,
        "min_radius_mm": options.min_radius,
        "max_radius_mm": options.max_radius,
        "tick_size_mm": options.tick_size,
    }
    if extra_values is not None:
        values.update(extra_values)
    return parameter_type(**values)

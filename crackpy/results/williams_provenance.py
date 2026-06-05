"""Compatibility facade for Williams-fit provenance construction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from crackpy.fracture_analysis.methods.williams_fit import (
    WilliamsCoefficientSet,
    WilliamsFitResult,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
    build_williams_fit_envelope_from_source,
    load_williams_fit_spec,
    source_from_result,
)
from crackpy.results.result_data import CrackTipFrame


def williams_fit_source_from_analysis(analysis: Any):
    if getattr(analysis, "williams_fit_res", None) is None:
        raise ValueError("Williams fit results are missing; run Williams optimization before building provenance.")

    stem = Path(str(getattr(analysis, "nodemap_file", "unknown_input"))).stem or "unknown_input"
    side = getattr(analysis.crack_tip, "left_or_right", None) or "unknown_side"
    frame = CrackTipFrame(
        frame_id=f"crack_tip_frame:{stem}:{side}",
        tip_id=f"crack_tip:{stem}:{side}",
        origin_mm={
            "x": getattr(analysis.crack_tip, "crack_tip_x", None),
            "y": getattr(analysis.crack_tip, "crack_tip_y", None),
        },
        angle_deg=getattr(analysis.crack_tip, "crack_tip_angle", None),
        compatibility_side=getattr(analysis.crack_tip, "left_or_right", None),
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
            a=getattr(analysis, "williams_fit_a_n", {}) or {},
            b=getattr(analysis, "williams_fit_b_n", {}) or {},
            c=getattr(analysis, "williams_fit_c_n", {}) or {},
        ),
    )
    material = analysis.material
    options = analysis.optimization_properties
    return source_from_result(
        input_id=f"input:{stem}",
        data_ref=str(getattr(analysis, "nodemap_file", "")),
        source_label=stem,
        crack_tip_frame=frame,
        parameters=WilliamsFitResultParameters(
            material=WilliamsMaterialParameters(
                name=getattr(material, "name", None),
                E_MPa=getattr(material, "E", None),
                nu_xy=getattr(material, "nu_xy", None),
                sig_yield_MPa=getattr(material, "sig_yield", None),
                plane_strain=getattr(material, "plane_strain", None),
                G_MPa=getattr(material, "G", None),
                kappa=getattr(material, "kappa", None),
            ),
            optimization=WilliamsOptimizationParameters(
                angle_gap_deg=getattr(options, "angle_gap", None),
                min_radius_mm=getattr(options, "min_radius", None),
                max_radius_mm=getattr(options, "max_radius", None),
                tick_size_mm=getattr(options, "tick_size", None),
                terms=tuple(getattr(options, "terms", []) or ()),
            ),
        ),
        result=result,
    )


def build_williams_fit_envelope(
    analysis: Any,
    *,
    spec=None,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
):
    source = williams_fit_source_from_analysis(analysis)
    return build_williams_fit_envelope_from_source(
        source,
        spec=spec,
        crackpy_version=crackpy_version,
        started_at=started_at,
        completed_at=completed_at,
    )

__all__ = [
    "build_williams_fit_envelope",
    "build_williams_fit_envelope_from_source",
    "load_williams_fit_spec",
    "williams_fit_source_from_analysis",
]

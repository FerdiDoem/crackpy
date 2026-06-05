"""Williams-fit method module."""
from crackpy.fracture_analysis.methods.williams_fit.parameters import (
    RESOLVED_OPTIMIZATION_ORIGIN,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
)
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsCoefficientSet, WilliamsFitResult
from crackpy.fracture_analysis.methods.williams_fit.runner import run_williams_fit

__all__ = [
    "RESOLVED_OPTIMIZATION_ORIGIN",
    "WilliamsCoefficientSet",
    "WilliamsFitResult",
    "WilliamsFitResultParameters",
    "WilliamsMaterialParameters",
    "WilliamsOptimizationParameters",
    "build_williams_fit_envelope_from_result",
    "build_williams_fit_envelope_from_source",
    "load_williams_fit_spec",
    "run_williams_fit",
    "source_from_result",
]


def build_williams_fit_envelope_from_result(*args, **kwargs):
    from crackpy.fracture_analysis.methods.williams_fit.builder import (
        build_williams_fit_envelope_from_result as build_envelope,
    )

    return build_envelope(*args, **kwargs)


def build_williams_fit_envelope_from_source(*args, **kwargs):
    from crackpy.fracture_analysis.methods.williams_fit.builder import (
        build_williams_fit_envelope_from_source as build_envelope,
    )

    return build_envelope(*args, **kwargs)


def load_williams_fit_spec(*args, **kwargs):
    from crackpy.fracture_analysis.methods.williams_fit.spec_loader import load_williams_fit_spec as load_spec

    return load_spec(*args, **kwargs)


def source_from_result(*args, **kwargs):
    from crackpy.fracture_analysis.methods.williams_fit.provenance import source_from_result as create_source

    return create_source(*args, **kwargs)

"""CJP-fit method module."""
from crackpy.fracture_analysis.methods.cjp_fit.parameters import (
    RESOLVED_OPTIMIZATION_ORIGIN,
    CjpFitResultParameters,
    CjpMaterialParameters,
    CjpOptimizationParameters,
)
from crackpy.fracture_analysis.methods.cjp_fit.result import (
    CjpFitResult,
    CjpModeICoefficientSet,
    CjpModeIResult,
    CjpMixedModeCoefficientSet,
    CjpMixedModeResult,
    CjpNativeModeICoefficientSet,
    CjpNativeMixedModeCoefficientSet,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
)
from crackpy.fracture_analysis.methods.cjp_fit.runner import (
    CjpFitDisplacementField,
    CjpOptimizer,
    fit_cjp_displacement_field,
    run_cjp_fit,
    run_cjp_fit_from_coefficients,
)
from crackpy.fracture_analysis.methods.cjp_fit.source_adapter import source_from_analysis, source_from_result

__all__ = [
    "CjpFitResult",
    "CjpFitResultParameters",
    "CjpMaterialParameters",
    "CjpModeICoefficientSet",
    "CjpModeIResult",
    "CjpMixedModeCoefficientSet",
    "CjpMixedModeResult",
    "CjpNativeModeICoefficientSet",
    "CjpNativeMixedModeCoefficientSet",
    "CjpOptimizationParameters",
    "CjpOptimizer",
    "CjpFitDisplacementField",
    "RESOLVED_OPTIMIZATION_ORIGIN",
    "build_cjp_fit_envelope_from_analysis",
    "build_cjp_fit_envelope_from_result",
    "build_cjp_fit_envelope_from_source",
    "cjp_mode_i_outputs_from_coefficients",
    "cjp_mixed_mode_outputs_from_coefficients",
    "fit_cjp_displacement_field",
    "load_cjp_fit_spec",
    "run_cjp_fit",
    "run_cjp_fit_from_coefficients",
    "source_from_analysis",
    "source_from_result",
]


def build_cjp_fit_envelope_from_analysis(*args, **kwargs):
    from crackpy.fracture_analysis.methods.cjp_fit.builder import (
        build_cjp_fit_envelope_from_analysis as build_envelope,
    )

    return build_envelope(*args, **kwargs)


def build_cjp_fit_envelope_from_result(*args, **kwargs):
    from crackpy.fracture_analysis.methods.cjp_fit.builder import (
        build_cjp_fit_envelope_from_result as build_envelope,
    )

    return build_envelope(*args, **kwargs)


def build_cjp_fit_envelope_from_source(*args, **kwargs):
    from crackpy.fracture_analysis.methods.cjp_fit.builder import (
        build_cjp_fit_envelope_from_source as build_envelope,
    )

    return build_envelope(*args, **kwargs)


def load_cjp_fit_spec(*args, **kwargs):
    from crackpy.fracture_analysis.methods.cjp_fit.spec_loader import load_cjp_fit_spec as load_spec

    return load_spec(*args, **kwargs)

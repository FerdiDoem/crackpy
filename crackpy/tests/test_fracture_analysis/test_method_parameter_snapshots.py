from types import SimpleNamespace

from crackpy.fracture_analysis.methods.cjp_fit.parameters import (
    CjpMaterialParameters,
    CjpOptimizationParameters,
)
from crackpy.fracture_analysis.methods import (
    material_parameters_from_analysis_material,
    optimization_parameters_from_analysis_options,
)
from crackpy.fracture_analysis.methods.williams_fit.parameters import (
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
)


def _material():
    return SimpleNamespace(
        name="AA2024-T3",
        E=72000,
        nu_xy=0.33,
        sig_yield=350,
        plane_strain=False,
        G=27067.66917293233,
        kappa=2.007518796992481,
    )


def _options():
    return SimpleNamespace(
        angle_gap=20,
        min_radius=0.2,
        max_radius=1.0,
        tick_size=0.01,
        terms=[-1, 1, 2],
    )


def test_material_snapshot_can_build_williams_and_cjp_parameter_models():
    williams = material_parameters_from_analysis_material(_material(), WilliamsMaterialParameters)
    cjp = material_parameters_from_analysis_material(_material(), CjpMaterialParameters)

    assert williams.model_dump(mode="json") == cjp.model_dump(mode="json")
    assert williams.E_MPa == 72000
    assert williams.sig_yield_MPa == 350


def test_optimization_snapshot_keeps_method_specific_extra_values():
    williams = optimization_parameters_from_analysis_options(
        _options(),
        WilliamsOptimizationParameters,
        extra_values={"terms": tuple(_options().terms)},
    )
    cjp = optimization_parameters_from_analysis_options(_options(), CjpOptimizationParameters)

    assert williams.angle_gap_deg == cjp.angle_gap_deg == 20
    assert williams.min_radius_mm == cjp.min_radius_mm == 0.2
    assert williams.terms == (-1, 1, 2)
    assert not hasattr(cjp, "terms")

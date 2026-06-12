from unittest.mock import patch

from crackpy.fracture_analysis.analysis import (
    FractureAnalysis,
    default_integral_properties,
    default_optimization_properties,
)
from crackpy.fracture_analysis.optimization import Optimization, OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.structure_elements.material import Material


def _analysis_with_default_integrals() -> FractureAnalysis:
    return FractureAnalysis(
        material=Material(),
        nodemap="DemoNodemap.txt",
        data=InputData(),
        crack_tip_info=CrackTipInfo(50.0, 0.0, 0.0, "right"),
        optimization_properties=None,
    )


def test_fracture_analysis_default_integral_properties_are_independent_per_analysis():
    first = _analysis_with_default_integrals()
    second = _analysis_with_default_integrals()

    assert first.integral_properties is not second.integral_properties

    first.integral_properties.buckner_williams_terms.append(99)

    assert 99 not in second.integral_properties.buckner_williams_terms


def test_fracture_analysis_none_still_disables_integrals_and_optimization():
    analysis = FractureAnalysis(
        material=Material(),
        nodemap="DemoNodemap.txt",
        data=InputData(),
        crack_tip_info=CrackTipInfo(50.0, 0.0, 0.0, "right"),
        integral_properties=None,
        optimization_properties=None,
    )

    assert analysis.integral_properties is None
    assert analysis.optimization_properties is None


def test_default_optimization_properties_are_independent_before_resolution():
    first = default_optimization_properties()
    second = default_optimization_properties()

    assert first is not second

    Optimization.ensure_defaults_williams(first, crack_tip_x=50.0)

    assert first.terms == [-1, 1, 2, 3, 4, 5]
    assert second.terms is None


def test_default_integral_properties_are_independent_before_resolution():
    first = default_integral_properties()
    second = default_integral_properties()

    assert first is not second

    first.buckner_williams_terms = [1, 2]

    assert second.buckner_williams_terms is None


def test_optimization_default_material_is_independent_per_optimizer():
    options = OptimizationProperties(
        angle_gap=20,
        min_radius=1,
        max_radius=2,
        tick_size=0.5,
        terms=[1, 2],
    )

    with patch.object(Optimization, "_interpolate_data_on_grid", return_value=None):
        first = Optimization(data=InputData(), options=options)
        second = Optimization(data=InputData(), options=options)

    assert first.material is not second.material

    first.material.name = "changed material"

    assert second.material.name == "not defined material"

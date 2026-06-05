from types import SimpleNamespace

import numpy as np

from crackpy.results.result_data import CrackTipFrame


def test_williams_method_module_builds_source_from_typed_result():
    from crackpy.fracture_analysis.methods.williams_fit import (
        WilliamsCoefficientSet,
        WilliamsFitResult,
        WilliamsFitResultParameters,
        WilliamsMaterialParameters,
        WilliamsOptimizationParameters,
        load_williams_fit_spec,
        source_from_result,
    )

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    parameters = WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=WilliamsOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, terms=(-1, 1, 2)),
    )
    result = WilliamsFitResult(
        error_xy=0.1,
        error_z=np.nan,
        K_I=12.5,
        K_II=-2.0,
        K_III=np.nan,
        T=4.0,
        coefficients=WilliamsCoefficientSet(
            a={-1: 0.01, 1: 2.0, 2: 1.0},
            b={-1: 0.02, 1: -0.5, 2: 0.3},
            c={-1: np.nan, 1: np.nan, 2: np.nan},
        ),
    )

    source = source_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
    )
    spec = load_williams_fit_spec()

    assert source.inputs[0].input_id == "input:demo"
    assert source.parameters.result_parameters["material"]["E_MPa"] == 72000
    assert source.parameters.result_parameters["optimization"]["terms"] == [-1, 1, 2]
    assert source.parameters.parameter_origins["angle_gap_deg"] == "resolved optimization property"
    assert spec.dependencies["crack_tip_frame"].role == "used_crack_tip_frame"
    assert {quantity.quantity_name for quantity in source.quantities} == {
        "error_xy",
        "error_z",
        "K_I",
        "K_II",
        "K_III",
        "T",
        "williams_coefficient",
    }


def test_run_williams_fit_returns_typed_result_from_optimization_object():
    from crackpy.fracture_analysis.methods.williams_fit import run_williams_fit

    optimization = SimpleNamespace(
        terms=np.asarray([-1, 1, 2]),
        data=SimpleNamespace(disp_z=None),
        optimize_williams_displacements_xy=lambda: SimpleNamespace(
            x=np.asarray([0.01, 2.0, 1.0, 0.02, -0.5, 0.3]),
            cost=0.1,
        ),
    )

    result = run_williams_fit(optimization)

    assert result.error_xy == 0.1
    assert result.error_z is np.nan or np.isnan(result.error_z)
    assert result.K_I == np.sqrt(2 * np.pi) * 2.0 / np.sqrt(1000)
    assert result.K_II == -np.sqrt(2 * np.pi) * -0.5 / np.sqrt(1000)
    assert result.T == 4.0
    assert result.coefficients.a == {-1: 0.01, 1: 2.0, 2: 1.0}
    assert result.coefficients.b == {-1: 0.02, 1: -0.5, 2: 0.3}
    assert tuple(result.coefficients.c) == (-1, 1, 2)

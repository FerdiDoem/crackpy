from inspect import signature
from types import SimpleNamespace
from typing import get_type_hints

import numpy as np
from scipy.optimize import OptimizeResult


def test_cjp_mixed_mode_outputs_convert_native_coefficients_to_canonical_units():
    from crackpy.fracture_analysis.methods.cjp_fit import cjp_mixed_mode_outputs_from_coefficients

    result = cjp_mixed_mode_outputs_from_coefficients(
        [2.0, -0.5, 0.25, 30.0, 0.75],
        error=0.125,
    )

    assert result.error == 0.125
    assert result.K_F == np.sqrt(np.pi / 2) * (2.0 - 3 * -0.5 - 8 * 0.75) / np.sqrt(1000)
    assert result.K_R == -4 * np.sqrt(np.pi / 2) * (2 * 0.25 + 0.75 * np.pi) / np.sqrt(1000)
    assert result.K_S == -np.sqrt(np.pi / 2) * (2.0 + -0.5) / np.sqrt(1000)
    assert result.K_II == 2 * np.sqrt(2 * np.pi) * 0.25 / np.sqrt(1000)
    assert result.T == -30.0
    assert result.coefficients.A_r == 2.0 / np.sqrt(1000)
    assert result.coefficients.B_r == -0.5 / np.sqrt(1000)
    assert result.coefficients.B_i == 0.25 / np.sqrt(1000)
    assert result.coefficients.C == 30.0
    assert result.coefficients.E == 0.75 / np.sqrt(1000)
    assert result.native_coefficients_MPa_sqrt_mm.A_r == 2.0


def test_cjp_mode_i_outputs_convert_native_coefficients_to_canonical_units():
    from crackpy.fracture_analysis.methods.cjp_fit import cjp_mode_i_outputs_from_coefficients

    result = cjp_mode_i_outputs_from_coefficients(
        [3.0, -1.0, 25.0, 0.5, 12.0],
        error=0.25,
    )

    assert result.error == 0.25
    assert result.K_F == np.sqrt(np.pi / 2) * (3.0 - 3 * -1.0 - 8 * 0.5) / np.sqrt(1000)
    assert result.K_R == -((2 * np.pi) ** 1.5) * 0.5 / np.sqrt(1000)
    assert result.K_S == np.sqrt(np.pi / 2) * (3.0 + -1.0) / np.sqrt(1000)
    assert result.T_x == -25.0
    assert result.T_y == -12.0
    assert result.coefficients.A == 3.0 / np.sqrt(1000)
    assert result.coefficients.B == -1.0 / np.sqrt(1000)
    assert result.coefficients.C == 25.0
    assert result.coefficients.E == 0.5 / np.sqrt(1000)
    assert result.coefficients.F == 12.0
    assert result.native_coefficients_MPa_sqrt_mm.A == 3.0


def test_cjp_conversion_functions_reject_wrong_coefficient_count():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import (
        cjp_mode_i_outputs_from_coefficients,
        cjp_mixed_mode_outputs_from_coefficients,
    )

    with pytest.raises(ValueError, match="five"):
        cjp_mixed_mode_outputs_from_coefficients([1.0, 2.0], error=0.0)

    with pytest.raises(ValueError, match="five"):
        cjp_mode_i_outputs_from_coefficients([1.0, 2.0], error=0.0)


def test_run_cjp_fit_declares_minimal_optimizer_protocol():
    from crackpy.fracture_analysis.methods.cjp_fit import CjpOptimizer, run_cjp_fit

    assert tuple(signature(run_cjp_fit).parameters) == ("optimizer",)
    assert get_type_hints(run_cjp_fit)["optimizer"] is CjpOptimizer
    assert get_type_hints(CjpOptimizer.optimize_cjp_displacements_mixedmode)["return"] is OptimizeResult
    assert get_type_hints(CjpOptimizer.optimize_cjp_displacements_modeI)["return"] is OptimizeResult


def test_run_cjp_fit_returns_typed_results_from_optimization_object():
    from crackpy.fracture_analysis.methods.cjp_fit import (
        cjp_mixed_mode_outputs_from_coefficients,
        run_cjp_fit,
    )

    optimizer = SimpleNamespace(
        optimize_cjp_displacements_mixedmode=lambda: OptimizeResult(
            x=np.asarray([2.0, -0.5, 0.25, 30.0, 0.75]),
            cost=0.125,
        ),
        optimize_cjp_displacements_modeI=lambda: OptimizeResult(
            x=np.asarray([3.0, -1.0, 25.0, 0.5, 12.0]),
            cost=0.25,
        ),
    )

    result = run_cjp_fit(optimizer)
    expected_mixed = cjp_mixed_mode_outputs_from_coefficients(
        [2.0, -0.5, 0.25, 30.0, 0.75],
        error=0.125,
    )

    assert result.mixed_mode.K_II == expected_mixed.K_II
    assert result.mode_i.T_y == -12.0


def test_run_cjp_fit_propagates_optimization_failures():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import run_cjp_fit

    optimizer = SimpleNamespace(
        optimize_cjp_displacements_mixedmode=lambda: (_ for _ in ()).throw(RuntimeError("mixed failed")),
        optimize_cjp_displacements_modeI=lambda: OptimizeResult(
            x=np.asarray([3.0, -1.0, 25.0, 0.5, 12.0]),
            cost=0.25,
        ),
    )

    with pytest.raises(RuntimeError, match="mixed failed"):
        run_cjp_fit(optimizer)

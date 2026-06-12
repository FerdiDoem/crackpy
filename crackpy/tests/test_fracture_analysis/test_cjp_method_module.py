from inspect import signature
from types import SimpleNamespace
from typing import get_type_hints

import numpy as np
from scipy.optimize import OptimizeResult

from crackpy.results.result_data import CrackTipFrame


def _demo_cjp_source_inputs():
    from crackpy.fracture_analysis.methods.cjp_fit import (
        CjpFitResultParameters,
        CjpMaterialParameters,
        CjpOptimizationParameters,
        cjp_mode_i_outputs_from_coefficients,
        cjp_mixed_mode_outputs_from_coefficients,
    )

    frame = CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )
    parameters = CjpFitResultParameters(
        material=CjpMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=CjpOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, max_radius_mm=1.0),
    )
    result = SimpleNamespace(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            [2.0, -0.5, 0.25, 30.0, 0.75],
            error=0.125,
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            [3.0, -1.0, 25.0, 0.5, 12.0],
            error=0.25,
        ),
    )
    return frame, parameters, result


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


def test_run_cjp_fit_from_coefficients_builds_both_result_variants():
    from crackpy.fracture_analysis.methods.cjp_fit import (
        cjp_mixed_mode_outputs_from_coefficients,
        run_cjp_fit_from_coefficients,
    )

    result = run_cjp_fit_from_coefficients(
        mixed_mode_coefficients=np.asarray([2.0, -0.5, 0.25, 30.0, 0.75]),
        mixed_mode_error=0.125,
        mode_i_coefficients=np.asarray([3.0, -1.0, 25.0, 0.5, 12.0]),
        mode_i_error=0.25,
    )
    expected_mixed = cjp_mixed_mode_outputs_from_coefficients(
        [2.0, -0.5, 0.25, 30.0, 0.75],
        error=0.125,
    )

    assert result.mixed_mode.K_II == expected_mixed.K_II
    assert result.mode_i.T_y == -12.0


def test_cjp_fit_displacement_field_recovers_synthetic_coefficients():
    import pytest
    from crackpy.fracture_analysis.crack_tip import cjp_displ_field_mixedmode, cjp_displ_field_modeI
    from crackpy.fracture_analysis.methods.cjp_fit import CjpFitDisplacementField, fit_cjp_displacement_field
    from crackpy.structure_elements.material import Material

    material = Material()
    r_grid, phi_grid = np.mgrid[1.0:2.0:5j, -1.0:1.0:6j]
    mixed_coefficients = np.asarray([2.0, -0.5, 0.25, 30.0, 0.75])
    mixed_x, mixed_y = cjp_displ_field_mixedmode(mixed_coefficients, phi_grid, r_grid, material)
    mode_i_coefficients = np.asarray([3.0, -1.0, 25.0, 0.5, 12.0])
    mode_i_x, mode_i_y = cjp_displ_field_modeI(mode_i_coefficients, phi_grid, r_grid, material)
    field = CjpFitDisplacementField(
        r_grid=r_grid,
        phi_grid=phi_grid,
        mixed_mode_disp_x=mixed_x,
        mixed_mode_disp_y=mixed_y,
        mode_i_disp_x=mode_i_x,
        mode_i_disp_y=mode_i_y,
        material=material,
    )

    result = fit_cjp_displacement_field(
        field,
        initial_mixed_mode_coefficients=mixed_coefficients,
        initial_mode_i_coefficients=mode_i_coefficients,
    )

    assert result.mixed_mode.error < 1e-20
    assert result.mode_i.error < 1e-20
    assert result.mixed_mode.native_coefficients_MPa_sqrt_mm.A_r == pytest.approx(mixed_coefficients[0])
    assert result.mode_i.native_coefficients_MPa_sqrt_mm.A == pytest.approx(mode_i_coefficients[0])


def test_cjp_fit_displacement_field_validates_shapes_and_initial_coefficients():
    import pytest
    from crackpy.fracture_analysis.methods.cjp_fit import CjpFitDisplacementField, fit_cjp_displacement_field
    from crackpy.structure_elements.material import Material

    grid = np.ones((2, 2))
    with pytest.raises(ValueError, match="mode_i_disp_y shape"):
        CjpFitDisplacementField(
            r_grid=grid,
            phi_grid=grid,
            mixed_mode_disp_x=grid,
            mixed_mode_disp_y=grid,
            mode_i_disp_x=grid,
            mode_i_disp_y=np.ones((3, 2)),
            material=Material(),
        )

    field = CjpFitDisplacementField(
        r_grid=grid,
        phi_grid=grid,
        mixed_mode_disp_x=grid,
        mixed_mode_disp_y=grid,
        mode_i_disp_x=grid,
        mode_i_disp_y=grid,
        material=Material(),
    )
    with pytest.raises(ValueError, match="Initial mixed-mode CJP coefficient vector"):
        fit_cjp_displacement_field(
            field,
            initial_mixed_mode_coefficients=np.ones(4),
            initial_mode_i_coefficients=np.ones(5),
        )


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


def test_cjp_fit_spec_loads_method_identities_aliases_quantities_and_variants():
    from crackpy.fracture_analysis.methods.cjp_fit import load_cjp_fit_spec

    spec = load_cjp_fit_spec()

    assert spec.schemas.envelope == "crackpy.result_envelope.cjp_fit.v1"
    assert spec.methods["mixed_mode"].method_id == "crackpy.fracture.cjp_mixed_mode_fit"
    assert spec.methods["mode_i"].method_id == "crackpy.fracture.cjp_mode_i_fit"
    assert spec.methods["mixed_mode"].aliases == ("CJP_results",)
    assert spec.methods["mode_i"].aliases == ("CJP_modeI_results",)
    assert spec.quantities["mixed_mode.K_F"].variant == "mixed_mode"
    assert spec.quantities["mode_i.K_F"].variant == "mode_i"
    assert spec.quantities["mixed_mode.A_r"].symbol == "A_r"
    assert spec.quantities["mode_i.A"].unit == "MPa*m^{1/2}"


def test_source_from_result_maps_typed_cjp_result_to_method_source():
    from crackpy.fracture_analysis.methods.cjp_fit import source_from_result

    frame, parameters, result = _demo_cjp_source_inputs()

    source = source_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
    )

    assert source.inputs[0].input_id == "input:demo"
    assert source.dependencies[0].dependency_name == "crack_tip_frame"
    assert source.parameters.result_parameters["material"]["E_MPa"] == 72000
    assert source.parameters.result_parameters["optimization"]["max_radius_mm"] == 1.0
    assert source.parameters.parameter_origins["angle_gap_deg"] == "resolved optimization property"
    quantity_by_name = {quantity.quantity_name: quantity for quantity in source.quantities}
    assert quantity_by_name["mixed_mode.A_r"].value == result.mixed_mode.coefficients.A_r
    assert quantity_by_name["mixed_mode.K_II"].qualifiers == {"variant": "mixed_mode"}
    assert quantity_by_name["mode_i.A"].value == result.mode_i.coefficients.A
    assert quantity_by_name["mode_i.T_y"].qualifiers == {"variant": "mode_i"}


def test_cjp_parameter_and_spec_models_document_fields():
    from crackpy.fracture_analysis.methods.cjp_fit import parameters as parameter_models
    from crackpy.fracture_analysis.methods.cjp_fit import spec_loader as spec_models

    for model in (
        parameter_models.CjpMaterialParameters,
        parameter_models.CjpOptimizationParameters,
        parameter_models.CjpFitResultParameters,
        spec_models.CjpQuantitySpec,
        spec_models.CjpFitSliceSpec,
    ):
        missing_descriptions = [
            field_name
            for field_name, model_field in model.model_fields.items()
            if not model_field.description
        ]
        assert missing_descriptions == []

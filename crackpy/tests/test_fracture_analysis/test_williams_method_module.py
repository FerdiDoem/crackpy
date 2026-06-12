from inspect import signature
from types import SimpleNamespace
from typing import get_type_hints

import numpy as np
import pytest

from crackpy.results.result_data import CrackTipFrame


def _demo_source_inputs():
    from crackpy.fracture_analysis.methods.williams_fit import (
        WilliamsCoefficientSet,
        WilliamsFitResult,
        WilliamsFitResultParameters,
        WilliamsMaterialParameters,
        WilliamsOptimizationParameters,
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
    return frame, parameters, result


def test_williams_method_module_builds_source_from_typed_result():
    from crackpy.fracture_analysis.methods.williams_fit import (
        load_williams_fit_spec,
        source_from_result,
    )
    from crackpy.fracture_analysis.methods.williams_fit.source_adapter import source_from_result as adapter_source_from_result

    frame, parameters, result = _demo_source_inputs()

    assert source_from_result is adapter_source_from_result

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


def test_source_from_result_uses_spec_quantity_definitions_for_scalar_results():
    from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec, source_from_result

    frame, parameters, result = _demo_source_inputs()
    spec = load_williams_fit_spec()
    spec_without_t = spec.model_copy(
        update={"quantities": {name: quantity for name, quantity in spec.quantities.items() if name != "T"}}
    )

    source = source_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
        spec=spec_without_t,
    )

    assert "T" not in {quantity.quantity_name for quantity in source.quantities}
    assert {"error_xy", "K_I", "williams_coefficient"} <= {
        quantity.quantity_name for quantity in source.quantities
    }


def test_source_from_result_validates_dependency_names_against_spec():
    from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec, source_from_result

    frame, parameters, result = _demo_source_inputs()
    spec = load_williams_fit_spec().model_copy(update={"dependencies": {}})

    with pytest.raises(ValueError, match="crack_tip_frame"):
        source_from_result(
            input_id="input:demo",
            data_ref="DemoNodemap.txt",
            source_label="demo",
            crack_tip_frame=frame,
            parameters=parameters,
            result=result,
            spec=spec,
        )


def test_run_williams_fit_declares_minimal_optimizer_protocol():
    from crackpy.fracture_analysis.methods.williams_fit import WilliamsFitOptimizer, run_williams_fit

    assert tuple(signature(run_williams_fit).parameters) == ("optimizer",)
    assert get_type_hints(run_williams_fit)["optimizer"] is WilliamsFitOptimizer


def test_run_williams_fit_protocol_uses_actual_optimizer_result_type():
    import crackpy.fracture_analysis.methods.williams_fit.runner as runner_module
    from crackpy.fracture_analysis.methods.williams_fit import WilliamsFitOptimizer
    from scipy.optimize import OptimizeResult

    assert not hasattr(runner_module, "_WilliamsFitData")
    assert not hasattr(runner_module, "_WilliamsOptimizationResult")
    assert get_type_hints(WilliamsFitOptimizer)["data"] is object
    assert get_type_hints(WilliamsFitOptimizer.optimize_williams_displacements_xy)["return"] is OptimizeResult
    assert get_type_hints(WilliamsFitOptimizer.optimize_williams_displacements_z)["return"] is OptimizeResult


def test_williams_result_can_be_built_from_explicit_coefficient_arrays():
    from crackpy.fracture_analysis.methods.williams_fit import run_williams_fit_from_coefficients

    result = run_williams_fit_from_coefficients(
        terms=(1, 2),
        xy_coefficients=np.asarray([2.0, 1.0, -0.5, 0.3]),
        error_xy=0.1,
    )

    assert result.error_xy == 0.1
    assert result.error_z is np.nan or np.isnan(result.error_z)
    assert result.K_I == np.sqrt(2 * np.pi) * 2.0 / np.sqrt(1000)
    assert result.K_II == -np.sqrt(2 * np.pi) * -0.5 / np.sqrt(1000)
    assert result.T == 4.0
    assert result.coefficients.a == {1: 2.0, 2: 1.0}
    assert result.coefficients.b == {1: -0.5, 2: 0.3}


def test_williams_result_from_coefficients_validates_terms_and_lengths():
    from crackpy.fracture_analysis.methods.williams_fit import run_williams_fit_from_coefficients

    with pytest.raises(ValueError, match="terms 1 and 2"):
        run_williams_fit_from_coefficients(
            terms=(1,),
            xy_coefficients=np.asarray([2.0, -0.5]),
            error_xy=0.1,
        )

    with pytest.raises(ValueError, match="in-plane coefficient vector"):
        run_williams_fit_from_coefficients(
            terms=(1, 2),
            xy_coefficients=np.asarray([2.0, 1.0, -0.5]),
            error_xy=0.1,
        )


def test_williams_fit_displacement_field_recovers_synthetic_xy_coefficients():
    from crackpy.fracture_analysis.crack_tip import williams_displ_field_xy
    from crackpy.fracture_analysis.methods.williams_fit import (
        WilliamsFitDisplacementField,
        fit_williams_displacement_field,
    )
    from crackpy.structure_elements.material import Material

    material = Material()
    terms = (1, 2)
    r_grid, phi_grid = np.mgrid[1.0:2.0:5j, -1.0:1.0:6j]
    expected_a = np.asarray([2.0, 1.0])
    expected_b = np.asarray([-0.5, 0.3])
    disp_x, disp_y = williams_displ_field_xy(expected_a, expected_b, terms, phi_grid, r_grid, material)
    field = WilliamsFitDisplacementField(
        terms=terms,
        r_grid=r_grid,
        phi_grid=phi_grid,
        disp_x=disp_x,
        disp_y=disp_y,
        disp_z=None,
        material=material,
    )

    result = fit_williams_displacement_field(
        field,
        initial_xy_coefficients=np.asarray([1.5, 0.5, -0.2, 0.1]),
    )

    assert result.error_xy < 1e-20
    assert result.coefficients.a[1] == pytest.approx(expected_a[0])
    assert result.coefficients.a[2] == pytest.approx(expected_a[1])
    assert result.coefficients.b[1] == pytest.approx(expected_b[0])
    assert result.coefficients.b[2] == pytest.approx(expected_b[1])


def test_williams_fit_displacement_field_validates_initial_coefficient_length():
    from crackpy.fracture_analysis.methods.williams_fit import (
        WilliamsFitDisplacementField,
        fit_williams_displacement_field,
    )
    from crackpy.structure_elements.material import Material

    grid = np.ones((2, 2))
    field = WilliamsFitDisplacementField(
        terms=(1, 2),
        r_grid=grid,
        phi_grid=grid,
        disp_x=grid,
        disp_y=grid,
        disp_z=None,
        material=Material(),
    )

    with pytest.raises(ValueError, match="Initial in-plane Williams coefficient vector"):
        fit_williams_displacement_field(field, initial_xy_coefficients=np.ones(3))


def test_williams_fit_displacement_field_validates_shape_and_required_terms():
    from crackpy.fracture_analysis.methods.williams_fit import WilliamsFitDisplacementField
    from crackpy.structure_elements.material import Material

    grid = np.ones((2, 2))

    with pytest.raises(ValueError, match="terms 1 and 2"):
        WilliamsFitDisplacementField(
            terms=(1,),
            r_grid=grid,
            phi_grid=grid,
            disp_x=grid,
            disp_y=grid,
            disp_z=None,
            material=Material(),
        )

    with pytest.raises(ValueError, match="disp_y shape"):
        WilliamsFitDisplacementField(
            terms=(1, 2),
            r_grid=grid,
            phi_grid=grid,
            disp_x=grid,
            disp_y=np.ones((3, 2)),
            disp_z=None,
            material=Material(),
        )


def test_common_provenance_builder_projects_scalar_source_quantities_from_spec():
    from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec, source_from_result
    from crackpy.provenance import MethodResultEnvelopeBuilder

    frame, parameters, result = _demo_source_inputs()
    spec = load_williams_fit_spec()
    source = source_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=result,
    )
    builder = MethodResultEnvelopeBuilder(source, spec)
    scalar_quantity = next(
        quantity
        for quantity in source.quantities
        if quantity.quantity_name == "K_I"
    )

    assert builder.dependency_record("crack_tip_frame", CrackTipFrame) is frame
    projected = builder.result_quantity_from_source(
        result_id="result:demo",
        method_id=spec.methods["analysis"].method_id,
        source_quantity=scalar_quantity,
    )

    assert projected.symbol == "K_I"
    assert projected.unit == "MPa*m^{1/2}"
    assert projected.legacy_aliases == ["Williams_fit_results.K_I"]


def test_provenance_slice_spec_allows_scalar_only_methods_without_coefficients():
    from crackpy.fracture_analysis.methods.williams_fit import load_williams_fit_spec
    from crackpy.provenance import (
        MethodResultEnvelopeBuilder,
        MethodResultSource,
        SourceInput,
        SourceParameters,
        SourceQuantity,
    )
    from crackpy.provenance.spec import ProvenanceSliceSpec

    spec_payload = load_williams_fit_spec().model_dump()
    spec_payload["quantities"] = {
        "J": {
            "quantity_name": "J",
            "symbol": "J",
            "description": "Path-independent J-integral.",
            "unit": "N/mm",
            "legacy_aliases": (),
        }
    }
    spec_payload.pop("coefficient_quantity")
    spec = ProvenanceSliceSpec.model_validate(spec_payload)
    source = MethodResultSource(
        inputs=(SourceInput(input_id="input:demo", data_ref="DemoNodemap.txt"),),
        dependencies=(),
        parameters=SourceParameters(result_parameters={}, parameter_origins={}),
        quantities=(SourceQuantity("J", 2.5),),
    )

    projected = MethodResultEnvelopeBuilder(source, spec).result_quantity_from_source(
        result_id="result:j_integral:demo",
        method_id="crackpy.fracture.j_integral",
        source_quantity=source.quantities[0],
    )

    assert projected.symbol == "J"
    assert projected.unit == "N/mm"


def test_williams_envelope_builder_requires_stable_input_identity():
    from crackpy.fracture_analysis.methods.williams_fit import build_williams_fit_envelope_from_result

    frame, parameters, result = _demo_source_inputs()

    with pytest.raises(ValueError, match="data_ref"):
        build_williams_fit_envelope_from_result(
            input_id="input:demo",
            data_ref="",
            source_label=None,
            crack_tip_frame=frame,
            parameters=parameters,
            result=result,
        )


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


def test_run_williams_fit_propagates_xy_optimization_failures():
    from crackpy.fracture_analysis.methods.williams_fit import run_williams_fit

    optimization = SimpleNamespace(
        terms=np.asarray([-1, 1, 2]),
        data=SimpleNamespace(disp_z=None),
        optimize_williams_displacements_xy=lambda: (_ for _ in ()).throw(RuntimeError("xy failed")),
    )

    with pytest.raises(RuntimeError, match="xy failed"):
        run_williams_fit(optimization)


def test_run_williams_fit_propagates_z_optimization_failures_when_z_is_present():
    from crackpy.fracture_analysis.methods.williams_fit import run_williams_fit

    optimization = SimpleNamespace(
        terms=np.asarray([-1, 1, 2]),
        data=SimpleNamespace(disp_z=np.asarray([0.0, 1.0])),
        optimize_williams_displacements_xy=lambda: SimpleNamespace(
            x=np.asarray([0.01, 2.0, 1.0, 0.02, -0.5, 0.3]),
            cost=0.1,
        ),
        optimize_williams_displacements_z=lambda: (_ for _ in ()).throw(RuntimeError("z failed")),
    )

    with pytest.raises(RuntimeError, match="z failed"):
        run_williams_fit(optimization)

import pytest

from crackpy.fracture_analysis.methods.cjp_fit import (
    CjpFitResult,
    CjpFitResultParameters,
    CjpMaterialParameters,
    CjpOptimizationParameters,
    build_cjp_fit_envelope_from_result,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
)
from crackpy.fracture_analysis.methods.williams_fit import (
    WilliamsCoefficientSet,
    WilliamsFitResult,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
    build_williams_fit_envelope_from_result,
)
from crackpy.results.legacy_schema import (
    LegacyResultSections,
    legacy_result_sections_from_envelope,
)
from crackpy.results.result_data import CrackTipFrame, ResultEnvelope, ResultQuantity, ResultRecord


def _frame() -> CrackTipFrame:
    return CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )


def _williams_envelope() -> ResultEnvelope:
    parameters = WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=WilliamsOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, terms=(-1, 1, 2)),
    )
    result = WilliamsFitResult(
        error_xy=0.1,
        error_z=float("nan"),
        K_I=12.5,
        K_II=-2.0,
        K_III=float("nan"),
        T=4.0,
        coefficients=WilliamsCoefficientSet(
            a={-1: 0.01, 1: 2.0, 2: 1.0},
            b={-1: 0.02, 1: -0.5, 2: 0.3},
            c={-1: float("nan"), 1: float("nan"), 2: float("nan")},
        ),
    )
    return build_williams_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=_frame(),
        parameters=parameters,
        result=result,
        crackpy_version="test-version",
    )


def _cjp_envelope() -> ResultEnvelope:
    parameters = CjpFitResultParameters(
        material=CjpMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=CjpOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, max_radius_mm=1.0),
    )
    result = CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            [2.0, -0.5, 0.25, 30.0, 0.75],
            error=0.125,
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            [3.0, -1.0, 25.0, 0.5, 12.0],
            error=0.25,
        ),
    )
    return build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=_frame(),
        parameters=parameters,
        result=result,
        crackpy_version="test-version",
    )


def test_williams_envelope_projects_legacy_result_section():
    sections = legacy_result_sections_from_envelope(_williams_envelope())

    assert isinstance(sections, LegacyResultSections)
    legacy = sections.as_legacy_dict()
    schema = sections.as_schema_dict()

    assert set(legacy) == {"Williams_fit_results"}
    assert legacy["Williams_fit_results"]["K_I"] == {"unit": "MPa*m^{1/2}", "result": 12.5}
    assert legacy["Williams_fit_results"]["error_z"] == {"unit": "1", "result": None}
    assert legacy["Williams_fit_results"]["a_1"] == {"unit": "MPa*mm^{1/2}", "result": 2.0}
    assert schema["Williams_fit_results"]["K_I"]["description"].startswith("Mode I stress intensity factor")
    assert schema["Williams_fit_results"]["K_I"]["result_schema_version"] == "crackpy.result_record.williams_fit.v1"


def test_cjp_envelope_projects_legacy_sections_with_contextual_error_keys():
    sections = legacy_result_sections_from_envelope(_cjp_envelope())
    legacy = sections.as_legacy_dict()
    schema = sections.as_schema_dict()

    assert set(legacy) == {"CJP_results", "CJP_modeI_results"}
    assert legacy["CJP_results"]["error"] == {"unit": "1", "result": 0.125}
    assert legacy["CJP_results"]["Error"] == {"unit": "1", "result": 0.125}
    assert legacy["CJP_modeI_results"]["error"] == {"unit": "1", "result": 0.25}
    assert legacy["CJP_modeI_results"]["Error"] == {"unit": "1", "result": 0.25}
    assert schema["CJP_results"]["error"]["method_id"] == "crackpy.fracture.cjp_mixed_mode_fit"
    assert schema["CJP_modeI_results"]["error"]["method_id"] == "crackpy.fracture.cjp_mode_i_fit"
    assert schema["CJP_results"]["error"]["result_id"] != schema["CJP_modeI_results"]["error"]["result_id"]


def test_legacy_projection_rejects_two_quantities_for_one_section_key():
    first = ResultQuantity(
        quantity_id="quantity:demo:one",
        result_id="result:demo",
        symbol="one",
        description="First quantity.",
        value=1.0,
        unit="1",
        method_id="crackpy.demo",
        legacy_aliases=["Demo_results.value"],
    )
    second = ResultQuantity(
        quantity_id="quantity:demo:two",
        result_id="result:demo",
        symbol="two",
        description="Second quantity.",
        value=2.0,
        unit="1",
        method_id="crackpy.demo",
        legacy_aliases=["Demo_results.value"],
    )
    envelope = ResultEnvelope(
        input_records=[],
        methods=[],
        configurations=[],
        crack_tip_frames=[],
        crack_tip_estimates=[],
        analysis_runs=[],
        results=[
            ResultRecord(
                result_id="result:demo",
                run_id="run:demo",
                result_schema_version="crackpy.result_record.demo.v1",
                quantities=[first, second],
            )
        ],
        envelope_schema_version="crackpy.result_envelope.demo.v1",
    )

    with pytest.raises(ValueError, match="Duplicate legacy result alias|claimed by both"):
        legacy_result_sections_from_envelope(envelope)

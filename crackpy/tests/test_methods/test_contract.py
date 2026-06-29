from crackpy.fracture_analysis.methods.cjp_fit import (
    CjpFitResult,
    CjpFitResultParameters,
    CjpMaterialParameters,
    CjpOptimizationParameters,
    build_cjp_fit_envelope_from_result,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
    source_from_result as cjp_source_from_result,
)
from crackpy.fracture_analysis.methods.williams_fit import (
    WilliamsCoefficientSet,
    WilliamsFitResult,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
    build_williams_fit_envelope_from_result,
    source_from_result as williams_source_from_result,
)
from crackpy.methods import MethodContractFixture, verify_method_module_contract
from crackpy.results.result_data import CrackTipFrame


def _frame() -> CrackTipFrame:
    return CrackTipFrame(
        frame_id="crack_tip_frame:demo:right",
        tip_id="crack_tip:demo:right",
        origin_mm={"x": 1.5, "y": 2.5},
        angle_deg=12.0,
        compatibility_side="right",
    )


def _williams_parameters() -> WilliamsFitResultParameters:
    return WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=WilliamsOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, terms=(-1, 1, 2)),
    )


def _williams_result() -> WilliamsFitResult:
    return WilliamsFitResult(
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


def _williams_fixture() -> MethodContractFixture:
    return MethodContractFixture(
        source_factory=lambda: williams_source_from_result(
            input_id="input:demo",
            data_ref="DemoNodemap.txt",
            source_label="demo",
            crack_tip_frame=_frame(),
            parameters=_williams_parameters(),
            result=_williams_result(),
        ),
        envelope_factory=lambda: build_williams_fit_envelope_from_result(
            input_id="input:demo",
            data_ref="DemoNodemap.txt",
            source_label="demo",
            crack_tip_frame=_frame(),
            parameters=_williams_parameters(),
            result=_williams_result(),
            crackpy_version="test-version",
        ),
        artifact_stem="williams_contract",
        graph_title="Williams Contract Graph",
    )


def _cjp_parameters() -> CjpFitResultParameters:
    return CjpFitResultParameters(
        material=CjpMaterialParameters(E_MPa=72000, nu_xy=0.33),
        optimization=CjpOptimizationParameters(angle_gap_deg=20, min_radius_mm=0.2, max_radius_mm=1.0),
    )


def _cjp_result() -> CjpFitResult:
    return CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            [2.0, -0.5, 0.25, 30.0, 0.75],
            error=0.125,
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            [3.0, -1.0, 25.0, 0.5, 12.0],
            error=0.25,
        ),
    )


def _cjp_fixture() -> MethodContractFixture:
    return MethodContractFixture(
        source_factory=lambda: cjp_source_from_result(
            input_id="input:demo",
            data_ref="DemoNodemap.txt",
            source_label="demo",
            crack_tip_frame=_frame(),
            parameters=_cjp_parameters(),
            result=_cjp_result(),
        ),
        envelope_factory=lambda: build_cjp_fit_envelope_from_result(
            input_id="input:demo",
            data_ref="DemoNodemap.txt",
            source_label="demo",
            crack_tip_frame=_frame(),
            parameters=_cjp_parameters(),
            result=_cjp_result(),
            crackpy_version="test-version",
        ),
        artifact_stem="cjp_contract",
        graph_title="CJP Contract Graph",
    )


def test_williams_method_module_passes_contract(tmp_path):
    report = verify_method_module_contract(
        "crackpy.fracture_analysis.methods.williams_fit",
        fixture=_williams_fixture(),
        artifact_dir=tmp_path,
    )

    assert report.module_name == "crackpy.fracture_analysis.methods.williams_fit"
    assert report.result_count == 1
    assert "crackpy.fracture.williams_fit" in report.method_ids
    assert all(path.exists() for path in report.artifact_paths.as_dict().values())


def test_cjp_method_module_passes_contract_with_variants(tmp_path):
    report = verify_method_module_contract(
        "crackpy.fracture_analysis.methods.cjp_fit",
        fixture=_cjp_fixture(),
        artifact_dir=tmp_path,
    )

    assert report.module_name == "crackpy.fracture_analysis.methods.cjp_fit"
    assert report.result_count == 2
    assert "crackpy.fracture.cjp_mixed_mode_fit" in report.method_ids
    assert "crackpy.fracture.cjp_mode_i_fit" in report.method_ids
    assert all(path.exists() for path in report.artifact_paths.as_dict().values())

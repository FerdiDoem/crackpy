"""Demonstrate the Williams-fit and CJP-fit method-module APIs.

The script uses deterministic synthetic displacement fields so it can be run as
a smoke test without nodemap files or random CJP optimizer starts. It shows the
three intended usage levels for the newer method modules:

1. assemble typed results from explicit fitted coefficient arrays;
2. fit already-sampled crack-tip-centered displacement fields;
3. build and write provenance artifacts from typed results.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
from scipy.optimize import OptimizeResult

from crackpy.fracture_analysis.crack_tip import (
    cjp_displ_field_mixedmode,
    cjp_displ_field_modeI,
    williams_displ_field_xy,
)
from crackpy.fracture_analysis.methods.cjp_fit import (
    CjpFitDisplacementField,
    CjpFitResultParameters,
    CjpMaterialParameters,
    CjpOptimizationParameters,
    build_cjp_fit_envelope_from_result,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
    fit_cjp_displacement_field,
    run_cjp_fit,
    run_cjp_fit_from_coefficients,
)
from crackpy.fracture_analysis.methods.williams_fit import (
    WilliamsFitDisplacementField,
    WilliamsFitResultParameters,
    WilliamsMaterialParameters,
    WilliamsOptimizationParameters,
    build_williams_fit_envelope_from_result,
    fit_williams_displacement_field,
    run_williams_fit,
    run_williams_fit_from_coefficients,
)
from crackpy.results.result_data import CrackTipFrame
from crackpy.results.write import write_cjp_fit_provenance_artifacts, write_williams_fit_provenance_artifacts
from crackpy.structure_elements.material import Material

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".scratch" / "method_fit_usage_demo"


def _crack_tip_frame() -> CrackTipFrame:
    return CrackTipFrame(
        frame_id="crack_tip_frame:method_fit_demo:right",
        tip_id="crack_tip:method_fit_demo:right",
        origin_mm={"x": 0.0, "y": 0.0},
        angle_deg=0.0,
        compatibility_side="right",
    )


def _williams_parameters(material: Material) -> WilliamsFitResultParameters:
    return WilliamsFitResultParameters(
        material=WilliamsMaterialParameters(
            name="Synthetic AA2024-T3",
            E_MPa=material.E,
            nu_xy=material.nu_xy,
            sig_yield_MPa=material.sig_yield,
            plane_strain=material.plane_strain,
            G_MPa=material.G,
            kappa=material.kappa,
        ),
        optimization=WilliamsOptimizationParameters(
            angle_gap_deg=10.0,
            min_radius_mm=1.0,
            max_radius_mm=2.0,
            tick_size_mm=0.25,
            terms=(1, 2),
        ),
    )


def _cjp_parameters(material: Material) -> CjpFitResultParameters:
    return CjpFitResultParameters(
        material=CjpMaterialParameters(
            name="Synthetic AA2024-T3",
            E_MPa=material.E,
            nu_xy=material.nu_xy,
            sig_yield_MPa=material.sig_yield,
            plane_strain=material.plane_strain,
            G_MPa=material.G,
            kappa=material.kappa,
        ),
        optimization=CjpOptimizationParameters(
            angle_gap_deg=10.0,
            min_radius_mm=1.0,
            max_radius_mm=2.0,
            tick_size_mm=0.25,
        ),
    )


def demonstrate_williams_fit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run the Williams result, field-fit, legacy-adapter, and artifact paths."""
    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    terms = (1, 2)
    a_coefficients = np.asarray([2.0, 1.0])
    b_coefficients = np.asarray([-0.5, 0.3])
    xy_coefficients = np.concatenate([a_coefficients, b_coefficients])

    result_from_coefficients = run_williams_fit_from_coefficients(
        terms=terms,
        xy_coefficients=xy_coefficients,
        error_xy=0.0,
    )

    r_grid, phi_grid = np.mgrid[1.0:2.0:5j, -1.0:1.0:6j]
    disp_x, disp_y = williams_displ_field_xy(a_coefficients, b_coefficients, terms, phi_grid, r_grid, material)
    field = WilliamsFitDisplacementField(
        terms=terms,
        r_grid=r_grid,
        phi_grid=phi_grid,
        disp_x=disp_x,
        disp_y=disp_y,
        disp_z=None,
        material=material,
    )
    result_from_field = fit_williams_displacement_field(
        field,
        initial_xy_coefficients=xy_coefficients,
    )

    optimizer_adapter = SimpleNamespace(
        terms=terms,
        data=SimpleNamespace(disp_z=None),
        optimize_williams_displacements_xy=lambda: OptimizeResult(x=xy_coefficients, cost=0.0),
    )
    result_from_legacy_adapter = run_williams_fit(optimizer_adapter)

    envelope = build_williams_fit_envelope_from_result(
        input_id="input:method_fit_demo:williams",
        data_ref="synthetic://method_fit_demo/williams",
        source_label="method_fit_demo_williams",
        crack_tip_frame=_crack_tip_frame(),
        parameters=_williams_parameters(material),
        result=result_from_field,
        crackpy_version="demo",
    )
    artifacts = write_williams_fit_provenance_artifacts(
        envelope,
        output_dir,
        stem="method_fit_demo_williams",
    )

    return {
        "result_from_coefficients": result_from_coefficients,
        "result_from_field": result_from_field,
        "result_from_legacy_adapter": result_from_legacy_adapter,
        "envelope": envelope,
        "artifacts": artifacts,
    }


def demonstrate_cjp_fit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run the CJP mixed-mode, Mode-I, field-fit, adapter, and artifact paths."""
    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    mixed_mode_coefficients = np.asarray([2.0, -0.5, 0.25, 30.0, 0.75])
    mode_i_coefficients = np.asarray([3.0, -1.0, 25.0, 0.5, 12.0])

    mixed_mode_only = cjp_mixed_mode_outputs_from_coefficients(mixed_mode_coefficients, error=0.0)
    mode_i_only = cjp_mode_i_outputs_from_coefficients(mode_i_coefficients, error=0.0)
    result_from_coefficients = run_cjp_fit_from_coefficients(
        mixed_mode_coefficients=mixed_mode_coefficients,
        mixed_mode_error=0.0,
        mode_i_coefficients=mode_i_coefficients,
        mode_i_error=0.0,
    )

    r_grid, phi_grid = np.mgrid[1.0:2.0:5j, -1.0:1.0:6j]
    mixed_x, mixed_y = cjp_displ_field_mixedmode(mixed_mode_coefficients, phi_grid, r_grid, material)
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
    result_from_field = fit_cjp_displacement_field(
        field,
        initial_mixed_mode_coefficients=mixed_mode_coefficients,
        initial_mode_i_coefficients=mode_i_coefficients,
    )

    optimizer_adapter = SimpleNamespace(
        optimize_cjp_displacements_mixedmode=lambda: OptimizeResult(x=mixed_mode_coefficients, cost=0.0),
        optimize_cjp_displacements_modeI=lambda: OptimizeResult(x=mode_i_coefficients, cost=0.0),
    )
    result_from_legacy_adapter = run_cjp_fit(optimizer_adapter)

    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:method_fit_demo:cjp",
        data_ref="synthetic://method_fit_demo/cjp",
        source_label="method_fit_demo_cjp",
        crack_tip_frame=_crack_tip_frame(),
        parameters=_cjp_parameters(material),
        result=result_from_field,
        crackpy_version="demo",
    )
    artifacts = write_cjp_fit_provenance_artifacts(
        envelope,
        output_dir,
        stem="method_fit_demo_cjp",
    )

    return {
        "mixed_mode_only": mixed_mode_only,
        "mode_i_only": mode_i_only,
        "result_from_coefficients": result_from_coefficients,
        "result_from_field": result_from_field,
        "result_from_legacy_adapter": result_from_legacy_adapter,
        "envelope": envelope,
        "artifacts": artifacts,
    }


def run_demo(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run all method-fit demos and assert the deterministic fits recover the inputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    williams = demonstrate_williams_fit(output_dir)
    cjp = demonstrate_cjp_fit(output_dir)

    assert williams["result_from_field"].error_xy < 1e-20
    assert cjp["result_from_field"].mixed_mode.error < 1e-20
    assert cjp["result_from_field"].mode_i.error < 1e-20

    return {"williams": williams, "cjp": cjp}


def _artifact_summary(artifacts: dict[str, Path]) -> dict[str, str]:
    return {name: str(path.relative_to(PROJECT_ROOT)) for name, path in artifacts.items()}


def main() -> None:
    demo = run_demo()
    williams_result = demo["williams"]["result_from_field"]
    cjp_result = demo["cjp"]["result_from_field"]

    print("Williams fit")
    print(f"  K_I  = {williams_result.K_I:.6f} MPa*m^0.5")
    print(f"  K_II = {williams_result.K_II:.6f} MPa*m^0.5")
    print(f"  T    = {williams_result.T:.6f} MPa")
    print("  artifacts:")
    for name, path in _artifact_summary(demo["williams"]["artifacts"]).items():
        print(f"    {name}: {path}")

    print("\nCJP mixed-mode fit")
    mixed = cjp_result.mixed_mode
    print(f"  K_F  = {mixed.K_F:.6f} MPa*m^0.5")
    print(f"  K_R  = {mixed.K_R:.6f} MPa*m^0.5")
    print(f"  K_S  = {mixed.K_S:.6f} MPa*m^0.5")
    print(f"  K_II = {mixed.K_II:.6f} MPa*m^0.5")
    print(f"  T    = {mixed.T:.6f} MPa")

    print("\nCJP Mode-I fit")
    mode_i = cjp_result.mode_i
    print(f"  K_F = {mode_i.K_F:.6f} MPa*m^0.5")
    print(f"  K_R = {mode_i.K_R:.6f} MPa*m^0.5")
    print(f"  K_S = {mode_i.K_S:.6f} MPa*m^0.5")
    print(f"  T_x = {mode_i.T_x:.6f} MPa")
    print(f"  T_y = {mode_i.T_y:.6f} MPa")
    print("  artifacts:")
    for name, path in _artifact_summary(demo["cjp"]["artifacts"]).items():
        print(f"    {name}: {path}")


if __name__ == "__main__":
    main()

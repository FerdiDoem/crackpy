"""CJP fit numerical runner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt
from scipy import optimize
from scipy.optimize import OptimizeResult

from crackpy.fracture_analysis.crack_tip import cjp_displ_field_mixedmode, cjp_displ_field_modeI
from crackpy.fracture_analysis.methods.cjp_fit.result import (
    CjpFitResult,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
)
from crackpy.structure_elements.material import Material


class CjpOptimizer(Protocol):
    """Minimal optimizer surface needed by the method-local CJP runner."""

    def optimize_cjp_displacements_mixedmode(self) -> OptimizeResult: ...

    def optimize_cjp_displacements_modeI(self) -> OptimizeResult: ...


@dataclass(frozen=True)
class CjpFitDisplacementField:
    """Resolved displacement fields consumed by the array-based CJP fit.

    The arrays are already in crack-tip-centered polar coordinates. This keeps
    fitting separate from file loading, coordinate transformation, interpolation,
    and radius-domain selection so future methods can reuse the same resolved
    field data without rebuilding `Optimization`.
    """

    r_grid: npt.NDArray[np.float64]
    phi_grid: npt.NDArray[np.float64]
    mixed_mode_disp_x: npt.NDArray[np.float64]
    mixed_mode_disp_y: npt.NDArray[np.float64]
    mode_i_disp_x: npt.NDArray[np.float64]
    mode_i_disp_y: npt.NDArray[np.float64]
    material: Material

    def __post_init__(self) -> None:
        expected_shape = self.r_grid.shape
        for name, values in {
            "phi_grid": self.phi_grid,
            "mixed_mode_disp_x": self.mixed_mode_disp_x,
            "mixed_mode_disp_y": self.mixed_mode_disp_y,
            "mode_i_disp_x": self.mode_i_disp_x,
            "mode_i_disp_y": self.mode_i_disp_y,
        }.items():
            if values.shape != expected_shape:
                raise ValueError(f"{name} shape {values.shape} does not match r_grid shape {expected_shape}.")


def _five_coefficients(name: str, values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    coefficients = np.ravel(np.asarray(values, dtype=float))
    if len(coefficients) != 5:
        raise ValueError(f"{name} must contain five coefficients, got {len(coefficients)}.")
    return coefficients


def run_cjp_fit_from_coefficients(
    *,
    mixed_mode_coefficients: npt.ArrayLike,
    mixed_mode_error: float,
    mode_i_coefficients: npt.ArrayLike,
    mode_i_error: float,
) -> CjpFitResult:
    """Build typed CJP results from explicit coefficient vectors."""
    return CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            _five_coefficients("Mixed-mode CJP coefficient vector", mixed_mode_coefficients),
            error=mixed_mode_error,
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            _five_coefficients("Mode-I CJP coefficient vector", mode_i_coefficients),
            error=mode_i_error,
        ),
    )


def fit_cjp_displacement_field(
    field: CjpFitDisplacementField,
    *,
    method: str = "lm",
    initial_mixed_mode_coefficients: npt.ArrayLike,
    initial_mode_i_coefficients: npt.ArrayLike,
) -> CjpFitResult:
    """Fit CJP coefficients from explicit crack-tip-centered displacement arrays."""
    initial_mixed_mode = _five_coefficients(
        "Initial mixed-mode CJP coefficient vector",
        initial_mixed_mode_coefficients,
    )
    initial_mode_i = _five_coefficients(
        "Initial Mode-I CJP coefficient vector",
        initial_mode_i_coefficients,
    )

    def residuals_mixed_mode(coefficients: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        model_x, model_y = cjp_displ_field_mixedmode(coefficients, field.phi_grid, field.r_grid, field.material)
        return np.ravel(np.array([model_x - field.mixed_mode_disp_x, model_y - field.mixed_mode_disp_y]))

    def residuals_mode_i(coefficients: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        model_x, model_y = cjp_displ_field_modeI(coefficients, field.phi_grid, field.r_grid, field.material)
        return np.ravel(np.array([model_x - field.mode_i_disp_x, model_y - field.mode_i_disp_y]))

    mixed_mode_result = optimize.least_squares(
        fun=residuals_mixed_mode,
        x0=initial_mixed_mode,
        method=method,
    )
    mode_i_result = optimize.least_squares(
        fun=residuals_mode_i,
        x0=initial_mode_i,
        method=method,
    )
    return run_cjp_fit_from_coefficients(
        mixed_mode_coefficients=mixed_mode_result.x,
        mixed_mode_error=mixed_mode_result.cost,
        mode_i_coefficients=mode_i_result.x,
        mode_i_error=mode_i_result.cost,
    )


def run_cjp_fit(optimizer: CjpOptimizer) -> CjpFitResult:
    """Run both current CJP optimizer variants and return typed results.

    This method-local runner intentionally lets optimizer exceptions propagate:
    a failed CJP optimization should not be converted into valid-looking
    provenance records.
    """
    mixed_mode_result = optimizer.optimize_cjp_displacements_mixedmode()
    mode_i_result = optimizer.optimize_cjp_displacements_modeI()

    return run_cjp_fit_from_coefficients(
        mixed_mode_coefficients=mixed_mode_result.x,
        mixed_mode_error=mixed_mode_result.cost,
        mode_i_coefficients=mode_i_result.x,
        mode_i_error=mode_i_result.cost,
    )

"""Williams-fit numerical runner."""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt
from scipy import optimize
from scipy.optimize import OptimizeResult

from crackpy.fracture_analysis.crack_tip import williams_displ_field_xy, williams_displ_field_z
from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsCoefficientSet, WilliamsFitResult
from crackpy.structure_elements.material import Material

logger = logging.getLogger(__name__)


class WilliamsFitOptimizer(Protocol):
    terms: Iterable[int]
    data: object

    def optimize_williams_displacements_xy(self) -> OptimizeResult: ...

    def optimize_williams_displacements_z(self) -> OptimizeResult: ...


@dataclass(frozen=True)
class WilliamsFitDisplacementField:
    """Resolved displacement field consumed by the array-based Williams fit.

    `terms` are the Williams expansion orders to fit. `r_grid` and `phi_grid`
    are crack-tip-centered polar coordinates in millimetres and radians.
    `disp_x`, `disp_y`, and optional `disp_z` are displacement values on the
    same grid, already shifted into the crack-tip frame by an adapter such as
    the current `Optimization` implementation. `material` supplies elastic
    constants used by the Williams displacement fields. This interface performs
    no file loading, coordinate transformation, or `InputData` interpolation.
    """

    terms: tuple[int, ...]
    r_grid: npt.NDArray[np.float64]
    phi_grid: npt.NDArray[np.float64]
    disp_x: npt.NDArray[np.float64]
    disp_y: npt.NDArray[np.float64]
    disp_z: npt.NDArray[np.float64] | None
    material: Material

    def __post_init__(self) -> None:
        if 1 not in self.terms or 2 not in self.terms:
            raise ValueError("WilliamsFitDisplacementField requires terms 1 and 2 for K and T results.")
        expected_shape = self.r_grid.shape
        for name, values in {
            "phi_grid": self.phi_grid,
            "disp_x": self.disp_x,
            "disp_y": self.disp_y,
        }.items():
            if values.shape != expected_shape:
                raise ValueError(f"{name} shape {values.shape} does not match r_grid shape {expected_shape}.")
        if self.disp_z is not None and self.disp_z.shape != expected_shape:
            raise ValueError(f"disp_z shape {self.disp_z.shape} does not match r_grid shape {expected_shape}.")


def _coefficient_map(terms: list[int], values: npt.ArrayLike) -> dict[int, float]:
    coefficient_values = np.ravel(np.asarray(values, dtype=float))
    return {term: float(coefficient_values[index]) for index, term in enumerate(terms)}


def _validate_result_terms(terms: Iterable[int]) -> list[int]:
    resolved_terms = [int(term) for term in terms]
    if 1 not in resolved_terms or 2 not in resolved_terms:
        raise ValueError("Williams result assembly requires terms 1 and 2 for K and T results.")
    if len(set(resolved_terms)) != len(resolved_terms):
        raise ValueError("Williams result assembly requires unique term orders.")
    return resolved_terms


def _coefficient_vector(name: str, values: npt.ArrayLike, expected_length: int) -> npt.NDArray[np.float64]:
    vector = np.ravel(np.asarray(values, dtype=float))
    if len(vector) != expected_length:
        raise ValueError(f"{name} must contain {expected_length} coefficients, got {len(vector)}.")
    return vector


def run_williams_fit_from_coefficients(
        *,
        terms: Iterable[int],
        xy_coefficients: npt.ArrayLike,
        error_xy: float,
        z_coefficients: npt.ArrayLike | None = None,
        error_z: float | None = None,
) -> WilliamsFitResult:
    """Build a typed Williams result from explicit fitted coefficient arrays.

    This is the result assembly interface shared by the legacy optimizer adapter
    and the array-based displacement-field fit. Coefficients are ordered as all
    a-series terms followed by all b-series terms for the in-plane fit, and all
    c-series terms for the optional out-of-plane fit. Units follow CrackPy's
    existing convention: coefficients are fitted in the current millimetre-based
    displacement field and stress intensity factors are reported in
    `MPa*sqrt(m)`.
    """
    resolved_terms = _validate_result_terms(terms)
    n_terms = len(resolved_terms)
    xy_values = _coefficient_vector(
        "Williams in-plane coefficient vector",
        xy_coefficients,
        expected_length=2 * n_terms,
    )

    a_n = _coefficient_map(resolved_terms, xy_values[:n_terms])
    b_n = _coefficient_map(resolved_terms, xy_values[n_terms:])

    K_I = np.sqrt(2 * np.pi) * a_n[1] / np.sqrt(1000)
    K_II = -np.sqrt(2 * np.pi) * b_n[1] / np.sqrt(1000)
    T = 4 * a_n[2]
    coefficients_flat = tuple(float(value) for value in xy_values)

    if z_coefficients is None:
        c_n = _coefficient_map(resolved_terms, [np.nan] * n_terms)
        return WilliamsFitResult(
            error_xy=error_xy,
            error_z=np.nan if error_z is None else error_z,
            K_I=K_I,
            K_II=K_II,
            K_III=np.nan,
            T=T,
            coefficients=WilliamsCoefficientSet(a=a_n, b=b_n, c=c_n),
            coefficients_flat=(*coefficients_flat, *tuple(np.array([np.nan] * n_terms))),
        )

    z_values = _coefficient_vector(
        "Williams out-of-plane coefficient vector",
        z_coefficients,
        expected_length=n_terms,
    )
    c_n = _coefficient_map(resolved_terms, z_values)
    K_III = np.sqrt(0.5 * np.pi) * c_n[1] / np.sqrt(1000)
    return WilliamsFitResult(
        error_xy=error_xy,
        error_z=np.nan if error_z is None else error_z,
        K_I=K_I,
        K_II=K_II,
        K_III=K_III,
        T=T,
        coefficients=WilliamsCoefficientSet(a=a_n, b=b_n, c=c_n),
        coefficients_flat=(*coefficients_flat, *tuple(float(value) for value in z_values)),
    )


def fit_williams_displacement_field(
        field: WilliamsFitDisplacementField,
        *,
        method: str = "lm",
        initial_xy_coefficients: npt.ArrayLike | None = None,
        initial_z_coefficients: npt.ArrayLike | None = None,
) -> WilliamsFitResult:
    """Fit Williams coefficients from explicit displacement-field arrays.

    The field must already be transformed into crack-tip-centered coordinates.
    This function owns only the numerical least-squares fit and typed result
    assembly; loading nodemaps, interpolating `InputData`, and choosing fit
    radii remain adapter responsibilities.
    """
    terms = list(field.terms)
    n_terms = len(terms)
    initial_xy = (
        np.ones(2 * n_terms)
        if initial_xy_coefficients is None
        else _coefficient_vector("Initial in-plane Williams coefficient vector", initial_xy_coefficients, 2 * n_terms)
    )

    def residuals_xy(coefficients: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        a = coefficients[:n_terms]
        b = coefficients[n_terms:]
        model_x, model_y = williams_displ_field_xy(a, b, terms, field.phi_grid, field.r_grid, field.material)
        return np.ravel(np.array([model_x - field.disp_x, model_y - field.disp_y]))

    xy_result = optimize.least_squares(fun=residuals_xy, x0=initial_xy, method=method)
    if field.disp_z is None or not np.any(field.disp_z):
        return run_williams_fit_from_coefficients(
            terms=terms,
            xy_coefficients=xy_result.x,
            error_xy=xy_result.cost,
        )

    initial_z = (
        np.ones(n_terms)
        if initial_z_coefficients is None
        else _coefficient_vector("Initial out-of-plane Williams coefficient vector", initial_z_coefficients, n_terms)
    )

    def residuals_z(coefficients: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        model_z = williams_displ_field_z(coefficients, terms, field.phi_grid, field.r_grid, field.material)
        return np.ravel(model_z - field.disp_z)

    z_result = optimize.least_squares(fun=residuals_z, x0=initial_z, method=method)
    return run_williams_fit_from_coefficients(
        terms=terms,
        xy_coefficients=xy_result.x,
        error_xy=xy_result.cost,
        z_coefficients=z_result.x,
        error_z=z_result.cost,
    )


def run_williams_fit(optimizer: WilliamsFitOptimizer) -> WilliamsFitResult:
    """Run Williams displacement fitting through the legacy optimizer adapter."""
    terms = [int(term) for term in optimizer.terms]
    disp_z = optimizer.data.disp_z
    skip_disp_z_optimization = disp_z is None or not np.any(disp_z)

    williams_results_xy = optimizer.optimize_williams_displacements_xy()

    if skip_disp_z_optimization:
        logger.info(
            "No sensible z-displacements provided; skipping z-direction optimization. "
            "Corresponding Williams optimization results set to NaN."
        )
        result = run_williams_fit_from_coefficients(
            terms=terms,
            xy_coefficients=williams_results_xy.x,
            error_xy=williams_results_xy.cost,
        )
        logger.debug(
            "Williams optimization results in xy-plane: Error_xy=%s, K_I=%.2f, K_II=%.2f, T=%.2f",
            result.error_xy,
            result.K_I,
            result.K_II,
            result.T,
        )
        return result

    williams_results_z = optimizer.optimize_williams_displacements_z()

    result = run_williams_fit_from_coefficients(
        terms=terms,
        xy_coefficients=williams_results_xy.x,
        error_xy=williams_results_xy.cost,
        z_coefficients=williams_results_z.x,
        error_z=williams_results_z.cost,
    )
    logger.debug(
        "Williams optimization results in xy-plane: Error_xy=%s, K_I=%.2f, K_II=%.2f, T=%.2f",
        result.error_xy,
        result.K_I,
        result.K_II,
        result.T,
    )
    logger.debug(
        "Williams optimization results in z-plane: Error_z=%s, K_III=%.2f",
        result.error_z,
        result.K_III,
    )
    return result

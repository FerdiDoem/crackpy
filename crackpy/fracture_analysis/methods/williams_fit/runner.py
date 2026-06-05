"""Williams-fit numerical runner."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from crackpy.fracture_analysis.methods.williams_fit.result import WilliamsCoefficientSet, WilliamsFitResult

logger = logging.getLogger(__name__)


def _coefficient_map(terms: Any, values: Any) -> dict[int, float]:
    return {int(term): values[index] for index, term in enumerate(terms)}


def run_williams_fit(optimization: Any) -> WilliamsFitResult:
    """Run Williams displacement fitting and return a typed result."""
    terms = [int(term) for term in optimization.terms]
    n_terms = len(terms)
    skip_disp_z_optimization = optimization.data.disp_z is None or not np.any(optimization.data.disp_z)

    try:
        williams_results_xy = optimization.optimize_williams_displacements_xy()
        williams_coeffs_xy = williams_results_xy.x

        a_n = _coefficient_map(terms, williams_coeffs_xy[:n_terms])
        b_n = _coefficient_map(terms, williams_coeffs_xy[n_terms:])

        K_I = np.sqrt(2 * np.pi) * a_n[1] / np.sqrt(1000)
        K_II = -np.sqrt(2 * np.pi) * b_n[1] / np.sqrt(1000)
        T = 4 * a_n[2]
        error_xy = williams_results_xy.cost
        coefficients_flat = tuple(williams_coeffs_xy)

        logger.debug(
            "Williams optimization results in xy-plane: Error_xy=%s, K_I=%.2f, K_II=%.2f, T=%.2f",
            error_xy,
            K_I,
            K_II,
            T,
        )
    except Exception:
        logger.exception(
            "Williams optimization for xy failed. Corresponding Williams optimization results set to NaN."
        )
        coefficients_flat = tuple(np.array([np.nan] * (2 * n_terms)))
        a_n = _coefficient_map(terms, [np.nan] * n_terms)
        b_n = _coefficient_map(terms, [np.nan] * n_terms)
        error_xy = np.nan
        K_I = np.nan
        K_II = np.nan
        T = np.nan

    if skip_disp_z_optimization:
        logger.info(
            "No sensible z-displacements provided; skipping z-direction optimization. "
            "Corresponding Williams optimization results set to NaN."
        )
        c_n = _coefficient_map(terms, [np.nan] * n_terms)
        return WilliamsFitResult(
            error_xy=error_xy,
            error_z=np.nan,
            K_I=K_I,
            K_II=K_II,
            K_III=np.nan,
            T=T,
            coefficients=WilliamsCoefficientSet(a=a_n, b=b_n, c=c_n),
            coefficients_flat=(*coefficients_flat, *tuple(np.array([np.nan] * n_terms))),
        )

    try:
        williams_results_z = optimization.optimize_williams_displacements_z()
        williams_coeffs_z = williams_results_z.x
        c_n = _coefficient_map(terms, williams_coeffs_z)
        K_III = np.sqrt(0.5 * np.pi) * c_n[1] / np.sqrt(1000)
        error_z = williams_results_z.cost

        logger.debug(
            "Williams optimization results in z-plane: Error_z=%s, K_III=%.2f",
            error_z,
            K_III,
        )
    except Exception:
        logger.exception(
            "Williams optimization for z-displacements failed. Corresponding Williams optimization results set to NaN."
        )
        williams_coeffs_z = np.array([np.nan] * n_terms)
        c_n = _coefficient_map(terms, [np.nan] * n_terms)
        error_z = np.nan
        K_III = np.nan

    return WilliamsFitResult(
        error_xy=error_xy,
        error_z=error_z,
        K_I=K_I,
        K_II=K_II,
        K_III=K_III,
        T=T,
        coefficients=WilliamsCoefficientSet(a=a_n, b=b_n, c=c_n),
        coefficients_flat=(*coefficients_flat, *tuple(williams_coeffs_z)),
    )

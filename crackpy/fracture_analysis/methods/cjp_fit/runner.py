"""CJP fit numerical runner."""
from __future__ import annotations

from typing import Protocol

from scipy.optimize import OptimizeResult

from crackpy.fracture_analysis.methods.cjp_fit.result import (
    CjpFitResult,
    cjp_mode_i_outputs_from_coefficients,
    cjp_mixed_mode_outputs_from_coefficients,
)


class CjpOptimizer(Protocol):
    """Minimal optimizer surface needed by the method-local CJP runner."""

    def optimize_cjp_displacements_mixedmode(self) -> OptimizeResult: ...

    def optimize_cjp_displacements_modeI(self) -> OptimizeResult: ...


def run_cjp_fit(optimizer: CjpOptimizer) -> CjpFitResult:
    """Run both current CJP optimizer variants and return typed results.

    This method-local runner intentionally lets optimizer exceptions propagate:
    a failed CJP optimization should not be converted into valid-looking
    provenance records.
    """
    mixed_mode_result = optimizer.optimize_cjp_displacements_mixedmode()
    mode_i_result = optimizer.optimize_cjp_displacements_modeI()

    return CjpFitResult(
        mixed_mode=cjp_mixed_mode_outputs_from_coefficients(
            mixed_mode_result.x,
            error=mixed_mode_result.cost,
        ),
        mode_i=cjp_mode_i_outputs_from_coefficients(
            mode_i_result.x,
            error=mode_i_result.cost,
        ),
    )

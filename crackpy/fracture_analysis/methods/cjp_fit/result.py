"""Typed CJP fit results and coefficient-to-output conversions."""
from __future__ import annotations

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

SINGULAR_COEFFICIENT_MM_TO_M = np.sqrt(1000)


class CjpMixedModeCoefficientSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    A_r: float = Field(description="Mixed-mode CJP A_r coefficient exported in MPa*m^{1/2}.")
    B_r: float = Field(description="Mixed-mode CJP B_r coefficient exported in MPa*m^{1/2}.")
    B_i: float = Field(description="Mixed-mode CJP B_i coefficient exported in MPa*m^{1/2}.")
    C: float = Field(description="Mixed-mode CJP non-singular C coefficient exported in MPa.")
    E: float = Field(description="Mixed-mode CJP E coefficient exported in MPa*m^{1/2}.")


class CjpNativeMixedModeCoefficientSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    A_r: float = Field(description="Native optimizer A_r coefficient in MPa*mm^{1/2}.")
    B_r: float = Field(description="Native optimizer B_r coefficient in MPa*mm^{1/2}.")
    B_i: float = Field(description="Native optimizer B_i coefficient in MPa*mm^{1/2}.")
    C: float = Field(description="Native optimizer non-singular C coefficient in MPa.")
    E: float = Field(description="Native optimizer E coefficient in MPa*mm^{1/2}.")


class CjpModeICoefficientSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    A: float = Field(description="Mode-I CJP A coefficient exported in MPa*m^{1/2}.")
    B: float = Field(description="Mode-I CJP B coefficient exported in MPa*m^{1/2}.")
    C: float = Field(description="Mode-I CJP non-singular C coefficient exported in MPa.")
    E: float = Field(description="Mode-I CJP E coefficient exported in MPa*m^{1/2}.")
    F: float = Field(description="Mode-I CJP non-singular F coefficient exported in MPa.")


class CjpNativeModeICoefficientSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    A: float = Field(description="Native optimizer A coefficient in MPa*mm^{1/2}.")
    B: float = Field(description="Native optimizer B coefficient in MPa*mm^{1/2}.")
    C: float = Field(description="Native optimizer non-singular C coefficient in MPa.")
    E: float = Field(description="Native optimizer E coefficient in MPa*mm^{1/2}.")
    F: float = Field(description="Native optimizer non-singular F coefficient in MPa.")


class CjpMixedModeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    error: float = Field(description="Mixed-mode CJP optimizer residual cost.")
    K_F: float = Field(description="Mixed-mode CJP K_F value derived from A_r, B_r, and E, in MPa*m^{1/2}.")
    K_R: float = Field(description="Mixed-mode CJP K_R value derived from B_i and E, in MPa*m^{1/2}.")
    K_S: float = Field(description="Mixed-mode CJP K_S value derived from A_r and B_r, in MPa*m^{1/2}.")
    K_II: float = Field(description="Mixed-mode CJP K_II value derived from B_i, in MPa*m^{1/2}.")
    T: float = Field(description="Mixed-mode CJP T-stress derived from C, in MPa.")
    coefficients: CjpMixedModeCoefficientSet = Field(
        description="Canonical mixed-mode CJP coefficients for provenance export."
    )
    native_coefficients_MPa_sqrt_mm: CjpNativeMixedModeCoefficientSet = Field(
        description="Native mixed-mode optimizer coefficients before singular unit conversion."
    )


class CjpModeIResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    error: float = Field(description="Mode-I CJP optimizer residual cost.")
    K_F: float = Field(description="Mode-I CJP K_F value derived from A, B, and E, in MPa*m^{1/2}.")
    K_R: float = Field(description="Mode-I CJP K_R value derived from E, in MPa*m^{1/2}.")
    K_S: float = Field(description="Mode-I CJP K_S value derived from A and B, in MPa*m^{1/2}.")
    T_x: float = Field(description="Mode-I CJP x-direction T-stress derived from C, in MPa.")
    T_y: float = Field(description="Mode-I CJP y-direction T-stress derived from F, in MPa.")
    coefficients: CjpModeICoefficientSet = Field(
        description="Canonical Mode-I CJP coefficients for provenance export."
    )
    native_coefficients_MPa_sqrt_mm: CjpNativeModeICoefficientSet = Field(
        description="Native Mode-I optimizer coefficients before singular unit conversion."
    )


class CjpFitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    mixed_mode: CjpMixedModeResult = Field(description="Mixed-mode CJP fit result.")
    mode_i: CjpModeIResult = Field(description="Mode-I CJP fit result.")


def _five_coefficients(coefficients: npt.ArrayLike) -> np.ndarray:
    values = np.asarray(coefficients, dtype=float)
    if values.size != 5:
        raise ValueError("CJP coefficient conversion requires exactly five coefficients.")
    return values


def cjp_mixed_mode_outputs_from_coefficients(coefficients: npt.ArrayLike, *, error: float) -> CjpMixedModeResult:
    """Convert native mixed-mode CJP optimizer coefficients into canonical result quantities.

    The current optimizer fits singular coefficients against radii in mm, so
    A_r, B_r, B_i, and E are native `MPa*mm^{1/2}` values. Public result
    quantities use `MPa*m^{1/2}` to match the legacy K-value output.
    """
    A_r, B_r, B_i, C, E = _five_coefficients(coefficients)
    native = CjpNativeMixedModeCoefficientSet(A_r=A_r, B_r=B_r, B_i=B_i, C=C, E=E)
    canonical = CjpMixedModeCoefficientSet(
        A_r=A_r / SINGULAR_COEFFICIENT_MM_TO_M,
        B_r=B_r / SINGULAR_COEFFICIENT_MM_TO_M,
        B_i=B_i / SINGULAR_COEFFICIENT_MM_TO_M,
        C=C,
        E=E / SINGULAR_COEFFICIENT_MM_TO_M,
    )

    return CjpMixedModeResult(
        error=error,
        K_F=np.sqrt(np.pi / 2) * (A_r - 3 * B_r - 8 * E) / SINGULAR_COEFFICIENT_MM_TO_M,
        K_R=-4 * np.sqrt(np.pi / 2) * (2 * B_i + E * np.pi) / SINGULAR_COEFFICIENT_MM_TO_M,
        K_S=-np.sqrt(np.pi / 2) * (A_r + B_r) / SINGULAR_COEFFICIENT_MM_TO_M,
        K_II=2 * np.sqrt(2 * np.pi) * B_i / SINGULAR_COEFFICIENT_MM_TO_M,
        T=-C,
        coefficients=canonical,
        native_coefficients_MPa_sqrt_mm=native,
    )


def cjp_mode_i_outputs_from_coefficients(coefficients: npt.ArrayLike, *, error: float) -> CjpModeIResult:
    """Convert native Mode-I CJP optimizer coefficients into canonical result quantities.

    A, B, and E are fitted with mm-based radii and exported in
    `MPa*m^{1/2}`. C and F are non-singular stress coefficients and stay in MPa.
    """
    A, B, C, E, F = _five_coefficients(coefficients)
    native = CjpNativeModeICoefficientSet(A=A, B=B, C=C, E=E, F=F)
    canonical = CjpModeICoefficientSet(
        A=A / SINGULAR_COEFFICIENT_MM_TO_M,
        B=B / SINGULAR_COEFFICIENT_MM_TO_M,
        C=C,
        E=E / SINGULAR_COEFFICIENT_MM_TO_M,
        F=F,
    )

    return CjpModeIResult(
        error=error,
        K_F=np.sqrt(np.pi / 2) * (A - 3 * B - 8 * E) / SINGULAR_COEFFICIENT_MM_TO_M,
        K_R=-((2 * np.pi) ** 1.5) * E / SINGULAR_COEFFICIENT_MM_TO_M,
        K_S=np.sqrt(np.pi / 2) * (A + B) / SINGULAR_COEFFICIENT_MM_TO_M,
        T_x=-C,
        T_y=-F,
        coefficients=canonical,
        native_coefficients_MPa_sqrt_mm=native,
    )

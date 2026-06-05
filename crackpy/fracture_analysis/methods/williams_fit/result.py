"""Typed Williams-fit results."""
from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WilliamsCoefficientSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    a: dict[int, float] = Field(
        default_factory=dict,
        description="Williams coefficient series a_n.",
    )
    b: dict[int, float] = Field(
        default_factory=dict,
        description="Williams coefficient series b_n.",
    )
    c: dict[int, float] = Field(
        default_factory=dict,
        description="Williams coefficient series c_n.",
    )

    @field_validator("a", "b", "c", mode="before")
    @classmethod
    def _coerce_term_keys(cls, value: Mapping[Any, Any] | None) -> dict[int, float]:
        if value is None:
            return {}
        return {int(term): coefficient for term, coefficient in value.items()}


class WilliamsFitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    error_xy: float = Field(description="Williams fit residual for in-plane displacement components.")
    error_z: float = Field(description="Williams fit residual for out-of-plane displacement component.")
    K_I: float = Field(description="Mode I stress intensity factor derived from Williams coefficient a_1.")
    K_II: float = Field(description="Mode II stress intensity factor derived from Williams coefficient b_1.")
    K_III: float = Field(description="Mode III stress intensity factor derived from Williams coefficient c_1.")
    T: float = Field(description="T-stress derived from Williams coefficient a_2.")
    coefficients: WilliamsCoefficientSet = Field(description="Williams expansion coefficients grouped by series.")
    coefficients_flat: tuple[float, ...] = Field(
        default_factory=tuple,
        description="Flat coefficient vector in current optimization order: a-series, b-series, then c-series.",
    )

    @field_validator("coefficients_flat", mode="before")
    @classmethod
    def _coerce_coefficients_flat(cls, value: Any) -> tuple[float, ...]:
        if value is None:
            return ()
        return tuple(value)

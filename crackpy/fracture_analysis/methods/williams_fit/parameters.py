"""Williams-fit result-affecting parameter schema."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ANALYSIS_OBJECT_ORIGIN = "analysis object"
RESOLVED_OPTIMIZATION_ORIGIN = "resolved optimization property"
PARAMETER_ORIGIN_KEY = "parameter_origin"


class WilliamsMaterialParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = Field(
        default=None,
        description="Material name used by the Williams-fit analysis.",
    )
    E_MPa: float | None = Field(
        default=None,
        description="Young's modulus used by the Williams-fit analysis, in MPa.",
    )
    nu_xy: float | None = Field(
        default=None,
        description="In-plane Poisson ratio used by the Williams-fit analysis.",
    )
    sig_yield_MPa: float | None = Field(
        default=None,
        description="Yield stress carried with the material snapshot, in MPa.",
    )
    plane_strain: bool | None = Field(
        default=None,
        description="Whether the material calculation used the plane-strain assumption.",
    )
    G_MPa: float | None = Field(
        default=None,
        description="Shear modulus used by the Williams-fit analysis, in MPa.",
    )
    kappa: float | None = Field(
        default=None,
        description="Kolosov constant used by the Williams-fit analysis.",
    )

class WilliamsOptimizationParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    angle_gap_deg: float | None = Field(
        default=None,
        description="Angular gap excluded from the Williams-fit displacement sampling, in degrees.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    min_radius_mm: float | None = Field(
        default=None,
        description="Minimum crack-tip-centered sampling radius for the Williams fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    max_radius_mm: float | None = Field(
        default=None,
        description="Maximum crack-tip-centered sampling radius for the Williams fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    tick_size_mm: float | None = Field(
        default=None,
        description="Sampling grid tick size used for the Williams fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    terms: tuple[int, ...] = Field(
        default_factory=tuple,
        description="Williams expansion term orders included in the fit.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )

    @field_validator("terms", mode="before")
    @classmethod
    def _coerce_terms(cls, value: Any) -> tuple[int, ...]:
        if value is None:
            return ()
        return tuple(value)

class WilliamsFitResultParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    material: WilliamsMaterialParameters = Field(
        description="Resolved material values used by the Williams-fit analysis.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: ANALYSIS_OBJECT_ORIGIN},
    )
    optimization: WilliamsOptimizationParameters = Field(
        description="Resolved Williams optimization settings that affect fitted quantities.",
    )

    def result_parameters(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def parameter_origins(cls) -> dict[str, str]:
        material_origin = cls.model_fields["material"].json_schema_extra[PARAMETER_ORIGIN_KEY]
        origins = {"material": material_origin}
        for name, field in WilliamsOptimizationParameters.model_fields.items():
            origins[name] = field.json_schema_extra[PARAMETER_ORIGIN_KEY]
        return origins

"""CJP-fit result-affecting parameter schema."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ANALYSIS_OBJECT_ORIGIN = "analysis object"
RESOLVED_OPTIMIZATION_ORIGIN = "resolved optimization property"
PARAMETER_ORIGIN_KEY = "parameter_origin"


class CjpMaterialParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, description="Material name used by the CJP-fit analysis.")
    E_MPa: float | None = Field(default=None, description="Young's modulus used by the CJP-fit analysis, in MPa.")
    nu_xy: float | None = Field(default=None, description="In-plane Poisson ratio used by the CJP-fit analysis.")
    sig_yield_MPa: float | None = Field(
        default=None,
        description="Yield stress carried with the CJP material snapshot, in MPa.",
    )
    plane_strain: bool | None = Field(
        default=None,
        description="Whether the material calculation used the plane-strain assumption.",
    )
    G_MPa: float | None = Field(default=None, description="Shear modulus used by the CJP-fit analysis, in MPa.")
    kappa: float | None = Field(default=None, description="Kolosov constant used by the CJP-fit analysis.")


class CjpOptimizationParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    angle_gap_deg: float | None = Field(
        default=None,
        description="Angular gap excluded from the CJP displacement sampling, in degrees.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    min_radius_mm: float | None = Field(
        default=None,
        description="Minimum crack-tip-centered sampling radius for the CJP fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    max_radius_mm: float | None = Field(
        default=None,
        description="Maximum crack-tip-centered sampling radius for the CJP fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )
    tick_size_mm: float | None = Field(
        default=None,
        description="Sampling grid tick size used for the CJP fit, in mm.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: RESOLVED_OPTIMIZATION_ORIGIN},
    )


class CjpFitResultParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    material: CjpMaterialParameters = Field(
        description="Resolved material values used by the CJP-fit analysis.",
        json_schema_extra={PARAMETER_ORIGIN_KEY: ANALYSIS_OBJECT_ORIGIN},
    )
    optimization: CjpOptimizationParameters = Field(
        description="Resolved CJP optimization settings that affect fitted quantities."
    )

    def result_parameters(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def parameter_origins(cls) -> dict[str, str]:
        material_origin = cls.model_fields["material"].json_schema_extra[PARAMETER_ORIGIN_KEY]
        origins = {"material": material_origin}
        for name, field in CjpOptimizationParameters.model_fields.items():
            origins[name] = field.json_schema_extra[PARAMETER_ORIGIN_KEY]
        return origins

"""Pydantic models holding fracture analysis results.

Each model mirrors the tag definitions in :mod:`crackpy.structure_elements.tags`.
Fields expose alias, unit, label and LTM (Length-Time-Mass exponents) metadata
for later processing or plotting.
"""

from pydantic import BaseModel, Field, create_model

from .tags import (
    TagCJPModel,
    TagWillimasFitting,
    TagSIFIntegralEvalMean,
    TagSIFIntegralEvalMedian,
    TagSIFIntegralEvalMeanWOoutliers,
)


tag_cjp = TagCJPModel()
class CJPResults(BaseModel):
    error: float = Field(
        ...,
        alias=tag_cjp.error["tag"],
        unit=tag_cjp.error["unit"],
        ltm=tag_cjp.error["ltm"],
        label=tag_cjp.error["label"],
    )
    K_F: float = Field(
        ...,
        alias=tag_cjp.K_F["tag"],
        unit=tag_cjp.K_F["unit"],
        ltm=tag_cjp.K_F["ltm"],
        label=tag_cjp.K_F["label"],
    )
    K_R: float = Field(
        ...,
        alias=tag_cjp.K_R["tag"],
        unit=tag_cjp.K_R["unit"],
        ltm=tag_cjp.K_R["ltm"],
        label=tag_cjp.K_R["label"],
    )
    K_S: float = Field(
        ...,
        alias=tag_cjp.K_S["tag"],
        unit=tag_cjp.K_S["unit"],
        ltm=tag_cjp.K_S["ltm"],
        label=tag_cjp.K_S["label"],
    )
    K_II: float = Field(
        ...,
        alias=tag_cjp.K_II["tag"],
        unit=tag_cjp.K_II["unit"],
        ltm=tag_cjp.K_II["ltm"],
        label=tag_cjp.K_II["label"],
    )
    K_eff_Yang: float = Field(
        ...,
        alias=tag_cjp.K_eff_Yang["tag"],
        unit=tag_cjp.K_eff_Yang["unit"],
        ltm=tag_cjp.K_eff_Yang["ltm"],
        label=tag_cjp.K_eff_Yang["label"],
    )
    K_eff_Nowell: float = Field(
        ...,
        alias=tag_cjp.K_eff_Nowell["tag"],
        unit=tag_cjp.K_eff_Nowell["unit"],
        ltm=tag_cjp.K_eff_Nowell["ltm"],
        label=tag_cjp.K_eff_Nowell["label"],
    )
    T: float = Field(
        ...,
        alias=tag_cjp.T["tag"],
        unit=tag_cjp.T["unit"],
        ltm=tag_cjp.T["ltm"],
        label=tag_cjp.T["label"],
    )

    class Config:
        allow_population_by_field_name = True


tag_williams = TagWillimasFitting()

def _create_williams_model(orders=tag_williams.orders):
    fields = {
        'error': (float, Field(..., alias=tag_williams.error['tag'], unit=tag_williams.error['unit'], ltm=tag_williams.error['ltm'], label=tag_williams.error['label'])),
        'K_I': (float, Field(..., alias=tag_williams.K_I['tag'], unit=tag_williams.K_I['unit'], ltm=tag_williams.K_I['ltm'], label=tag_williams.K_I['label'])),
        'K_II': (float, Field(..., alias=tag_williams.K_II['tag'], unit=tag_williams.K_II['unit'], ltm=tag_williams.K_II['ltm'], label=tag_williams.K_II['label'])),
        'K_V': (float, Field(..., alias=tag_williams.K_V['tag'], unit=tag_williams.K_V['unit'], ltm=tag_williams.K_V['ltm'], label=tag_williams.K_V['label'])),
        'T': (float, Field(..., alias=tag_williams.T['tag'], unit=tag_williams.T['unit'], ltm=tag_williams.T['ltm'], label=tag_williams.T['label'])),
    }
    for n in orders:
        a = tag_williams.coeff('a', n)
        b = tag_williams.coeff('b', n)
        fields[f'a_{n}'] = (float, Field(..., alias=a['tag'], unit=a['unit'], ltm=a['ltm'], label=a['label']))
        fields[f'b_{n}'] = (float, Field(..., alias=b['tag'], unit=b['unit'], ltm=b['ltm'], label=b['label']))
    model = create_model('WilliamsODMResults', __config__=type('Config', (), {'allow_population_by_field_name': True}), **fields)
    return model

WilliamsODMResults = _create_williams_model()


# Integral result models -------------------------------------------------------
tag_int_mean = TagSIFIntegralEvalMean()
class SIFsIntegralMeanResults(BaseModel):
    J: float = Field(
        ...,
        alias=tag_int_mean.J["tag"],
        unit=tag_int_mean.J["unit"],
        ltm=tag_int_mean.J["ltm"],
        label=tag_int_mean.J["label"],
    )
    K_J: float = Field(
        ...,
        alias=tag_int_mean.K_J["tag"],
        unit=tag_int_mean.K_J["unit"],
        ltm=tag_int_mean.K_J["ltm"],
        label=tag_int_mean.K_J["label"],
    )
    K_I_interac: float = Field(
        ...,
        alias=tag_int_mean.K_I_interac["tag"],
        unit=tag_int_mean.K_I_interac["unit"],
        ltm=tag_int_mean.K_I_interac["ltm"],
        label=tag_int_mean.K_I_interac["label"],
    )
    K_II_interac: float = Field(
        ...,
        alias=tag_int_mean.K_II_interac["tag"],
        unit=tag_int_mean.K_II_interac["unit"],
        ltm=tag_int_mean.K_II_interac["ltm"],
        label=tag_int_mean.K_II_interac["label"],
    )
    T_interac: float = Field(
        ...,
        alias=tag_int_mean.T_interac["tag"],
        unit=tag_int_mean.T_interac["unit"],
        ltm=tag_int_mean.T_interac["ltm"],
        label=tag_int_mean.T_interac["label"],
    )
    K_I_Chen: float = Field(
        ...,
        alias=tag_int_mean.K_I_Chen["tag"],
        unit=tag_int_mean.K_I_Chen["unit"],
        ltm=tag_int_mean.K_I_Chen["ltm"],
        label=tag_int_mean.K_I_Chen["label"],
    )
    K_II_Chen: float = Field(
        ...,
        alias=tag_int_mean.K_II_Chen["tag"],
        unit=tag_int_mean.K_II_Chen["unit"],
        ltm=tag_int_mean.K_II_Chen["ltm"],
        label=tag_int_mean.K_II_Chen["label"],
    )
    T_Chen: float = Field(
        ...,
        alias=tag_int_mean.T_Chen["tag"],
        unit=tag_int_mean.T_Chen["unit"],
        ltm=tag_int_mean.T_Chen["ltm"],
        label=tag_int_mean.T_Chen["label"],
    )
    T_SDM: float = Field(
        ...,
        alias=tag_int_mean.T_SDM["tag"],
        unit=tag_int_mean.T_SDM["unit"],
        ltm=tag_int_mean.T_SDM["ltm"],
        label=tag_int_mean.T_SDM["label"],
    )

    class Config:
        allow_population_by_field_name = True


tag_int_median = TagSIFIntegralEvalMedian()
class SIFsIntegralMedianResults(BaseModel):
    J: float = Field(
        ...,
        alias=tag_int_median.J["tag"],
        unit=tag_int_median.J["unit"],
        ltm=tag_int_median.J["ltm"],
        label=tag_int_median.J["label"],
    )
    K_J: float = Field(
        ...,
        alias=tag_int_median.K_J["tag"],
        unit=tag_int_median.K_J["unit"],
        ltm=tag_int_median.K_J["ltm"],
        label=tag_int_median.K_J["label"],
    )
    K_I_interac: float = Field(
        ...,
        alias=tag_int_median.K_I_interac["tag"],
        unit=tag_int_median.K_I_interac["unit"],
        ltm=tag_int_median.K_I_interac["ltm"],
        label=tag_int_median.K_I_interac["label"],
    )
    K_II_interac: float = Field(
        ...,
        alias=tag_int_median.K_II_interac["tag"],
        unit=tag_int_median.K_II_interac["unit"],
        ltm=tag_int_median.K_II_interac["ltm"],
        label=tag_int_median.K_II_interac["label"],
    )
    T_interac: float = Field(
        ...,
        alias=tag_int_median.T_interac["tag"],
        unit=tag_int_median.T_interac["unit"],
        ltm=tag_int_median.T_interac["ltm"],
        label=tag_int_median.T_interac["label"],
    )
    K_I_Chen: float = Field(
        ...,
        alias=tag_int_median.K_I_Chen["tag"],
        unit=tag_int_median.K_I_Chen["unit"],
        ltm=tag_int_median.K_I_Chen["ltm"],
        label=tag_int_median.K_I_Chen["label"],
    )
    K_II_Chen: float = Field(
        ...,
        alias=tag_int_median.K_II_Chen["tag"],
        unit=tag_int_median.K_II_Chen["unit"],
        ltm=tag_int_median.K_II_Chen["ltm"],
        label=tag_int_median.K_II_Chen["label"],
    )
    T_Chen: float = Field(
        ...,
        alias=tag_int_median.T_Chen["tag"],
        unit=tag_int_median.T_Chen["unit"],
        ltm=tag_int_median.T_Chen["ltm"],
        label=tag_int_median.T_Chen["label"],
    )
    T_SDM: float = Field(
        ...,
        alias=tag_int_median.T_SDM["tag"],
        unit=tag_int_median.T_SDM["unit"],
        ltm=tag_int_median.T_SDM["ltm"],
        label=tag_int_median.T_SDM["label"],
    )

    class Config:
        allow_population_by_field_name = True


tag_int_rej = TagSIFIntegralEvalMeanWOoutliers()
class SIFsIntegralMeanwoOutlierResults(BaseModel):
    J: float = Field(
        ...,
        alias=tag_int_rej.J["tag"],
        unit=tag_int_rej.J["unit"],
        ltm=tag_int_rej.J["ltm"],
        label=tag_int_rej.J["label"],
    )
    K_J: float = Field(
        ...,
        alias=tag_int_rej.K_J["tag"],
        unit=tag_int_rej.K_J["unit"],
        ltm=tag_int_rej.K_J["ltm"],
        label=tag_int_rej.K_J["label"],
    )
    K_I_interac: float = Field(
        ...,
        alias=tag_int_rej.K_I_interac["tag"],
        unit=tag_int_rej.K_I_interac["unit"],
        ltm=tag_int_rej.K_I_interac["ltm"],
        label=tag_int_rej.K_I_interac["label"],
    )
    K_II_interac: float = Field(
        ...,
        alias=tag_int_rej.K_II_interac["tag"],
        unit=tag_int_rej.K_II_interac["unit"],
        ltm=tag_int_rej.K_II_interac["ltm"],
        label=tag_int_rej.K_II_interac["label"],
    )
    T_interac: float = Field(
        ...,
        alias=tag_int_rej.T_interac["tag"],
        unit=tag_int_rej.T_interac["unit"],
        ltm=tag_int_rej.T_interac["ltm"],
        label=tag_int_rej.T_interac["label"],
    )
    K_I_Chen: float = Field(
        ...,
        alias=tag_int_rej.K_I_Chen["tag"],
        unit=tag_int_rej.K_I_Chen["unit"],
        ltm=tag_int_rej.K_I_Chen["ltm"],
        label=tag_int_rej.K_I_Chen["label"],
    )
    K_II_Chen: float = Field(
        ...,
        alias=tag_int_rej.K_II_Chen["tag"],
        unit=tag_int_rej.K_II_Chen["unit"],
        ltm=tag_int_rej.K_II_Chen["ltm"],
        label=tag_int_rej.K_II_Chen["label"],
    )
    T_Chen: float = Field(
        ...,
        alias=tag_int_rej.T_Chen["tag"],
        unit=tag_int_rej.T_Chen["unit"],
        ltm=tag_int_rej.T_Chen["ltm"],
        label=tag_int_rej.T_Chen["label"],
    )
    T_SDM: float = Field(
        ...,
        alias=tag_int_rej.T_SDM["tag"],
        unit=tag_int_rej.T_SDM["unit"],
        ltm=tag_int_rej.T_SDM["ltm"],
        label=tag_int_rej.T_SDM["label"],
    )

    class Config:
        allow_population_by_field_name = True


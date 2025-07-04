"""Dataclasses describing fracture analysis results.

Each dataclass mirrors the tag definitions in :mod:`crackpy.structure_elements.tags`
and stores unit and label information in the field metadata for convenient
consumption by plotting and output utilities.
"""

from dataclasses import dataclass, field, make_dataclass

from .tags import (
    TagCJPModel,
    TagWillimasFitting,
    TagSIFIntegralEvalMean,
    TagSIFIntegralEvalMedian,
    TagSIFIntegralEvalMeanWOoutliers,
)


# CJP model results ------------------------------------------------------------

tag_cjp = TagCJPModel()

@dataclass
class CJPResults:
    error: float = field(metadata={"unit": tag_cjp.error["unit"], "label": tag_cjp.error["label"]})
    K_F: float = field(metadata={"unit": tag_cjp.K_F["unit"], "label": tag_cjp.K_F["label"]})
    K_R: float = field(metadata={"unit": tag_cjp.K_R["unit"], "label": tag_cjp.K_R["label"]})
    K_S: float = field(metadata={"unit": tag_cjp.K_S["unit"], "label": tag_cjp.K_S["label"]})
    K_II: float = field(metadata={"unit": tag_cjp.K_II["unit"], "label": tag_cjp.K_II["label"]})
    K_eff_Yang: float = field(metadata={"unit": tag_cjp.K_eff_Yang["unit"], "label": tag_cjp.K_eff_Yang["label"]})
    K_eff_Nowell: float = field(metadata={"unit": tag_cjp.K_eff_Nowell["unit"], "label": tag_cjp.K_eff_Nowell["label"]})
    T: float = field(metadata={"unit": tag_cjp.T["unit"], "label": tag_cjp.T["label"]})


# Williams fitting results -----------------------------------------------------

tag_williams = TagWillimasFitting()

def _create_williams_model(orders=tag_williams.orders):
    fields = [
        ("error", float, field(metadata={"unit": tag_williams.error["unit"], "label": tag_williams.error["label"]})),
        ("K_I", float, field(metadata={"unit": tag_williams.K_I["unit"], "label": tag_williams.K_I["label"]})),
        ("K_II", float, field(metadata={"unit": tag_williams.K_II["unit"], "label": tag_williams.K_II["label"]})),
        ("K_V", float, field(metadata={"unit": tag_williams.K_V["unit"], "label": tag_williams.K_V["label"]})),
        ("T", float, field(metadata={"unit": tag_williams.T["unit"], "label": tag_williams.T["label"]})),
    ]
    for n in orders:
        a = tag_williams.coeff("a", n)
        b = tag_williams.coeff("b", n)
        fields.append((f"a_{n}", float, field(metadata={"unit": a["unit"], "label": a["label"]})))
        fields.append((f"b_{n}", float, field(metadata={"unit": b["unit"], "label": b["label"]})))
    return make_dataclass("WilliamsODMResults", fields)


WilliamsODMResults = _create_williams_model()


# Integral result models -------------------------------------------------------

# Mean values ------------------------------------------------------------------

tag_int_mean = TagSIFIntegralEvalMean()

@dataclass
class SIFsIntegralMeanResults:
    J: float = field(metadata={"unit": tag_int_mean.J["unit"], "label": tag_int_mean.J["label"]})
    K_J: float = field(metadata={"unit": tag_int_mean.K_J["unit"], "label": tag_int_mean.K_J["label"]})
    K_I_interac: float = field(metadata={"unit": tag_int_mean.K_I_interac["unit"], "label": tag_int_mean.K_I_interac["label"]})
    K_II_interac: float = field(metadata={"unit": tag_int_mean.K_II_interac["unit"], "label": tag_int_mean.K_II_interac["label"]})
    T_interac: float = field(metadata={"unit": tag_int_mean.T_interac["unit"], "label": tag_int_mean.T_interac["label"]})
    K_I_Chen: float = field(metadata={"unit": tag_int_mean.K_I_Chen["unit"], "label": tag_int_mean.K_I_Chen["label"]})
    K_II_Chen: float = field(metadata={"unit": tag_int_mean.K_II_Chen["unit"], "label": tag_int_mean.K_II_Chen["label"]})
    T_Chen: float = field(metadata={"unit": tag_int_mean.T_Chen["unit"], "label": tag_int_mean.T_Chen["label"]})
    T_SDM: float = field(metadata={"unit": tag_int_mean.T_SDM["unit"], "label": tag_int_mean.T_SDM["label"]})


# Median values ----------------------------------------------------------------

tag_int_median = TagSIFIntegralEvalMedian()

@dataclass
class SIFsIntegralMedianResults:
    J: float = field(metadata={"unit": tag_int_median.J["unit"], "label": tag_int_median.J["label"]})
    K_J: float = field(metadata={"unit": tag_int_median.K_J["unit"], "label": tag_int_median.K_J["label"]})
    K_I_interac: float = field(metadata={"unit": tag_int_median.K_I_interac["unit"], "label": tag_int_median.K_I_interac["label"]})
    K_II_interac: float = field(metadata={"unit": tag_int_median.K_II_interac["unit"], "label": tag_int_median.K_II_interac["label"]})
    T_interac: float = field(metadata={"unit": tag_int_median.T_interac["unit"], "label": tag_int_median.T_interac["label"]})
    K_I_Chen: float = field(metadata={"unit": tag_int_median.K_I_Chen["unit"], "label": tag_int_median.K_I_Chen["label"]})
    K_II_Chen: float = field(metadata={"unit": tag_int_median.K_II_Chen["unit"], "label": tag_int_median.K_II_Chen["label"]})
    T_Chen: float = field(metadata={"unit": tag_int_median.T_Chen["unit"], "label": tag_int_median.T_Chen["label"]})
    T_SDM: float = field(metadata={"unit": tag_int_median.T_SDM["unit"], "label": tag_int_median.T_SDM["label"]})


# Mean values without outliers -------------------------------------------------

tag_int_rej = TagSIFIntegralEvalMeanWOoutliers()

@dataclass
class SIFsIntegralMeanwoOutlierResults:
    J: float = field(metadata={"unit": tag_int_rej.J["unit"], "label": tag_int_rej.J["label"]})
    K_J: float = field(metadata={"unit": tag_int_rej.K_J["unit"], "label": tag_int_rej.K_J["label"]})
    K_I_interac: float = field(metadata={"unit": tag_int_rej.K_I_interac["unit"], "label": tag_int_rej.K_I_interac["label"]})
    K_II_interac: float = field(metadata={"unit": tag_int_rej.K_II_interac["unit"], "label": tag_int_rej.K_II_interac["label"]})
    T_interac: float = field(metadata={"unit": tag_int_rej.T_interac["unit"], "label": tag_int_rej.T_interac["label"]})
    K_I_Chen: float = field(metadata={"unit": tag_int_rej.K_I_Chen["unit"], "label": tag_int_rej.K_I_Chen["label"]})
    K_II_Chen: float = field(metadata={"unit": tag_int_rej.K_II_Chen["unit"], "label": tag_int_rej.K_II_Chen["label"]})
    T_Chen: float = field(metadata={"unit": tag_int_rej.T_Chen["unit"], "label": tag_int_rej.T_Chen["label"]})
    T_SDM: float = field(metadata={"unit": tag_int_rej.T_SDM["unit"], "label": tag_int_rej.T_SDM["label"]})

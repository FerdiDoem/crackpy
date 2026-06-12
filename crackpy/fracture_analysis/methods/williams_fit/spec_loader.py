"""Load the Williams-fit provenance slice specification."""
from importlib.resources import files

import yaml
from pydantic import BaseModel, ConfigDict, Field

from crackpy.provenance.spec import ProvenanceSliceSpec


class WilliamsCoefficientQuantitySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    quantity_name: str = Field(description="SourceQuantity name used for Williams coefficient values.")
    symbol_template: str = Field(description="Template for canonical Williams coefficient symbols.")
    description_template: str = Field(description="Template for Williams coefficient result descriptions.")
    legacy_alias_template: str = Field(description="Template for current Williams_fit_results coefficient aliases.")
    allowed_qualifiers: tuple[str, ...] = Field(
        default=("coefficient_series", "term_order"),
        description="SourceQuantity qualifier names accepted for Williams coefficient quantities.",
    )
    allowed_coefficient_series: tuple[str, ...] = Field(
        description="Allowed Williams coefficient series labels, currently lower-case a, b, and c.",
    )


class WilliamsFitSliceSpec(ProvenanceSliceSpec):
    model_config = ConfigDict(frozen=True)

    coefficient_quantity: WilliamsCoefficientQuantitySpec = Field(
        description="Williams-specific repeated coefficient quantity definition."
    )


def load_williams_fit_spec() -> WilliamsFitSliceSpec:
    spec_path = files("crackpy.fracture_analysis.methods.williams_fit").joinpath("spec.yaml")
    with spec_path.open(encoding="utf-8") as spec_file:
        payload = yaml.safe_load(spec_file)
    return WilliamsFitSliceSpec.model_validate(payload)

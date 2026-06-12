"""Load the CJP-fit provenance slice specification."""
from __future__ import annotations

from importlib.resources import files

import yaml
from pydantic import ConfigDict, Field, model_validator

from crackpy.provenance.spec import ProvenanceSliceSpec, QuantitySpec

ALLOWED_CJP_VARIANTS = {"mixed_mode", "mode_i"}


class CjpQuantitySpec(QuantitySpec):
    model_config = ConfigDict(frozen=True)

    variant: str = Field(description="CJP variant that owns this quantity: mixed_mode or mode_i.")


class CjpFitSliceSpec(ProvenanceSliceSpec):
    model_config = ConfigDict(frozen=True)

    quantities: dict[str, CjpQuantitySpec] = Field(
        description="Allowed CJP source quantities keyed by variant-scoped quantity name."
    )

    @model_validator(mode="after")
    def require_supported_variants(self) -> CjpFitSliceSpec:
        for quantity_key, quantity_spec in self.quantities.items():
            if quantity_spec.variant not in ALLOWED_CJP_VARIANTS:
                raise ValueError(f"quantities['{quantity_key}'] declares unsupported variant {quantity_spec.variant!r}.")
        return self


def load_cjp_fit_spec() -> CjpFitSliceSpec:
    spec_path = files("crackpy.fracture_analysis.methods.cjp_fit").joinpath("spec.yaml")
    with spec_path.open(encoding="utf-8") as spec_file:
        payload = yaml.safe_load(spec_file)
    return CjpFitSliceSpec.model_validate(payload)

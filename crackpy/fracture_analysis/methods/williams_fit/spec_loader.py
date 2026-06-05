"""Load the Williams-fit provenance slice specification."""
from importlib.resources import files

from crackpy.results.provenance.spec import ProvenanceSliceSpec, load_provenance_slice_spec


def load_williams_fit_spec() -> ProvenanceSliceSpec:
    spec_path = files("crackpy.fracture_analysis.methods.williams_fit").joinpath("spec.yaml")
    return load_provenance_slice_spec(spec_path)

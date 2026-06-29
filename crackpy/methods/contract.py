"""Method-module contract verification helpers.

The verifier checks behavior at a method module's public Interface. It does not
require inheritance and it does not know method-local numerical details; tests
provide fixtures for each method slice.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Callable

from crackpy.provenance import MethodResultSource
from crackpy.provenance.spec import ProvenanceSliceSpec
from crackpy.results.envelope_artifacts import ResultEnvelopeArtifactPaths, write_result_envelope_artifacts
from crackpy.results.result_data import ResultEnvelope, ResultSchemaIndex


@dataclass(frozen=True, slots=True)
class MethodContractFixture:
    """Fixtures needed to verify one method module contract.

    `source_factory` builds a method-local `MethodResultSource` without
    constructing `FractureAnalysis`. `envelope_factory` builds the corresponding
    `ResultEnvelope`. `artifact_stem` and `graph_title` define harmless
    verification artifacts written to a temporary directory.
    """

    source_factory: Callable[[], MethodResultSource]
    envelope_factory: Callable[[], ResultEnvelope]
    artifact_stem: str
    graph_title: str

    def __post_init__(self) -> None:
        if not self.artifact_stem:
            raise ValueError("MethodContractFixture requires a non-empty artifact_stem.")
        if not self.graph_title:
            raise ValueError("MethodContractFixture requires a non-empty graph_title.")


@dataclass(frozen=True, slots=True)
class MethodContractReport:
    """Summary returned after verifying one method module.

    `module_name` identifies the checked method module. `method_ids` records
    stable method identities from the loaded spec. `result_count` records how
    many result records the fixture envelope emitted, which distinguishes
    one-result methods such as Williams-fit from multi-variant methods such as
    CJP. `artifact_paths` proves standard envelope artifacts were writable from
    the produced envelope.
    """

    module_name: str
    method_ids: tuple[str, ...]
    result_count: int
    artifact_paths: ResultEnvelopeArtifactPaths


REQUIRED_METHOD_MODULE_FILES = (
    "__init__.py",
    "spec.yaml",
    "spec_loader.py",
    "parameters.py",
    "result.py",
    "runner.py",
    "source_adapter.py",
    "builder.py",
)

REQUIRED_METHOD_MODULE_EXPORTS = (
    "source_from_result",
)


def verify_method_module_contract(
    module_name: str,
    *,
    fixture: MethodContractFixture,
    artifact_dir: str | Path,
) -> MethodContractReport:
    """Verify a method module against the first Williams/CJP contract slice.

    The verifier checks the public method-module Interface, then walks one
    fixture through source snapshot, envelope construction, schema lookup, and
    standard artifact writing. It intentionally leaves numerical fixture
    construction to method-local tests.
    """
    module = import_module(module_name)
    module_dir = _module_directory(module)
    _verify_required_files(module_dir)
    _verify_required_exports(module)
    spec = _load_spec_from_module(module)
    _verify_spec(spec)

    source = fixture.source_factory()
    if not isinstance(source, MethodResultSource):
        raise TypeError("source_factory must return MethodResultSource.")

    envelope = fixture.envelope_factory()
    if not isinstance(envelope, ResultEnvelope):
        raise TypeError("envelope_factory must return ResultEnvelope.")
    if not envelope.results:
        raise ValueError("Method contract fixture envelope must contain at least one result record.")

    ResultSchemaIndex.from_envelope(envelope)
    artifacts = write_result_envelope_artifacts(
        envelope=envelope,
        path=artifact_dir,
        stem=fixture.artifact_stem,
        graph_title=fixture.graph_title,
    )

    return MethodContractReport(
        module_name=module_name,
        method_ids=tuple(method.method_id for method in spec.methods.values()),
        result_count=len(envelope.results),
        artifact_paths=artifacts,
    )


def _module_directory(module: ModuleType) -> Path:
    if module.__file__ is None:
        raise ValueError(f"Method module {module.__name__!r} has no filesystem file.")
    return Path(module.__file__).parent


def _verify_required_files(module_dir: Path) -> None:
    missing = [name for name in REQUIRED_METHOD_MODULE_FILES if not (module_dir / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Method module is missing required files: {joined}.")


def _verify_required_exports(module: ModuleType) -> None:
    missing = [name for name in REQUIRED_METHOD_MODULE_EXPORTS if not hasattr(module, name)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Method module {module.__name__!r} is missing required exports: {joined}.")


def _load_spec_from_module(module: ModuleType) -> ProvenanceSliceSpec:
    loader_names = [name for name in dir(module) if name.startswith("load_") and name.endswith("_spec")]
    if len(loader_names) != 1:
        raise ValueError(f"Method module {module.__name__!r} must expose exactly one load_*_spec function.")
    spec = getattr(module, loader_names[0])()
    if not isinstance(spec, ProvenanceSliceSpec):
        raise TypeError(f"{loader_names[0]}() must return ProvenanceSliceSpec.")
    return spec


def _verify_spec(spec: ProvenanceSliceSpec) -> None:
    method_ids = [method.method_id for method in spec.methods.values()]
    if len(set(method_ids)) != len(method_ids):
        raise ValueError("Method spec contains duplicate method_id values.")
    aliases = [alias for method in spec.methods.values() for alias in method.aliases]
    if len(set(aliases)) != len(aliases):
        raise ValueError("Method spec contains duplicate method aliases.")
    for method in spec.methods.values():
        for field_name in ("method_id", "display_name", "kind", "method_revision", "implementation_ref"):
            if not getattr(method, field_name):
                raise ValueError(f"Method {method.method_id!r} has empty {field_name}.")
    for quantity in spec.quantities.values():
        for field_name in ("quantity_name", "symbol", "description", "unit"):
            if not getattr(quantity, field_name):
                raise ValueError(f"Quantity {quantity.quantity_name!r} has empty {field_name}.")

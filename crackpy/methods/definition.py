"""Generic method definitions shared by detection and analysis methods."""

from __future__ import annotations

from dataclasses import dataclass

from crackpy.provenance.spec import MethodSpec


@dataclass(frozen=True, slots=True)
class MethodArtifactDefinition:
    """Artifact dependency or output declared by a method definition.

    `artifact_id` names the artifact when it is known, such as `UNetPath.pth`.
    `role` explains why the artifact matters, such as `pretrained_weights` or
    `result_envelope`. `required` tells orchestration or validation whether the
    method can run without the artifact.
    """

    artifact_id: str | None
    role: str
    required: bool = True

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("MethodArtifactDefinition requires a non-empty role.")
        if self.required and not self.artifact_id:
            raise ValueError("Required method artifacts need a non-empty artifact_id.")


@dataclass(frozen=True, slots=True)
class MethodDefinition:
    """Shared importable method definition.

    `method_spec` is the generic method metadata core also used in provenance
    specs. `domain` names the package area that owns the method. `tasks` names
    output or workflow tasks at the method level. `artifacts` records declared
    method assets or output artifact roles without embedding writer policy.
    """

    method_spec: MethodSpec
    domain: str
    tasks: tuple[str, ...]
    artifacts: tuple[MethodArtifactDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("MethodDefinition requires a non-empty domain.")
        if not self.tasks:
            raise ValueError("MethodDefinition requires at least one task.")

    @property
    def method_id(self) -> str:
        """Stable method identity from the wrapped method spec."""
        return self.method_spec.method_id

    @property
    def display_name(self) -> str:
        """Human-facing method label from the wrapped method spec."""
        return self.method_spec.display_name

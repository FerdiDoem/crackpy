"""Method-side metadata for crack detection and crack-tip estimation.

This module names crack-detection methods by their scientific or workflow
output before naming implementation artifacts.  It intentionally does not load
PyTorch networks or resolve files; `model.get_model()` still owns that
compatibility behavior until a separate provider seam is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from crackpy.provenance.spec import MethodSpec

DetectionTask = Literal[
    "crack_tip_localization",
    "crack_path_segmentation",
    "crack_tip_correction",
    "crack_growth_tracking",
]
ImplementationFamily = Literal[
    "neural_network",
    "line_intercept",
    "williams_series_fit",
    "symbolic_regression",
    "grid_search",
    "differential_evolution",
    "image_processing",
    "manual_import",
    "external_provider",
]


@dataclass(frozen=True, slots=True)
class CrackDetectionMethodMetadata:
    """Declared identity and detection-specific vocabulary for one method.

    `method_spec` uses the same generic method metadata shape as Williams-fit
    and CJP-fit provenance specs: stable method ID, display name, kind, method
    revision, implementation reference, aliases, and references.  That keeps
    crack detection from growing a parallel metadata vocabulary.  The remaining
    fields are detection-specific: `detection_task` declares the method output,
    `implementation_family` names the algorithm family, and
    `network_architecture` / `weights_artifact_id` are only present when a
    pretrained neural-network artifact affects the implementation.
    """

    method_spec: MethodSpec
    detection_task: DetectionTask
    implementation_family: ImplementationFamily
    network_architecture: str | None = None
    weights_artifact_id: str | None = None

    def __post_init__(self) -> None:
        if not self.method_spec.aliases:
            raise ValueError("method_spec.aliases must contain at least one current selector or compatibility alias.")
        if self.weights_artifact_id and not self.network_architecture:
            raise ValueError("weights_artifact_id requires a network_architecture.")

    @property
    def method_id(self) -> str:
        """Stable method identity shared with Williams/CJP provenance records."""
        return self.method_spec.method_id

    @property
    def display_name(self) -> str:
        """Human-facing method label shared with generic method metadata."""
        return self.method_spec.display_name

    @property
    def method_revision(self) -> str:
        """Maintainer-declared revision of method semantics."""
        return self.method_spec.method_revision

    @property
    def implementation_ref(self) -> str:
        """Current implementation reference used for maintainability and traceability."""
        return self.method_spec.implementation_ref

    @property
    def compatibility_selectors(self) -> tuple[str, ...]:
        """Current public selectors and aliases resolving to this method."""
        return self.method_spec.aliases


KNOWN_CRACK_DETECTION_METHODS: tuple[CrackDetectionMethodMetadata, ...] = (
    CrackDetectionMethodMetadata(
        method_spec=MethodSpec(
            method_id="crackpy.detection.parallel_nets_crack_tip_localization",
            display_name="ParallelNets Crack-Tip Localization",
            kind="crack_tip_estimate",
            method_revision="1",
            implementation_ref="crackpy.crack_detection.deep_learning.nets.ParallelNets",
            aliases=("ParallelNets",),
            references=(),
        ),
        detection_task="crack_tip_localization",
        implementation_family="neural_network",
        network_architecture="ParallelNets",
        weights_artifact_id="ParallelNets.pth",
    ),
    CrackDetectionMethodMetadata(
        method_spec=MethodSpec(
            method_id="crackpy.detection.unet_crack_path_segmentation",
            display_name="UNet Crack-Path Segmentation",
            kind="crack_path_segmentation",
            method_revision="1",
            implementation_ref="crackpy.crack_detection.deep_learning.nets.UNet",
            aliases=("UNetPath",),
            references=(),
        ),
        detection_task="crack_path_segmentation",
        implementation_family="neural_network",
        network_architecture="UNet",
        weights_artifact_id="UNetPath.pth",
    ),
    CrackDetectionMethodMetadata(
        method_spec=MethodSpec(
            method_id="crackpy.detection.line_intercept_crack_tip_localization",
            display_name="Line-Intercept Crack-Tip Localization",
            kind="crack_tip_estimate",
            method_revision="1",
            implementation_ref="crackpy.crack_detection.line_intercept.CrackDetectionLineIntercept",
            aliases=("line_intercept", "CrackDetectionLineIntercept"),
            references=(),
        ),
        detection_task="crack_tip_localization",
        implementation_family="line_intercept",
    ),
)


_METHODS_BY_ID = {metadata.method_id: metadata for metadata in KNOWN_CRACK_DETECTION_METHODS}
_METHODS_BY_SELECTOR = {
    selector: metadata
    for metadata in KNOWN_CRACK_DETECTION_METHODS
    for selector in metadata.compatibility_selectors
}


def known_crack_detection_methods() -> tuple[CrackDetectionMethodMetadata, ...]:
    """Return the registered crack-detection method metadata in declaration order."""
    return KNOWN_CRACK_DETECTION_METHODS


def method_metadata_for_id(method_id: str) -> CrackDetectionMethodMetadata:
    """Return metadata for a stable crack-detection `method_id`.

    Raises:
        ValueError: If the method ID is not registered in the current metadata
            slice.
    """
    try:
        return _METHODS_BY_ID[method_id]
    except KeyError as exc:
        supported_ids = ", ".join(sorted(_METHODS_BY_ID))
        raise ValueError(f"Unknown crack-detection method_id {method_id!r}. Supported IDs: {supported_ids}") from exc


def method_metadata_for_compatibility_selector(selector: str) -> CrackDetectionMethodMetadata:
    """Return metadata for a current public selector or compatibility alias.

    This lookup keeps legacy names such as `ParallelNets` and `UNetPath`
    available while allowing newer code to talk about method identity, task,
    implementation family, network architecture, and weights artifact
    separately.

    Raises:
        ValueError: If the selector is unknown.
    """
    try:
        return _METHODS_BY_SELECTOR[selector]
    except KeyError as exc:
        supported_selectors = ", ".join(sorted(_METHODS_BY_SELECTOR))
        raise ValueError(
            f"Unknown crack-detection compatibility selector {selector!r}. "
            f"Supported selectors: {supported_selectors}"
        ) from exc


__all__ = [
    "CrackDetectionMethodMetadata",
    "DetectionTask",
    "ImplementationFamily",
    "KNOWN_CRACK_DETECTION_METHODS",
    "known_crack_detection_methods",
    "method_metadata_for_compatibility_selector",
    "method_metadata_for_id",
]

import pytest

from crackpy.crack_detection.method_metadata import (
    CrackDetectionMethodMetadata,
    known_crack_detection_method_definitions,
    known_crack_detection_methods,
    method_metadata_for_compatibility_selector,
    method_metadata_for_id,
)
from crackpy.provenance.spec import MethodSpec


def test_parallel_nets_selector_resolves_to_crack_tip_localization_method():
    metadata = method_metadata_for_compatibility_selector("ParallelNets")

    assert metadata.method_id == "crackpy.detection.parallel_nets_crack_tip_localization"
    assert metadata.method_spec.kind == "crack_tip_estimate"
    assert metadata.detection_task == "crack_tip_localization"
    assert metadata.implementation_family == "neural_network"
    assert metadata.network_architecture == "ParallelNets"
    assert metadata.weights_artifact_id == "ParallelNets.pth"


def test_unet_path_selector_resolves_to_path_segmentation_method():
    metadata = method_metadata_for_compatibility_selector("UNetPath")

    assert metadata.method_id == "crackpy.detection.unet_crack_path_segmentation"
    assert metadata.method_spec.kind == "crack_path_segmentation"
    assert metadata.detection_task == "crack_path_segmentation"
    assert metadata.implementation_family == "neural_network"
    assert metadata.network_architecture == "UNet"
    assert metadata.weights_artifact_id == "UNetPath.pth"


def test_line_intercept_metadata_is_not_forced_into_network_vocabulary():
    metadata = method_metadata_for_compatibility_selector("CrackDetectionLineIntercept")

    assert metadata.method_id == "crackpy.detection.line_intercept_crack_tip_localization"
    assert metadata.detection_task == "crack_tip_localization"
    assert metadata.implementation_family == "line_intercept"
    assert metadata.network_architecture is None
    assert metadata.weights_artifact_id is None


def test_stable_method_id_lookup_returns_declared_metadata():
    metadata = method_metadata_for_id("crackpy.detection.unet_crack_path_segmentation")

    assert metadata.display_name == "UNet Crack-Path Segmentation"
    assert "UNetPath" in metadata.compatibility_selectors


def test_registered_methods_have_unique_ids_and_compatibility_selectors():
    methods = known_crack_detection_methods()

    assert len({metadata.method_id for metadata in methods}) == len(methods)
    selectors = [
        selector
        for metadata in methods
        for selector in metadata.compatibility_selectors
    ]
    assert len(set(selectors)) == len(selectors)


def test_unknown_compatibility_selector_reports_supported_terms():
    with pytest.raises(ValueError, match="Supported selectors: .*ParallelNets.*UNetPath"):
        method_metadata_for_compatibility_selector("model")


def test_weights_artifact_requires_network_architecture():
    with pytest.raises(ValueError, match="weights_artifact_id requires a network_architecture"):
        CrackDetectionMethodMetadata(
            method_spec=MethodSpec(
                method_id="crackpy.detection.invalid",
                display_name="Invalid method",
                kind="crack_tip_estimate",
                method_revision="1",
                implementation_ref="crackpy.invalid",
                aliases=("invalid",),
            ),
            detection_task="crack_tip_localization",
            implementation_family="neural_network",
            weights_artifact_id="weights.pth",
        )


def test_detection_metadata_uses_generic_method_spec_shape():
    metadata = method_metadata_for_compatibility_selector("ParallelNets")

    assert isinstance(metadata.method_spec, MethodSpec)
    assert metadata.method_spec.aliases == metadata.compatibility_selectors
    assert metadata.method_spec.implementation_ref == metadata.implementation_ref


def test_detection_metadata_exports_generic_method_definitions():
    definitions = known_crack_detection_method_definitions()

    by_id = {definition.method_id: definition for definition in definitions}
    parallel_nets = by_id["crackpy.detection.parallel_nets_crack_tip_localization"]
    line_intercept = by_id["crackpy.detection.line_intercept_crack_tip_localization"]

    assert parallel_nets.domain == "crack_detection"
    assert parallel_nets.tasks == ("crack_tip_localization",)
    assert parallel_nets.artifacts[0].artifact_id == "ParallelNets.pth"
    assert parallel_nets.artifacts[0].role == "pretrained_weights"
    assert line_intercept.artifacts == ()

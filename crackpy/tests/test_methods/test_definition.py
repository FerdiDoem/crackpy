import pytest

from crackpy.crack_detection.method_metadata import known_crack_detection_methods
from crackpy.fracture_analysis.methods.cjp_fit.spec_loader import load_cjp_fit_spec
from crackpy.fracture_analysis.methods.williams_fit.spec_loader import load_williams_fit_spec
from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition
from crackpy.methods.runtime import MethodRunIdentityPolicy, build_manual_crack_tip_estimate
from crackpy.provenance.spec import MethodSpec
from crackpy.results.result_data import CrackTipFrame


def _current_method_specs() -> list[MethodSpec]:
    detection_specs = [method.method_spec for method in known_crack_detection_methods()]
    williams_specs = list(load_williams_fit_spec().methods.values())
    cjp_specs = list(load_cjp_fit_spec().methods.values())
    return detection_specs + williams_specs + cjp_specs


def test_detection_williams_and_cjp_expose_method_spec_records():
    all_specs = _current_method_specs()

    assert all(isinstance(method_spec, MethodSpec) for method_spec in all_specs)
    assert all(method_spec.method_id for method_spec in all_specs)
    assert all(method_spec.display_name for method_spec in all_specs)
    assert all(method_spec.kind for method_spec in all_specs)
    assert all(method_spec.method_revision for method_spec in all_specs)
    assert all(method_spec.implementation_ref for method_spec in all_specs)


def test_repeated_method_ids_have_identical_specs_across_current_slices():
    specs_by_id: dict[str, MethodSpec] = {}

    for method_spec in _current_method_specs():
        existing_spec = specs_by_id.get(method_spec.method_id)
        if existing_spec is None:
            specs_by_id[method_spec.method_id] = method_spec
        else:
            assert method_spec == existing_spec


def test_method_definition_wraps_generic_method_spec_with_domain_tasks():
    detection_method = known_crack_detection_methods()[0]

    definition = MethodDefinition(
        method_spec=detection_method.method_spec,
        domain="crack_detection",
        tasks=(detection_method.detection_task,),
        artifacts=(
            MethodArtifactDefinition(
                artifact_id=detection_method.weights_artifact_id,
                role="pretrained_weights",
                required=True,
            ),
        ),
    )

    assert definition.method_id == detection_method.method_id
    assert definition.display_name == detection_method.display_name
    assert definition.domain == "crack_detection"
    assert definition.tasks == ("crack_tip_localization",)
    assert definition.artifacts[0].role == "pretrained_weights"


def test_method_definition_rejects_empty_tasks():
    detection_method = known_crack_detection_methods()[0]

    with pytest.raises(ValueError, match="at least one task"):
        MethodDefinition(
            method_spec=detection_method.method_spec,
            domain="crack_detection",
            tasks=(),
        )


def test_required_method_artifact_requires_artifact_id():
    with pytest.raises(ValueError, match="artifact_id"):
        MethodArtifactDefinition(artifact_id=None, role="pretrained_weights", required=True)


def test_method_run_identity_policy_derives_ids_from_parameter_hash():
    policy = MethodRunIdentityPolicy(method_key="williams_fit")

    assert policy.short_hash("sha256:abcdef1234567890") == "abcdef123456"
    assert policy.configuration_id("sha256:abcdef1234567890") == "configuration:williams_fit:abcdef123456"
    assert policy.run_id(stem="Dummy2", side="right", short_hash="abcdef123456") == (
        "run:williams_fit:Dummy2:right:abcdef123456"
    )
    assert policy.result_id(stem="Dummy2", side="right", short_hash="abcdef123456") == (
        "result:williams_fit:Dummy2:right:abcdef123456"
    )


def test_method_run_identity_policy_supports_variant_ids():
    policy = MethodRunIdentityPolicy(method_key="cjp_fit")

    assert policy.run_id(stem="Dummy2", side="right", short_hash="abcdef123456", variant="mode_i") == (
        "run:cjp_fit:mode_i:Dummy2:right:abcdef123456"
    )
    assert policy.result_id(stem="Dummy2", side="right", short_hash="abcdef123456", variant="mode_i") == (
        "result:cjp_fit:mode_i:Dummy2:right:abcdef123456"
    )


def test_method_run_identity_policy_rejects_empty_parts():
    policy = MethodRunIdentityPolicy(method_key="williams_fit")

    with pytest.raises(ValueError, match="stem"):
        policy.run_id(stem="", side="right", short_hash="abcdef123456")
    with pytest.raises(ValueError, match="method_key"):
        MethodRunIdentityPolicy(method_key="")


def test_manual_crack_tip_estimate_projection_is_shared():
    frame = CrackTipFrame.from_legacy_side(
        stem="Dummy2",
        side="right",
        origin_mm={"x": 1.0, "y": 2.0},
        angle_deg=0.0,
    )

    estimate = build_manual_crack_tip_estimate(
        stem="Dummy2",
        side="right",
        input_id="input:Dummy2",
        method_id="crackpy.crack_tip.manual_import",
        configuration_id="configuration:williams_fit:abcdef123456",
        frame=frame,
    )

    assert estimate.estimate_id == "crack_tip_estimate:Dummy2:right"
    assert estimate.input_id == "input:Dummy2"
    assert estimate.frame_id == frame.frame_id
    assert estimate.observed_mm == {"x": 1.0, "y": 2.0}
    assert estimate.corrected_mm == {"x": 1.0, "y": 2.0}
    assert estimate.correction_delta_mm == {"x": 0.0, "y": 0.0}

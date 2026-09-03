"""Behavioral tests for the CTD P2 evidence and replay layer."""

from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import math

import pytest

from crackpy.benchmarking.ctd_decoders import DecoderConfig, DecoderOutput
from crackpy.benchmarking.ctd_p2 import (
    DicFieldQuality,
    EvaluatedFrame,
    P2_RAW_SIGNAL_SEMANTICS,
    P2RunConfig,
    SyntheticReplayResult,
    WilliamsMode,
    WilliamsOutcome,
    WilliamsPolicy,
    WilliamsSolverResult,
    adapt_decoder_output,
    aggregate_sequence_metrics,
    build_evidence_manifest,
    clopper_pearson_upper,
    evaluate_selective_williams,
    load_p1_signals,
    run_p2_benchmark,
    run_synthetic_replays,
    same_scenario_baseline_sha256,
)
from crackpy.crack_detection.adaptive_roi import (
    AdaptiveRoiController,
    GateConfig,
    LegacySideAdapter,
    PhysicalBounds,
    PhysicalRoi,
    P2Variant,
    RoiAttempt,
    RoiState,
)


def _p1_artifact() -> dict[str, object]:
    selected = DecoderConfig.historical().to_dict()
    confidence_gated = dict(selected)
    confidence_gated["uncertainty_threshold"] = 0.21
    return {
        "stage": "P1",
        "schema_version": "ctd-p1-v1",
        "scope": {
            "full_split": True,
            "limit_per_split": None,
        },
        "metadata": {
            "artifact_sha256": {
                "ParallelNets": "a" * 64,
                "UNetPath": "b" * 64,
            },
        },
        "provenance_verification": {"all_checks_passed": True},
        "resolutions": {
            "trained_256": {
                "resolution_mode": "trained-256",
                "decoder_frozen_before_test": True,
                "test_recalibration_performed": False,
                "calibration": {
                    "source_split": "validation",
                    "test_split_used_for_selection": False,
                    "selected_config": selected,
                    "confidence_gated_config": confidence_gated,
                    "risk_coverage": {
                        "selected_uncertainty_threshold": 0.21,
                    },
                },
                "confidence_policy": {
                    "threshold_source": "validation_only",
                    "test_recalibration_performed": False,
                    "hard_rejection_is_default": False,
                },
                "frozen_test_metrics": {"detection_rate": 0.99},
            },
            "native_128": {"must_not_be_read": object()},
        },
    }


def _same_scenario_baseline(
    frame_ids: list[str],
    *,
    reference_source: str = "fixture reference",
) -> dict[str, object]:
    baseline: dict[str, object] = {
        "scenario": "same_frames_fixed_physical_roi",
        "decoder": "frozen_p1_ungated",
        "decoder_config": DecoderConfig.historical().to_dict(),
        "pixels": 256,
        "model_artifact_sha256": "a" * 64,
        "p1_source_sha256": None,
        "roi": {
            "center_xy_mm": [35.0, 0.0],
            "extent_xy_mm": [70.0, 70.0],
            "bounds_mm": [0.0, 70.0, -35.0, 35.0],
            "search_bounds_mm": [0.0, 70.0, -35.0, 35.0],
        },
        "frames_evaluated": len(frame_ids),
        "failures": 0,
        "failure_rate": 0.0,
        "localization_error_mm": {
            "count": len(frame_ids),
            "median": 0.0,
            "p95": 0.0,
            "maximum": 0.0,
        },
        "frames": [
            {
                "frame_id": frame_id,
                "success": True,
                "candidate_tip_xy_mm": [20.0, 0.0],
                "reference_tip_xy_mm": [20.0, 0.0],
                "reference_role": "evaluation_only",
                "reference_source": reference_source,
                "error_mm": 0.0,
                "decoder_invalid_reason": None,
            }
            for frame_id in frame_ids
        ],
    }
    baseline["baseline_content_sha256"] = same_scenario_baseline_sha256(baseline)
    return baseline


def test_p1_loader_freezes_only_ungated_trained_256_signals() -> None:
    artifact = _p1_artifact()

    contract = load_p1_signals(artifact)

    assert contract.resolution_mode == "trained-256"
    assert contract.decoder_config.uncertainty_threshold is None
    assert contract.confidence_threshold == pytest.approx(0.21)
    assert contract.calibration_split == "validation"
    assert contract.test_recalibration_performed is False
    assert contract.crackmnist_test_failure_rate_context == pytest.approx(0.01)
    assert contract.source_verification_status == "in_memory_unverified_test_only"
    assert contract.source_artifact_sha256 is None
    assert contract.production_eligible is False


def test_p1_loader_reads_the_same_contract_from_json_path(tmp_path) -> None:
    artifact = _p1_artifact()
    artifact["resolutions"]["native_128"] = {}
    path = tmp_path / "p1.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    contract = load_p1_signals(path)

    assert contract.decoder_config == DecoderConfig.historical()
    assert contract.confidence_threshold == pytest.approx(0.21)
    assert contract.source_verification_status == "file_sha256_verified"
    assert contract.source_path == str(path.resolve())
    assert contract.source_artifact_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert contract.production_eligible is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["resolutions"]["trained_256"]["calibration"].__setitem__(
                "source_split", "test"
            ),
            "validation",
        ),
        (
            lambda payload: payload["resolutions"]["trained_256"].__setitem__(
                "test_recalibration_performed", True
            ),
            "recalibration",
        ),
        (
            lambda payload: payload["resolutions"]["trained_256"]["calibration"][
                "selected_config"
            ].__setitem__("uncertainty_threshold", 0.21),
            "ungated",
        ),
        (
            lambda payload: payload["resolutions"]["trained_256"]["confidence_policy"].__setitem__(
                "threshold_source", "test"
            ),
            "validation",
        ),
        (
            lambda payload: payload.__setitem__("schema_version", 1),
            "ctd-p1-v1",
        ),
        (
            lambda payload: payload["scope"].__setitem__("full_split", False),
            "full split",
        ),
        (
            lambda payload: payload["scope"].__setitem__("limit_per_split", 10),
            "smoke",
        ),
        (
            lambda payload: payload["provenance_verification"].__setitem__(
                "all_checks_passed", False
            ),
            "provenance",
        ),
    ],
)
def test_p1_loader_rejects_leakage_and_gated_default(mutation, message: str) -> None:
    artifact = copy.deepcopy(_p1_artifact())
    mutation(artifact)

    with pytest.raises(ValueError, match=message):
        load_p1_signals(artifact)


def _roi() -> PhysicalRoi:
    return PhysicalRoi(
        center_x_mm=0.0,
        center_y_mm=0.0,
        extent_x_mm=10.0,
        extent_y_mm=10.0,
        search_bounds=PhysicalBounds(-20.0, 20.0, -20.0, 20.0),
    )


def _right_tracking_roi() -> PhysicalRoi:
    return PhysicalRoi.from_bounds(
        PhysicalBounds(0.0, 40.0, -20.0, 20.0),
        search_bounds=PhysicalBounds(0.0, 70.0, -35.0, 35.0),
    )


def _attempt(roi: PhysicalRoi | None = None) -> RoiAttempt:
    return RoiAttempt(
        frame_id="frame-1",
        attempt_id=0,
        state=RoiState.START,
        roi=_roi() if roi is None else roi,
        cycle_count=12.0,
        cycle_delta_from_last_accepted=2.0,
    )


def _decoder_output() -> DecoderOutput:
    return DecoderOutput(
        point_rc=None,
        ungated_point_rc=(127.5, 255.0),
        mask_point_rc=(127.5, 255.0),
        coordinate_point_rc=(127.5, 245.0),
        mask_confidence=0.83,
        selected_region_score=22.5,
        selected_region_area=6554,
        disagreement_px=10.0,
        uncertainty=0.22,
        invalid_reason="uncertainty_threshold_exceeded",
    )


@pytest.mark.parametrize(("side", "expected_x"), [("right", 5.0), ("left", -5.0)])
def test_decoder_adapter_uses_ungated_tip_and_absolute_legacy_geometry(
    side: str,
    expected_x: float,
) -> None:
    attempt = _attempt()

    observation = adapt_decoder_output(
        _decoder_output(),
        decoder_config=DecoderConfig.historical(),
        attempt=attempt,
        side_adapter=LegacySideAdapter(side),
        resolution_px=256,
        dic_quality=DicFieldQuality(
            finite_grid_fraction=0.997,
            ux_std_mm=0.04,
            uy_std_mm=0.03,
        ),
        elapsed_seconds=0.012,
    )

    assert observation.candidate_tip_xy_mm == pytest.approx((expected_x, 0.0))
    assert observation.mask_area_fraction == pytest.approx(6554 / (256 * 256))
    assert observation.head_disagreement_fraction == pytest.approx(
        10.0 / math.hypot(255.0, 255.0)
    )
    assert observation.head_disagreement_mm == pytest.approx(10.0 * 10.0 / 255.0)
    assert observation.mask_mean_score == pytest.approx(0.83)
    assert observation.region_selection_score == pytest.approx(22.5)
    assert observation.decoder_uncertainty == pytest.approx(0.22)
    assert observation.cycle_delta_from_last_accepted == pytest.approx(2.0)
    assert observation.decoder_invalid_reason == "uncertainty_threshold_exceeded"


def test_decoder_adapter_preserves_nonfinite_evidence_for_the_gate() -> None:
    output = DecoderOutput(
        point_rc=(float("nan"), 1.0),
        ungated_point_rc=(float("nan"), 1.0),
        mask_point_rc=(float("nan"), 1.0),
        coordinate_point_rc=(1.0, 1.0),
        mask_confidence=0.8,
        selected_region_score=0.8,
        selected_region_area=1,
        disagreement_px=float("nan"),
        uncertainty=float("nan"),
        invalid_reason="nonfinite_decoder_output",
    )

    observation = adapt_decoder_output(
        output,
        decoder_config=DecoderConfig.historical(),
        attempt=_attempt(),
        side_adapter=LegacySideAdapter("right"),
        resolution_px=(256, 256),
        dic_quality=DicFieldQuality(
            finite_grid_fraction=float("nan"),
            ux_std_mm=0.0,
            uy_std_mm=0.0,
        ),
        elapsed_seconds=0.0,
    )

    assert observation.candidate_tip_xy_mm is not None
    assert math.isnan(observation.candidate_tip_xy_mm[0])
    assert math.isnan(observation.finite_grid_fraction)
    assert observation.channel_std_mm == (0.0, 0.0)


def test_decoder_adapter_applies_frozen_fusion_after_physical_mapping() -> None:
    config_payload = DecoderConfig.historical().to_dict()
    config_payload["fusion_weight"] = 0.5
    config_payload["region_rule"] = "mean_probability"
    config_payload["coordinate_convention"] = "model_index"
    config = DecoderConfig.from_dict(config_payload)
    output = DecoderOutput(
        point_rc=(127.5, 191.25),
        ungated_point_rc=(127.5, 191.25),
        mask_point_rc=(127.5, 127.5),
        coordinate_point_rc=(127.5, 255.0),
        mask_confidence=0.8,
        selected_region_score=0.8,
        selected_region_area=200,
        disagreement_px=127.5,
        uncertainty=0.2,
        invalid_reason=None,
    )

    observation = adapt_decoder_output(
        output,
        decoder_config=config,
        attempt=_attempt(),
        side_adapter=LegacySideAdapter("right"),
        resolution_px=256,
        dic_quality=DicFieldQuality(1.0, 0.02, 0.02),
        elapsed_seconds=0.01,
    )

    assert observation.mask_tip_xy_mm == pytest.approx((0.0, 0.0))
    assert observation.coordinate_tip_xy_mm == pytest.approx((5.0, 0.0))
    assert observation.candidate_tip_xy_mm == pytest.approx((2.5, 0.0))
    assert observation.head_disagreement_mm == pytest.approx(5.0)
    assert observation.head_disagreement_fraction == pytest.approx(5.0 / math.sqrt(200.0))


def test_raw_signal_vocabulary_does_not_claim_probability_calibration() -> None:
    assert P2_RAW_SIGNAL_SEMANTICS["mask_mean_score"]["source"] == (
        "DecoderOutput.mask_confidence"
    )
    assert "not a calibrated probability" in (
        P2_RAW_SIGNAL_SEMANTICS["mask_mean_score"]["meaning"]
    )
    assert P2_RAW_SIGNAL_SEMANTICS["mask_area_fraction"]["normalization"] == (
        "selected_region_area / (rows * columns)"
    )
    assert P2_RAW_SIGNAL_SEMANTICS["head_disagreement_fraction"]["normalization"] == (
        "physical head distance / applied ROI physical diagonal"
    )


def _gate_config() -> GateConfig:
    return GateConfig(
        min_mask_mean_score=0.5,
        min_region_selection_score=None,
        min_mask_area_fraction=0.001,
        max_mask_area_fraction=0.3,
        max_head_disagreement_fraction=0.05,
        max_decoder_uncertainty=0.4,
        mask_score_marginal_band=0.1,
        head_disagreement_marginal_band=0.2,
        decoder_uncertainty_marginal_band=0.1,
        min_tip_roi_margin_mm=0.2,
        min_tip_search_margin_mm=0.1,
        min_finite_grid_fraction=0.99,
        min_channel_std_mm=0.001,
        jump_noise_mm=0.1,
        max_growth_mm_per_cycle=0.5,
        max_jump_without_cycles_mm=2.0,
        max_jump_cap_mm=3.0,
        calibration_source="unit-test validation policy",
    )


def _output_for_absolute_points(
    *,
    attempt: RoiAttempt,
    candidate_xy_mm: tuple[float, float],
    coordinate_xy_mm: tuple[float, float] | None = None,
    uncertainty: float = 0.1,
) -> DecoderOutput:
    adapter = LegacySideAdapter("right")
    candidate_rc = adapter.point_xy_to_rc(candidate_xy_mm, attempt.roi, resolution_px=256)
    coordinate = candidate_xy_mm if coordinate_xy_mm is None else coordinate_xy_mm
    coordinate_rc = adapter.point_xy_to_rc(coordinate, attempt.roi, resolution_px=256)
    disagreement = math.dist(candidate_rc, coordinate_rc)
    return DecoderOutput(
        point_rc=candidate_rc,
        ungated_point_rc=candidate_rc,
        mask_point_rc=candidate_rc,
        coordinate_point_rc=coordinate_rc,
        mask_confidence=0.8,
        selected_region_score=0.8,
        selected_region_area=400,
        disagreement_px=disagreement,
        uncertainty=uncertainty,
        invalid_reason=None,
    )


def _observation_for_output(attempt: RoiAttempt, output: DecoderOutput):
    return adapt_decoder_output(
        output,
        decoder_config=DecoderConfig.historical(),
        attempt=attempt,
        side_adapter=LegacySideAdapter("right"),
        resolution_px=256,
        dic_quality=DicFieldQuality(1.0, 0.02, 0.02),
        elapsed_seconds=0.01,
    )


def _eligible_lost_frame(*, frame_id: str = "marginal"):
    controller = AdaptiveRoiController(
        start_roi=_roi(),
        gate_config=_gate_config(),
        variant=P2Variant.P2_2_EXPANDED_FULL_SEARCH,
        expanded_scale=2.0,
    )
    accepted_attempt = controller.begin_frame("anchor", cycle_count=10.0)
    accepted = controller.submit(
        _observation_for_output(
            accepted_attempt,
            _output_for_absolute_points(
                attempt=accepted_attempt,
                candidate_xy_mm=(0.0, 0.0),
            ),
        )
    )
    assert accepted.completed

    attempt = controller.begin_frame(frame_id, cycle_count=11.0)
    while True:
        output = _output_for_absolute_points(
            attempt=attempt,
            candidate_xy_mm=(0.5, 0.0),
            coordinate_xy_mm=(4.5, 0.0),
        )
        step = controller.submit(_observation_for_output(attempt, output))
        if step.completed:
            assert step.frame_result is not None
            return step.frame_result
        assert step.next_attempt is not None
        attempt = step.next_attempt


def _successful_williams() -> WilliamsSolverResult:
    return WilliamsSolverResult(
        converged=True,
        iterations=4,
        residual_before=0.5,
        residual_after=0.1,
        correction_delta_xy_mm=(0.1, 0.0),
        corrected_tip_xy_mm=(0.6, 0.0),
        elapsed_seconds=0.03,
        failure_reason=None,
    )


def test_williams_default_is_diagnostic_after_complete_roi_cascade() -> None:
    frame = _eligible_lost_frame()
    calls = []

    decision = evaluate_selective_williams(
        frame,
        gate_config=_gate_config(),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: calls.append(observation) or _successful_williams(),
    )

    assert [item.attempt_id for item in calls] == [frame.williams_eligible_attempt_ids[-1]]
    assert calls[0].attempt_id == frame.attempts[-1].attempt.attempt_id
    assert decision.outcome is WilliamsOutcome.DIAGNOSTIC_ONLY
    assert decision.called is True
    assert decision.adopted is False
    assert decision.safety_recheck is not None
    assert decision.safety_recheck.field_ok is True
    assert decision.safety_recheck.geometry_ok is True


def test_williams_off_policy_never_calls_solver() -> None:
    frame = _eligible_lost_frame()

    decision = evaluate_selective_williams(
        frame,
        gate_config=_gate_config(),
        policy=WilliamsPolicy(mode=WilliamsMode.OFF),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: pytest.fail("disabled Williams solver was called"),
    )

    assert decision.outcome is WilliamsOutcome.DISABLED
    assert decision.called is False


def test_williams_missing_solver_is_unevaluable_not_rejected() -> None:
    decision = evaluate_selective_williams(
        _eligible_lost_frame(),
        gate_config=_gate_config(),
        policy=WilliamsPolicy(mode=WilliamsMode.DIAGNOSTIC),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=None,
    )

    assert decision.outcome is WilliamsOutcome.UNEVALUABLE
    assert decision.called is False
    assert decision.rejection_reasons == ("solver_not_provided",)


def test_williams_selective_policy_adopts_only_after_all_safety_checks() -> None:
    decision = evaluate_selective_williams(
        _eligible_lost_frame(),
        gate_config=_gate_config(),
        policy=WilliamsPolicy(mode=WilliamsMode.SELECTIVE, max_correction_mm=0.5),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: _successful_williams(),
    )

    assert decision.outcome is WilliamsOutcome.ADOPTED
    assert decision.adopted is True
    assert decision.final_tip_xy_mm == pytest.approx((0.6, 0.0))
    assert decision.rejection_reasons == ()


@pytest.mark.parametrize(
    ("solver_result", "reason"),
    [
        (
            WilliamsSolverResult(
                converged=False,
                iterations=8,
                residual_before=0.5,
                residual_after=0.1,
                correction_delta_xy_mm=(0.1, 0.0),
                corrected_tip_xy_mm=(0.6, 0.0),
                elapsed_seconds=0.03,
                failure_reason="no_convergence",
            ),
            "not_converged",
        ),
        (
            WilliamsSolverResult(
                converged=True,
                iterations=4,
                residual_before=0.5,
                residual_after=0.6,
                correction_delta_xy_mm=(0.1, 0.0),
                corrected_tip_xy_mm=(0.6, 0.0),
                elapsed_seconds=0.03,
                failure_reason=None,
            ),
            "residual_not_reduced",
        ),
        (
            WilliamsSolverResult(
                converged=True,
                iterations=4,
                residual_before=0.5,
                residual_after=0.1,
                correction_delta_xy_mm=(4.0, 0.0),
                corrected_tip_xy_mm=(4.5, 0.0),
                elapsed_seconds=0.03,
                failure_reason=None,
            ),
            "correction_too_large",
        ),
        (
            WilliamsSolverResult(
                converged=True,
                iterations=4,
                residual_before=0.5,
                residual_after=0.1,
                correction_delta_xy_mm=(0.1, 0.0),
                corrected_tip_xy_mm=(19.95, 0.0),
                elapsed_seconds=0.03,
                failure_reason=None,
            ),
            "correction_delta_inconsistent",
        ),
    ],
)
def test_williams_rejects_unsafe_or_unimproved_solver_results(
    solver_result: WilliamsSolverResult,
    reason: str,
) -> None:
    decision = evaluate_selective_williams(
        _eligible_lost_frame(),
        gate_config=_gate_config(),
        policy=WilliamsPolicy(mode=WilliamsMode.SELECTIVE, max_correction_mm=0.5),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: solver_result,
    )

    assert decision.outcome is WilliamsOutcome.REJECTED
    assert decision.adopted is False
    assert reason in decision.rejection_reasons


def test_williams_rechecks_jump_margin_and_search_bounds_on_corrected_tip() -> None:
    result = WilliamsSolverResult(
        converged=True,
        iterations=4,
        residual_before=0.5,
        residual_after=0.1,
        correction_delta_xy_mm=(19.45, 0.0),
        corrected_tip_xy_mm=(19.95, 0.0),
        elapsed_seconds=0.03,
        failure_reason=None,
    )

    decision = evaluate_selective_williams(
        _eligible_lost_frame(),
        gate_config=_gate_config(),
        policy=WilliamsPolicy(mode=WilliamsMode.SELECTIVE, max_correction_mm=20.0),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: result,
    )

    assert decision.outcome is WilliamsOutcome.REJECTED
    assert "geometry_recheck_failed" in decision.rejection_reasons
    assert decision.safety_recheck is not None
    assert {reason.value for reason in decision.safety_recheck.reasons} >= {
        "tip_near_search_boundary",
        "tip_jump_too_large",
    }


def _accepted_frame(
    *,
    frame_id: str,
    point_xy_mm: tuple[float, float],
    uncertainty: float,
    variant: P2Variant = P2Variant.P2_2_EXPANDED_FULL_SEARCH,
    start_roi: PhysicalRoi | None = None,
):
    controller = AdaptiveRoiController(
        start_roi=_roi() if start_roi is None else start_roi,
        gate_config=_gate_config(),
        variant=variant,
        expanded_scale=(
            2.0 if variant is P2Variant.P2_2_EXPANDED_FULL_SEARCH else None
        ),
    )
    attempt = controller.begin_frame(frame_id)
    output = _output_for_absolute_points(
        attempt=attempt,
        candidate_xy_mm=point_xy_mm,
        uncertainty=uncertainty,
    )
    step = controller.submit(_observation_for_output(attempt, output))
    assert step.frame_result is not None
    return step.frame_result


def test_sequence_metrics_report_coverage_fallback_risk_runtime_and_williams() -> None:
    first = _accepted_frame(frame_id="exact", point_xy_mm=(0.0, 0.0), uncertainty=0.1)
    confident_wrong = _accepted_frame(
        frame_id="confident-wrong",
        point_xy_mm=(0.0, 0.0),
        uncertainty=0.05,
    )
    lost = _eligible_lost_frame()
    williams = evaluate_selective_williams(
        lost,
        gate_config=_gate_config(),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: _successful_williams(),
    )
    records = (
        EvaluatedFrame(first, (0.0, 0.0), "synthetic"),
        EvaluatedFrame(confident_wrong, (3.0, 0.0), "synthetic"),
        EvaluatedFrame(lost, (0.0, 0.0), "synthetic", williams),
    )

    metrics = aggregate_sequence_metrics(
        records,
        minimum_safe_margin_mm=0.2,
        confidence_threshold=0.2,
        confident_error_threshold_mm=1.0,
    )

    assert metrics["coverage"]["inside"]["count"] == 3
    assert metrics["coverage"]["safe"]["rate"] == pytest.approx(1.0)
    assert metrics["acceptance"]["first_attempt"]["count"] == 2
    assert metrics["acceptance"]["fallback_by_stage"]["expanded_fallback"]["count"] == 1
    assert metrics["acceptance"]["fallback_by_stage"]["full_search"]["count"] == 1
    assert metrics["acceptance"]["recovery"]["denominator"] == 1
    assert metrics["acceptance"]["final_lost"]["count"] == 1
    assert metrics["acceptance"]["unnecessary_fallback"]["count"] == 1
    assert metrics["localization_error_mm"]["median"] == pytest.approx(1.5)
    assert metrics["localization_error_mm"]["p95"] == pytest.approx(2.85)
    assert metrics["localization_error_mm"]["maximum"] == pytest.approx(3.0)
    assert metrics["confident_errors"]["confident_predictions"] == 2
    assert metrics["confident_errors"]["count"] == 1
    assert metrics["confident_errors"]["one_sided_95_upper"] == pytest.approx(
        clopper_pearson_upper(1, 2)
    )
    assert "correlated" in metrics["confident_errors"]["correlation_caveat"]
    assert metrics["runtime_seconds"]["p50"] == pytest.approx(0.01)
    assert metrics["runtime_seconds"]["p95"] == pytest.approx(0.055)
    assert metrics["boundary_violations"]["count"] == 0
    assert metrics["williams"]["calls"] == 1
    assert metrics["williams"]["eligible_frames"] == 1
    assert metrics["williams"]["call_rate_of_eligible"] == pytest.approx(1.0)
    assert metrics["williams"]["success_rate_of_calls"] == pytest.approx(1.0)
    assert metrics["williams"]["rejection_rate_of_calls"] == pytest.approx(0.0)
    assert metrics["williams"]["outcomes"] == {"diagnostic_only": 1}
    assert metrics["williams"]["runtime_seconds"]["median"] == pytest.approx(0.03)
    assert metrics["williams"]["quality_effect_mm"]["after_minus_before"][
        "median"
    ] == pytest.approx(0.1)


def test_sequence_metrics_separate_rejected_williams_outputs_from_quality_effect() -> None:
    lost = _eligible_lost_frame()
    rejected_solver_result = replace(
        _successful_williams(),
        converged=False,
        failure_reason="no_convergence",
    )
    rejected = evaluate_selective_williams(
        lost,
        gate_config=_gate_config(),
        previous_tip_xy_mm=(0.0, 0.0),
        solver=lambda observation: rejected_solver_result,
    )

    metrics = aggregate_sequence_metrics(
        (EvaluatedFrame(lost, (0.0, 0.0), "synthetic", rejected),),
        minimum_safe_margin_mm=0.2,
        confidence_threshold=0.2,
        confident_error_threshold_mm=1.0,
    )

    assert rejected.outcome is WilliamsOutcome.REJECTED
    assert metrics["williams"]["quality_effect_mm"]["comparable_references"] == 0
    rejected_effect = metrics["williams"]["rejected_solver_outputs_mm"]
    assert rejected_effect["comparable_references"] == 1
    assert rejected_effect["after_minus_before"]["median"] == pytest.approx(0.1)


def test_attaching_a_different_reference_cannot_change_controller_outcome() -> None:
    result = _accepted_frame(frame_id="reference-blind", point_xy_mm=(0.0, 0.0), uncertainty=0.1)

    near = aggregate_sequence_metrics(
        (EvaluatedFrame(result, (0.0, 0.0), "synthetic-a"),),
        minimum_safe_margin_mm=0.2,
        confidence_threshold=0.2,
        confident_error_threshold_mm=1.0,
    )
    far = aggregate_sequence_metrics(
        (EvaluatedFrame(result, (4.0, 0.0), "synthetic-b"),),
        minimum_safe_margin_mm=0.2,
        confidence_threshold=0.2,
        confident_error_threshold_mm=1.0,
    )

    assert near["acceptance"] == far["acceptance"]
    assert near["rejection_reasons"] == far["rejection_reasons"]
    assert near["localization_error_mm"]["maximum"] == pytest.approx(0.0)
    assert far["localization_error_mm"]["maximum"] == pytest.approx(4.0)


def test_clopper_pearson_upper_is_nominal_one_sided_exact_bound() -> None:
    assert clopper_pearson_upper(0, 100) == pytest.approx(1.0 - 0.05 ** (1.0 / 100.0))
    assert clopper_pearson_upper(5, 5) == 1.0
    with pytest.raises(ValueError, match="successes"):
        clopper_pearson_upper(2, 1)


def test_evidence_manifest_keeps_sequence_claims_and_references_bounded() -> None:
    manifest = build_evidence_manifest()

    assert manifest["reference_in_controller_input"] is False
    repository = manifest["repository_fixtures"]
    assert repository["sample_count"] == 3
    assert repository["side"] == "left"
    assert repository["input_sources"] == [
        "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_7.txt",
        "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_407.txt",
        "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_807.txt",
    ]
    assert repository["reference_sources"] == [
        "test_data/crack_detection/raw/GroundTruth/AllDataPoints_1_7_left.txt",
        "test_data/crack_detection/raw/GroundTruth/AllDataPoints_1_407_left.txt",
        "test_data/crack_detection/raw/GroundTruth/AllDataPoints_1_807_left.txt",
    ]
    assert repository["trajectory_role"] == "sparse_historical_replay"
    assert repository["independent_of_training_claimed"] is False

    dummy2 = manifest["dummy2"]
    assert [frame["stage"] for frame in dummy2["frames"]] == [52, 53, 54, 55]
    assert [frame["load_phase"] for frame in dummy2["frames"]] == [
        "peak_load_before_cycle_advance",
        "unloaded_cycle_checkpoint",
        "reload_ramp",
        "peak_load_after_cycle_advance",
    ]
    assert all(frame["reference_kind"] == "pseudoreference" for frame in dummy2["frames"])
    assert all(
        frame["reference_source"] == "test_data/crack_detection/crack_info_by_nodemap.txt"
        for frame in dummy2["frames"]
    )
    assert dummy2["reference_role"] == "evaluation_only"

    assert manifest["crackmnist"]["role"] == "single_image_confidence_only"
    assert manifest["crackmnist"]["sequence_accuracy_claimed"] is False
    assert manifest["mendeley"]["label_status"] == "pending_verified_tip_labels"
    assert manifest["mendeley"]["quantitative_roi_accuracy_reported"] is False


def _synthetic_by_name() -> dict[str, SyntheticReplayResult]:
    return {result.name: result for result in run_synthetic_replays()}


def test_synthetic_replays_cover_declared_tracking_and_stress_cases() -> None:
    replays = _synthetic_by_name()

    assert set(replays) == {
        "small_jump",
        "large_jump",
        "edge_recovery",
        "expanded_full_recovery",
        "nan_zero_variation",
        "head_conflict",
        "lost_reset",
        "confident_wrong",
    }

    small = replays["small_jump"].records
    assert [record.result.final_state for record in small] == [
        RoiState.TRACKING,
        RoiState.TRACKING,
    ]
    assert small[1].result.attempts[0].attempt.state is RoiState.TRACKING

    large = replays["large_jump"].records[-1].result
    assert large.final_state is RoiState.LOST
    assert any(
        "tip_jump_too_large" in [reason.value for reason in attempt.decision.reasons]
        for attempt in large.attempts
    )

    edge = replays["edge_recovery"].records[0].result
    assert edge.accepted_attempt_state is RoiState.EXPANDED_FALLBACK

    full = replays["expanded_full_recovery"].records[0].result
    assert [attempt.attempt.state for attempt in full.attempts] == [
        RoiState.START,
        RoiState.EXPANDED_FALLBACK,
        RoiState.FULL_SEARCH,
    ]
    assert full.accepted_attempt_state is RoiState.FULL_SEARCH


def test_synthetic_replays_expose_invalid_fields_conflict_reset_and_confident_error() -> None:
    replays = _synthetic_by_name()

    invalid = replays["nan_zero_variation"].records[0].result
    invalid_reasons = {
        reason.value
        for attempt in invalid.attempts
        for reason in attempt.decision.reasons
    }
    assert invalid.final_state is RoiState.LOST
    assert "nonfinite_field" in invalid_reasons
    assert "field_variation_too_low" in invalid_reasons
    invalid_audit = replays["nan_zero_variation"].to_dict()["frames"][0]
    assert invalid_audit["attempts"][0]["signals"]["finite_grid_fraction"] == "NaN"
    json.dumps(invalid_audit, allow_nan=False)

    conflict = replays["head_conflict"].records[0].result
    assert conflict.final_state is RoiState.LOST
    assert conflict.williams_eligible is True
    assert all(
        "head_disagreement_too_large"
        in [reason.value for reason in attempt.decision.reasons]
        for attempt in conflict.attempts
    )

    reset = replays["lost_reset"].records
    assert reset[0].result.final_state is RoiState.LOST
    assert reset[1].result.attempts[0].attempt.state is RoiState.START
    assert reset[1].result.final_state is RoiState.TRACKING

    confident_wrong = replays["confident_wrong"].metrics["confident_errors"]
    assert confident_wrong["confident_predictions"] == 1
    assert confident_wrong["count"] == 1


def test_synthetic_replays_are_bitwise_deterministic_as_report_records() -> None:
    first = [result.to_dict() for result in run_synthetic_replays()]
    second = [result.to_dict() for result in run_synthetic_replays()]

    assert first == second


def test_p2_orchestrator_reports_missing_real_evidence_without_silent_gates() -> None:
    result = run_p2_benchmark(
        P2RunConfig(
            p1_results=_p1_artifact(),
            allow_unverified_p1_for_tests=True,
        )
    )

    assert result["stage"] == "P2"
    assert result["p1_contract"]["resolution_mode"] == "trained-256"
    assert len(result["synthetic_replays"]) == 8
    assert result["real_evidence_status"] == {
        "crackmnist_single_image": "not_provided",
        "dummy2": "not_provided",
        "repository_sparse": "not_provided",
    }
    assert result["technical_gates"]["status"] == "not_evaluable_without_primary_sequence"
    assert result["technical_gates"]["all_evaluable_passed"] is None
    assert result["p1_contract"]["source_verification_status"] == (
        "in_memory_unverified_test_only"
    )
    assert result["scientific_release"]["approved"] is False
    json.dumps(result, allow_nan=False)


def test_p2_orchestrator_rejects_unverified_in_memory_p1_in_production() -> None:
    with pytest.raises(ValueError, match="in-memory P1.*test-only"):
        run_p2_benchmark(P2RunConfig(p1_results=_p1_artifact()))


def test_p2_orchestrator_aggregates_complete_dummy2_sequence_and_applies_gates() -> None:
    dummy2 = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=(
                    f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt"
                ),
                point_xy_mm=(20.0, 0.0),
                uncertainty=0.1,
                start_roi=_right_tracking_roi(),
            ),
            (20.0, 0.0),
            "crack_info_by_nodemap pseudoreference",
        )
        for stage in (52, 53, 54, 55)
    )

    frame_ids = [record.result.frame_id for record in dummy2]
    result = run_p2_benchmark(
        P2RunConfig(
            p1_results=_p1_artifact(),
            allow_unverified_p1_for_tests=True,
            same_scenario_p1_baselines={
                "dummy2": _same_scenario_baseline(
                    frame_ids,
                    reference_source="crack_info_by_nodemap pseudoreference",
                )
            },
        ),
        evidence_sets={"dummy2": dummy2},
    )

    assert result["real_evidence_status"]["dummy2"] == "provided_complete"
    evidence = result["real_evidence"]["dummy2"]
    assert evidence["variant"] == P2Variant.P2_2_EXPANDED_FULL_SEARCH.value
    assert evidence["metrics"]["frames"] == 4
    assert len(evidence["records"]) == 4
    audit = evidence["records"][0]
    assert audit["final_state"] == "tracking"
    assert audit["total_elapsed_seconds"] == pytest.approx(0.01)
    assert audit["skipped_states"] == ["expanded_fallback"]
    assert audit["next_frame_roi"]["extent_xy_mm"] == [40.0, 40.0]
    assert audit["next_frame_roi"]["bounds"] == {
        "x_min_mm": 0.0,
        "x_max_mm": 40.0,
        "y_min_mm": -20.0,
        "y_max_mm": 20.0,
    }
    assert audit["attempts"][0]["attempt_id"] == 0
    assert audit["attempts"][0]["state"] == "start"
    assert audit["attempts"][0]["applied_roi"]["extent_xy_mm"] == [40.0, 40.0]
    assert audit["attempts"][0]["next_roi"] == audit["next_frame_roi"]
    assert audit["attempts"][0]["gate"]["reasons"] == []
    assert audit["attempts"][0]["signals"]["decoder_uncertainty"] == pytest.approx(0.1)
    assert result["technical_gates"]["safe_coverage_at_least_0.99"] is True
    assert result["technical_gates"]["zero_boundary_violations"] is True
    assert result["technical_gates"][
        "final_failure_not_above_same_scenario_p1"
    ] is True
    assert result["technical_gates"]["same_scenario_p1_failure_rate"] == 0.0
    assert result["technical_gates"]["all_evaluable_passed"] is True


def test_p2_never_uses_crackmnist_context_as_sequence_failure_baseline() -> None:
    dummy2 = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=str(stage),
                point_xy_mm=(0.0, 0.0),
                uncertainty=0.1,
            ),
            (0.0, 0.0),
            "Dummy2 pseudoreference",
        )
        for stage in (52, 53, 54, 55)
    )

    result = run_p2_benchmark(
        P2RunConfig(
            p1_results=_p1_artifact(),
            allow_unverified_p1_for_tests=True,
        ),
        evidence_sets={"dummy2": dummy2},
    )

    gates = result["technical_gates"]
    assert gates["status"] == "partially_evaluable"
    assert gates["final_failure_not_above_same_scenario_p1"] is None
    assert gates["same_scenario_p1_failure_rate"] is None
    assert gates["all_evaluable_passed"] is None
    assert result["p1_contract"]["crackmnist_test_failure_rate_context"] == pytest.approx(
        0.01
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda baseline: baseline.__setitem__(
                "model_artifact_sha256", "c" * 64
            ),
            "model hash",
        ),
        (
            lambda baseline: baseline["frames"][0].__setitem__(
                "frame_id", "different-frame"
            ),
            "frame IDs",
        ),
        (
            lambda baseline: (
                baseline["roi"].__setitem__(
                    "center_xy_mm", [-35.0, 0.0]
                ),
                baseline["roi"].__setitem__(
                    "bounds_mm", [-70.0, 0.0, -35.0, 35.0]
                ),
                baseline["roi"].__setitem__(
                    "search_bounds_mm", [-70.0, 0.0, -35.0, 35.0]
                ),
            ),
            "P2 search bounds",
        ),
        (
            lambda baseline: baseline["frames"][0].__setitem__(
                "success", False
            ),
            "success flags",
        ),
    ],
)
def test_p2_rejects_same_scenario_baseline_with_mismatched_provenance(
    mutation,
    message: str,
) -> None:
    records = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=f"fixture-{index}",
                point_xy_mm=(20.0, 0.0),
                uncertainty=0.1,
                start_roi=_right_tracking_roi(),
            ),
            (20.0, 0.0),
            "fixture reference",
        )
        for index in range(3)
    )
    baseline = _same_scenario_baseline(
        [record.result.frame_id for record in records]
    )
    mutation(baseline)

    with pytest.raises(ValueError, match=message):
        run_p2_benchmark(
            P2RunConfig(
                p1_results=_p1_artifact(),
                allow_unverified_p1_for_tests=True,
                primary_sequence_evidence="repository_sparse",
                same_scenario_p1_baselines={"repository_sparse": baseline},
            ),
            evidence_sets={"repository_sparse": records},
        )


def test_p2_rejects_coordinated_same_scenario_failure_flag_tampering() -> None:
    records = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=f"fixture-{index}",
                point_xy_mm=(20.0, 0.0),
                uncertainty=0.1,
                start_roi=_right_tracking_roi(),
            ),
            (20.0, 0.0),
            "fixture reference",
        )
        for index in range(3)
    )
    baseline = _same_scenario_baseline(
        [record.result.frame_id for record in records]
    )
    baseline["frames"][0]["success"] = False
    baseline["failures"] = 1
    baseline["failure_rate"] = 1.0 / 3.0

    with pytest.raises(ValueError, match="success.*candidate"):
        run_p2_benchmark(
            P2RunConfig(
                p1_results=_p1_artifact(),
                allow_unverified_p1_for_tests=True,
                primary_sequence_evidence="repository_sparse",
                same_scenario_p1_baselines={"repository_sparse": baseline},
            ),
            evidence_sets={"repository_sparse": records},
        )


def test_p2_keeps_p21_and_p22_evidence_sets_separate_and_rejects_mixed_variants() -> None:
    p21 = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=f"p21-{index}",
                point_xy_mm=(0.0, 0.0),
                uncertainty=0.1,
                variant=P2Variant.P2_1_START_RESET,
            ),
            (0.0, 0.0),
            "fixture reference",
        )
        for index in range(3)
    )
    p22 = tuple(
        EvaluatedFrame(
            _accepted_frame(
                frame_id=f"p22-{index}",
                point_xy_mm=(0.0, 0.0),
                uncertainty=0.1,
            ),
            (0.0, 0.0),
            "fixture reference",
        )
        for index in range(3)
    )
    result = run_p2_benchmark(
        P2RunConfig(
            p1_results=_p1_artifact(),
            allow_unverified_p1_for_tests=True,
            primary_sequence_evidence="repository_sparse@p2.2_expanded_full_search",
        ),
        evidence_sets={
            "repository_sparse@p2.1_start_reset": p21,
            "repository_sparse@p2.2_expanded_full_search": p22,
        },
    )

    assert result["real_evidence"]["repository_sparse@p2.1_start_reset"][
        "variant"
    ] == "p2.1_start_reset"
    assert result["real_evidence"]["repository_sparse@p2.2_expanded_full_search"][
        "variant"
    ] == "p2.2_expanded_full_search"

    with pytest.raises(ValueError, match="single P2 variant"):
        run_p2_benchmark(
            P2RunConfig(
                p1_results=_p1_artifact(),
                allow_unverified_p1_for_tests=True,
                primary_sequence_evidence="repository_sparse",
            ),
            evidence_sets={"repository_sparse": (*p21[:2], p22[0])},
        )


def test_p2_orchestrator_applies_williams_or_marks_missing_solver_unevaluable() -> None:
    lost = _eligible_lost_frame(
        frame_id="Dummy2_WPXXX_DummyVersuch_2_dic_results_1_55.txt"
    )
    records = tuple(
        [
            EvaluatedFrame(
                _accepted_frame(
                    frame_id=f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt",
                    point_xy_mm=(0.0, 0.0),
                    uncertainty=0.1,
                ),
                (0.0, 0.0),
                "Dummy2 pseudoreference",
            )
            for stage in (52, 53, 54)
        ]
        + [EvaluatedFrame(lost, (0.0, 0.0), "Dummy2 pseudoreference")]
    )
    config = P2RunConfig(
        p1_results=_p1_artifact(),
        allow_unverified_p1_for_tests=True,
    )

    unevaluable = run_p2_benchmark(
        config,
        evidence_sets={"dummy2": records},
        williams_policy=WilliamsPolicy(mode=WilliamsMode.DIAGNOSTIC),
        williams_gate_config=_gate_config(),
    )
    missing = unevaluable["real_evidence"]["dummy2"]
    assert missing["records"][-1]["williams"]["outcome"] == "unevaluable"
    assert missing["metrics"]["williams"]["calls"] == 0
    assert missing["metrics"]["williams"]["rejected"] == 0
    assert missing["metrics"]["williams"]["unevaluable"] == 1

    calls = []
    evaluated = run_p2_benchmark(
        config,
        evidence_sets={"dummy2": records},
        williams_policy=WilliamsPolicy(mode=WilliamsMode.DIAGNOSTIC),
        williams_gate_config=_gate_config(),
        williams_solver=lambda observation: calls.append(observation) or _successful_williams(),
    )
    evidence = evaluated["real_evidence"]["dummy2"]
    assert len(calls) == 1
    assert evidence["records"][-1]["williams"]["outcome"] == "diagnostic_only"
    assert evidence["metrics"]["williams"]["calls"] == 1
    assert evidence["metrics"]["williams"]["success_rate_of_calls"] == 1.0


def test_p2_orchestrator_rejects_incomplete_dummy2_or_crackmnist_references() -> None:
    incomplete = (
        EvaluatedFrame(
            _accepted_frame(frame_id="52", point_xy_mm=(0.0, 0.0), uncertainty=0.1),
            (0.0, 0.0),
            "pseudoreference",
        ),
    )
    with pytest.raises(ValueError, match="52 through 55"):
        run_p2_benchmark(
            P2RunConfig(
                p1_results=_p1_artifact(),
                allow_unverified_p1_for_tests=True,
            ),
            evidence_sets={"dummy2": incomplete},
        )

    crackmnist_with_sequence_reference = (
        EvaluatedFrame(
            _accepted_frame(frame_id="cm-1", point_xy_mm=(0.0, 0.0), uncertainty=0.1),
            (0.0, 0.0),
            "forbidden sequence reference",
        ),
    )
    with pytest.raises(ValueError, match="single-image confidence"):
        run_p2_benchmark(
            P2RunConfig(
                p1_results=_p1_artifact(),
                allow_unverified_p1_for_tests=True,
            ),
            evidence_sets={"crackmnist_single_image": crackmnist_with_sequence_reference},
        )

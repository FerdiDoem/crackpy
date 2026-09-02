"""Behavioral tests for deterministic physical adaptive-ROI tracking."""

from __future__ import annotations

from dataclasses import replace

import pytest

from crackpy.crack_detection.adaptive_roi import (
    AdaptiveRoiController,
    GateConfig,
    GateReason,
    LegacySideAdapter,
    P2Variant,
    PhysicalBounds,
    PhysicalRoi,
    RoiAttempt,
    RoiObservation,
    RoiState,
)


def test_physical_roi_clamps_its_center_without_changing_physical_size() -> None:
    search = PhysicalBounds(x_min_mm=0.0, x_max_mm=80.0, y_min_mm=-40.0, y_max_mm=40.0)
    start = PhysicalRoi(
        center_x_mm=35.0,
        center_y_mm=0.0,
        extent_x_mm=70.0,
        extent_y_mm=70.0,
        search_bounds=search,
    )

    tracked = start.recentered_clamped((60.0, 3.0))

    assert tracked.center_xy_mm == (45.0, 3.0)
    assert tracked.extent_xy_mm == (70.0, 70.0)
    assert tracked.bounds == PhysicalBounds(10.0, 80.0, -32.0, 38.0)
    assert tracked.signed_margin_mm((60.0, 3.0)) == pytest.approx(20.0)
    assert tracked.contains((60.0, 3.0), minimum_margin_mm=20.0)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {"x_min_mm": 2.0, "x_max_mm": 2.0, "y_min_mm": -1.0, "y_max_mm": 1.0},
            "strictly increasing",
        ),
        (
            {"x_min_mm": 0.0, "x_max_mm": 2.0, "y_min_mm": float("nan"), "y_max_mm": 1.0},
            "finite",
        ),
    ],
)
def test_physical_bounds_reject_invalid_geometry(
    kwargs: dict[str, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PhysicalBounds(**kwargs)


def test_physical_roi_rejects_nonpositive_or_out_of_bounds_extent() -> None:
    search = PhysicalBounds(0.0, 80.0, -40.0, 40.0)

    with pytest.raises(ValueError, match="positive"):
        PhysicalRoi(35.0, 0.0, 0.0, 70.0, search)
    with pytest.raises(ValueError, match="inside search_bounds"):
        PhysicalRoi(40.0, 0.0, 90.0, 70.0, search)


def test_legacy_side_adapter_uses_inner_edge_offsets_and_n_minus_one_mapping() -> None:
    right_search = PhysicalBounds(0.0, 90.0, -40.0, 50.0)
    right_roi = PhysicalRoi(45.0, 5.0, 70.0, 70.0, right_search)
    left_search = PhysicalBounds(-90.0, 0.0, -40.0, 50.0)
    left_roi = PhysicalRoi(-45.0, 5.0, 70.0, 70.0, left_search)
    right = LegacySideAdapter("right")
    left = LegacySideAdapter("left")

    assert right.interpolation_args(right_roi) == (70.0, (10.0, 5.0))
    assert left.interpolation_args(left_roi) == (-70.0, (-10.0, 5.0))
    assert right.point_rc_to_xy((0.0, 0.0), right_roi, resolution_px=256) == (10.0, -30.0)
    assert right.point_rc_to_xy((255.0, 255.0), right_roi, resolution_px=256) == (80.0, 40.0)
    assert left.point_rc_to_xy((0.0, 0.0), left_roi, resolution_px=256) == (-10.0, -30.0)
    assert left.point_rc_to_xy((255.0, 255.0), left_roi, resolution_px=256) == (-80.0, 40.0)

    for adapter, roi, point in (
        (right, right_roi, (63.25, 11.5)),
        (left, left_roi, (-63.25, 11.5)),
    ):
        point_rc = adapter.point_xy_to_rc(point, roi, resolution_px=(256, 256))
        converted = adapter.point_rc_to_xy(point_rc, roi, resolution_px=(256, 256))
        assert converted == pytest.approx(point)


def test_legacy_side_adapter_rejects_rectangular_rois_and_invalid_sides() -> None:
    search = PhysicalBounds(0.0, 80.0, -40.0, 40.0)
    rectangular = PhysicalRoi(35.0, 0.0, 70.0, 60.0, search)

    with pytest.raises(ValueError, match="left or right"):
        LegacySideAdapter("top")
    with pytest.raises(ValueError, match="square"):
        LegacySideAdapter("right").interpolation_args(rectangular)


def _gate_config(**changes: object) -> GateConfig:
    values: dict[str, object] = {
        "min_mask_mean_score": 0.85,
        "min_region_selection_score": 0.80,
        "min_mask_area_fraction": 0.0001,
        "max_mask_area_fraction": 0.05,
        "max_head_disagreement_fraction": 0.10,
        "max_decoder_uncertainty": 0.12,
        "mask_score_marginal_band": 0.05,
        "head_disagreement_marginal_band": 0.02,
        "decoder_uncertainty_marginal_band": 0.03,
        "min_tip_roi_margin_mm": 2.0,
        "min_tip_search_margin_mm": 1.0,
        "min_finite_grid_fraction": 1.0,
        "min_channel_std_mm": 1e-6,
        "jump_noise_mm": 0.5,
        "max_growth_mm_per_cycle": 0.2,
        "max_jump_without_cycles_mm": 3.0,
        "max_jump_cap_mm": 10.0,
        "calibration_source": "p1-validation-sha256:abc",
    }
    values.update(changes)
    return GateConfig(**values)


def _start_roi() -> PhysicalRoi:
    return PhysicalRoi(
        35.0,
        0.0,
        70.0,
        70.0,
        PhysicalBounds(0.0, 80.0, -40.0, 40.0),
    )


def _observation(**changes: object) -> RoiObservation:
    values: dict[str, object] = {
        "frame_id": "52",
        "attempt_id": 0,
        "applied_roi": _start_roi(),
        "mask_tip_xy_mm": (30.0, 0.0),
        "coordinate_tip_xy_mm": (30.5, 0.0),
        "fusion_weight": 0.0,
        "mask_mean_score": 0.95,
        "region_selection_score": 0.95,
        "mask_area_fraction": 0.002,
        "decoder_uncertainty": 0.05,
        "finite_grid_fraction": 1.0,
        "channel_std_mm": (0.004, 0.018),
        "cycle_delta_from_last_accepted": None,
        "elapsed_seconds": 0.2,
        "decoder_invalid_reason": None,
    }
    values.update(changes)
    return RoiObservation.from_decoder_heads(**values)


def test_observation_factory_derives_candidate_and_physical_head_disagreement() -> None:
    observation = _observation(
        mask_tip_xy_mm=(30.0, 1.0),
        coordinate_tip_xy_mm=(33.0, 5.0),
    )

    assert observation.candidate_tip_xy_mm == (30.0, 1.0)
    assert observation.head_disagreement_mm == pytest.approx(5.0)
    assert observation.head_disagreement_fraction == pytest.approx(
        5.0 / observation.applied_roi.diagonal_mm
    )

    fused = _observation(
        mask_tip_xy_mm=(30.0, 1.0),
        coordinate_tip_xy_mm=(33.0, 5.0),
        fusion_weight=0.25,
    )
    assert fused.candidate_tip_xy_mm == pytest.approx((30.75, 2.0))


def test_observation_rejects_caller_supplied_inconsistent_derived_signals() -> None:
    observation = _observation()

    with pytest.raises(ValueError, match="candidate tip"):
        replace(observation, candidate_tip_xy_mm=(31.0, 0.0))
    with pytest.raises(ValueError, match="head disagreement fraction"):
        replace(observation, head_disagreement_fraction=0.5)


def test_gate_accepts_complete_finite_observation_at_declared_thresholds() -> None:
    config = _gate_config()
    observation = _observation(
        mask_tip_xy_mm=(65.0, 0.0),
        coordinate_tip_xy_mm=(65.0 + 0.10 * _start_roi().diagonal_mm, 0.0),
        mask_mean_score=0.85,
        mask_area_fraction=0.0001,
        decoder_uncertainty=0.12,
    )

    decision = config.evaluate(observation)

    assert decision.accepted
    assert decision.field_ok
    assert decision.geometry_ok
    assert decision.evidence_ok
    assert decision.reasons == ()
    assert not decision.williams_eligible
    assert decision.roi_margin_mm == pytest.approx(5.0)
    assert decision.search_margin_mm == pytest.approx(15.0)


@pytest.mark.parametrize(
    "changes, expected_reason, expected_group",
    [
        ({"finite_grid_fraction": 0.99}, GateReason.NONFINITE_FIELD, "field"),
        ({"channel_std_mm": (0.0, 0.02)}, GateReason.FIELD_VARIATION_TOO_LOW, "field"),
        ({"mask_tip_xy_mm": None}, GateReason.MISSING_TIP, "geometry"),
        (
            {"mask_tip_xy_mm": (0.5, 0.0), "coordinate_tip_xy_mm": (1.0, 0.0)},
            GateReason.TIP_NEAR_ROI_EDGE,
            "geometry",
        ),
        ({"mask_mean_score": 0.5}, GateReason.MASK_SCORE_TOO_LOW, "evidence"),
        (
            {"region_selection_score": None},
            GateReason.MISSING_REGION_SELECTION_SCORE,
            "evidence",
        ),
        (
            {"region_selection_score": float("nan")},
            GateReason.INVALID_REGION_SELECTION_SCORE,
            "evidence",
        ),
        (
            {"region_selection_score": 0.5},
            GateReason.REGION_SELECTION_SCORE_TOO_LOW,
            "evidence",
        ),
        ({"mask_area_fraction": 0.1}, GateReason.MASK_AREA_TOO_LARGE, "evidence"),
        (
            {
                "coordinate_tip_xy_mm": (
                    30.0 + 0.2 * _start_roi().diagonal_mm,
                    0.0,
                )
            },
            GateReason.HEAD_DISAGREEMENT_TOO_LARGE,
            "evidence",
        ),
        ({"decoder_uncertainty": 0.5}, GateReason.DECODER_UNCERTAINTY_TOO_HIGH, "evidence"),
    ],
)
def test_gate_reports_the_failed_contract_group_without_hiding_other_evidence(
    changes: dict[str, object],
    expected_reason: GateReason,
    expected_group: str,
) -> None:
    decision = _gate_config().evaluate(_observation(**changes))

    assert not decision.accepted
    assert expected_reason in decision.reasons
    assert not getattr(decision, f"{expected_group}_ok")
    assert not decision.williams_eligible


def test_gate_derives_cycle_aware_jump_limit_from_last_accepted_tip() -> None:
    observation = _observation(
        mask_tip_xy_mm=(34.0, 0.0),
        coordinate_tip_xy_mm=(34.5, 0.0),
        cycle_delta_from_last_accepted=10.0,
    )

    decision = _gate_config().evaluate(observation, previous_tip_xy_mm=(30.0, 0.0))

    assert not decision.accepted
    assert decision.tip_jump_mm == pytest.approx(4.0)
    assert decision.max_tip_jump_mm == pytest.approx(2.5)
    assert GateReason.TIP_JUMP_TOO_LARGE in decision.reasons
    assert not decision.williams_eligible


def test_gate_uses_conservative_jump_limit_without_cycle_information() -> None:
    observation = _observation(
        mask_tip_xy_mm=(33.0, 0.0),
        coordinate_tip_xy_mm=(33.5, 0.0),
    )

    decision = _gate_config().evaluate(observation, previous_tip_xy_mm=(30.0, 0.0))

    assert decision.accepted
    assert decision.tip_jump_mm == pytest.approx(3.0)
    assert decision.max_tip_jump_mm == pytest.approx(3.0)


def test_gate_caps_cycle_aware_jump_limit() -> None:
    observation = _observation(
        mask_tip_xy_mm=(33.0, 0.0),
        coordinate_tip_xy_mm=(33.5, 0.0),
        cycle_delta_from_last_accepted=100.0,
    )

    decision = _gate_config(max_jump_cap_mm=2.0).evaluate(
        observation,
        previous_tip_xy_mm=(30.0, 0.0),
    )

    assert decision.tip_jump_mm == pytest.approx(3.0)
    assert decision.max_tip_jump_mm == pytest.approx(2.0)
    assert GateReason.TIP_JUMP_TOO_LARGE in decision.reasons


def test_gate_rejects_invalid_config_and_observation_contracts() -> None:
    with pytest.raises(ValueError, match="mask area"):
        _gate_config(min_mask_area_fraction=0.2, max_mask_area_fraction=0.1)
    with pytest.raises(ValueError, match="mask score marginal band"):
        _gate_config(mask_score_marginal_band=0.9)
    with pytest.raises(ValueError, match="head disagreement marginal band"):
        _gate_config(head_disagreement_marginal_band=0.95)
    with pytest.raises(ValueError, match="decoder uncertainty marginal band"):
        _gate_config(decoder_uncertainty_marginal_band=0.9)
    with pytest.raises(ValueError, match="min_region_selection_score"):
        _gate_config(min_region_selection_score=float("nan"))
    with pytest.raises(ValueError, match="cycle delta"):
        _observation(cycle_delta_from_last_accepted=-1.0)
    with pytest.raises(ValueError, match="elapsed_seconds"):
        _observation(elapsed_seconds=float("nan"))


def test_region_selection_score_is_diagnostic_when_its_gate_is_disabled() -> None:
    config = _gate_config(min_region_selection_score=None)

    missing = config.evaluate(_observation(region_selection_score=None))
    rule_specific = config.evaluate(_observation(region_selection_score=22.5))

    assert missing.accepted
    assert rule_specific.accepted


def test_williams_gate_eligibility_requires_marginal_not_missing_evidence() -> None:
    marginal = _gate_config().evaluate(_observation(mask_mean_score=0.82))
    missing = _gate_config().evaluate(
        _observation(coordinate_tip_xy_mm=None)
    )

    assert marginal.williams_eligible
    assert not missing.williams_eligible
    assert GateReason.MISSING_COORDINATE_TIP in missing.reasons
    assert GateReason.MISSING_HEAD_DISAGREEMENT in missing.reasons


@pytest.mark.parametrize(
    "changes",
    [
        {"mask_mean_score": 0.82},
        {
            "coordinate_tip_xy_mm": (
                30.0 + 0.11 * _start_roi().diagonal_mm,
                0.0,
            )
        },
        {"decoder_uncertainty": 0.14},
        {
            "decoder_uncertainty": 0.14,
            "decoder_invalid_reason": "uncertainty_threshold_exceeded",
        },
    ],
)
def test_williams_eligibility_accepts_only_near_threshold_evidence(
    changes: dict[str, object],
) -> None:
    decision = _gate_config().evaluate(_observation(**changes))

    assert not decision.accepted
    assert decision.field_ok
    assert decision.geometry_ok
    assert decision.williams_eligible


@pytest.mark.parametrize(
    "changes",
    [
        {"mask_mean_score": 0.5},
        {
            "coordinate_tip_xy_mm": (
                30.0 + 0.3 * _start_roi().diagonal_mm,
                0.0,
            )
        },
        {"decoder_uncertainty": 0.8},
        {
            "decoder_uncertainty": 0.8,
            "decoder_invalid_reason": "uncertainty_threshold_exceeded",
        },
    ],
)
def test_williams_eligibility_rejects_extreme_evidence(changes: dict[str, object]) -> None:
    decision = _gate_config().evaluate(_observation(**changes))

    assert not decision.accepted
    assert not decision.williams_eligible


def test_decoder_invalid_reason_distinguishes_confidence_from_structural_failure() -> None:
    confidence = _gate_config().evaluate(
        _observation(
            decoder_uncertainty=0.14,
            decoder_invalid_reason="uncertainty_threshold_exceeded",
        )
    )
    structural = _gate_config().evaluate(
        _observation(decoder_invalid_reason="invalid_probability_mask")
    )
    unknown = _gate_config().evaluate(
        _observation(decoder_invalid_reason="future_structural_failure")
    )

    assert GateReason.DECODER_CONFIDENCE_THRESHOLD_EXCEEDED in confidence.reasons
    assert confidence.williams_eligible
    assert GateReason.DECODER_STRUCTURAL_INVALID in structural.reasons
    assert not structural.williams_eligible
    assert GateReason.DECODER_STRUCTURAL_INVALID in unknown.reasons
    assert not unknown.williams_eligible


def _controller(
    variant: P2Variant = P2Variant.P2_1_START_RESET,
    *,
    expanded_scale: float | None = None,
    gates: GateConfig | None = None,
) -> AdaptiveRoiController:
    return AdaptiveRoiController(
        start_roi=_start_roi(),
        gate_config=_gate_config() if gates is None else gates,
        variant=variant,
        expanded_scale=expanded_scale,
    )


def _attempt_observation(attempt: RoiAttempt, **changes: object) -> RoiObservation:
    values: dict[str, object] = {
        "frame_id": attempt.frame_id,
        "attempt_id": attempt.attempt_id,
        "applied_roi": attempt.roi,
        "cycle_delta_from_last_accepted": attempt.cycle_delta_from_last_accepted,
    }
    values.update(changes)
    return _observation(**values)


def _tip_observation(
    attempt: RoiAttempt,
    tip_xy_mm: tuple[float, float],
    **changes: object,
) -> RoiObservation:
    values: dict[str, object] = {
        "mask_tip_xy_mm": tip_xy_mm,
        "coordinate_tip_xy_mm": (tip_xy_mm[0] + 0.5, tip_xy_mm[1]),
    }
    values.update(changes)
    return _attempt_observation(attempt, **values)


def test_controller_requires_square_search_only_when_p22_can_execute_full_search() -> None:
    rectangular_search = PhysicalBounds(0.0, 100.0, -40.0, 40.0)
    square_start = PhysicalRoi(35.0, 0.0, 70.0, 70.0, rectangular_search)
    square_search = PhysicalBounds(0.0, 100.0, -50.0, 50.0)
    rectangular_start = PhysicalRoi(40.0, 0.0, 70.0, 60.0, square_search)

    p21 = AdaptiveRoiController(
        start_roi=square_start,
        gate_config=_gate_config(),
        variant=P2Variant.P2_1_START_RESET,
    )
    p21_attempt = p21.begin_frame("52")
    assert LegacySideAdapter("right").interpolation_args(p21_attempt.roi) == (
        70.0,
        (0.0, 0.0),
    )

    with pytest.raises(ValueError, match="search_bounds.*square"):
        AdaptiveRoiController(
            start_roi=square_start,
            gate_config=_gate_config(),
            variant=P2Variant.P2_2_EXPANDED_FULL_SEARCH,
            expanded_scale=1.1,
        )
    with pytest.raises(ValueError, match="start_roi.*square"):
        AdaptiveRoiController(
            start_roi=rectangular_start,
            gate_config=_gate_config(),
            variant=P2Variant.P2_1_START_RESET,
        )


def test_controller_accepts_start_and_tracks_from_only_the_accepted_tip() -> None:
    controller = _controller()
    attempt = controller.begin_frame("52", cycle_count=100.0)

    assert attempt.state is RoiState.START
    step = controller.submit(_tip_observation(attempt, (60.0, 0.0), elapsed_seconds=0.25))

    assert step.completed
    assert step.next_attempt is None
    assert step.frame_result is not None
    assert step.frame_result.final_state is RoiState.TRACKING
    assert step.frame_result.accepted_tip_xy_mm == (60.0, 0.0)
    assert step.frame_result.accepted_attempt_state is RoiState.START
    assert step.frame_result.total_elapsed_seconds == pytest.approx(0.25)
    assert not step.frame_result.williams_eligible
    assert controller.state is RoiState.TRACKING

    next_attempt = controller.begin_frame("53", cycle_count=110.0)
    assert next_attempt.state is RoiState.TRACKING
    assert next_attempt.roi.center_xy_mm == (45.0, 0.0)
    assert next_attempt.roi.extent_xy_mm == (70.0, 70.0)
    assert next_attempt.cycle_delta_from_last_accepted == pytest.approx(10.0)


def test_p21_retries_tracking_failure_in_exact_start_roi_and_keeps_size_constant() -> None:
    controller = _controller()
    first = controller.begin_frame("52", cycle_count=100.0)
    controller.submit(_tip_observation(first, (60.0, 0.0)))
    tracking = controller.begin_frame("53", cycle_count=110.0)

    retry = controller.submit(
        _tip_observation(tracking, (61.0, 0.0), mask_mean_score=0.5, elapsed_seconds=0.3)
    )

    assert not retry.completed
    assert retry.next_attempt is not None
    assert retry.next_attempt.state is RoiState.START_FALLBACK
    assert retry.next_attempt.roi.same_geometry(_start_roi())
    completed = controller.submit(
        _tip_observation(retry.next_attempt, (60.0, 0.0), elapsed_seconds=0.7)
    )

    assert completed.frame_result is not None
    result = completed.frame_result
    assert result.final_state is RoiState.TRACKING
    assert result.accepted_attempt_state is RoiState.START_FALLBACK
    assert [item.attempt.state for item in result.attempts] == [
        RoiState.TRACKING,
        RoiState.START_FALLBACK,
    ]
    assert {item.attempt.roi.extent_xy_mm for item in result.attempts} == {(70.0, 70.0)}
    assert result.total_elapsed_seconds == pytest.approx(1.0)


def test_confidence_rejection_runs_fallback_and_clean_retry_recovers() -> None:
    controller = _controller()
    first = controller.begin_frame("52", cycle_count=100.0)
    controller.submit(_tip_observation(first, (60.0, 0.0)))
    tracking = controller.begin_frame("53", cycle_count=110.0)

    retry = controller.submit(
        _tip_observation(
            tracking,
            (61.0, 0.0),
            decoder_uncertainty=0.14,
            decoder_invalid_reason="uncertainty_threshold_exceeded",
            elapsed_seconds=0.3,
        )
    )

    assert retry.next_attempt is not None
    assert retry.next_attempt.state is RoiState.START_FALLBACK
    assert GateReason.DECODER_CONFIDENCE_THRESHOLD_EXCEEDED in (
        retry.attempt_result.decision.reasons
    )
    recovered = controller.submit(
        _tip_observation(retry.next_attempt, (60.5, 0.0), elapsed_seconds=0.2)
    )
    assert recovered.frame_result is not None
    assert recovered.frame_result.final_state is RoiState.TRACKING
    assert recovered.frame_result.accepted_attempt_state is RoiState.START_FALLBACK
    assert recovered.frame_result.total_elapsed_seconds == pytest.approx(0.5)


def test_p21_skips_identical_start_fallback_and_resets_after_lost() -> None:
    controller = _controller()
    first = controller.begin_frame("52", cycle_count=100.0)
    controller.submit(_tip_observation(first, (30.0, 0.0)))
    tracking = controller.begin_frame("53", cycle_count=101.0)
    assert tracking.roi.same_geometry(_start_roi())

    lost = controller.submit(
        _tip_observation(tracking, (30.0, 0.0), mask_mean_score=0.82, elapsed_seconds=0.4)
    )

    assert lost.completed
    assert lost.frame_result is not None
    assert lost.frame_result.final_state is RoiState.LOST
    assert lost.frame_result.skipped_states == (RoiState.START_FALLBACK,)
    assert lost.frame_result.williams_eligible
    assert lost.frame_result.williams_eligible_attempt_ids == (0,)
    assert controller.state is RoiState.LOST
    reset = controller.begin_frame("54", cycle_count=102.0)
    assert reset.state is RoiState.START
    assert reset.roi.same_geometry(_start_roi())


def test_p22_runs_expanded_then_true_full_search_after_start_failure() -> None:
    controller = _controller(
        P2Variant.P2_2_EXPANDED_FULL_SEARCH,
        expanded_scale=75.0 / 70.0,
    )
    start = controller.begin_frame("52", cycle_count=100.0)

    expanded_step = controller.submit(
        _tip_observation(start, (30.0, 0.0), mask_mean_score=0.5, elapsed_seconds=0.1)
    )
    assert expanded_step.next_attempt is not None
    expanded = expanded_step.next_attempt
    assert expanded.state is RoiState.EXPANDED_FALLBACK
    assert expanded.roi.extent_xy_mm == pytest.approx((75.0, 75.0))

    full_step = controller.submit(
        _tip_observation(expanded, (30.0, 0.0), mask_mean_score=0.5, elapsed_seconds=0.2)
    )
    assert full_step.next_attempt is not None
    full = full_step.next_attempt
    assert full.state is RoiState.FULL_SEARCH
    assert full.roi.bounds == _start_roi().search_bounds
    assert full.roi.covers_search_bounds()

    completed = controller.submit(_tip_observation(full, (30.0, 0.0), elapsed_seconds=0.3))
    assert completed.frame_result is not None
    result = completed.frame_result
    assert [item.attempt.state for item in result.attempts] == [
        RoiState.START,
        RoiState.EXPANDED_FALLBACK,
        RoiState.FULL_SEARCH,
    ]
    assert result.total_elapsed_seconds == pytest.approx(0.6)
    assert result.final_state is RoiState.TRACKING


def test_p22_collapses_oversized_expansion_to_one_honest_full_search_attempt() -> None:
    controller = _controller(P2Variant.P2_2_EXPANDED_FULL_SEARCH, expanded_scale=2.0)
    start = controller.begin_frame("52")

    next_step = controller.submit(
        _tip_observation(start, (30.0, 0.0), mask_mean_score=0.5)
    )

    assert next_step.next_attempt is not None
    assert next_step.next_attempt.state is RoiState.FULL_SEARCH
    assert next_step.next_attempt.roi.covers_search_bounds()
    lost = controller.submit(
        _tip_observation(next_step.next_attempt, (30.0, 0.0), mask_mean_score=0.5)
    )
    assert lost.frame_result is not None
    assert lost.frame_result.final_state is RoiState.LOST
    assert RoiState.EXPANDED_FALLBACK in lost.frame_result.skipped_states
    assert [item.attempt.state for item in lost.frame_result.attempts] == [
        RoiState.START,
        RoiState.FULL_SEARCH,
    ]


def test_p22_tracking_failure_uses_start_then_expanded_then_full_ladder() -> None:
    controller = _controller(
        P2Variant.P2_2_EXPANDED_FULL_SEARCH,
        expanded_scale=75.0 / 70.0,
    )
    first = controller.begin_frame("52", cycle_count=100.0)
    controller.submit(_tip_observation(first, (60.0, 0.0)))
    tracking = controller.begin_frame("53", cycle_count=101.0)

    seen_states = [tracking.state]
    current = tracking
    for _ in range(3):
        step = controller.submit(
            _tip_observation(current, (60.0, 0.0), mask_mean_score=0.5)
        )
        assert step.next_attempt is not None
        current = step.next_attempt
        seen_states.append(current.state)

    completed = controller.submit(_tip_observation(current, (60.0, 0.0)))

    assert seen_states == [
        RoiState.TRACKING,
        RoiState.START_FALLBACK,
        RoiState.EXPANDED_FALLBACK,
        RoiState.FULL_SEARCH,
    ]
    assert completed.frame_result is not None
    assert completed.frame_result.final_state is RoiState.TRACKING


def test_williams_eligibility_is_terminal_and_excludes_invalid_field_or_geometry() -> None:
    evidence_only = _controller()
    attempt = evidence_only.begin_frame("52")
    eligible = evidence_only.submit(
        _tip_observation(attempt, (30.0, 0.0), decoder_uncertainty=0.14)
    )
    assert eligible.frame_result is not None
    assert eligible.frame_result.williams_eligible

    invalid_field = _controller()
    attempt = invalid_field.begin_frame("52")
    ineligible = invalid_field.submit(
        _tip_observation(
            attempt,
            (30.0, 0.0),
            decoder_uncertainty=0.14,
            finite_grid_fraction=0.9,
        )
    )
    assert ineligible.frame_result is not None
    assert not ineligible.frame_result.williams_eligible
    assert ineligible.frame_result.williams_eligible_attempt_ids == ()


def test_williams_eligibility_is_reported_after_complete_p22_cascade() -> None:
    controller = _controller(
        P2Variant.P2_2_EXPANDED_FULL_SEARCH,
        expanded_scale=75.0 / 70.0,
    )
    current = controller.begin_frame("52")

    for expected_next in (RoiState.EXPANDED_FALLBACK, RoiState.FULL_SEARCH):
        step = controller.submit(
            _tip_observation(current, (30.0, 0.0), mask_mean_score=0.82)
        )
        assert step.attempt_result.decision.williams_eligible
        assert step.frame_result is None
        assert step.next_attempt is not None
        assert step.next_attempt.state is expected_next
        current = step.next_attempt

    terminal = controller.submit(
        _tip_observation(current, (30.0, 0.0), mask_mean_score=0.82)
    )

    assert terminal.frame_result is not None
    assert terminal.frame_result.final_state is RoiState.LOST
    assert terminal.frame_result.williams_eligible
    assert terminal.frame_result.williams_eligible_attempt_ids == (0, 1, 2)


def test_controller_rejects_roi_and_cycle_delta_mismatches() -> None:
    controller = _controller()
    attempt = controller.begin_frame("52", cycle_count=100.0)
    mismatched_roi = PhysicalRoi(
        36.0,
        0.0,
        70.0,
        70.0,
        _start_roi().search_bounds,
    )

    with pytest.raises(ValueError, match="observation ROI"):
        controller.submit(_attempt_observation(attempt, applied_roi=mismatched_roi))
    with pytest.raises(ValueError, match="cycle delta"):
        controller.submit(
            _attempt_observation(attempt, cycle_delta_from_last_accepted=1.0)
        )


def test_controller_rejects_stale_observations_active_frames_and_cycle_regression() -> None:
    controller = _controller()
    attempt = controller.begin_frame("52", cycle_count=100.0)
    with pytest.raises(RuntimeError, match="already active"):
        controller.begin_frame("other")
    stale = _attempt_observation(attempt, attempt_id=99)
    with pytest.raises(ValueError, match="active attempt"):
        controller.submit(stale)

    controller.submit(_tip_observation(attempt, (30.0, 0.0)))
    with pytest.raises(RuntimeError, match="no active frame"):
        controller.submit(_tip_observation(attempt, (30.0, 0.0)))
    with pytest.raises(ValueError, match="precede"):
        controller.begin_frame("53", cycle_count=99.0)


def test_p22_requires_an_explicit_growth_factor_greater_than_one() -> None:
    with pytest.raises(ValueError, match="expanded_scale"):
        _controller(P2Variant.P2_2_EXPANDED_FULL_SEARCH)
    with pytest.raises(ValueError, match="greater than one"):
        _controller(P2Variant.P2_2_EXPANDED_FULL_SEARCH, expanded_scale=1.0)

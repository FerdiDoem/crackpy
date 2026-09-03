"""Tests for the real-data execution seam of the CTD P2 benchmark."""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from crackpy.benchmarking.ctd_decoders import DecoderConfig, DecoderOutput
from crackpy.benchmarking.ctd_p2 import same_scenario_baseline_sha256
from crackpy.benchmarking.ctd_p2_runner import (
    P2DicFrame,
    P2AttemptServices,
    P2FullRunConfig,
    analyze_p1_signal_records,
    compare_same_scenario,
    dic_field_quality,
    evaluate_fixed_roi_p1,
    execute_dic_attempt,
    load_dummy2_sequences,
    load_repository_fixture_sequence,
    mendeley_evidence_manifest,
    p2_candidate_gate_config,
    parse_crack_info_rows,
    p2_input_artifact_manifest,
    reference_tip_from_mask,
    replay_dic_sequence,
    side_rois,
)
from crackpy.crack_detection.adaptive_roi import (
    GateConfig,
    LegacySideAdapter,
    P2Variant,
    PhysicalBounds,
    PhysicalRoi,
    RoiAttempt,
    RoiState,
)


def _full_left_roi() -> PhysicalRoi:
    bounds = PhysicalBounds(-70.0, 0.0, -35.0, 35.0)
    return PhysicalRoi.from_bounds(bounds)


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_dic_field_quality_requires_both_displacement_channels_to_be_finite() -> None:
    fields = np.asarray(
        [
            [[0.0, 1.0], [2.0, np.nan]],
            [[0.0, 2.0], [np.nan, 6.0]],
        ]
    )

    quality = dic_field_quality(fields)

    assert quality.finite_grid_fraction == pytest.approx(0.5)
    assert quality.ux_std_mm == pytest.approx(0.5)
    assert quality.uy_std_mm == pytest.approx(1.0)


def test_reference_tip_from_mask_uses_the_endpoint_inclusive_side_adapter() -> None:
    mask = np.zeros((256, 256), dtype=float)
    mask[129, 38] = 2.0

    point = reference_tip_from_mask(
        mask,
        side_adapter=LegacySideAdapter("left"),
        full_roi=_full_left_roi(),
    )

    assert point == pytest.approx((-38.0 * 70.0 / 255.0, 129.0 * 70.0 / 255.0 - 35.0))


def test_reference_tip_from_mask_rejects_missing_or_ambiguous_tip_labels() -> None:
    missing = np.zeros((4, 4), dtype=float)
    ambiguous = missing.copy()
    ambiguous[0, 0] = 2.0
    ambiguous[1, 1] = 2.0

    with pytest.raises(ValueError, match="exactly one"):
        reference_tip_from_mask(
            missing,
            side_adapter=LegacySideAdapter("left"),
            full_roi=_full_left_roi(),
        )
    with pytest.raises(ValueError, match="exactly one"):
        reference_tip_from_mask(
            ambiguous,
            side_adapter=LegacySideAdapter("left"),
            full_roi=_full_left_roi(),
        )


def test_crack_info_parser_keeps_pseudoreferences_separate_by_side() -> None:
    rows = parse_crack_info_rows(
        [
            "Filename, Crack Tip x [mm], Crack Tip y [mm], Crack Angle, Side",
            "frame_52.txt, -15.43, 0.41, 181.88, left",
            "frame_52.txt, 14.90, 0.66, -2.21, right",
        ]
    )

    assert rows[("frame_52.txt", "left")].tip_xy_mm == (-15.43, 0.41)
    assert rows[("frame_52.txt", "right")].angle_deg == pytest.approx(-2.21)
    assert rows[("frame_52.txt", "right")].reference_kind == "pseudoreference"


def test_p1_signal_analysis_reports_joint_coverage_without_sequence_claims() -> None:
    records = [
        {
            "point_rc": [10.0, 10.0],
            "coordinate_point_rc": [10.0, 10.0],
            "mask_confidence": 0.95,
            "selected_region_area": 20,
            "disagreement_px": 1.0,
            "uncertainty": 0.05,
            "error_px": 0.5,
        },
        {
            "point_rc": [10.0, 10.0],
            "coordinate_point_rc": None,
            "mask_confidence": 0.99,
            "selected_region_area": 20,
            "disagreement_px": None,
            "uncertainty": 1.0,
            "error_px": 4.0,
        },
        {
            "point_rc": None,
            "coordinate_point_rc": None,
            "mask_confidence": None,
            "selected_region_area": None,
            "disagreement_px": None,
            "uncertainty": 1.0,
            "error_px": None,
        },
    ]

    result = analyze_p1_signal_records(
        records,
        model_pixels=256,
        original_pixels=128,
        min_mask_score=0.85,
        min_mask_area_fraction=7.0 / (256 * 256),
        max_mask_area_fraction=43.0 / (256 * 256),
        max_head_disagreement_fraction=16.55 / (np.sqrt(2.0) * 127.0),
        confident_error_threshold_px=2.975,
    )

    assert result["role"] == "single_image_confidence_only"
    assert result["sequence_accuracy_claimed"] is False
    assert result["samples"] == 3
    assert result["successful_detections"] == 2
    assert result["raw_gate_evaluable"] == 1
    assert result["raw_gate_passed"] == 1
    assert result["raw_gate_coverage_of_successful"] == pytest.approx(0.5)
    assert result["confident_error_count"] == 0


def test_dic_frame_requires_a_side_and_reference_kind_contract() -> None:
    with pytest.raises(ValueError, match="side"):
        P2DicFrame("f", object(), "top", None, "none")
    with pytest.raises(ValueError, match="reference_kind"):
        P2DicFrame("f", object(), "left", None, "ground_truth")


def test_repository_fixture_loader_keeps_three_historical_labels_evaluation_only(
    repository_root,
) -> None:
    frames = load_repository_fixture_sequence(repository_root)

    assert [frame.frame_id for frame in frames] == [
        "repository-left-7",
        "repository-left-407",
        "repository-left-807",
    ]
    assert all(frame.side == "left" for frame in frames)
    assert all(frame.reference_kind == "historical_mask_label" for frame in frames)
    assert frames[0].reference_tip_xy_mm == pytest.approx(
        (-38.0 * 70.0 / 255.0, 129.0 * 70.0 / 255.0 - 35.0)
    )
    assert frames[1].reference_tip_xy_mm == pytest.approx(
        (-97.0 * 70.0 / 255.0, 134.0 * 70.0 / 255.0 - 35.0)
    )


def test_dummy2_loader_includes_all_four_load_phases_on_both_sides(
    repository_root,
) -> None:
    sequences = load_dummy2_sequences(repository_root)

    assert set(sequences) == {"left", "right"}
    assert [frame.frame_id for frame in sequences["right"]] == [
        "dummy2-right-52",
        "dummy2-right-53",
        "dummy2-right-54",
        "dummy2-right-55",
    ]
    assert [frame.load_phase for frame in sequences["right"]] == [
        "peak_load_before_cycle_advance",
        "unloaded_cycle_checkpoint",
        "reload_ramp",
        "peak_load_after_cycle_advance",
    ]
    assert [frame.cycle_count for frame in sequences["left"]] == pytest.approx(
        [888983.0, 901098.0, 901099.0, 901100.0]
    )
    assert all(frame.reference_kind == "pseudoreference" for frame in sequences["left"])
    assert sequences["right"][0].reference_tip_xy_mm == pytest.approx((14.90, 0.66))
    assert sequences["right"][0].reference_derivation == "direct_pseudoreference"
    assert sequences["right"][1].reference_derivation == "propagated_by_legacy_pipeline"
    assert sequences["right"][1].reference_source_stage == "55"
    assert sequences["right"][2].reference_source_stage == "55"


class _InferenceProbe:
    def __init__(self, pixels: int = 4) -> None:
        self.calls = 0
        self.pixels = pixels

    def predict(self, batch, *, include_path):
        self.calls += 1
        assert include_path is False
        assert tuple(batch.shape) == (1, 2, self.pixels, self.pixels)
        return SimpleNamespace(
            tip_probabilities=torch.ones((1, 1, self.pixels, self.pixels)),
            coordinate_outputs=torch.zeros((1, 2)),
        )


def _attempt_for_executor(side: str = "right") -> RoiAttempt:
    bounds = (
        PhysicalBounds(0.0, 10.0, -5.0, 5.0)
        if side == "right"
        else PhysicalBounds(-10.0, 0.0, -5.0, 5.0)
    )
    return RoiAttempt(
        frame_id=f"frame-{side}",
        attempt_id=0,
        state=RoiState.START,
        roi=PhysicalRoi.from_bounds(bounds),
        cycle_count=None,
        cycle_delta_from_last_accepted=None,
    )


def _executor_services(
    fields: np.ndarray,
    clocks: iter,
    *,
    expected_size_mm: float = 10.0,
    expected_pixels: int = 4,
) -> P2AttemptServices:
    def interpolate(data, *, size, offset, pixels, include_eps_vm):
        assert data == "dic-data"
        assert pixels == expected_pixels
        assert include_eps_vm is False
        assert abs(size) == pytest.approx(expected_size_mm)
        return np.empty((2, 4, 4)), fields, None

    def decode(probability, coordinate, *, config, model_pixels, original_pixels):
        assert tuple(probability.shape) == (1, expected_pixels, expected_pixels)
        assert tuple(coordinate.shape) == (2,)
        assert model_pixels == original_pixels == expected_pixels
        assert config == DecoderConfig.historical()
        return DecoderOutput(
            point_rc=((expected_pixels - 1) / 2.0, (expected_pixels - 1) / 2.0),
            ungated_point_rc=(
                (expected_pixels - 1) / 2.0,
                (expected_pixels - 1) / 2.0,
            ),
            mask_point_rc=(
                (expected_pixels - 1) / 2.0,
                (expected_pixels - 1) / 2.0,
            ),
            coordinate_point_rc=(
                (expected_pixels - 1) / 2.0,
                (expected_pixels - 1) / 2.0,
            ),
            mask_confidence=0.95,
            selected_region_score=0.95,
            selected_region_area=1,
            disagreement_px=0.0,
            uncertainty=0.05,
            invalid_reason=None,
        )

    return P2AttemptServices(
        interpolate=interpolate,
        preprocess=lambda values: torch.as_tensor(values).unsqueeze(0),
        decode_tip=decode,
        clock=lambda: next(clocks),
    )


def test_dic_attempt_executes_finite_fields_without_using_the_reference() -> None:
    fields = np.stack(
        [np.arange(16, dtype=float).reshape(4, 4), np.arange(16, dtype=float).reshape(4, 4) * 2]
    )
    inference = _InferenceProbe()
    attempt = _attempt_for_executor("left")
    frame = P2DicFrame(
        attempt.frame_id,
        "dic-data",
        "left",
        (-999.0, -999.0),
        "pseudoreference",
    )

    observation = execute_dic_attempt(
        frame,
        attempt=attempt,
        inference=inference,
        decoder_config=DecoderConfig.historical(),
        pixels=4,
        services=_executor_services(fields, iter((10.0, 10.25))),
    )

    assert inference.calls == 1
    assert observation.candidate_tip_xy_mm == pytest.approx((-5.0, 0.0))
    assert observation.finite_grid_fraction == 1.0
    assert observation.elapsed_seconds == pytest.approx(0.25)
    assert observation.decoder_invalid_reason is None


def test_dic_attempt_blocks_nonfinite_fields_before_neural_inference() -> None:
    fields = np.ones((2, 4, 4), dtype=float)
    fields[0, 0, 0] = np.nan
    inference = _InferenceProbe()
    attempt = _attempt_for_executor("right")
    frame = P2DicFrame(attempt.frame_id, "dic-data", "right", None, "none")

    observation = execute_dic_attempt(
        frame,
        attempt=attempt,
        inference=inference,
        decoder_config=DecoderConfig.historical(),
        pixels=4,
        services=_executor_services(fields, iter((20.0, 20.1))),
    )

    assert inference.calls == 0
    assert observation.candidate_tip_xy_mm is None
    assert observation.finite_grid_fraction == pytest.approx(15.0 / 16.0)
    assert observation.decoder_invalid_reason == "dic_field_precheck_failed"


def test_dic_attempt_blocks_near_constant_fields_at_the_frozen_gate_floor() -> None:
    fields = np.stack(
        [
            np.linspace(0.0, 1e-8, 16).reshape(4, 4),
            np.linspace(0.0, 2e-8, 16).reshape(4, 4),
        ]
    )
    inference = _InferenceProbe()
    attempt = _attempt_for_executor("right")
    frame = P2DicFrame(attempt.frame_id, "dic-data", "right", None, "none")

    observation = execute_dic_attempt(
        frame,
        attempt=attempt,
        inference=inference,
        decoder_config=DecoderConfig.historical(),
        minimum_channel_std_mm=1e-6,
        pixels=4,
        services=_executor_services(fields, iter((25.0, 25.1))),
    )

    assert inference.calls == 0
    assert observation.decoder_invalid_reason == "dic_field_precheck_failed"


def _executor_gate() -> GateConfig:
    return GateConfig(
        min_mask_mean_score=0.8,
        min_region_selection_score=0.8,
        min_mask_area_fraction=0.01,
        max_mask_area_fraction=0.2,
        max_head_disagreement_fraction=0.1,
        max_decoder_uncertainty=0.2,
        mask_score_marginal_band=0.05,
        head_disagreement_marginal_band=0.02,
        decoder_uncertainty_marginal_band=0.05,
        min_tip_roi_margin_mm=0.0,
        min_tip_search_margin_mm=0.0,
        min_finite_grid_fraction=1.0,
        min_channel_std_mm=1e-9,
        jump_noise_mm=1.0,
        max_growth_mm_per_cycle=1.0,
        max_jump_without_cycles_mm=10.0,
        max_jump_cap_mm=20.0,
        calibration_source="unit-test",
    )


def test_real_replay_attaches_reference_only_after_controller_completion() -> None:
    fields = np.stack(
        [np.arange(16, dtype=float).reshape(4, 4), np.arange(16, dtype=float).reshape(4, 4) * 2]
    )
    frame = P2DicFrame(
        "frame-right",
        "dic-data",
        "right",
        (5.0, 0.0),
        "pseudoreference",
    )
    services = _executor_services(fields, iter((30.0, 30.1)))

    records = replay_dic_sequence(
        (frame,),
        start_roi=_attempt_for_executor("right").roi,
        gate_config=_executor_gate(),
        variant=P2Variant.P2_1_START_RESET,
        inference=_InferenceProbe(),
        decoder_config=DecoderConfig.historical(),
        pixels=4,
        services=services,
    )

    assert len(records) == 1
    assert records[0].result.accepted_tip_xy_mm == pytest.approx((5.0, 0.0))
    assert records[0].reference_tip_xy_mm == (5.0, 0.0)
    assert "pseudoreference" in records[0].reference_source
    assert "evaluation-only" in records[0].reference_source


def test_fixed_roi_p1_baseline_uses_the_same_real_frames_without_p2_gates() -> None:
    base = np.arange(256 * 256, dtype=float).reshape(256, 256)
    fields = np.stack([base, base * 2.0])
    _, roi = side_rois("right")
    frame = P2DicFrame(
        "frame-right",
        "dic-data",
        "right",
        (35.0, 0.0),
        "pseudoreference",
    )

    result = evaluate_fixed_roi_p1(
        (frame,),
        roi=roi,
        inference=_InferenceProbe(256),
        decoder_config=DecoderConfig.historical(),
        model_artifact_sha256="a" * 64,
        p1_source_sha256="b" * 64,
        pixels=256,
        services=_executor_services(
            fields,
            iter((40.0, 40.2)),
            expected_size_mm=70.0,
            expected_pixels=256,
        ),
    )

    assert result["scenario"] == "same_frames_fixed_physical_roi"
    assert result["failure_rate"] == 0.0
    assert result["localization_error_mm"]["median"] == pytest.approx(0.0)
    assert result["model_artifact_sha256"] == "a" * 64
    assert result["p1_source_sha256"] == "b" * 64
    assert result["pixels"] == 256
    assert result["roi"]["extent_xy_mm"] == [70.0, 70.0]
    assert result["decoder_config"] == DecoderConfig.historical().to_dict()
    assert result["frames"][0]["reference_role"] == "evaluation_only"
    assert result["frames"][0]["elapsed_seconds"] == pytest.approx(0.2)


def test_fixed_roi_p1_baseline_rejects_nonfull_or_mixed_side_scenarios() -> None:
    right = P2DicFrame("right", object(), "right", None, "none")
    left = P2DicFrame("left", object(), "left", None, "none")

    with pytest.raises(ValueError, match="complete 70-mm"):
        evaluate_fixed_roi_p1(
            (right,),
            roi=_attempt_for_executor("right").roi,
            inference=_InferenceProbe(),
            decoder_config=DecoderConfig.historical(),
            model_artifact_sha256="a" * 64,
            p1_source_sha256="b" * 64,
        )
    with pytest.raises(ValueError, match="one specimen side"):
        evaluate_fixed_roi_p1(
            (right, left),
            roi=side_rois("right")[1],
            inference=_InferenceProbe(),
            decoder_config=DecoderConfig.historical(),
            model_artifact_sha256="a" * 64,
            p1_source_sha256="b" * 64,
        )


def test_candidate_gate_is_bound_to_p1_validation_and_explicit_engineering_limits() -> None:
    gate = p2_candidate_gate_config()

    assert gate.min_mask_mean_score == pytest.approx(0.85)
    assert gate.min_region_selection_score == pytest.approx(0.85)
    assert gate.min_mask_area_fraction == pytest.approx(7.0 / (256 * 256))
    assert gate.max_mask_area_fraction == pytest.approx(43.0 / (256 * 256))
    assert gate.max_jump_without_cycles_mm == pytest.approx(20.0)
    assert "P1 validation" in gate.calibration_source
    assert "engineering" in gate.calibration_source


@pytest.mark.parametrize(
    ("side", "start_bounds", "full_bounds"),
    [
        ("right", (0.0, 40.0, -20.0, 20.0), (0.0, 70.0, -35.0, 35.0)),
        ("left", (-40.0, 0.0, -20.0, 20.0), (-70.0, 0.0, -35.0, 35.0)),
    ],
)
def test_side_rois_define_a_40_mm_tracker_inside_a_70_mm_search(
    side: str,
    start_bounds: tuple[float, float, float, float],
    full_bounds: tuple[float, float, float, float],
) -> None:
    start, full = side_rois(side)

    assert (
        start.bounds.x_min_mm,
        start.bounds.x_max_mm,
        start.bounds.y_min_mm,
        start.bounds.y_max_mm,
    ) == start_bounds
    assert (
        full.bounds.x_min_mm,
        full.bounds.x_max_mm,
        full.bounds.y_min_mm,
        full.bounds.y_max_mm,
    ) == full_bounds
    assert start.search_bounds == full.search_bounds


def test_mendeley_manifest_keeps_sequence_assets_and_missing_tip_labels_distinct(
    tmp_path: Path,
) -> None:
    manifest = mendeley_evidence_manifest(tmp_path, verify_hashes=False)

    assert manifest["doi"] == "10.17632/dywwnjv22h.1"
    assert manifest["interpolated_pt_inspection"]["frames"] == 17897
    assert manifest["interpolated_pt_inspection"]["shape"] == [1, 2, 128, 128]
    assert manifest["interpolated_pt_inspection"]["nonfinite_frames"] == 1
    assert manifest["raw_csv_role"] == "required_for_new_physical_roi_interpolation"
    assert manifest["tip_label_status"] == "pending_annotation_and_adjudication"
    assert manifest["quantitative_roi_accuracy_reported"] is False
    assert "experiment_group_id" in manifest["annotation_manifest"]["split_invariants"][0]
    assert manifest["files"]["3. TrainedModel_PT.zip"]["download_policy"] == (
        "not_required_for_p2"
    )


def test_full_run_config_keeps_all_provenance_paths_explicit(tmp_path: Path) -> None:
    config = P2FullRunConfig(
        repository_root=tmp_path,
        p1_results_path=tmp_path / "p1.json",
        p0_results_path=tmp_path / "p0.json",
        mendeley_cache_root=tmp_path / "mendeley",
        device="cuda:0",
        verify_mendeley_hashes=False,
    )

    assert config.pixels == 256
    assert config.expanded_scale == pytest.approx(55.0 / 40.0)
    assert config.to_dict()["device"] == "cuda:0"
    assert config.to_dict()["verify_mendeley_hashes"] is False

    with pytest.raises(ValueError, match="pixels"):
        P2FullRunConfig(
            repository_root=tmp_path,
            p1_results_path=tmp_path / "p1.json",
            p0_results_path=tmp_path / "p0.json",
            mendeley_cache_root=tmp_path / "mendeley",
            device="cpu",
            pixels=128,
        )


def test_real_input_manifest_hashes_every_local_evidence_file(
    repository_root: Path,
) -> None:
    manifest = p2_input_artifact_manifest(
        repository_root,
        p0_results_path=(
            repository_root / "docs" / "ctd-optimization" / "p0-results.json"
        ),
        p1_results_path=(
            repository_root / "docs" / "ctd-optimization" / "p1-results.json"
        ),
    )

    assert manifest["content_addressed"] is True
    assert len(manifest["artifacts"]) == 13
    assert "repository/historical_mask/807" in manifest["artifacts"]
    assert "dummy2/nodemap/55" in manifest["artifacts"]
    assert all(
        len(item["sha256"]) == 64 and item["size_bytes"] > 0
        for item in manifest["artifacts"].values()
    )


def test_same_scenario_comparison_prevents_failure_only_optimization_claims() -> None:
    fields = np.stack(
        [
            np.arange(16, dtype=float).reshape(4, 4),
            np.arange(16, dtype=float).reshape(4, 4) * 2.0,
        ]
    )
    frames = tuple(
        P2DicFrame(
            f"frame-{index}",
            "dic-data",
            "right",
            (5.7, 0.0),
            "pseudoreference",
        )
        for index in range(3)
    )
    records = replay_dic_sequence(
        frames,
        start_roi=_attempt_for_executor("right").roi,
        gate_config=_executor_gate(),
        variant=P2Variant.P2_1_START_RESET,
        inference=_InferenceProbe(),
        decoder_config=DecoderConfig.historical(),
        pixels=4,
        services=_executor_services(
            fields,
            iter((0.0, 0.1, 1.0, 1.1, 2.0, 2.1)),
        ),
    )
    baseline = {
        "frames_evaluated": 3,
        "failures": 0,
        "failure_rate": 0.0,
        "localization_error_mm": {
            "count": 3,
            "median": 0.4,
            "p95": 0.4,
            "maximum": 0.4,
        },
        "frames": [
            {
                "frame_id": frame.frame_id,
                "success": True,
                "candidate_tip_xy_mm": [5.3, 0.0],
                "reference_tip_xy_mm": [5.7, 0.0],
                "reference_source": "pseudoreference; evaluation-only",
                "decoder_invalid_reason": None,
                "error_mm": 0.4,
            }
            for frame in frames
        ],
    }
    baseline["baseline_content_sha256"] = same_scenario_baseline_sha256(baseline)

    comparison = compare_same_scenario(records, baseline)

    assert comparison["failure_rate_non_degraded"] is True
    assert comparison["median_error_delta_mm"] == pytest.approx(0.3)
    assert comparison["p95_error_delta_mm"] == pytest.approx(0.3)
    assert comparison["success_population_same"] is True
    assert comparison["paired_comparable_frames"] == 3
    assert comparison["paired_error_delta_mm"]["median"] == pytest.approx(0.3)
    assert comparison["localization_non_degraded"] is False
    assert comparison["optimization_supported"] is False

    mismatched_population = copy.deepcopy(baseline)
    mismatched_population["frames"][0].update(
        {
            "success": False,
            "candidate_tip_xy_mm": None,
            "decoder_invalid_reason": "no_candidate",
            "error_mm": None,
        }
    )
    mismatched_population["failures"] = 1
    mismatched_population["failure_rate"] = 1.0 / 3.0
    mismatched_population["localization_error_mm"]["count"] = 2
    mismatched_population["baseline_content_sha256"] = (
        same_scenario_baseline_sha256(mismatched_population)
    )

    mismatch = compare_same_scenario(records, mismatched_population)

    assert mismatch["failure_rate_non_degraded"] is True
    assert mismatch["success_population_same"] is False
    assert mismatch["localization_non_degraded"] is False
    assert mismatch["optimization_supported"] is False


def test_same_scenario_comparison_rejects_reference_mismatch() -> None:
    fields = np.stack(
        [
            np.arange(16, dtype=float).reshape(4, 4),
            np.arange(16, dtype=float).reshape(4, 4) * 2.0,
        ]
    )
    frame = P2DicFrame(
        "frame-0",
        "dic-data",
        "right",
        (5.0, 0.0),
        "pseudoreference",
    )
    records = replay_dic_sequence(
        (frame,),
        start_roi=_attempt_for_executor("right").roi,
        gate_config=_executor_gate(),
        variant=P2Variant.P2_1_START_RESET,
        inference=_InferenceProbe(),
        decoder_config=DecoderConfig.historical(),
        pixels=4,
        services=_executor_services(fields, iter((0.0, 0.1))),
    )
    baseline = {
        "frames_evaluated": 1,
        "failures": 0,
        "failure_rate": 0.0,
        "frames": [
            {
                "frame_id": "frame-0",
                "success": True,
                "candidate_tip_xy_mm": [5.0, 0.0],
                "reference_tip_xy_mm": [6.0, 0.0],
                "reference_source": "pseudoreference; evaluation-only",
                "decoder_invalid_reason": None,
            }
        ],
    }
    baseline["baseline_content_sha256"] = same_scenario_baseline_sha256(baseline)

    with pytest.raises(ValueError, match="reference coordinates"):
        compare_same_scenario(records, baseline)

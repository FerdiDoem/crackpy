"""Validation-lock and metric tests for P1 decoder calibration."""

import json

import numpy as np
import pytest

from crackpy.benchmarking.ctd_calibration import (
    DecoderEvaluation,
    apply_frozen_decoder,
    calibrate_decoder,
    risk_coverage_analysis,
    select_best_evaluation,
)
from crackpy.benchmarking.ctd_decoders import (
    CoordinateConvention,
    DecoderConfig,
    RegionRule,
)


def _config(*, threshold: float = 0.5, fusion_weight: float = 0.0) -> DecoderConfig:
    return DecoderConfig(
        threshold=threshold,
        region_rule=RegionRule.MEAN_PROBABILITY,
        fusion_weight=fusion_weight,
        coordinate_convention=CoordinateConvention.MODEL_INDEX,
    )


def _evaluation(
    config: DecoderConfig,
    *,
    detection_rate: float,
    p95: float,
    median: float,
) -> DecoderEvaluation:
    successful = round(100 * detection_rate)
    return DecoderEvaluation(
        config=config,
        split="validation",
        references=100,
        successful_detections=successful,
        detection_failures=100 - successful,
        missing_references=0,
        detection_rate=detection_rate,
        mean_error_px=median,
        median_error_px=median,
        p95_error_px=p95,
        sample_records=(),
    )


@pytest.mark.parametrize("forbidden_split", ["test", "train", "testing"])
def test_calibrator_rejects_every_nonvalidation_split_before_decoding(
    forbidden_split: str,
) -> None:
    with pytest.raises(ValueError, match="validation split only"):
        calibrate_decoder(
            [],
            [],
            [],
            split=forbidden_split,
            model_pixels=5,
        )


def test_selection_prioritizes_detection_then_p95_then_median() -> None:
    simple = _config(fusion_weight=0.0)
    fused = _config(fusion_weight=0.5)

    detection_winner = select_best_evaluation(
        [
            _evaluation(simple, detection_rate=0.99, p95=1.0, median=0.5),
            _evaluation(fused, detection_rate=1.0, p95=50.0, median=40.0),
        ]
    )
    p95_winner = select_best_evaluation(
        [
            _evaluation(simple, detection_rate=1.0, p95=3.0, median=0.5),
            _evaluation(fused, detection_rate=1.0, p95=2.0, median=1.5),
        ]
    )
    median_winner = select_best_evaluation(
        [
            _evaluation(simple, detection_rate=1.0, p95=2.0, median=1.0),
            _evaluation(fused, detection_rate=1.0, p95=2.0, median=0.9),
        ]
    )

    assert detection_winner.config == fused
    assert p95_winner.config == fused
    assert median_winner.config == fused


def test_exact_metric_tie_is_deterministically_resolved_by_simplicity() -> None:
    simple = _evaluation(_config(fusion_weight=0.0), detection_rate=1.0, p95=2.0, median=1.0)
    fused = _evaluation(_config(fusion_weight=0.5), detection_rate=1.0, p95=2.0, median=1.0)

    assert select_best_evaluation([fused, simple]).config == simple.config
    assert select_best_evaluation([simple, fused]).config == simple.config


def test_detection_gate_uses_p95_within_admissible_candidates() -> None:
    accurate = _evaluation(
        _config(fusion_weight=0.0),
        detection_rate=0.995,
        p95=2.0,
        median=1.0,
    )
    always_finite_but_inaccurate = _evaluation(
        _config(fusion_weight=1.0),
        detection_rate=1.0,
        p95=50.0,
        median=20.0,
    )

    selected = select_best_evaluation(
        [always_finite_but_inaccurate, accurate],
        minimum_detection_rate=0.995,
    )

    assert selected.config == accurate.config


def test_risk_coverage_sorts_by_uncertainty_and_selects_a_validation_cutoff() -> None:
    analysis = risk_coverage_analysis(
        errors_px=[1.0, 3.0, 2.0],
        uncertainties=[0.1, 0.9, 0.2],
        minimum_coverage=2 / 3,
    )

    assert [point["coverage"] for point in analysis.curve] == pytest.approx([1 / 3, 2 / 3, 1.0])
    assert [point["risk_mean_error_px"] for point in analysis.curve] == pytest.approx([1.0, 1.5, 2.0])
    assert analysis.aurc == pytest.approx(1.5)
    assert analysis.pearson_error_correlation is not None
    assert analysis.pearson_error_correlation > 0.9
    assert analysis.spearman_error_correlation == pytest.approx(1.0)
    assert analysis.selected_uncertainty_threshold == pytest.approx(0.2)
    json.dumps(analysis.to_dict(), allow_nan=False)


def test_risk_coverage_handles_empty_and_constant_inputs_without_nan() -> None:
    empty = risk_coverage_analysis([], [], minimum_coverage=0.95)
    constant = risk_coverage_analysis([1.0, 1.0], [0.2, 0.2], minimum_coverage=0.5)

    assert empty.observations == 0
    assert empty.aurc is None
    assert empty.selected_uncertainty_threshold is None
    assert constant.pearson_error_correlation is None
    assert constant.spearman_error_correlation is None
    json.dumps(empty.to_dict(), allow_nan=False)
    json.dumps(constant.to_dict(), allow_nan=False)


def test_calibration_freezes_validation_choice_and_test_application_cannot_change_it() -> None:
    masks = np.zeros((3, 5, 5), dtype=float)
    masks[0, 0, 0] = 0.95
    masks[1, 2, 2] = 0.9
    masks[2, 4, 4] = 0.85
    coordinate_heads = np.asarray(
        [
            [-1.0, -1.0],
            [-0.2, -0.2],
            [0.6, 0.6],
        ]
    )
    references = [(0.0, 0.0), (2.0, 2.0), (4.0, 4.0)]
    candidates = [_config(fusion_weight=0.5), _config(fusion_weight=0.0)]

    calibration = calibrate_decoder(
        masks,
        coordinate_heads,
        references,
        split="val",
        model_pixels=5,
        original_pixels=5,
        candidate_configs=candidates,
        minimum_uncertainty_coverage=2 / 3,
        minimum_detection_rate=1.0,
    )
    frozen_payload = calibration.selected_config.to_dict()
    evaluation = apply_frozen_decoder(
        masks,
        coordinate_heads,
        references,
        split="test",
        config=calibration.selected_config,
        model_pixels=5,
        original_pixels=5,
    )

    assert calibration.source_split == "validation"
    assert calibration.selected_config.fusion_weight == 0.0
    assert calibration.selected_config.uncertainty_threshold is not None
    assert calibration.selection_metrics.successful_detections == 3
    assert calibration.risk_coverage.minimum_coverage == 1.0
    assert calibration.frozen_validation_metrics.successful_detections == 3
    assert calibration.frozen_validation_metrics.detection_rate >= 1.0
    assert evaluation.config.to_dict() == frozen_payload
    assert calibration.efficiency["connected_component_labelings_per_sample"] == 1
    json.dumps(calibration.to_dict(), allow_nan=False)
    json.dumps(evaluation.to_dict(), allow_nan=False)


def test_missing_references_and_invalid_head_values_remain_explicit_in_frozen_evaluation() -> None:
    masks = np.zeros((2, 3, 3), dtype=float)
    masks[0, 1, 1] = 0.9
    masks[1, 1, 1] = np.nan
    coordinates = np.asarray([[np.nan, 0.0], [0.0, 0.0]])

    evaluation = apply_frozen_decoder(
        masks,
        coordinates,
        [(1.0, 1.0), None],
        split="test",
        config=_config(),
        model_pixels=3,
    )

    assert evaluation.references == 1
    assert evaluation.successful_detections == 1
    assert evaluation.detection_failures == 0
    assert evaluation.missing_references == 1
    assert evaluation.sample_records[1]["invalid_reason"] == "invalid_probability_mask"
    json.dumps(evaluation.to_dict(), allow_nan=False)

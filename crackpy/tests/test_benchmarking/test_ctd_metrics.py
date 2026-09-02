"""Contract tests for CTD P0 metrics.

These tests deliberately keep the benchmark contract independent of CrackPy's
legacy training evaluation helpers, which skip unsuccessful detections.
"""

import json
import math

import numpy as np
import pytest

from crackpy.benchmarking.ctd_metrics import (
    _nearest_distances,
    angle_error_degrees,
    dice_score,
    hausdorff95_distance,
    intersection_over_union,
    path_distance,
    tip_metrics,
)


def test_tip_metrics_counts_successes_and_failures_without_hiding_failures():
    metrics = tip_metrics(
        predictions=[(3.0, 4.0), None, (0.0, 0.0)],
        references=[(0.0, 0.0), (1.0, 1.0), None],
        pixel_size_mm=0.5,
    )

    assert metrics.references == 2
    assert metrics.successful_detections == 1
    assert metrics.detection_failures == 1
    assert metrics.missing_references == 1
    assert metrics.detection_rate == 0.5
    assert metrics.error_px.count == 1
    assert metrics.error_px.mean == 5.0
    assert metrics.error_px.median == 5.0
    assert metrics.error_px.p95 == 5.0
    assert metrics.error_mm is not None
    assert metrics.error_mm.mean == 2.5


def test_tip_metrics_reports_empty_conditional_distribution_when_every_detection_fails():
    metrics = tip_metrics(predictions=[None], references=[(2.0, 3.0)])

    assert metrics.references == 1
    assert metrics.successful_detections == 0
    assert metrics.detection_failures == 1
    assert metrics.detection_rate == 0.0
    assert metrics.error_px.count == 0
    assert metrics.error_px.mean is None
    assert metrics.error_px.median is None
    assert metrics.error_px.p95 is None
    assert metrics.error_mm is None


def test_tip_metrics_result_is_strict_json_serializable():
    metrics = tip_metrics(predictions=[None], references=[(2.0, 3.0)])

    encoded = json.dumps(metrics.to_dict(), allow_nan=False)

    assert json.loads(encoded)["error_mm"] is None


@pytest.mark.parametrize(
    ("prediction", "reference", "expected"),
    [
        (np.array([[1, 0], [0, 1]], dtype=bool), np.array([[1, 0], [0, 1]], dtype=bool), 1.0),
        (np.array([[1, 0], [0, 0]], dtype=bool), np.array([[0, 1], [0, 0]], dtype=bool), 0.0),
        (np.zeros((2, 2), dtype=bool), np.zeros((2, 2), dtype=bool), 1.0),
        (np.zeros((2, 2), dtype=bool), np.array([[1, 0], [0, 0]], dtype=bool), 0.0),
    ],
)
def test_dice_score_handles_overlap_and_explicit_empty_cases(prediction, reference, expected):
    assert dice_score(prediction, reference) == expected


@pytest.mark.parametrize(
    ("prediction", "reference", "expected"),
    [
        (np.array([[1, 0], [0, 1]], dtype=bool), np.array([[1, 0], [0, 1]], dtype=bool), 1.0),
        (np.array([[1, 0], [0, 0]], dtype=bool), np.array([[0, 1], [0, 0]], dtype=bool), 0.0),
        (np.zeros((2, 2), dtype=bool), np.zeros((2, 2), dtype=bool), 1.0),
        (np.zeros((2, 2), dtype=bool), np.array([[1, 0], [0, 0]], dtype=bool), 0.0),
    ],
)
def test_intersection_over_union_handles_overlap_and_explicit_empty_cases(prediction, reference, expected):
    assert intersection_over_union(prediction, reference) == expected


@pytest.mark.parametrize(
    "invalid_mask",
    [np.array([[0.0, np.nan]]), np.array([[0.0, 0.25]]), np.array([[0, 2]])],
)
def test_overlap_metrics_reject_nonbinary_or_nonfinite_masks(invalid_mask):
    reference = np.zeros_like(invalid_mask)

    with pytest.raises(ValueError, match="binary"):
        dice_score(invalid_mask, reference)
    with pytest.raises(ValueError, match="binary"):
        intersection_over_union(invalid_mask, reference)


def test_path_distance_is_symmetric_mean_nearest_neighbour_distance():
    prediction = np.array([[0.0, 0.0], [2.0, 0.0]])
    reference = np.array([[0.0, 0.0], [1.0, 0.0]])

    assert path_distance(prediction, reference) == 0.5
    assert path_distance(reference, prediction) == 0.5


def test_path_distances_define_empty_cases_explicitly():
    empty = np.empty((0, 2))
    path = np.array([[0.0, 0.0]])

    assert path_distance(empty, empty) == 0.0
    assert path_distance(empty, path) is None
    assert hausdorff95_distance(empty, empty) == 0.0
    assert hausdorff95_distance(empty, path) is None


def test_hausdorff95_uses_both_directed_nearest_neighbour_sets():
    prediction = np.array([[0.0, 0.0], [1.0, 0.0], [10.0, 0.0]])
    reference = np.array([[0.0, 0.0], [1.0, 0.0]])

    assert hausdorff95_distance(prediction, reference) == pytest.approx(7.2)


def test_nearest_distance_avoids_dense_pairwise_tensor(monkeypatch):
    source = np.column_stack((np.arange(100.0), np.zeros(100)))
    target = np.column_stack((np.arange(100.0), np.ones(100)))
    original_sum = np.sum

    def reject_dense_pairwise_sum(values, *args, **kwargs):
        if np.asarray(values).ndim == 3:
            raise AssertionError("dense pairwise allocation")
        return original_sum(values, *args, **kwargs)

    monkeypatch.setattr(np, "sum", reject_dense_pairwise_sum)

    assert np.allclose(_nearest_distances(source, target), 1.0)


@pytest.mark.parametrize(
    ("prediction", "reference", "expected"),
    [(10.0, 170.0, 20.0), (0.0, 180.0, 0.0), (45.0, 135.0, 90.0)],
)
def test_angle_error_is_orientation_aware_modulo_180_degrees(prediction, reference, expected):
    assert angle_error_degrees(prediction, reference) == expected


def test_angle_error_returns_none_for_missing_or_nonfinite_angles():
    assert angle_error_degrees(None, 30.0) is None
    assert angle_error_degrees(math.nan, 30.0) is None

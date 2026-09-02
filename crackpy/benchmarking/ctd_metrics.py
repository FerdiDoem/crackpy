"""Serializable evaluation metrics for the CTD P0 benchmark.

The functions in this module deliberately do not reuse the legacy training
helpers: P0 must retain failed detections in its reported denominator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np
from numpy.typing import ArrayLike
from scipy.spatial import cKDTree

Point = tuple[float, float]


@dataclass(frozen=True)
class DistributionSummary:
    """Conditional distribution summary with JSON-native scalar values.

    ``count`` records the number of valid observations; all summary values are
    ``None`` when that conditional population is empty.
    """

    count: int
    mean: float | None
    median: float | None
    p95: float | None
    minimum: float | None
    maximum: float | None

    def to_dict(self) -> dict[str, int | float | None]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class TipMetrics:
    """Detection accounting and conditional localization errors for CTD tips.

    Failures are predictions missing for samples with a valid reference.
    Error summaries therefore remain explicitly conditional on successful
    detections and never silently remove failures from the detection rate.
    """

    references: int
    successful_detections: int
    detection_failures: int
    missing_references: int
    detection_rate: float | None
    error_px: DistributionSummary
    error_mm: DistributionSummary | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "references": self.references,
            "successful_detections": self.successful_detections,
            "detection_failures": self.detection_failures,
            "missing_references": self.missing_references,
            "detection_rate": self.detection_rate,
            "error_px": self.error_px.to_dict(),
            "error_mm": None if self.error_mm is None else self.error_mm.to_dict(),
        }


def tip_metrics(
    predictions: Sequence[Point | ArrayLike | None],
    references: Sequence[Point | ArrayLike | None],
    *,
    pixel_size_mm: float | None = None,
) -> TipMetrics:
    """Aggregate localization accuracy while preserving every failed detection.

    A non-finite or absent reference is counted as missing reference and is not
    part of the detection-rate denominator. A non-finite or absent prediction
    paired with a valid reference is an explicit detection failure.
    """

    if len(predictions) != len(references):
        raise ValueError("predictions and references must have the same length")
    if pixel_size_mm is not None and (not np.isfinite(pixel_size_mm) or pixel_size_mm <= 0):
        raise ValueError("pixel_size_mm must be finite and greater than zero")

    errors_px: list[float] = []
    references_count = 0
    successful = 0
    failures = 0
    missing_references = 0

    for prediction, reference in zip(predictions, references, strict=True):
        reference_point = _finite_point(reference)
        if reference_point is None:
            missing_references += 1
            continue

        references_count += 1
        prediction_point = _finite_point(prediction)
        if prediction_point is None:
            failures += 1
            continue

        successful += 1
        errors_px.append(float(np.linalg.norm(np.subtract(prediction_point, reference_point))))

    error_px = distribution_summary(errors_px)
    error_mm = None
    if pixel_size_mm is not None:
        error_mm = distribution_summary([error * pixel_size_mm for error in errors_px])

    return TipMetrics(
        references=references_count,
        successful_detections=successful,
        detection_failures=failures,
        missing_references=missing_references,
        detection_rate=None if references_count == 0 else successful / references_count,
        error_px=error_px,
        error_mm=error_mm,
    )


def distribution_summary(values: Iterable[float]) -> DistributionSummary:
    """Summarize finite values, returning explicit ``None`` values when empty."""

    array = np.asarray(list(values), dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return DistributionSummary(0, None, None, None, None, None)

    return DistributionSummary(
        count=int(finite.size),
        mean=float(np.mean(finite)),
        median=float(np.median(finite)),
        p95=float(np.percentile(finite, 95)),
        minimum=float(np.min(finite)),
        maximum=float(np.max(finite)),
    )


def dice_score(prediction: ArrayLike, reference: ArrayLike) -> float:
    """Return binary Dice overlap, defining two empty masks as a perfect match."""

    predicted_mask, reference_mask = _binary_masks(prediction, reference)
    predicted_count = int(np.count_nonzero(predicted_mask))
    reference_count = int(np.count_nonzero(reference_mask))
    denominator = predicted_count + reference_count
    if denominator == 0:
        return 1.0
    intersection = int(np.count_nonzero(predicted_mask & reference_mask))
    return 2.0 * intersection / denominator


def intersection_over_union(prediction: ArrayLike, reference: ArrayLike) -> float:
    """Return binary IoU, defining two empty masks as a perfect match."""

    predicted_mask, reference_mask = _binary_masks(prediction, reference)
    union = int(np.count_nonzero(predicted_mask | reference_mask))
    if union == 0:
        return 1.0
    intersection = int(np.count_nonzero(predicted_mask & reference_mask))
    return intersection / union


def path_distance(prediction: ArrayLike, reference: ArrayLike) -> float | None:
    """Return symmetric mean nearest-neighbour distance between two paths.

    Two empty paths are equal and score ``0.0``. A path compared with an empty
    counterpart is undefined and returns ``None`` instead of a fabricated value.
    """

    predicted_path, reference_path = _paths(prediction, reference)
    if predicted_path.size == 0 and reference_path.size == 0:
        return 0.0
    if predicted_path.size == 0 or reference_path.size == 0:
        return None

    directed = np.concatenate(
        (_nearest_distances(predicted_path, reference_path), _nearest_distances(reference_path, predicted_path))
    )
    return float(np.mean(directed))


def hausdorff95_distance(prediction: ArrayLike, reference: ArrayLike) -> float | None:
    """Return the 95th percentile of both directed nearest-neighbour distances.

    The empty-path policy matches :func:`path_distance`.
    """

    predicted_path, reference_path = _paths(prediction, reference)
    if predicted_path.size == 0 and reference_path.size == 0:
        return 0.0
    if predicted_path.size == 0 or reference_path.size == 0:
        return None

    directed = np.concatenate(
        (_nearest_distances(predicted_path, reference_path), _nearest_distances(reference_path, predicted_path))
    )
    return float(np.percentile(directed, 95))


def angle_error_degrees(prediction: float | None, reference: float | None) -> float | None:
    """Return the smallest orientation error in degrees modulo 180 degrees."""

    if prediction is None or reference is None:
        return None
    try:
        predicted_angle = float(prediction)
        reference_angle = float(reference)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(predicted_angle) or not np.isfinite(reference_angle):
        return None
    return float(abs((predicted_angle - reference_angle + 90.0) % 180.0 - 90.0))


def _finite_point(value: Point | ArrayLike | None) -> Point | None:
    """Normalize a two-coordinate value or return ``None`` for an invalid point."""

    if value is None:
        return None
    try:
        point = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if point.shape != (2,) or not np.all(np.isfinite(point)):
        return None
    return float(point[0]), float(point[1])


def _binary_masks(prediction: ArrayLike, reference: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Validate equal, already-binarized masks and convert them to booleans."""

    predicted_values = np.asarray(prediction)
    reference_values = np.asarray(reference)
    predicted_mask = _binary_mask(predicted_values, "prediction")
    reference_mask = _binary_mask(reference_values, "reference")
    if predicted_mask.shape != reference_mask.shape:
        raise ValueError("prediction and reference masks must have the same shape")
    return predicted_mask, reference_mask


def _binary_mask(values: np.ndarray, name: str) -> np.ndarray:
    """Reject probabilities, labels, and non-finite values before scoring."""

    try:
        is_binary = np.logical_or(values == 0, values == 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} mask must be binary") from exc
    if not np.all(is_binary):
        raise ValueError(f"{name} mask must be binary")
    return values.astype(bool, copy=False)


def _paths(prediction: ArrayLike, reference: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Validate and normalize a pair of finite ``(x, y)`` path arrays."""

    return _path_array(prediction, "prediction"), _path_array(reference, "reference")


def _path_array(path: ArrayLike, name: str) -> np.ndarray:
    """Validate a path with shape ``(n, 2)`` and finite coordinates."""

    array = np.asarray(path, dtype=float)
    if array.ndim != 2 or array.shape[1:] != (2,):
        raise ValueError(f"{name} path must have shape (n, 2)")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} path must contain only finite coordinates")
    return array


def _nearest_distances(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Compute nearest distances with bounded-memory spatial indexing."""

    tree = cKDTree(target)
    distances, _ = tree.query(source, k=1, workers=1)
    return np.asarray(distances, dtype=float)

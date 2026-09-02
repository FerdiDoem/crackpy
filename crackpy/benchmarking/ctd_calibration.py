"""Validation-only decoder calibration and confidence analysis for CTD P1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np
from scipy.stats import rankdata

from crackpy.benchmarking.ctd_decoders import (
    DecoderConfig,
    candidate_decoder_configs,
    decode_tip_grid,
    decoder_complexity_key,
)
from crackpy.benchmarking.ctd_metrics import distribution_summary

Point = tuple[float, float]


@dataclass(frozen=True)
class DecoderEvaluation:
    """Accuracy accounting for one immutable decoder on one named split.

    ``config`` is retained because metrics are meaningless without the exact
    threshold, region, fusion, coordinate, and confidence choices that made
    them.
    ``split`` distinguishes validation selection from untouched test evidence.
    ``references``, ``successful_detections``, ``detection_failures``, and
    ``missing_references`` keep all denominators explicit.
    ``detection_rate`` is the unconditional success fraction over valid
    references and is the primary failure-control quantity.
    ``mean_error_px``, ``median_error_px``, and ``p95_error_px`` summarize
    localization only for successful detections, matching the P0 contract.
    ``sample_records`` exists for the selected or frozen configuration only so
    diagnostics remain traceable without inflating every sweep candidate.
    """

    config: DecoderConfig
    split: str
    references: int
    successful_detections: int
    detection_failures: int
    missing_references: int
    detection_rate: float | None
    mean_error_px: float | None
    median_error_px: float | None
    p95_error_px: float | None
    sample_records: tuple[dict[str, Any], ...]

    def to_dict(self, *, include_samples: bool = True) -> dict[str, Any]:
        """Return a strict-JSON-native metric record."""

        result: dict[str, Any] = {
            "config": self.config.to_dict(),
            "split": self.split,
            "references": self.references,
            "successful_detections": self.successful_detections,
            "detection_failures": self.detection_failures,
            "missing_references": self.missing_references,
            "detection_rate": self.detection_rate,
            "error_px": {
                "mean": self.mean_error_px,
                "median": self.median_error_px,
                "p95": self.p95_error_px,
            },
        }
        if include_samples:
            result["samples"] = list(self.sample_records)
        return result


@dataclass(frozen=True)
class RiskCoverageAnalysis:
    """Conditional selective-risk evidence for one validation decoder.

    ``curve`` stores mean localization risk at every attainable confidence
    coverage after grouping equal uncertainty values.
    ``aurc`` is the right-continuous empirical area under that curve and exists
    as a scalar comparison metric without hiding the full curve.
    ``pearson_error_correlation`` and ``spearman_error_correlation`` quantify
    whether the uncertainty ordering tracks localization error linearly and by
    rank.
    ``selected_uncertainty_threshold`` is the validation-only cutoff with the
    lowest risk among points satisfying ``minimum_coverage``.
    ``observations`` and ``discarded_observations`` expose the exact conditional
    population used for these quantities.
    """

    curve: tuple[dict[str, float | int], ...]
    aurc: float | None
    pearson_error_correlation: float | None
    spearman_error_correlation: float | None
    selected_uncertainty_threshold: float | None
    minimum_coverage: float
    observations: int
    discarded_observations: int

    def to_dict(self) -> dict[str, Any]:
        """Return a strict-JSON-native confidence-analysis record."""

        return {
            "curve": list(self.curve),
            "aurc": self.aurc,
            "error_correlation": {
                "pearson": self.pearson_error_correlation,
                "spearman": self.spearman_error_correlation,
            },
            "selected_uncertainty_threshold": self.selected_uncertainty_threshold,
            "minimum_coverage": self.minimum_coverage,
            "observations": self.observations,
            "discarded_observations": self.discarded_observations,
            "population": "successful_detections_with_valid_references",
        }


@dataclass(frozen=True)
class CalibrationResult:
    """Frozen validation result ready for unchanged application to test data.

    ``selected_config`` contains the decoder frozen on validation for the P1
    default operating point without rejecting otherwise valid detections.
    ``confidence_gated_config`` adds the validation-only confidence cutoff for
    diagnostic selective-risk evidence and as a prospective P2 fallback
    trigger.
    ``selection_metrics`` records its ungated metrics because configuration
    selection precedes confidence rejection.
    ``confidence_gated_validation_metrics`` records what would happen if low
    confidence were treated as a hard rejection rather than a fallback signal.
    ``candidate_summaries`` keeps every predeclared comparison auditable.
    ``risk_coverage`` explains the confidence cutoff and its usefulness.
    ``source_split`` is fixed to validation as a technical leakage barrier.
    ``minimum_detection_rate`` records an optional admissibility gate derived
    outside this module, for example P0 detection minus 0.5 percentage points.
    ``efficiency`` proves the sweep shares mask labeling across region and
    fusion variants instead of repeating all decoder work.
    """

    selected_config: DecoderConfig
    confidence_gated_config: DecoderConfig
    selection_metrics: DecoderEvaluation
    confidence_gated_validation_metrics: DecoderEvaluation
    candidate_summaries: tuple[DecoderEvaluation, ...]
    risk_coverage: RiskCoverageAnalysis
    source_split: str
    minimum_detection_rate: float | None
    efficiency: dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        """Return the complete frozen calibration artifact in strict JSON form."""

        return {
            "source_split": self.source_split,
            "selected_config": self.selected_config.to_dict(),
            "confidence_gated_config": self.confidence_gated_config.to_dict(),
            "selection_objective": {
                "admissibility_gate": "minimum_detection_rate",
                "without_gate": ["detection_rate_desc", "p95_asc", "median_asc"],
                "within_gate": ["p95_asc", "median_asc", "simplicity"],
                "final_tie_break": "stable_config_values",
            },
            "minimum_detection_rate": self.minimum_detection_rate,
            "selection_metrics": self.selection_metrics.to_dict(),
            "confidence_gated_validation_metrics": (
                self.confidence_gated_validation_metrics.to_dict(
                    include_samples=False
                )
            ),
            "risk_coverage": self.risk_coverage.to_dict(),
            "candidate_summaries": [
                evaluation.to_dict(include_samples=False)
                for evaluation in self.candidate_summaries
            ],
            "efficiency": dict(self.efficiency),
            "test_split_used_for_selection": False,
        }


def calibrate_decoder(
    probability_masks: Sequence[Any] | Any,
    coordinate_heads: Sequence[Any] | Any,
    references: Sequence[Point | None] | Any,
    *,
    split: str,
    model_pixels: int,
    original_pixels: int | None = None,
    candidate_configs: Sequence[DecoderConfig] | None = None,
    minimum_uncertainty_coverage: float = 0.95,
    minimum_detection_rate: float | None = None,
) -> CalibrationResult:
    """Select and freeze one decoder using validation observations only.

    Component labels are cached per sample and threshold, so the complete
    predefined grid performs five labeling passes per valid mask rather than
    one pass for each of roughly one hundred fusion-region configurations.
    """

    source_split = _canonical_validation_split(split)
    masks, coordinates, reference_values = _validated_samples(
        probability_masks,
        coordinate_heads,
        references,
    )
    configs = _calibration_configs(candidate_configs)
    minimum_detection_rate = _validate_minimum_detection_rate(minimum_detection_rate)
    if original_pixels is None:
        original_pixels = model_pixels

    accumulators = {
        config: {"successful": 0, "failures": 0, "errors": []}
        for config in configs
    }
    reference_count = 0
    missing_references = 0
    total_labelings = 0
    for mask, coordinate, reference in zip(masks, coordinates, reference_values, strict=True):
        reference_point = _finite_point(reference)
        if reference_point is None:
            missing_references += 1
        else:
            reference_count += 1
        outputs, labelings = decode_tip_grid(
            mask,
            coordinate,
            configs=configs,
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )
        total_labelings += labelings
        if reference_point is None:
            continue
        for config, output in outputs.items():
            accumulator = accumulators[config]
            if output.point_rc is None:
                accumulator["failures"] += 1
                continue
            accumulator["successful"] += 1
            accumulator["errors"].append(_distance(output.point_rc, reference_point))

    summaries = tuple(
        _evaluation_from_counts(
            config=config,
            split=source_split,
            references=reference_count,
            successful=int(accumulators[config]["successful"]),
            failures=int(accumulators[config]["failures"]),
            missing_references=missing_references,
            errors=accumulators[config]["errors"],
        )
        for config in configs
    )
    selected_summary = select_best_evaluation(
        summaries,
        minimum_detection_rate=minimum_detection_rate,
    )
    selected_evaluation = evaluate_decoder_config(
        masks,
        coordinates,
        reference_values,
        split=source_split,
        config=selected_summary.config,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )
    selected_errors = [
        record["error_px"]
        for record in selected_evaluation.sample_records
        if record["error_px"] is not None
    ]
    selected_uncertainties = [
        record["uncertainty"]
        for record in selected_evaluation.sample_records
        if record["error_px"] is not None
    ]
    effective_uncertainty_coverage = float(minimum_uncertainty_coverage)
    if (
        minimum_detection_rate is not None
        and selected_evaluation.detection_rate is not None
        and selected_evaluation.detection_rate > 0.0
    ):
        effective_uncertainty_coverage = max(
            effective_uncertainty_coverage,
            minimum_detection_rate / selected_evaluation.detection_rate,
        )
    risk_coverage = risk_coverage_analysis(
        selected_errors,
        selected_uncertainties,
        minimum_coverage=min(effective_uncertainty_coverage, 1.0),
    )
    confidence_gated_config = selected_summary.config.with_uncertainty_threshold(
        risk_coverage.selected_uncertainty_threshold
    )
    confidence_gated_evaluation = evaluate_decoder_config(
        masks,
        coordinates,
        reference_values,
        split=source_split,
        config=confidence_gated_config,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )
    sample_count = len(masks)
    unique_thresholds = len({config.threshold for config in configs})
    naive_calls = sample_count * len(configs)
    return CalibrationResult(
        selected_config=selected_summary.config,
        confidence_gated_config=confidence_gated_config,
        selection_metrics=selected_evaluation,
        confidence_gated_validation_metrics=confidence_gated_evaluation,
        candidate_summaries=summaries,
        risk_coverage=risk_coverage,
        source_split=source_split,
        minimum_detection_rate=minimum_detection_rate,
        efficiency={
            "sample_count": sample_count,
            "candidate_configurations": len(configs),
            "unique_thresholds": unique_thresholds,
            "naive_decoder_calls": naive_calls,
            "connected_component_labelings": total_labelings,
            "connected_component_labelings_per_sample": (
                0.0 if sample_count == 0 else total_labelings / sample_count
            ),
            "labeling_reduction_factor": (
                0.0 if total_labelings == 0 else naive_calls / total_labelings
            ),
        },
    )


def evaluate_decoder_config(
    probability_masks: Sequence[Any] | Any,
    coordinate_heads: Sequence[Any] | Any,
    references: Sequence[Point | None] | Any,
    *,
    split: str,
    config: DecoderConfig,
    model_pixels: int,
    original_pixels: int | None = None,
) -> DecoderEvaluation:
    """Evaluate one fixed decoder without changing or selecting its parameters."""

    masks, coordinates, reference_values = _validated_samples(
        probability_masks,
        coordinate_heads,
        references,
    )
    if not isinstance(split, str) or not split.strip():
        raise ValueError("split must be a non-empty name")
    split_name = split.strip().lower()
    if split_name == "val":
        split_name = "validation"
    if original_pixels is None:
        original_pixels = model_pixels

    predictions: list[Point | None] = []
    finite_references: list[Point | None] = []
    records: list[dict[str, Any]] = []
    for index, (mask, coordinate, reference) in enumerate(
        zip(masks, coordinates, reference_values, strict=True)
    ):
        output = decode_tip_grid(
            mask,
            coordinate,
            configs=(config,),
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )[0][config]
        reference_point = _finite_point(reference)
        error = (
            None
            if output.point_rc is None or reference_point is None
            else _distance(output.point_rc, reference_point)
        )
        predictions.append(output.point_rc)
        finite_references.append(reference_point)
        record = {
            "index": index,
            "reference_available": reference_point is not None,
            "reference_tip_rc": _point_list(reference_point),
            "predicted_tip_rc": _point_list(output.point_rc),
            "error_px": error,
        }
        record.update(output.to_dict())
        records.append(record)
    return _evaluation_from_predictions(
        config=config,
        split=split_name,
        predictions=predictions,
        references=finite_references,
        records=records,
    )


def apply_frozen_decoder(
    probability_masks: Sequence[Any] | Any,
    coordinate_heads: Sequence[Any] | Any,
    references: Sequence[Point | None] | Any,
    *,
    split: str,
    config: DecoderConfig,
    model_pixels: int,
    original_pixels: int | None = None,
) -> DecoderEvaluation:
    """Apply a previously frozen configuration without any selection logic."""

    return evaluate_decoder_config(
        probability_masks,
        coordinate_heads,
        references,
        split=split,
        config=config,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )


def select_best_evaluation(
    evaluations: Sequence[DecoderEvaluation],
    *,
    minimum_detection_rate: float | None = None,
) -> DecoderEvaluation:
    """Choose deterministically by the frozen accuracy and simplicity policy.

    Without an admissibility gate, detection rate is maximized before P95 and
    median as required by the base P1 comparison contract.
    With a gate, only admissible configurations compete and P95, median, then
    implementation simplicity decide, preventing a poor coordinate-only head
    from winning solely because it always emits a finite value.
    """

    if not evaluations:
        raise ValueError("evaluations must not be empty")
    minimum_detection_rate = _validate_minimum_detection_rate(minimum_detection_rate)
    eligible = list(evaluations)
    if minimum_detection_rate is not None:
        eligible = [
            evaluation
            for evaluation in evaluations
            if evaluation.detection_rate is not None
            and evaluation.detection_rate >= minimum_detection_rate
        ]
        if not eligible:
            raise ValueError("no decoder configuration satisfies minimum_detection_rate")

    def stable_values(config: DecoderConfig) -> tuple[Any, ...]:
        return (
            config.threshold,
            config.region_rule.value,
            config.fusion_weight,
            config.coordinate_convention.value,
        )

    if minimum_detection_rate is None:
        key = lambda evaluation: (  # noqa: E731
            -_finite_or(evaluation.detection_rate, fallback=-1.0),
            _finite_or(evaluation.p95_error_px),
            _finite_or(evaluation.median_error_px),
            decoder_complexity_key(evaluation.config),
            stable_values(evaluation.config),
        )
    else:
        key = lambda evaluation: (  # noqa: E731
            _finite_or(evaluation.p95_error_px),
            _finite_or(evaluation.median_error_px),
            decoder_complexity_key(evaluation.config),
            stable_values(evaluation.config),
        )
    return min(eligible, key=key)


def risk_coverage_analysis(
    errors_px: Sequence[float] | Any,
    uncertainties: Sequence[float] | Any,
    *,
    minimum_coverage: float = 0.95,
) -> RiskCoverageAnalysis:
    """Build a grouped empirical risk-coverage curve and validation cutoff."""

    if not np.isfinite(minimum_coverage) or not 0.0 < minimum_coverage <= 1.0:
        raise ValueError("minimum_coverage must be finite and in (0, 1]")
    errors = np.asarray(list(errors_px), dtype=float)
    uncertainty_values = np.asarray(list(uncertainties), dtype=float)
    if errors.shape != uncertainty_values.shape or errors.ndim != 1:
        raise ValueError("errors_px and uncertainties must be one-dimensional and equally long")
    finite = np.isfinite(errors) & np.isfinite(uncertainty_values)
    discarded = int(len(errors) - np.count_nonzero(finite))
    errors = errors[finite]
    uncertainty_values = uncertainty_values[finite]
    if np.any(errors < 0):
        raise ValueError("errors_px must not be negative")
    if np.any((uncertainty_values < 0) | (uncertainty_values > 1)):
        raise ValueError("uncertainties must be between zero and one")
    if len(errors) == 0:
        return RiskCoverageAnalysis(
            curve=(),
            aurc=None,
            pearson_error_correlation=None,
            spearman_error_correlation=None,
            selected_uncertainty_threshold=None,
            minimum_coverage=float(minimum_coverage),
            observations=0,
            discarded_observations=discarded,
        )

    order = np.argsort(uncertainty_values, kind="stable")
    sorted_errors = errors[order]
    sorted_uncertainties = uncertainty_values[order]
    curve: list[dict[str, float | int]] = []
    cumulative_error = 0.0
    previous_index = 0
    aurc = 0.0
    index = 0
    while index < len(sorted_errors):
        threshold = sorted_uncertainties[index]
        group_end = index + 1
        while (
            group_end < len(sorted_errors)
            and sorted_uncertainties[group_end] == threshold
        ):
            group_end += 1
        cumulative_error += float(np.sum(sorted_errors[index:group_end]))
        coverage = group_end / len(sorted_errors)
        risk = cumulative_error / group_end
        aurc += risk * ((group_end - previous_index) / len(sorted_errors))
        curve.append(
            {
                "accepted": group_end,
                "coverage": float(coverage),
                "risk_mean_error_px": float(risk),
                "uncertainty_threshold": float(threshold),
            }
        )
        previous_index = group_end
        index = group_end

    eligible_points = [point for point in curve if point["coverage"] >= minimum_coverage]
    selected_point = min(
        eligible_points,
        key=lambda point: (
            point["risk_mean_error_px"],
            -point["coverage"],
            point["uncertainty_threshold"],
        ),
    )
    pearson = _correlation(errors, uncertainty_values)
    spearman = _correlation(rankdata(errors), rankdata(uncertainty_values))
    return RiskCoverageAnalysis(
        curve=tuple(curve),
        aurc=float(aurc),
        pearson_error_correlation=pearson,
        spearman_error_correlation=spearman,
        selected_uncertainty_threshold=float(selected_point["uncertainty_threshold"]),
        minimum_coverage=float(minimum_coverage),
        observations=int(len(errors)),
        discarded_observations=discarded,
    )


def _calibration_configs(
    configs: Sequence[DecoderConfig] | None,
) -> tuple[DecoderConfig, ...]:
    """Return stable unique ungated candidates from the predefined search space."""

    values = candidate_decoder_configs() if configs is None else tuple(configs)
    if not values:
        raise ValueError("candidate_configs must not be empty")
    if any(config.uncertainty_threshold is not None for config in values):
        raise ValueError("candidate configs must not contain a preselected uncertainty threshold")
    return tuple(dict.fromkeys(values))


def _canonical_validation_split(split: str) -> str:
    """Enforce the technical test-leakage barrier before any sample is touched."""

    if not isinstance(split, str) or split.strip().lower() not in {"val", "validation"}:
        raise ValueError("decoder calibration accepts the validation split only")
    return "validation"


def _validated_samples(
    masks: Sequence[Any] | Any,
    coordinates: Sequence[Any] | Any,
    references: Sequence[Any] | Any,
) -> tuple[list[Any], list[Any], list[Any]]:
    """Materialize three aligned sample sequences without changing their values."""

    try:
        mask_values = list(masks)
        coordinate_values = list(coordinates)
        reference_values = list(references)
    except TypeError as exc:
        raise ValueError("masks, coordinate heads, and references must be sample sequences") from exc
    if not (len(mask_values) == len(coordinate_values) == len(reference_values)):
        raise ValueError("masks, coordinate heads, and references must have equal sample counts")
    if not mask_values:
        raise ValueError("at least one sample is required")
    return mask_values, coordinate_values, reference_values


def _evaluation_from_predictions(
    *,
    config: DecoderConfig,
    split: str,
    predictions: Sequence[Point | None],
    references: Sequence[Point | None],
    records: Sequence[dict[str, Any]],
) -> DecoderEvaluation:
    """Build explicit detection and conditional-error metrics from sample values."""

    reference_count = 0
    successful = 0
    failures = 0
    missing = 0
    errors: list[float] = []
    for prediction, reference in zip(predictions, references, strict=True):
        if reference is None:
            missing += 1
            continue
        reference_count += 1
        if prediction is None:
            failures += 1
            continue
        successful += 1
        errors.append(_distance(prediction, reference))
    return _evaluation_from_counts(
        config=config,
        split=split,
        references=reference_count,
        successful=successful,
        failures=failures,
        missing_references=missing,
        errors=errors,
        records=records,
    )


def _evaluation_from_counts(
    *,
    config: DecoderConfig,
    split: str,
    references: int,
    successful: int,
    failures: int,
    missing_references: int,
    errors: Iterable[float],
    records: Sequence[dict[str, Any]] = (),
) -> DecoderEvaluation:
    """Create one summary from already-accounted detections and errors."""

    summary = distribution_summary(errors)
    return DecoderEvaluation(
        config=config,
        split=split,
        references=references,
        successful_detections=successful,
        detection_failures=failures,
        missing_references=missing_references,
        detection_rate=None if references == 0 else successful / references,
        mean_error_px=summary.mean,
        median_error_px=summary.median,
        p95_error_px=summary.p95,
        sample_records=tuple(records),
    )


def _validate_minimum_detection_rate(value: float | None) -> float | None:
    """Validate an optional externally derived detection admissibility gate."""

    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("minimum_detection_rate must be between zero and one") from exc
    if not np.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError("minimum_detection_rate must be between zero and one")
    return numeric


def _finite_point(value: Any) -> Point | None:
    """Normalize one finite two-coordinate reference or mark it unavailable."""

    if value is None:
        return None
    try:
        point = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if point.shape != (2,) or not np.all(np.isfinite(point)):
        return None
    return float(point[0]), float(point[1])


def _point_list(point: Point | None) -> list[float] | None:
    """Convert one optional point into a strict-JSON-native value."""

    return None if point is None else [float(point[0]), float(point[1])]


def _distance(first: Point, second: Point) -> float:
    """Return Euclidean localization error in reference-grid pixels."""

    return float(np.linalg.norm(np.subtract(first, second)))


def _finite_or(value: float | None, *, fallback: float = float("inf")) -> float:
    """Return a finite selection quantity or its explicit worst-case value."""

    if value is None or not np.isfinite(value):
        return fallback
    return float(value)


def _correlation(first: np.ndarray, second: np.ndarray) -> float | None:
    """Return Pearson correlation only when both finite series vary."""

    if len(first) < 2 or np.ptp(first) == 0 or np.ptp(second) == 0:
        return None
    value = float(np.corrcoef(first, second)[0, 1])
    return value if np.isfinite(value) else None

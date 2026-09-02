"""Additive crack-tip decoders for the frozen CTD P1 comparison.

Every public point returned by this module uses row-column coordinates on the
endpoint-inclusive original image index grid.
The historical endpoint convention remains explicit inside the configuration
so compatibility results cannot be confused with index-native alternatives.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from scipy.ndimage import label

from crackpy.benchmarking.ctd_baseline import (
    decode_historical_tip,
    denormalize_coordinate_head,
    map_legacy_decoder_point_to_original,
    map_model_index_point_to_original,
)

Point = tuple[float, float]
SUPPORTED_THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7)
SUPPORTED_FUSION_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


class RegionRule(str, Enum):
    """Connected-component selection rules evaluated without changing weights."""

    HISTORICAL_MEAN_PROBABILITY = "historical_mean_probability"
    MEAN_PROBABILITY = "mean_probability"
    PROBABILITY_MASS = "probability_mass"
    AREA = "area"
    NEAREST_COORDINATE_HEAD = "nearest_coordinate_head"


class CoordinateConvention(str, Enum):
    """Raw mask-coordinate conventions retained for auditable grid mapping."""

    LEGACY_ENDPOINT = "legacy_endpoint"
    MODEL_INDEX = "model_index"


@dataclass(frozen=True)
class DecoderConfig:
    """Immutable decoder choices selected only on validation data.

    ``threshold`` binarizes the probability mask and exists because connected
    regions, detection failures, and runtime depend on that operating point.
    ``region_rule`` states how one connected component is selected and exists
    to make the historical heuristic comparable with auditable alternatives.
    ``fusion_weight`` is the coordinate-head fraction in the final point and
    exists to include both single-head baselines and fixed linear fusions.
    ``coordinate_convention`` identifies whether the raw mask point follows
    CrackPy's endpoint-valued legacy grid or a true model-index grid so every
    result can be mapped to the same reference geometry without ambiguity.
    ``uncertainty_threshold`` is an optional validation-frozen rejection gate
    and exists to prevent a test split from choosing its own confidence cutoff.
    """

    threshold: float
    region_rule: RegionRule
    fusion_weight: float
    coordinate_convention: CoordinateConvention
    uncertainty_threshold: float | None = None

    def __post_init__(self) -> None:
        """Canonicalize enum/scalar inputs and reject undeclared sweep values."""

        try:
            region_rule = RegionRule(self.region_rule)
            coordinate_convention = CoordinateConvention(self.coordinate_convention)
        except ValueError as exc:
            raise ValueError("unsupported decoder enum value") from exc
        threshold = _canonical_choice(self.threshold, SUPPORTED_THRESHOLDS, "threshold")
        fusion_weight = _canonical_choice(
            self.fusion_weight,
            SUPPORTED_FUSION_WEIGHTS,
            "fusion weight",
        )
        uncertainty_threshold = self.uncertainty_threshold
        if uncertainty_threshold is not None:
            try:
                uncertainty_threshold = float(uncertainty_threshold)
            except (TypeError, ValueError) as exc:
                raise ValueError("uncertainty_threshold must be between zero and one") from exc
            if not np.isfinite(uncertainty_threshold) or not 0.0 <= uncertainty_threshold <= 1.0:
                raise ValueError("uncertainty_threshold must be between zero and one")

        if region_rule is RegionRule.HISTORICAL_MEAN_PROBABILITY:
            if threshold != 0.5 or fusion_weight != 0.0:
                raise ValueError("the historical decoder requires threshold 0.5 and mask-only fusion")
            if coordinate_convention is not CoordinateConvention.LEGACY_ENDPOINT:
                raise ValueError("the historical decoder requires the legacy endpoint convention")

        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "region_rule", region_rule)
        object.__setattr__(self, "fusion_weight", fusion_weight)
        object.__setattr__(self, "coordinate_convention", coordinate_convention)
        object.__setattr__(self, "uncertainty_threshold", uncertainty_threshold)

    @classmethod
    def historical(cls) -> DecoderConfig:
        """Return the unchanged CrackPy 1.3.0 mask-decoder contract."""

        return cls(
            threshold=0.5,
            region_rule=RegionRule.HISTORICAL_MEAN_PROBABILITY,
            fusion_weight=0.0,
            coordinate_convention=CoordinateConvention.LEGACY_ENDPOINT,
        )

    def with_uncertainty_threshold(self, value: float | None) -> DecoderConfig:
        """Return a new frozen configuration with one validation-selected gate."""

        payload = self.to_dict()
        payload["uncertainty_threshold"] = value
        return DecoderConfig.from_dict(payload)

    def to_dict(self) -> dict[str, float | str | None]:
        """Return a strict-JSON-native configuration payload."""

        return {
            "threshold": self.threshold,
            "region_rule": self.region_rule.value,
            "fusion_weight": self.fusion_weight,
            "coordinate_convention": self.coordinate_convention.value,
            "uncertainty_threshold": self.uncertainty_threshold,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DecoderConfig:
        """Restore a configuration while applying the same validation contract."""

        expected = {
            "threshold",
            "region_rule",
            "fusion_weight",
            "coordinate_convention",
            "uncertainty_threshold",
        }
        if set(payload) != expected:
            raise ValueError(f"decoder config fields must be exactly {sorted(expected)}")
        return cls(
            threshold=payload["threshold"],
            region_rule=payload["region_rule"],
            fusion_weight=payload["fusion_weight"],
            coordinate_convention=payload["coordinate_convention"],
            uncertainty_threshold=payload["uncertainty_threshold"],
        )


@dataclass(frozen=True)
class DecoderOutput:
    """One decoded point plus the evidence needed for confidence analysis.

    ``point_rc`` is the accepted original-grid prediction and becomes ``None``
    when a required head is invalid or the frozen uncertainty gate rejects it.
    ``ungated_point_rc`` preserves the same candidate before that optional gate
    so validation risk-coverage analysis never loses the underlying error.
    ``mask_point_rc`` and ``coordinate_point_rc`` expose the two head estimates
    because their disagreement is a central P1 and P2 confidence signal.
    ``mask_confidence`` is the selected region's mean probability, while
    ``selected_region_score`` records the actual rule-specific ranking value.
    ``selected_region_area`` provides a small-region diagnostic.
    ``disagreement_px`` is Euclidean head disagreement on the original grid.
    ``uncertainty`` combines missing evidence, mask confidence, and normalized
    disagreement into a finite zero-to-one ranking value.
    ``invalid_reason`` makes every failed or confidence-rejected prediction
    explicit instead of silently dropping it from evaluation.
    """

    point_rc: Point | None
    ungated_point_rc: Point | None
    mask_point_rc: Point | None
    coordinate_point_rc: Point | None
    mask_confidence: float | None
    selected_region_score: float | None
    selected_region_area: int | None
    disagreement_px: float | None
    uncertainty: float
    invalid_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-native values without non-finite sentinels."""

        payload = asdict(self)
        for name in ("point_rc", "ungated_point_rc", "mask_point_rc", "coordinate_point_rc"):
            point = payload[name]
            payload[name] = None if point is None else [float(point[0]), float(point[1])]
        return payload


@dataclass(frozen=True)
class _MaskRegion:
    point_model_rc: Point
    mean_probability: float
    selection_score: float
    area: int


@dataclass(frozen=True)
class _MaskComponent:
    label_index: int
    point_model_rc: Point
    mean_probability: float
    probability_mass: float
    area: int


def candidate_decoder_configs() -> tuple[DecoderConfig, ...]:
    """Return the complete predefined P1 decoder sweep in stable order."""

    configurations = [DecoderConfig.historical()]
    for threshold in SUPPORTED_THRESHOLDS:
        for rule in (
            RegionRule.MEAN_PROBABILITY,
            RegionRule.PROBABILITY_MASS,
            RegionRule.AREA,
            RegionRule.NEAREST_COORDINATE_HEAD,
        ):
            for fusion_weight in SUPPORTED_FUSION_WEIGHTS:
                configurations.append(
                    DecoderConfig(
                        threshold=threshold,
                        region_rule=rule,
                        fusion_weight=fusion_weight,
                        coordinate_convention=CoordinateConvention.MODEL_INDEX,
                    )
                )
    return tuple(configurations)


def decoder_complexity_key(config: DecoderConfig) -> tuple[int, int, float, int, str]:
    """Rank equal-accuracy configurations by a documented simplicity policy."""

    if config.region_rule is RegionRule.HISTORICAL_MEAN_PROBABILITY:
        return 0, 0, 0.0, 0, config.coordinate_convention.value
    fusion_complexity = 1 if config.fusion_weight in (0.0, 1.0) else 2
    rule_rank = {
        RegionRule.MEAN_PROBABILITY: 0,
        RegionRule.PROBABILITY_MASS: 1,
        RegionRule.AREA: 2,
        RegionRule.NEAREST_COORDINATE_HEAD: 3,
    }[config.region_rule]
    threshold_distance = abs(config.threshold - 0.5)
    fusion_rank = SUPPORTED_FUSION_WEIGHTS.index(config.fusion_weight)
    return fusion_complexity, rule_rank, threshold_distance, fusion_rank, config.coordinate_convention.value


def decode_tip(
    probability_mask: Any,
    coordinate_head: Sequence[float] | Any,
    *,
    config: DecoderConfig,
    model_pixels: int,
    original_pixels: int | None = None,
) -> DecoderOutput:
    """Decode both frozen heads and apply one immutable P1 decoder contract."""

    if not isinstance(model_pixels, int) or isinstance(model_pixels, bool) or model_pixels <= 1:
        raise ValueError("model_pixels must be an integer greater than one")
    if original_pixels is None:
        original_pixels = model_pixels
    if not isinstance(original_pixels, int) or isinstance(original_pixels, bool) or original_pixels <= 1:
        raise ValueError("original_pixels must be an integer greater than one")

    values = _single_probability_mask(probability_mask)
    coordinate_model = _coordinate_model_point(coordinate_head, model_pixels=model_pixels)
    coordinate_original = map_model_index_point_to_original(
        coordinate_model,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )

    if values is None:
        return _invalid_probability_output(config, coordinate_original)
    if values.shape != (model_pixels, model_pixels):
        raise ValueError("probability mask dimensions must match model_pixels")

    region = _decode_mask_region(
        values,
        config=config,
        coordinate_model_rc=coordinate_model,
    )
    mask_original = _map_mask_point(
        region,
        config=config,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
        probability_mask=values,
    )
    disagreement = _point_distance(mask_original, coordinate_original)
    uncertainty = _decoder_uncertainty(
        mask_confidence=None if region is None else region.mean_probability,
        disagreement_px=disagreement,
        mask_available=mask_original is not None,
        original_pixels=original_pixels,
    )

    ungated, reason = _fuse_points(
        mask_original,
        coordinate_original,
        config=config,
    )
    point = ungated
    if (
        point is not None
        and config.uncertainty_threshold is not None
        and uncertainty > config.uncertainty_threshold
    ):
        point = None
        reason = "uncertainty_threshold_exceeded"

    return DecoderOutput(
        point_rc=point,
        ungated_point_rc=ungated,
        mask_point_rc=mask_original,
        coordinate_point_rc=coordinate_original,
        mask_confidence=None if region is None else region.mean_probability,
        selected_region_score=None if region is None else region.selection_score,
        selected_region_area=None if region is None else region.area,
        disagreement_px=disagreement,
        uncertainty=uncertainty,
        invalid_reason=reason,
    )


def decode_tip_grid(
    probability_mask: Any,
    coordinate_head: Sequence[float] | Any,
    *,
    configs: Sequence[DecoderConfig],
    model_pixels: int,
    original_pixels: int | None = None,
) -> tuple[dict[DecoderConfig, DecoderOutput], int]:
    """Decode a configuration grid with one component labeling per threshold.

    The returned integer is the number of connected-component labeling passes.
    It makes the full validation sweep's bounded work explicit for reporting.
    """

    if not configs:
        raise ValueError("configs must contain at least one decoder configuration")
    if not isinstance(model_pixels, int) or isinstance(model_pixels, bool) or model_pixels <= 1:
        raise ValueError("model_pixels must be an integer greater than one")
    if original_pixels is None:
        original_pixels = model_pixels
    if not isinstance(original_pixels, int) or isinstance(original_pixels, bool) or original_pixels <= 1:
        raise ValueError("original_pixels must be an integer greater than one")

    stable_configs = tuple(dict.fromkeys(configs))
    values = _single_probability_mask(probability_mask)
    coordinate_model = _coordinate_model_point(coordinate_head, model_pixels=model_pixels)
    coordinate_original = map_model_index_point_to_original(
        coordinate_model,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )
    if values is None:
        return {
            config: _invalid_probability_output(config, coordinate_original)
            for config in stable_configs
        }, 0
    if values.shape != (model_pixels, model_pixels):
        raise ValueError("probability mask dimensions must match model_pixels")

    thresholds = tuple(dict.fromkeys(config.threshold for config in stable_configs))
    components_by_threshold = {
        threshold: _components_for_threshold(values, threshold)
        for threshold in thresholds
    }
    outputs: dict[DecoderConfig, DecoderOutput] = {}
    for config in stable_configs:
        region = _select_mask_region(
            components_by_threshold[config.threshold],
            config=config,
            coordinate_model_rc=coordinate_model,
        )
        mask_original = _map_cached_mask_point(
            region,
            config=config,
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )
        disagreement = _point_distance(mask_original, coordinate_original)
        uncertainty = _decoder_uncertainty(
            mask_confidence=None if region is None else region.mean_probability,
            disagreement_px=disagreement,
            mask_available=mask_original is not None,
            original_pixels=original_pixels,
        )
        ungated, reason = _fuse_points(mask_original, coordinate_original, config=config)
        point = ungated
        if (
            point is not None
            and config.uncertainty_threshold is not None
            and uncertainty > config.uncertainty_threshold
        ):
            point = None
            reason = "uncertainty_threshold_exceeded"
        outputs[config] = DecoderOutput(
            point_rc=point,
            ungated_point_rc=ungated,
            mask_point_rc=mask_original,
            coordinate_point_rc=coordinate_original,
            mask_confidence=None if region is None else region.mean_probability,
            selected_region_score=None if region is None else region.selection_score,
            selected_region_area=None if region is None else region.area,
            disagreement_px=disagreement,
            uncertainty=uncertainty,
            invalid_reason=reason,
        )
    return outputs, len(thresholds)


def _single_probability_mask(value: Any) -> np.ndarray | None:
    """Normalize one model mask and distinguish malformed values from emptiness."""

    if isinstance(value, torch.Tensor):
        array = value.detach().to("cpu").numpy()
    else:
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError):
            return None
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if (
        array.ndim != 2
        or not np.all(np.isfinite(array))
        or np.any(array < 0.0)
        or np.any(array > 1.0)
    ):
        return None
    return np.asarray(array, dtype=float)


def _coordinate_model_point(value: Any, *, model_pixels: int) -> Point | None:
    """Decode one coordinate head while treating malformed output as unavailable."""

    try:
        return denormalize_coordinate_head(value, model_pixels=model_pixels)
    except (TypeError, ValueError, RuntimeError):
        return None


def _invalid_probability_output(
    config: DecoderConfig,
    coordinate_original: Point | None,
) -> DecoderOutput:
    """Keep the independent coordinate baseline usable when only its peer fails."""

    coordinate_only = config.fusion_weight == 1.0 and coordinate_original is not None
    ungated = coordinate_original if coordinate_only else None
    point = ungated
    reason = None if coordinate_only else "invalid_probability_mask"
    if (
        point is not None
        and config.uncertainty_threshold is not None
        and 1.0 > config.uncertainty_threshold
    ):
        point = None
        reason = "uncertainty_threshold_exceeded"
    return DecoderOutput(
        point_rc=point,
        ungated_point_rc=ungated,
        mask_point_rc=None,
        coordinate_point_rc=coordinate_original,
        mask_confidence=None,
        selected_region_score=None,
        selected_region_area=None,
        disagreement_px=None,
        uncertainty=1.0,
        invalid_reason=reason,
    )


def _decode_mask_region(
    probabilities: np.ndarray,
    *,
    config: DecoderConfig,
    coordinate_model_rc: Point | None,
) -> _MaskRegion | None:
    """Select one connected mask region and retain its auditable evidence."""

    components = _components_for_threshold(probabilities, config.threshold)
    return _select_mask_region(
        components,
        config=config,
        coordinate_model_rc=coordinate_model_rc,
    )


def _components_for_threshold(
    probabilities: np.ndarray,
    threshold: float,
) -> tuple[_MaskComponent, ...]:
    """Label a thresholded mask once and compute reusable component evidence."""

    labels, count = label(probabilities >= threshold)
    components: list[_MaskComponent] = []
    for region_index in range(1, count + 1):
        region_mask = labels == region_index
        region_probabilities = probabilities[region_mask]
        area = int(region_probabilities.size)
        mass = float(np.sum(region_probabilities))
        rows, columns = np.nonzero(region_mask)
        components.append(
            _MaskComponent(
                label_index=region_index,
                point_model_rc=(
                    float(np.sum(rows * region_probabilities) / mass),
                    float(np.sum(columns * region_probabilities) / mass),
                ),
                mean_probability=mass / area,
                probability_mass=mass,
                area=area,
            )
        )
    return tuple(components)


def _select_mask_region(
    components: Sequence[_MaskComponent],
    *,
    config: DecoderConfig,
    coordinate_model_rc: Point | None,
) -> _MaskRegion | None:
    """Apply one region ranking without repeating connected-component labeling."""

    candidates: list[tuple[int, _MaskRegion]] = []
    for component in components:
        if config.region_rule in (
            RegionRule.HISTORICAL_MEAN_PROBABILITY,
            RegionRule.MEAN_PROBABILITY,
        ):
            score = component.mean_probability
        elif config.region_rule is RegionRule.PROBABILITY_MASS:
            score = component.probability_mass
        elif config.region_rule is RegionRule.AREA:
            score = float(component.area)
        else:
            if coordinate_model_rc is None:
                continue
            score = -float(
                np.linalg.norm(np.subtract(component.point_model_rc, coordinate_model_rc))
            )
        candidates.append(
            (
                component.label_index,
                _MaskRegion(
                    point_model_rc=component.point_model_rc,
                    mean_probability=component.mean_probability,
                    selection_score=score,
                    area=component.area,
                ),
            )
        )
    if not candidates:
        return None
    if config.region_rule is RegionRule.HISTORICAL_MEAN_PROBABILITY:
        return max(candidates, key=lambda candidate: (candidate[1].selection_score, candidate[0]))[1]
    return max(candidates, key=lambda candidate: (candidate[1].selection_score, -candidate[0]))[1]


def _map_cached_mask_point(
    region: _MaskRegion | None,
    *,
    config: DecoderConfig,
    model_pixels: int,
    original_pixels: int,
) -> Point | None:
    """Map cached component centroids without re-running the historical labeler."""

    if region is None:
        return None
    if config.coordinate_convention is CoordinateConvention.MODEL_INDEX:
        return map_model_index_point_to_original(
            region.point_model_rc,
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )
    endpoint_scale = model_pixels / (model_pixels - 1)
    return map_legacy_decoder_point_to_original(
        (
            region.point_model_rc[0] * endpoint_scale,
            region.point_model_rc[1] * endpoint_scale,
        ),
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )


def _map_mask_point(
    region: _MaskRegion | None,
    *,
    config: DecoderConfig,
    model_pixels: int,
    original_pixels: int,
    probability_mask: np.ndarray,
) -> Point | None:
    """Map a selected component through its declared raw coordinate convention."""

    if region is None:
        return None
    if config.region_rule is RegionRule.HISTORICAL_MEAN_PROBABILITY:
        historical = decode_historical_tip(
            torch.as_tensor(probability_mask, dtype=torch.float64).reshape(
                1,
                1,
                model_pixels,
                model_pixels,
            )
        )
        return map_legacy_decoder_point_to_original(
            historical,
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )
    if config.coordinate_convention is CoordinateConvention.MODEL_INDEX:
        return map_model_index_point_to_original(
            region.point_model_rc,
            model_pixels=model_pixels,
            original_pixels=original_pixels,
        )
    endpoint_scale = model_pixels / (model_pixels - 1)
    legacy_point = (
        region.point_model_rc[0] * endpoint_scale,
        region.point_model_rc[1] * endpoint_scale,
    )
    return map_legacy_decoder_point_to_original(
        legacy_point,
        model_pixels=model_pixels,
        original_pixels=original_pixels,
    )


def _fuse_points(
    mask_point: Point | None,
    coordinate_point: Point | None,
    *,
    config: DecoderConfig,
) -> tuple[Point | None, str | None]:
    """Apply fixed linear fusion and state exactly why a required head failed."""

    weight = config.fusion_weight
    if weight == 0.0:
        if mask_point is None:
            if (
                config.region_rule is RegionRule.NEAREST_COORDINATE_HEAD
                and coordinate_point is None
            ):
                return None, "coordinate_head_required_for_region_rule"
            return None, "mask_detection_unavailable"
        return mask_point, None
    if weight == 1.0:
        if coordinate_point is None:
            return None, "coordinate_head_required"
        return coordinate_point, None
    if mask_point is None:
        return None, "mask_detection_unavailable"
    if coordinate_point is None:
        return None, "coordinate_head_required"
    return (
        (1.0 - weight) * mask_point[0] + weight * coordinate_point[0],
        (1.0 - weight) * mask_point[1] + weight * coordinate_point[1],
    ), None


def _decoder_uncertainty(
    *,
    mask_confidence: float | None,
    disagreement_px: float | None,
    mask_available: bool,
    original_pixels: int,
) -> float:
    """Combine independent confidence warnings on one bounded ranking scale."""

    if not mask_available or mask_confidence is None:
        return 1.0
    uncertainty = float(np.clip(1.0 - mask_confidence, 0.0, 1.0))
    if disagreement_px is not None:
        diagonal = np.sqrt(2.0) * (original_pixels - 1)
        uncertainty = max(uncertainty, float(np.clip(disagreement_px / diagonal, 0.0, 1.0)))
    return uncertainty


def _point_distance(first: Point | None, second: Point | None) -> float | None:
    """Return finite Euclidean disagreement only when both heads are valid."""

    if first is None or second is None:
        return None
    return float(np.linalg.norm(np.subtract(first, second)))


def _canonical_choice(value: Any, supported: Sequence[float], name: str) -> float:
    """Return the declared float value or reject accidental sweep expansion."""

    if isinstance(value, bool):
        raise ValueError(f"unsupported {name}; expected one of {tuple(supported)}")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unsupported {name}; expected one of {tuple(supported)}") from exc
    for candidate in supported:
        if np.isclose(numeric, candidate, rtol=0.0, atol=1e-12):
            return candidate
    raise ValueError(f"unsupported {name}; expected one of {tuple(supported)}")

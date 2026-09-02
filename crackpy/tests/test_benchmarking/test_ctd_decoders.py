"""Behavioral tests for the additive P1 crack-tip decoders."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from crackpy.benchmarking.ctd_decoders import (
    CoordinateConvention,
    DecoderConfig,
    RegionRule,
    candidate_decoder_configs,
    decode_tip,
    decode_tip_grid,
)


def _config(
    *,
    threshold: float = 0.5,
    region_rule: RegionRule = RegionRule.MEAN_PROBABILITY,
    fusion_weight: float = 0.0,
    uncertainty_threshold: float | None = None,
) -> DecoderConfig:
    return DecoderConfig(
        threshold=threshold,
        region_rule=region_rule,
        fusion_weight=fusion_weight,
        coordinate_convention=CoordinateConvention.MODEL_INDEX,
        uncertainty_threshold=uncertainty_threshold,
    )


def test_historical_decoder_preserves_weighted_region_choice_and_geometry() -> None:
    probabilities = np.zeros((1, 1, 4, 4), dtype=np.float32)
    probabilities[0, 0, 0, :2] = 0.6
    probabilities[0, 0, 2, 2] = 0.9
    config = DecoderConfig.historical()

    decoded = decode_tip(
        probabilities,
        [np.nan, np.nan],
        config=config,
        model_pixels=4,
        original_pixels=4,
    )

    assert decoded.point_rc == pytest.approx((2.0, 2.0))
    assert decoded.mask_point_rc == pytest.approx((2.0, 2.0))
    assert decoded.coordinate_point_rc is None
    assert decoded.invalid_reason is None


@pytest.mark.parametrize(
    ("region_rule", "expected"),
    [
        (RegionRule.MEAN_PROBABILITY, (0.0, 0.5)),
        (RegionRule.PROBABILITY_MASS, (4.0, 3.0)),
        (RegionRule.AREA, (4.0, 3.0)),
        (RegionRule.NEAREST_COORDINATE_HEAD, (4.0, 3.0)),
    ],
)
def test_region_rules_select_the_declared_connected_component(
    region_rule: RegionRule,
    expected: tuple[float, float],
) -> None:
    probabilities = np.zeros((5, 5), dtype=float)
    probabilities[0, :2] = 0.8
    probabilities[4, 2:] = 0.7

    decoded = decode_tip(
        probabilities,
        [0.6, 0.2],
        config=_config(threshold=0.6, region_rule=region_rule),
        model_pixels=5,
        original_pixels=5,
    )

    assert decoded.point_rc == pytest.approx(expected)
    assert decoded.selected_region_area == (2 if region_rule is RegionRule.MEAN_PROBABILITY else 3)


def test_threshold_is_applied_before_connected_region_decoding() -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[1, 1] = 0.65

    detected = decode_tip(
        probabilities,
        [-1 / 3, -1 / 3],
        config=_config(threshold=0.6),
        model_pixels=3,
    )
    rejected = decode_tip(
        probabilities,
        [-1 / 3, -1 / 3],
        config=_config(threshold=0.7),
        model_pixels=3,
    )

    assert detected.point_rc == pytest.approx((1.0, 1.0))
    assert rejected.point_rc is None
    assert rejected.invalid_reason == "mask_detection_unavailable"


@pytest.mark.parametrize(
    ("fusion_weight", "expected"),
    [
        (0.0, (0.0, 0.0)),
        (0.25, (1.0, 1.0)),
        (0.5, (2.0, 2.0)),
        (0.75, (3.0, 3.0)),
        (1.0, (4.0, 4.0)),
    ],
)
def test_fusion_weight_is_the_coordinate_head_fraction(
    fusion_weight: float,
    expected: tuple[float, float],
) -> None:
    probabilities = np.zeros((5, 5), dtype=float)
    probabilities[0, 0] = 0.9

    decoded = decode_tip(
        probabilities,
        [0.6, 0.6],
        config=_config(fusion_weight=fusion_weight),
        model_pixels=5,
        original_pixels=5,
    )

    assert decoded.point_rc == pytest.approx(expected)
    assert decoded.disagreement_px == pytest.approx(np.sqrt(32.0))


def test_coordinate_only_decoder_survives_an_empty_mask_but_reports_maximum_uncertainty() -> None:
    decoded = decode_tip(
        np.zeros((5, 5), dtype=float),
        [0.6, 0.6],
        config=_config(fusion_weight=1.0),
        model_pixels=5,
    )

    assert decoded.point_rc == pytest.approx((4.0, 4.0))
    assert decoded.mask_point_rc is None
    assert decoded.uncertainty == 1.0
    assert decoded.invalid_reason is None


def test_invalid_coordinate_blocks_fusion_but_not_a_mask_only_decoder() -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[1, 1] = 0.8

    fused = decode_tip(
        probabilities,
        [np.nan, 0.0],
        config=_config(fusion_weight=0.5),
        model_pixels=3,
    )
    mask_only = decode_tip(
        probabilities,
        [np.nan, 0.0],
        config=_config(fusion_weight=0.0),
        model_pixels=3,
    )

    assert fused.point_rc is None
    assert fused.invalid_reason == "coordinate_head_required"
    assert mask_only.point_rc == pytest.approx((1.0, 1.0))
    assert mask_only.coordinate_point_rc is None
    assert mask_only.disagreement_px is None
    assert mask_only.uncertainty == pytest.approx(0.2)


def test_missing_or_malformed_coordinate_is_an_explicit_failed_head() -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[1, 1] = 0.8

    mask_only = decode_tip(
        probabilities,
        None,
        config=_config(fusion_weight=0.0),
        model_pixels=3,
    )
    fused = decode_tip(
        probabilities,
        ["not", "numeric"],
        config=_config(fusion_weight=0.5),
        model_pixels=3,
    )

    assert mask_only.point_rc == pytest.approx((1.0, 1.0))
    assert mask_only.coordinate_point_rc is None
    assert fused.point_rc is None
    assert fused.invalid_reason == "coordinate_head_required"


@pytest.mark.parametrize("coordinate", [[1.0, 0.0], [-1.1, 0.0], [0.0, 1.2]])
def test_coordinate_head_outside_model_grid_is_unavailable(
    coordinate: list[float],
) -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[1, 1] = 0.8

    coordinate_only = decode_tip(
        probabilities,
        coordinate,
        config=_config(fusion_weight=1.0),
        model_pixels=3,
    )
    mask_only = decode_tip(
        probabilities,
        coordinate,
        config=_config(fusion_weight=0.0),
        model_pixels=3,
    )

    assert coordinate_only.point_rc is None
    assert coordinate_only.invalid_reason == "coordinate_head_required"
    assert mask_only.point_rc == pytest.approx((1.0, 1.0))
    assert mask_only.coordinate_point_rc is None


def test_disagreement_contributes_to_uncertainty_and_the_frozen_gate_rejects_it() -> None:
    probabilities = np.zeros((5, 5), dtype=float)
    probabilities[0, 0] = 0.99

    decoded = decode_tip(
        probabilities,
        [0.6, 0.6],
        config=_config(fusion_weight=0.5, uncertainty_threshold=0.5),
        model_pixels=5,
    )

    assert decoded.ungated_point_rc == pytest.approx((2.0, 2.0))
    assert decoded.point_rc is None
    assert decoded.uncertainty == pytest.approx(1.0)
    assert decoded.invalid_reason == "uncertainty_threshold_exceeded"


def test_nonfinite_probability_values_are_explicitly_invalid() -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[0, 0] = np.inf

    decoded = decode_tip(
        probabilities,
        [0.0, 0.0],
        config=_config(),
        model_pixels=3,
    )

    assert decoded.point_rc is None
    assert decoded.invalid_reason == "invalid_probability_mask"
    assert decoded.uncertainty == 1.0


def test_coordinate_only_baseline_remains_independent_of_an_invalid_mask_head() -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[0, 0] = np.nan

    decoded = decode_tip(
        probabilities,
        [0.0, 0.0],
        config=_config(fusion_weight=1.0),
        model_pixels=3,
    )

    assert decoded.point_rc == pytest.approx((1.5, 1.5))
    assert decoded.mask_point_rc is None
    assert decoded.uncertainty == 1.0
    assert decoded.invalid_reason is None


@pytest.mark.parametrize("invalid_probability", [-0.01, 1.01])
def test_out_of_range_probability_values_are_explicitly_invalid(
    invalid_probability: float,
) -> None:
    probabilities = np.zeros((3, 3), dtype=float)
    probabilities[0, 0] = invalid_probability

    decoded = decode_tip(
        probabilities,
        [0.0, 0.0],
        config=_config(),
        model_pixels=3,
    )

    assert decoded.point_rc is None
    assert decoded.invalid_reason == "invalid_probability_mask"


def test_decoder_config_is_frozen_validated_and_strict_json_native() -> None:
    config = _config(
        threshold=0.3,
        region_rule=RegionRule.PROBABILITY_MASS,
        fusion_weight=0.75,
        uncertainty_threshold=0.4,
    )

    payload = config.to_dict()

    assert payload == {
        "threshold": 0.3,
        "region_rule": "probability_mass",
        "fusion_weight": 0.75,
        "coordinate_convention": "model_index",
        "uncertainty_threshold": 0.4,
    }
    assert DecoderConfig.from_dict(payload) == config
    with pytest.raises(FrozenInstanceError):
        config.threshold = 0.5  # type: ignore[misc]
    with pytest.raises(ValueError, match="supported threshold"):
        _config(threshold=0.55)
    with pytest.raises(ValueError, match="supported fusion weight"):
        _config(fusion_weight=0.1)
    with pytest.raises(ValueError, match="uncertainty_threshold"):
        _config(uncertainty_threshold=1.1)


def test_candidate_grid_contains_every_declared_threshold_rule_and_fusion_weight() -> None:
    configs = candidate_decoder_configs()

    assert {config.threshold for config in configs} >= {0.3, 0.4, 0.5, 0.6, 0.7}
    assert {config.region_rule for config in configs} >= {
        RegionRule.MEAN_PROBABILITY,
        RegionRule.PROBABILITY_MASS,
        RegionRule.AREA,
        RegionRule.NEAREST_COORDINATE_HEAD,
    }
    assert {config.fusion_weight for config in configs} >= {0.0, 0.25, 0.5, 0.75, 1.0}
    assert DecoderConfig.historical() in configs


def test_grid_decoder_matches_individual_decoders_and_labels_once_per_threshold() -> None:
    probabilities = np.zeros((5, 5), dtype=float)
    probabilities[0, :2] = 0.8
    probabilities[4, 2:] = 0.7
    configs = (
        DecoderConfig.historical(),
        _config(threshold=0.5, region_rule=RegionRule.PROBABILITY_MASS, fusion_weight=0.5),
        _config(threshold=0.7, region_rule=RegionRule.AREA, fusion_weight=1.0),
    )

    grid, labelings = decode_tip_grid(
        probabilities,
        [0.6, 0.2],
        configs=configs,
        model_pixels=5,
    )

    assert labelings == 2
    for config in configs:
        individual = decode_tip(
            probabilities,
            [0.6, 0.2],
            config=config,
            model_pixels=5,
        )
        assert grid[config].to_dict() == pytest.approx(individual.to_dict())

"""Deterministic physical ROI geometry and tracking policy for CTD P2.

The module deliberately contains no model inference, interpolation, reference
labels, plotting, or file I/O.  It therefore forms a small seam between the
state policy and the existing CrackPy 1.3.0 detector adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import TypeAlias


PointMm: TypeAlias = tuple[float, float]
PointRc: TypeAlias = tuple[float, float]

_GEOMETRY_TOLERANCE = 1e-9
_CONFIDENCE_DECODER_INVALID_REASONS = frozenset({"uncertainty_threshold_exceeded"})


@dataclass(frozen=True)
class PhysicalBounds:
    """Axis-aligned absolute specimen bounds in millimetres.

    The four fields describe an allowed physical search domain and are not
    mirrored detector coordinates.  Both axes must have a finite, strictly
    positive extent.
    """

    x_min_mm: float
    x_max_mm: float
    y_min_mm: float
    y_max_mm: float

    def __post_init__(self) -> None:
        values = (self.x_min_mm, self.x_max_mm, self.y_min_mm, self.y_max_mm)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("physical bounds must be finite")
        if self.x_min_mm >= self.x_max_mm or self.y_min_mm >= self.y_max_mm:
            raise ValueError("physical bounds must be strictly increasing")

    @property
    def center_xy_mm(self) -> PointMm:
        """Return the absolute centre of the rectangle."""

        return (
            (self.x_min_mm + self.x_max_mm) / 2.0,
            (self.y_min_mm + self.y_max_mm) / 2.0,
        )

    @property
    def extent_xy_mm(self) -> PointMm:
        """Return physical x/y side lengths."""

        return self.x_max_mm - self.x_min_mm, self.y_max_mm - self.y_min_mm

    def signed_margin_mm(self, point_xy_mm: PointMm) -> float:
        """Return the smallest signed distance from a point to an edge.

        A positive value is inside, zero is on an edge, and a negative value is
        outside.  The definition makes containment and safe-margin checks share
        one auditable convention.
        """

        x_mm, y_mm = _finite_point(point_xy_mm, name="point_xy_mm")
        return min(
            x_mm - self.x_min_mm,
            self.x_max_mm - x_mm,
            y_mm - self.y_min_mm,
            self.y_max_mm - y_mm,
        )

    def contains(self, point_xy_mm: PointMm, *, minimum_margin_mm: float = 0.0) -> bool:
        """Return whether a point has at least the requested physical margin."""

        margin = _finite_non_negative(minimum_margin_mm, name="minimum_margin_mm")
        return self.signed_margin_mm(point_xy_mm) + _GEOMETRY_TOLERANCE >= margin


@dataclass(frozen=True)
class PhysicalRoi:
    """One absolute physical detection rectangle inside an allowed search field.

    ``center_*`` identifies placement, while ``extent_*`` identifies physical
    size.  Keeping these concepts separate guarantees that P2.1 can move a
    window without accidentally resizing it.  ``search_bounds`` is carried with
    the ROI so every later decision can validate the same physical domain.
    """

    center_x_mm: float
    center_y_mm: float
    extent_x_mm: float
    extent_y_mm: float
    search_bounds: PhysicalBounds

    def __post_init__(self) -> None:
        values = (self.center_x_mm, self.center_y_mm, self.extent_x_mm, self.extent_y_mm)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("ROI centre and extent must be finite")
        if self.extent_x_mm <= 0.0 or self.extent_y_mm <= 0.0:
            raise ValueError("ROI extents must be positive")
        if not isinstance(self.search_bounds, PhysicalBounds):
            raise TypeError("search_bounds must be PhysicalBounds")
        bounds = self.bounds
        allowed = self.search_bounds
        if (
            bounds.x_min_mm < allowed.x_min_mm - _GEOMETRY_TOLERANCE
            or bounds.x_max_mm > allowed.x_max_mm + _GEOMETRY_TOLERANCE
            or bounds.y_min_mm < allowed.y_min_mm - _GEOMETRY_TOLERANCE
            or bounds.y_max_mm > allowed.y_max_mm + _GEOMETRY_TOLERANCE
        ):
            raise ValueError("ROI must lie inside search_bounds")

    @classmethod
    def from_bounds(
        cls,
        bounds: PhysicalBounds,
        *,
        search_bounds: PhysicalBounds | None = None,
    ) -> PhysicalRoi:
        """Construct a ROI from explicit edges, defaulting to its own search field."""

        allowed = bounds if search_bounds is None else search_bounds
        extent_x_mm, extent_y_mm = bounds.extent_xy_mm
        center_x_mm, center_y_mm = bounds.center_xy_mm
        return cls(center_x_mm, center_y_mm, extent_x_mm, extent_y_mm, allowed)

    @property
    def center_xy_mm(self) -> PointMm:
        """Return the absolute ROI centre."""

        return self.center_x_mm, self.center_y_mm

    @property
    def extent_xy_mm(self) -> PointMm:
        """Return physical x/y side lengths."""

        return self.extent_x_mm, self.extent_y_mm

    @property
    def bounds(self) -> PhysicalBounds:
        """Return edges derived from centre and extent."""

        half_x = self.extent_x_mm / 2.0
        half_y = self.extent_y_mm / 2.0
        return PhysicalBounds(
            self.center_x_mm - half_x,
            self.center_x_mm + half_x,
            self.center_y_mm - half_y,
            self.center_y_mm + half_y,
        )

    @property
    def diagonal_mm(self) -> float:
        """Return the physical diagonal used for normalized disagreement."""

        return math.hypot(self.extent_x_mm, self.extent_y_mm)

    def signed_margin_mm(self, point_xy_mm: PointMm) -> float:
        """Return the signed distance from a point to the nearest ROI edge."""

        return self.bounds.signed_margin_mm(point_xy_mm)

    def contains(self, point_xy_mm: PointMm, *, minimum_margin_mm: float = 0.0) -> bool:
        """Return whether the point lies safely inside this ROI."""

        return self.bounds.contains(point_xy_mm, minimum_margin_mm=minimum_margin_mm)

    def recentered_clamped(self, point_xy_mm: PointMm) -> PhysicalRoi:
        """Move towards a point while preserving size and staying in the search field."""

        target_x, target_y = _finite_point(point_xy_mm, name="point_xy_mm")
        half_x = self.extent_x_mm / 2.0
        half_y = self.extent_y_mm / 2.0
        center_x = min(
            max(target_x, self.search_bounds.x_min_mm + half_x),
            self.search_bounds.x_max_mm - half_x,
        )
        center_y = min(
            max(target_y, self.search_bounds.y_min_mm + half_y),
            self.search_bounds.y_max_mm - half_y,
        )
        return PhysicalRoi(
            center_x,
            center_y,
            self.extent_x_mm,
            self.extent_y_mm,
            self.search_bounds,
        )

    def scaled_clamped(self, factor: float) -> PhysicalRoi:
        """Scale about the current centre, cap to the search field, then clamp."""

        scale = float(factor)
        if not math.isfinite(scale) or scale <= 0.0:
            raise ValueError("scale factor must be finite and positive")
        search_extent_x, search_extent_y = self.search_bounds.extent_xy_mm
        extent_x = min(self.extent_x_mm * scale, search_extent_x)
        extent_y = min(self.extent_y_mm * scale, search_extent_y)
        center_x = min(
            max(self.center_x_mm, self.search_bounds.x_min_mm + extent_x / 2.0),
            self.search_bounds.x_max_mm - extent_x / 2.0,
        )
        center_y = min(
            max(self.center_y_mm, self.search_bounds.y_min_mm + extent_y / 2.0),
            self.search_bounds.y_max_mm - extent_y / 2.0,
        )
        scaled = PhysicalRoi(
            center_x_mm=center_x,
            center_y_mm=center_y,
            extent_x_mm=extent_x,
            extent_y_mm=extent_y,
            search_bounds=self.search_bounds,
        )
        return scaled

    def covers_search_bounds(self) -> bool:
        """Return whether this ROI is the complete declared search field."""

        return _bounds_close(self.bounds, self.search_bounds)

    def same_geometry(self, other: PhysicalRoi) -> bool:
        """Compare placement, extent, and declared search field with tight tolerance."""

        if not isinstance(other, PhysicalRoi):
            return False
        first = (*self.center_xy_mm, *self.extent_xy_mm)
        second = (*other.center_xy_mm, *other.extent_xy_mm)
        return all(
            math.isclose(left, right, abs_tol=_GEOMETRY_TOLERANCE, rel_tol=0.0)
            for left, right in zip(first, second, strict=True)
        ) and _bounds_close(self.search_bounds, other.search_bounds)


class GateReason(str, Enum):
    """Stable, machine-readable reasons why one ROI observation was rejected."""

    NONFINITE_FIELD = "nonfinite_field"
    FIELD_VARIATION_TOO_LOW = "field_variation_too_low"
    MISSING_TIP = "missing_tip"
    NONFINITE_TIP = "nonfinite_tip"
    TIP_OUTSIDE_ROI = "tip_outside_roi"
    TIP_NEAR_ROI_EDGE = "tip_near_roi_edge"
    TIP_OUTSIDE_SEARCH_BOUNDS = "tip_outside_search_bounds"
    TIP_NEAR_SEARCH_BOUNDARY = "tip_near_search_boundary"
    TIP_JUMP_TOO_LARGE = "tip_jump_too_large"
    MISSING_MASK_TIP = "missing_mask_tip"
    INVALID_MASK_TIP = "invalid_mask_tip"
    MISSING_COORDINATE_TIP = "missing_coordinate_tip"
    INVALID_COORDINATE_TIP = "invalid_coordinate_tip"
    MISSING_MASK_SCORE = "missing_mask_score"
    INVALID_MASK_SCORE = "invalid_mask_score"
    MASK_SCORE_TOO_LOW = "mask_score_too_low"
    MISSING_REGION_SELECTION_SCORE = "missing_region_selection_score"
    INVALID_REGION_SELECTION_SCORE = "invalid_region_selection_score"
    REGION_SELECTION_SCORE_TOO_LOW = "region_selection_score_too_low"
    MISSING_MASK_AREA = "missing_mask_area"
    INVALID_MASK_AREA = "invalid_mask_area"
    MASK_AREA_TOO_SMALL = "mask_area_too_small"
    MASK_AREA_TOO_LARGE = "mask_area_too_large"
    MISSING_HEAD_DISAGREEMENT = "missing_head_disagreement"
    INVALID_HEAD_DISAGREEMENT = "invalid_head_disagreement"
    HEAD_DISAGREEMENT_TOO_LARGE = "head_disagreement_too_large"
    INVALID_DECODER_UNCERTAINTY = "invalid_decoder_uncertainty"
    DECODER_UNCERTAINTY_TOO_HIGH = "decoder_uncertainty_too_high"
    DECODER_CONFIDENCE_THRESHOLD_EXCEEDED = "decoder_confidence_threshold_exceeded"
    DECODER_STRUCTURAL_INVALID = "decoder_structural_invalid"


@dataclass(frozen=True)
class RoiObservation:
    """Detector and DIC evidence for exactly one applied ROI attempt.

    Points use absolute specimen ``(x, y)`` coordinates in millimetres.
    ``mask_mean_score`` is a bounded neural score, not a calibrated
    probability.  ``region_selection_score`` remains diagnostic because its
    units depend on the frozen decoder rule.  Area and head disagreement are
    normalized so the same declared gate can be applied across input
    resolutions.  ``fusion_weight`` is the coordinate-head fraction of the
    candidate.  ``candidate_tip_xy_mm`` and both disagreement fields are
    validated against that fraction and the two heads; callers should use
    :meth:`from_decoder_heads` to derive them.  No reference or ground-truth
    value is accepted here, which prevents evaluation data from affecting
    tracking decisions.
    """

    frame_id: str
    attempt_id: int
    applied_roi: PhysicalRoi
    candidate_tip_xy_mm: PointMm | None
    mask_tip_xy_mm: PointMm | None
    coordinate_tip_xy_mm: PointMm | None
    mask_mean_score: float | None
    region_selection_score: float | None
    mask_area_fraction: float | None
    head_disagreement_fraction: float | None
    head_disagreement_mm: float | None
    decoder_uncertainty: float
    finite_grid_fraction: float
    channel_std_mm: PointMm
    cycle_delta_from_last_accepted: float | None
    elapsed_seconds: float
    decoder_invalid_reason: str | None
    fusion_weight: float = 0.0

    @classmethod
    def from_decoder_heads(
        cls,
        *,
        frame_id: str,
        attempt_id: int,
        applied_roi: PhysicalRoi,
        mask_tip_xy_mm: PointMm | None,
        coordinate_tip_xy_mm: PointMm | None,
        fusion_weight: float,
        mask_mean_score: float | None,
        region_selection_score: float | None,
        mask_area_fraction: float | None,
        decoder_uncertainty: float,
        finite_grid_fraction: float,
        channel_std_mm: PointMm,
        cycle_delta_from_last_accepted: float | None,
        elapsed_seconds: float,
        decoder_invalid_reason: str | None,
    ) -> RoiObservation:
        """Build one internally consistent observation from raw decoder heads.

        The factory is the preferred adapter seam: the candidate follows the
        decoder's declared linear fusion, while physical disagreement is
        derived from the absolute head coordinates and applied ROI diagonal.
        In particular, a mask-only ``fusion_weight`` of zero can never drift
        away from ``mask_tip_xy_mm``.
        """

        if not isinstance(applied_roi, PhysicalRoi):
            raise TypeError("applied_roi must be PhysicalRoi")
        mask_tip = _optional_numeric_point(mask_tip_xy_mm, name="mask_tip_xy_mm")
        coordinate_tip = _optional_numeric_point(
            coordinate_tip_xy_mm,
            name="coordinate_tip_xy_mm",
        )
        weight = _bounded_fraction(fusion_weight, name="fusion_weight")
        candidate = _fused_candidate_tip(mask_tip, coordinate_tip, weight)
        disagreement_mm, disagreement_fraction = _physical_head_disagreement(
            mask_tip,
            coordinate_tip,
            applied_roi=applied_roi,
        )
        return cls(
            frame_id=frame_id,
            attempt_id=attempt_id,
            applied_roi=applied_roi,
            candidate_tip_xy_mm=candidate,
            mask_tip_xy_mm=mask_tip,
            coordinate_tip_xy_mm=coordinate_tip,
            mask_mean_score=mask_mean_score,
            region_selection_score=region_selection_score,
            mask_area_fraction=mask_area_fraction,
            head_disagreement_fraction=disagreement_fraction,
            head_disagreement_mm=disagreement_mm,
            decoder_uncertainty=decoder_uncertainty,
            finite_grid_fraction=finite_grid_fraction,
            channel_std_mm=channel_std_mm,
            cycle_delta_from_last_accepted=cycle_delta_from_last_accepted,
            elapsed_seconds=elapsed_seconds,
            decoder_invalid_reason=decoder_invalid_reason,
            fusion_weight=weight,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise ValueError("frame_id must be a non-empty string")
        if (
            not isinstance(self.attempt_id, int)
            or isinstance(self.attempt_id, bool)
            or self.attempt_id < 0
        ):
            raise ValueError("attempt_id must be a non-negative integer")
        if not isinstance(self.applied_roi, PhysicalRoi):
            raise TypeError("applied_roi must be PhysicalRoi")
        for name in ("candidate_tip_xy_mm", "mask_tip_xy_mm", "coordinate_tip_xy_mm"):
            object.__setattr__(self, name, _optional_numeric_point(getattr(self, name), name=name))
        weight = _bounded_fraction(self.fusion_weight, name="fusion_weight")
        object.__setattr__(self, "fusion_weight", weight)
        expected_candidate = _fused_candidate_tip(
            self.mask_tip_xy_mm,
            self.coordinate_tip_xy_mm,
            weight,
        )
        if not _optional_points_match(self.candidate_tip_xy_mm, expected_candidate):
            raise ValueError("candidate tip is inconsistent with decoder heads and fusion_weight")
        object.__setattr__(self, "candidate_tip_xy_mm", expected_candidate)
        expected_disagreement_mm, expected_disagreement_fraction = (
            _physical_head_disagreement(
                self.mask_tip_xy_mm,
                self.coordinate_tip_xy_mm,
                applied_roi=self.applied_roi,
            )
        )
        object.__setattr__(
            self,
            "channel_std_mm",
            _numeric_point(self.channel_std_mm, name="channel_std_mm"),
        )
        for name in (
            "mask_mean_score",
            "region_selection_score",
            "mask_area_fraction",
            "head_disagreement_fraction",
            "head_disagreement_mm",
        ):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else float(value))
        if not _optional_scalars_match(
            self.head_disagreement_fraction,
            expected_disagreement_fraction,
        ):
            raise ValueError(
                "head disagreement fraction is inconsistent with physical decoder heads"
            )
        if not _optional_scalars_match(
            self.head_disagreement_mm,
            expected_disagreement_mm,
        ):
            raise ValueError("head disagreement mm is inconsistent with physical decoder heads")
        object.__setattr__(
            self,
            "head_disagreement_fraction",
            expected_disagreement_fraction,
        )
        object.__setattr__(self, "head_disagreement_mm", expected_disagreement_mm)
        object.__setattr__(self, "decoder_uncertainty", float(self.decoder_uncertainty))
        object.__setattr__(self, "finite_grid_fraction", float(self.finite_grid_fraction))
        cycle_delta = self.cycle_delta_from_last_accepted
        if cycle_delta is not None:
            cycle_delta = float(cycle_delta)
            if not math.isfinite(cycle_delta) or cycle_delta < 0.0:
                raise ValueError("cycle delta must be finite and non-negative")
            object.__setattr__(self, "cycle_delta_from_last_accepted", cycle_delta)
        elapsed = float(self.elapsed_seconds)
        if not math.isfinite(elapsed) or elapsed < 0.0:
            raise ValueError("elapsed_seconds must be finite and non-negative")
        object.__setattr__(self, "elapsed_seconds", elapsed)
        invalid_reason = self.decoder_invalid_reason
        if invalid_reason is not None:
            if not isinstance(invalid_reason, str):
                raise ValueError("decoder_invalid_reason must be a string or None")
            invalid_reason = invalid_reason.strip() or None
            object.__setattr__(self, "decoder_invalid_reason", invalid_reason)


@dataclass(frozen=True)
class GateDecision:
    """Auditable outcome of field, geometry, and detector-evidence gates.

    Williams eligibility means only that an otherwise valid geometric candidate
    failed detector evidence.  The controller never runs or accepts a Williams
    correction itself, and eligibility becomes actionable only after all ROI
    fallbacks for the frame have been exhausted.
    """

    accepted: bool
    field_ok: bool
    geometry_ok: bool
    evidence_ok: bool
    reasons: tuple[GateReason, ...]
    williams_eligible: bool
    tip_jump_mm: float | None
    max_tip_jump_mm: float | None
    roi_margin_mm: float | None
    search_margin_mm: float | None


@dataclass(frozen=True)
class GateConfig:
    """Explicit physical and validation-frozen acceptance thresholds.

    Score, area, disagreement, uncertainty, and finite-grid thresholds are
    dimensionless.  Tip margins, channel standard deviations, and jump limits
    are millimetres; the growth rate is millimetres per cycle.
    ``min_region_selection_score`` is optional because the selected-region
    score has decoder-rule-specific units.  Set it only from calibration for
    the frozen rule (for example a zero-to-one mean-probability rule); ``None``
    declares the signal diagnostic-only instead of silently applying a
    universal threshold.
    The three marginal bands do not relax normal acceptance: they only bound
    which near-threshold evidence failures may be reported as Williams
    eligible after all ROI fallbacks.  ``calibration_source`` binds every
    number to an auditable validation or engineering-policy artifact rather
    than an implicit default.
    """

    min_mask_mean_score: float
    min_region_selection_score: float | None
    min_mask_area_fraction: float
    max_mask_area_fraction: float
    max_head_disagreement_fraction: float
    max_decoder_uncertainty: float | None
    mask_score_marginal_band: float
    head_disagreement_marginal_band: float
    decoder_uncertainty_marginal_band: float
    min_tip_roi_margin_mm: float
    min_tip_search_margin_mm: float
    min_finite_grid_fraction: float
    min_channel_std_mm: float
    jump_noise_mm: float
    max_growth_mm_per_cycle: float
    max_jump_without_cycles_mm: float
    max_jump_cap_mm: float | None
    calibration_source: str

    def __post_init__(self) -> None:
        fraction_names = (
            "min_mask_mean_score",
            "min_mask_area_fraction",
            "max_mask_area_fraction",
            "max_head_disagreement_fraction",
            "min_finite_grid_fraction",
            "mask_score_marginal_band",
            "head_disagreement_marginal_band",
            "decoder_uncertainty_marginal_band",
        )
        for name in fraction_names:
            value = _bounded_fraction(getattr(self, name), name=name)
            object.__setattr__(self, name, value)
        if self.min_mask_area_fraction > self.max_mask_area_fraction:
            raise ValueError("minimum mask area must not exceed maximum mask area")
        selection_minimum = self.min_region_selection_score
        if selection_minimum is not None:
            object.__setattr__(
                self,
                "min_region_selection_score",
                _finite_non_negative(
                    selection_minimum,
                    name="min_region_selection_score",
                ),
            )
        uncertainty = self.max_decoder_uncertainty
        if uncertainty is not None:
            object.__setattr__(
                self,
                "max_decoder_uncertainty",
                _bounded_fraction(uncertainty, name="max_decoder_uncertainty"),
            )
        if self.mask_score_marginal_band > self.min_mask_mean_score:
            raise ValueError("mask score marginal band must stay inside the unit interval")
        if (
            self.head_disagreement_marginal_band
            > 1.0 - self.max_head_disagreement_fraction
        ):
            raise ValueError(
                "head disagreement marginal band must stay inside the unit interval"
            )
        if (
            self.max_decoder_uncertainty is not None
            and self.decoder_uncertainty_marginal_band
            > 1.0 - self.max_decoder_uncertainty
        ):
            raise ValueError(
                "decoder uncertainty marginal band must stay inside the unit interval"
            )
        for name in (
            "min_tip_roi_margin_mm",
            "min_tip_search_margin_mm",
            "min_channel_std_mm",
            "jump_noise_mm",
            "max_growth_mm_per_cycle",
            "max_jump_without_cycles_mm",
        ):
            object.__setattr__(
                self,
                name,
                _finite_non_negative(getattr(self, name), name=name),
            )
        jump_cap = self.max_jump_cap_mm
        if jump_cap is not None:
            jump_cap = float(jump_cap)
            if not math.isfinite(jump_cap) or jump_cap <= 0.0:
                raise ValueError("max_jump_cap_mm must be finite and positive or None")
            object.__setattr__(self, "max_jump_cap_mm", jump_cap)
        if not isinstance(self.calibration_source, str) or not self.calibration_source.strip():
            raise ValueError("calibration_source must be a non-empty string")

    def evaluate(
        self,
        observation: RoiObservation,
        *,
        previous_tip_xy_mm: PointMm | None = None,
    ) -> GateDecision:
        """Evaluate one observation without consulting reference data or mutable state."""

        if not isinstance(observation, RoiObservation):
            raise TypeError("observation must be RoiObservation")
        previous = (
            None
            if previous_tip_xy_mm is None
            else _finite_point(previous_tip_xy_mm, name="previous_tip_xy_mm")
        )
        return _evaluate_gate(self, observation, previous_tip_xy_mm=previous)


class P2Variant(str, Enum):
    """Declared fallback scope for one reproducible adaptive-ROI run."""

    P2_1_START_RESET = "p2.1_start_reset"
    P2_2_EXPANDED_FULL_SEARCH = "p2.2_expanded_full_search"


class RoiState(str, Enum):
    """Attempt and terminal states exposed in per-frame audit results."""

    START = "start"
    TRACKING = "tracking"
    START_FALLBACK = "start_fallback"
    EXPANDED_FALLBACK = "expanded_fallback"
    FULL_SEARCH = "full_search"
    LOST = "lost"


@dataclass(frozen=True)
class RoiAttempt:
    """One requested detector call for a physical ROI and frame.

    Attempt identifiers are contiguous within a frame and count actual detector
    calls only.  Skipped duplicate geometries are reported separately.
    """

    frame_id: str
    attempt_id: int
    state: RoiState
    roi: PhysicalRoi
    cycle_count: float | None
    cycle_delta_from_last_accepted: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise ValueError("frame_id must be a non-empty string")
        if (
            not isinstance(self.attempt_id, int)
            or isinstance(self.attempt_id, bool)
            or self.attempt_id < 0
        ):
            raise ValueError("attempt_id must be a non-negative integer")
        if self.state is RoiState.LOST:
            raise ValueError("LOST is a terminal state and cannot own a detector attempt")
        if not isinstance(self.roi, PhysicalRoi):
            raise TypeError("roi must be PhysicalRoi")
        cycle = _optional_cycle_count(self.cycle_count)
        object.__setattr__(self, "cycle_count", cycle)
        delta = self.cycle_delta_from_last_accepted
        if delta is not None:
            delta = _finite_non_negative(delta, name="cycle_delta_from_last_accepted")
            if cycle is None:
                raise ValueError("cycle delta requires an absolute cycle_count")
            object.__setattr__(self, "cycle_delta_from_last_accepted", delta)


@dataclass(frozen=True)
class AttemptResult:
    """One applied ROI, its observation, and the complete gate decision."""

    attempt: RoiAttempt
    observation: RoiObservation
    decision: GateDecision


@dataclass(frozen=True)
class FrameResult:
    """Terminal frame outcome containing every actual attempt and total runtime.

    ``williams_eligible`` is reported only for a lost frame after its full
    configured fallback ladder is exhausted.  Eligible attempt IDs identify
    geometrically and field-valid candidates whose detector evidence failed;
    no correction or acceptance is performed in this module.
    """

    frame_id: str
    variant: P2Variant
    final_state: RoiState
    accepted_tip_xy_mm: PointMm | None
    accepted_attempt_state: RoiState | None
    attempts: tuple[AttemptResult, ...]
    skipped_states: tuple[RoiState, ...]
    total_elapsed_seconds: float
    next_frame_roi: PhysicalRoi
    williams_eligible: bool
    williams_eligible_attempt_ids: tuple[int, ...]


@dataclass(frozen=True)
class RoiStep:
    """Result of submitting one observation to the controller.

    Exactly one of ``next_attempt`` and ``frame_result`` is present, so callers
    cannot mistake an unfinished fallback for a completed frame.
    """

    attempt_result: AttemptResult
    next_attempt: RoiAttempt | None
    frame_result: FrameResult | None

    def __post_init__(self) -> None:
        if (self.next_attempt is None) == (self.frame_result is None):
            raise ValueError("RoiStep requires exactly one next attempt or frame result")

    @property
    def completed(self) -> bool:
        """Return whether the frame reached an accepted or lost outcome."""

        return self.frame_result is not None


@dataclass
class _ActiveFrame:
    """Private lifecycle state retained only between begin and submit calls."""

    frame_id: str
    cycle_count: float | None
    attempts: tuple[RoiAttempt, ...]
    skipped_states: tuple[RoiState, ...]
    current_index: int
    results: list[AttemptResult]


class AdaptiveRoiController:
    """Drive one independent crack-tip sequence through deterministic ROI fallbacks.

    The controller owns only accepted tip/cycle history and an active frame's
    fallback ladder.  It never sees force, load phase, side labels, reference
    tips, or model objects.  Callers must therefore create one controller per
    independent sequence and select scientifically eligible frames before
    calling ``begin_frame``.
    """

    def __init__(
        self,
        *,
        start_roi: PhysicalRoi,
        gate_config: GateConfig,
        variant: P2Variant | str,
        expanded_scale: float | None = None,
    ) -> None:
        if not isinstance(start_roi, PhysicalRoi):
            raise TypeError("start_roi must be PhysicalRoi")
        if not isinstance(gate_config, GateConfig):
            raise TypeError("gate_config must be GateConfig")
        declared_variant = P2Variant(variant)
        if not _is_square_extent(start_roi.extent_xy_mm):
            raise ValueError("start_roi must be square for CrackPy 1.3.0 interpolation")
        if (
            declared_variant is P2Variant.P2_2_EXPANDED_FULL_SEARCH
            and not _is_square_extent(start_roi.search_bounds.extent_xy_mm)
        ):
            raise ValueError("search_bounds must be square for CrackPy 1.3.0 full search")
        self.start_roi = start_roi
        self.gate_config = gate_config
        self.variant = declared_variant
        if self.variant is P2Variant.P2_2_EXPANDED_FULL_SEARCH:
            if expanded_scale is None:
                raise ValueError("P2.2 requires an explicit expanded_scale")
            expanded_scale = float(expanded_scale)
            if not math.isfinite(expanded_scale) or expanded_scale <= 1.0:
                raise ValueError("expanded_scale must be finite and greater than one")
        elif expanded_scale is not None:
            raise ValueError("expanded_scale is only valid for P2.2")
        self.expanded_scale = expanded_scale
        self.state = RoiState.START
        self.last_accepted_tip_xy_mm: PointMm | None = None
        self.last_accepted_cycle_count: float | None = None
        self._active: _ActiveFrame | None = None

    def begin_frame(
        self,
        frame_id: str,
        *,
        cycle_count: float | None = None,
    ) -> RoiAttempt:
        """Begin one frame and return its start or tracking attempt.

        A frame must be completed before another begins.  Cycle progression is
        checked against the last accepted frame because rejected frames must not
        become scientific tracking anchors.
        """

        if self._active is not None:
            raise RuntimeError("a frame is already active")
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise ValueError("frame_id must be a non-empty string")
        cycle = _optional_cycle_count(cycle_count)
        cycle_delta: float | None = None
        if cycle is not None and self.last_accepted_cycle_count is not None:
            if cycle < self.last_accepted_cycle_count:
                raise ValueError("cycle_count must not precede the last accepted cycle")
            cycle_delta = cycle - self.last_accepted_cycle_count

        if self.state is RoiState.TRACKING and self.last_accepted_tip_xy_mm is not None:
            primary_state = RoiState.TRACKING
            primary_roi = self.start_roi.recentered_clamped(self.last_accepted_tip_xy_mm)
        else:
            primary_state = RoiState.START
            primary_roi = self.start_roi

        planned: list[tuple[RoiState, PhysicalRoi]] = [(primary_state, primary_roi)]
        skipped: list[RoiState] = []
        if primary_state is RoiState.TRACKING:
            _append_unique_plan(
                planned,
                skipped,
                state=RoiState.START_FALLBACK,
                roi=self.start_roi,
            )
        if self.variant is P2Variant.P2_2_EXPANDED_FULL_SEARCH:
            if self.expanded_scale is None:  # pragma: no cover - constructor invariant
                raise RuntimeError("P2.2 controller lost its expansion configuration")
            full_roi = PhysicalRoi.from_bounds(
                self.start_roi.search_bounds,
                search_bounds=self.start_roi.search_bounds,
            )
            expanded_roi = self.start_roi.scaled_clamped(self.expanded_scale)
            if expanded_roi.covers_search_bounds():
                skipped.append(RoiState.EXPANDED_FALLBACK)
                _append_unique_plan(
                    planned,
                    skipped,
                    state=RoiState.FULL_SEARCH,
                    roi=full_roi,
                )
            else:
                _append_unique_plan(
                    planned,
                    skipped,
                    state=RoiState.EXPANDED_FALLBACK,
                    roi=expanded_roi,
                )
                _append_unique_plan(
                    planned,
                    skipped,
                    state=RoiState.FULL_SEARCH,
                    roi=full_roi,
                )

        attempts = tuple(
            RoiAttempt(
                frame_id=frame_id,
                attempt_id=index,
                state=state,
                roi=roi,
                cycle_count=cycle,
                cycle_delta_from_last_accepted=cycle_delta,
            )
            for index, (state, roi) in enumerate(planned)
        )
        self._active = _ActiveFrame(
            frame_id=frame_id,
            cycle_count=cycle,
            attempts=attempts,
            skipped_states=tuple(skipped),
            current_index=0,
            results=[],
        )
        self.state = attempts[0].state
        return attempts[0]

    def submit(self, observation: RoiObservation) -> RoiStep:
        """Evaluate the active attempt and advance, accept, or mark the frame lost."""

        active = self._active
        if active is None:
            raise RuntimeError("there is no active frame")
        attempt = active.attempts[active.current_index]
        _validate_observation_matches_attempt(observation, attempt)
        decision = self.gate_config.evaluate(
            observation,
            previous_tip_xy_mm=self.last_accepted_tip_xy_mm,
        )
        attempt_result = AttemptResult(attempt, observation, decision)
        active.results.append(attempt_result)

        if decision.accepted:
            tip = observation.candidate_tip_xy_mm
            if tip is None or not _point_is_finite(tip):  # pragma: no cover - gate invariant
                raise RuntimeError("accepted gate decision does not contain a finite tip")
            self.last_accepted_tip_xy_mm = tip
            self.last_accepted_cycle_count = active.cycle_count
            self.state = RoiState.TRACKING
            next_roi = self.start_roi.recentered_clamped(tip)
            frame_result = self._finish_frame(
                final_state=RoiState.TRACKING,
                accepted_tip_xy_mm=tip,
                accepted_attempt_state=attempt.state,
                next_frame_roi=next_roi,
            )
            return RoiStep(attempt_result, None, frame_result)

        next_index = active.current_index + 1
        if next_index < len(active.attempts):
            active.current_index = next_index
            next_attempt = active.attempts[next_index]
            self.state = next_attempt.state
            return RoiStep(attempt_result, next_attempt, None)

        self.state = RoiState.LOST
        frame_result = self._finish_frame(
            final_state=RoiState.LOST,
            accepted_tip_xy_mm=None,
            accepted_attempt_state=None,
            next_frame_roi=self.start_roi,
        )
        return RoiStep(attempt_result, None, frame_result)

    def _finish_frame(
        self,
        *,
        final_state: RoiState,
        accepted_tip_xy_mm: PointMm | None,
        accepted_attempt_state: RoiState | None,
        next_frame_roi: PhysicalRoi,
    ) -> FrameResult:
        """Build one terminal result and release the active-frame lifecycle lock."""

        active = self._active
        if active is None:  # pragma: no cover - caller invariant
            raise RuntimeError("cannot finish without an active frame")
        eligible_ids = (
            tuple(
                item.attempt.attempt_id
                for item in active.results
                if item.decision.williams_eligible
            )
            if final_state is RoiState.LOST
            else ()
        )
        result = FrameResult(
            frame_id=active.frame_id,
            variant=self.variant,
            final_state=final_state,
            accepted_tip_xy_mm=accepted_tip_xy_mm,
            accepted_attempt_state=accepted_attempt_state,
            attempts=tuple(active.results),
            skipped_states=active.skipped_states,
            total_elapsed_seconds=math.fsum(
                item.observation.elapsed_seconds for item in active.results
            ),
            next_frame_roi=next_frame_roi,
            williams_eligible=bool(eligible_ids),
            williams_eligible_attempt_ids=eligible_ids,
        )
        self._active = None
        return result


@dataclass(frozen=True)
class LegacySideAdapter:
    """Translate absolute physical geometry at CrackPy's legacy side seam.

    CrackPy 1.3.0 uses a signed square size and an offset at the inner x edge.
    The detector grid is endpoint-inclusive, so row/column mapping divides by
    ``resolution - 1`` rather than by the number of samples.
    """

    side: str

    def __post_init__(self) -> None:
        if self.side not in {"left", "right"}:
            raise ValueError("legacy side must be left or right")

    def interpolation_args(self, roi: PhysicalRoi) -> tuple[float, PointMm]:
        """Return the legacy signed size and inner-edge offset for a square ROI."""

        if not math.isclose(
            roi.extent_x_mm,
            roi.extent_y_mm,
            abs_tol=_GEOMETRY_TOLERANCE,
            rel_tol=0.0,
        ):
            raise ValueError("CrackPy 1.3.0 interpolation requires a square ROI")
        bounds = roi.bounds
        if self.side == "right":
            return roi.extent_x_mm, (bounds.x_min_mm, roi.center_y_mm)
        return -roi.extent_x_mm, (bounds.x_max_mm, roi.center_y_mm)

    def point_rc_to_xy(
        self,
        point_rc: PointRc,
        roi: PhysicalRoi,
        *,
        resolution_px: int | tuple[int, int],
    ) -> PointMm:
        """Map a canonical endpoint-inclusive row/column point to absolute mm."""

        rows, columns = _resolution_shape(resolution_px)
        row, column = _finite_point(point_rc, name="point_rc")
        u = column / (columns - 1)
        v = row / (rows - 1)
        bounds = roi.bounds
        if self.side == "right":
            x_mm = bounds.x_min_mm + u * roi.extent_x_mm
        else:
            x_mm = bounds.x_max_mm - u * roi.extent_x_mm
        y_mm = bounds.y_min_mm + v * roi.extent_y_mm
        return x_mm, y_mm

    def point_xy_to_rc(
        self,
        point_xy_mm: PointMm,
        roi: PhysicalRoi,
        *,
        resolution_px: int | tuple[int, int],
    ) -> PointRc:
        """Map an absolute point back to the canonical detector row/column grid."""

        rows, columns = _resolution_shape(resolution_px)
        x_mm, y_mm = _finite_point(point_xy_mm, name="point_xy_mm")
        bounds = roi.bounds
        if self.side == "right":
            u = (x_mm - bounds.x_min_mm) / roi.extent_x_mm
        else:
            u = (bounds.x_max_mm - x_mm) / roi.extent_x_mm
        v = (y_mm - bounds.y_min_mm) / roi.extent_y_mm
        return v * (rows - 1), u * (columns - 1)


def _finite_point(value: PointMm, *, name: str) -> PointMm:
    """Validate and canonicalize a two-dimensional finite point."""

    try:
        first, second = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain exactly two coordinates") from exc
    first = float(first)
    second = float(second)
    if not math.isfinite(first) or not math.isfinite(second):
        raise ValueError(f"{name} must be finite")
    return first, second


def _numeric_point(value: PointMm, *, name: str) -> PointMm:
    """Canonicalize a numeric point while retaining non-finite gate evidence."""

    try:
        first, second = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain exactly two coordinates") from exc
    try:
        return float(first), float(second)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} coordinates must be numeric") from exc


def _optional_numeric_point(value: PointMm | None, *, name: str) -> PointMm | None:
    """Canonicalize an optional point without converting absence into NaNs."""

    if value is None:
        return None
    return _numeric_point(value, name=name)


def _fused_candidate_tip(
    mask_tip_xy_mm: PointMm | None,
    coordinate_tip_xy_mm: PointMm | None,
    fusion_weight: float,
) -> PointMm | None:
    """Derive the decoder candidate from its two physical head points."""

    if fusion_weight == 0.0:
        return mask_tip_xy_mm
    if fusion_weight == 1.0:
        return coordinate_tip_xy_mm
    if mask_tip_xy_mm is None or coordinate_tip_xy_mm is None:
        return None
    return (
        (1.0 - fusion_weight) * mask_tip_xy_mm[0]
        + fusion_weight * coordinate_tip_xy_mm[0],
        (1.0 - fusion_weight) * mask_tip_xy_mm[1]
        + fusion_weight * coordinate_tip_xy_mm[1],
    )


def _physical_head_disagreement(
    mask_tip_xy_mm: PointMm | None,
    coordinate_tip_xy_mm: PointMm | None,
    *,
    applied_roi: PhysicalRoi,
) -> tuple[float | None, float | None]:
    """Derive absolute and ROI-normalized disagreement from physical points."""

    if mask_tip_xy_mm is None or coordinate_tip_xy_mm is None:
        return None, None
    disagreement_mm = math.dist(mask_tip_xy_mm, coordinate_tip_xy_mm)
    return disagreement_mm, disagreement_mm / applied_roi.diagonal_mm


def _numeric_scalars_match(first: float, second: float) -> bool:
    """Compare derived signals while retaining like-for-like NaN evidence."""

    if math.isnan(first) or math.isnan(second):
        return math.isnan(first) and math.isnan(second)
    return math.isclose(
        first,
        second,
        rel_tol=_GEOMETRY_TOLERANCE,
        abs_tol=_GEOMETRY_TOLERANCE,
    )


def _optional_scalars_match(first: float | None, second: float | None) -> bool:
    """Compare optional raw and derived scalar signals."""

    if first is None or second is None:
        return first is second
    return _numeric_scalars_match(first, second)


def _optional_points_match(first: PointMm | None, second: PointMm | None) -> bool:
    """Compare optional raw and derived points coordinate by coordinate."""

    if first is None or second is None:
        return first is second
    return all(
        _numeric_scalars_match(left, right)
        for left, right in zip(first, second, strict=True)
    )


def _is_square_extent(extent_xy_mm: PointMm) -> bool:
    """Return whether the x/y extents meet the legacy square-grid contract."""

    return math.isclose(
        extent_xy_mm[0],
        extent_xy_mm[1],
        rel_tol=0.0,
        abs_tol=_GEOMETRY_TOLERANCE,
    )


def _finite_non_negative(value: float, *, name: str) -> float:
    """Validate a finite non-negative scalar."""

    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _bounded_fraction(value: float, *, name: str) -> float:
    """Validate a finite scalar in the closed unit interval."""

    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return result


def _resolution_shape(value: int | tuple[int, int]) -> tuple[int, int]:
    """Canonicalize a square scalar or explicit row/column resolution."""

    if isinstance(value, bool):
        raise ValueError("resolution_px must contain integers greater than one")
    if isinstance(value, int):
        rows = columns = value
    else:
        try:
            rows, columns = value
        except (TypeError, ValueError) as exc:
            raise ValueError("resolution_px must contain two dimensions") from exc
    if (
        not isinstance(rows, int)
        or isinstance(rows, bool)
        or not isinstance(columns, int)
        or isinstance(columns, bool)
        or rows <= 1
        or columns <= 1
    ):
        raise ValueError("resolution_px must contain integers greater than one")
    return rows, columns


def _bounds_close(first: PhysicalBounds, second: PhysicalBounds) -> bool:
    """Compare physical rectangles using only the declared geometry tolerance."""

    left = (first.x_min_mm, first.x_max_mm, first.y_min_mm, first.y_max_mm)
    right = (second.x_min_mm, second.x_max_mm, second.y_min_mm, second.y_max_mm)
    return all(
        math.isclose(a, b, abs_tol=_GEOMETRY_TOLERANCE, rel_tol=0.0)
        for a, b in zip(left, right, strict=True)
    )


def _evaluate_gate(
    config: GateConfig,
    observation: RoiObservation,
    *,
    previous_tip_xy_mm: PointMm | None,
) -> GateDecision:
    """Apply the three gate groups in a stable, complete reporting order."""

    field_reasons: list[GateReason] = []
    geometry_reasons: list[GateReason] = []
    evidence_reasons: list[GateReason] = []

    finite_fraction = observation.finite_grid_fraction
    if (
        not math.isfinite(finite_fraction)
        or finite_fraction < config.min_finite_grid_fraction
        or finite_fraction > 1.0
    ):
        field_reasons.append(GateReason.NONFINITE_FIELD)
    if any(
        not math.isfinite(channel_std) or channel_std < config.min_channel_std_mm
        for channel_std in observation.channel_std_mm
    ):
        field_reasons.append(GateReason.FIELD_VARIATION_TOO_LOW)

    tip = observation.candidate_tip_xy_mm
    roi_margin: float | None = None
    search_margin: float | None = None
    tip_jump: float | None = None
    max_tip_jump: float | None = None
    finite_tip: PointMm | None = None
    if tip is None:
        geometry_reasons.append(GateReason.MISSING_TIP)
    elif not _point_is_finite(tip):
        geometry_reasons.append(GateReason.NONFINITE_TIP)
    else:
        finite_tip = tip
        roi_margin = observation.applied_roi.signed_margin_mm(tip)
        search_margin = observation.applied_roi.search_bounds.signed_margin_mm(tip)
        if roi_margin < -_GEOMETRY_TOLERANCE:
            geometry_reasons.append(GateReason.TIP_OUTSIDE_ROI)
        elif roi_margin + _GEOMETRY_TOLERANCE < config.min_tip_roi_margin_mm:
            geometry_reasons.append(GateReason.TIP_NEAR_ROI_EDGE)
        if search_margin < -_GEOMETRY_TOLERANCE:
            geometry_reasons.append(GateReason.TIP_OUTSIDE_SEARCH_BOUNDS)
        elif search_margin + _GEOMETRY_TOLERANCE < config.min_tip_search_margin_mm:
            geometry_reasons.append(GateReason.TIP_NEAR_SEARCH_BOUNDARY)
        if previous_tip_xy_mm is not None:
            tip_jump = math.dist(tip, previous_tip_xy_mm)
            cycle_delta = observation.cycle_delta_from_last_accepted
            if cycle_delta is None:
                max_tip_jump = config.max_jump_without_cycles_mm
            else:
                max_tip_jump = config.jump_noise_mm + config.max_growth_mm_per_cycle * cycle_delta
            if config.max_jump_cap_mm is not None:
                max_tip_jump = min(max_tip_jump, config.max_jump_cap_mm)
            if tip_jump > max_tip_jump + _GEOMETRY_TOLERANCE:
                geometry_reasons.append(GateReason.TIP_JUMP_TOO_LARGE)

    _evaluate_head_point(
        observation.mask_tip_xy_mm,
        missing_reason=GateReason.MISSING_MASK_TIP,
        invalid_reason=GateReason.INVALID_MASK_TIP,
        reasons=evidence_reasons,
    )
    _evaluate_head_point(
        observation.coordinate_tip_xy_mm,
        missing_reason=GateReason.MISSING_COORDINATE_TIP,
        invalid_reason=GateReason.INVALID_COORDINATE_TIP,
        reasons=evidence_reasons,
    )
    _evaluate_minimum_fraction(
        observation.mask_mean_score,
        minimum=config.min_mask_mean_score,
        missing_reason=GateReason.MISSING_MASK_SCORE,
        invalid_reason=GateReason.INVALID_MASK_SCORE,
        low_reason=GateReason.MASK_SCORE_TOO_LOW,
        reasons=evidence_reasons,
    )
    if config.min_region_selection_score is not None:
        _evaluate_minimum_non_negative(
            observation.region_selection_score,
            minimum=config.min_region_selection_score,
            missing_reason=GateReason.MISSING_REGION_SELECTION_SCORE,
            invalid_reason=GateReason.INVALID_REGION_SELECTION_SCORE,
            low_reason=GateReason.REGION_SELECTION_SCORE_TOO_LOW,
            reasons=evidence_reasons,
        )
    area = observation.mask_area_fraction
    if area is None:
        evidence_reasons.append(GateReason.MISSING_MASK_AREA)
    elif not math.isfinite(area) or not 0.0 <= area <= 1.0:
        evidence_reasons.append(GateReason.INVALID_MASK_AREA)
    elif area < config.min_mask_area_fraction:
        evidence_reasons.append(GateReason.MASK_AREA_TOO_SMALL)
    elif area > config.max_mask_area_fraction:
        evidence_reasons.append(GateReason.MASK_AREA_TOO_LARGE)
    disagreement = observation.head_disagreement_fraction
    disagreement_mm = observation.head_disagreement_mm
    if disagreement is None or disagreement_mm is None:
        evidence_reasons.append(GateReason.MISSING_HEAD_DISAGREEMENT)
    elif (
        not math.isfinite(disagreement)
        or not 0.0 <= disagreement <= 1.0
        or not math.isfinite(disagreement_mm)
        or disagreement_mm < 0.0
    ):
        evidence_reasons.append(GateReason.INVALID_HEAD_DISAGREEMENT)
    elif disagreement > config.max_head_disagreement_fraction:
        evidence_reasons.append(GateReason.HEAD_DISAGREEMENT_TOO_LARGE)
    uncertainty = observation.decoder_uncertainty
    if not math.isfinite(uncertainty) or not 0.0 <= uncertainty <= 1.0:
        evidence_reasons.append(GateReason.INVALID_DECODER_UNCERTAINTY)
    elif (
        config.max_decoder_uncertainty is not None
        and uncertainty > config.max_decoder_uncertainty
    ):
        evidence_reasons.append(GateReason.DECODER_UNCERTAINTY_TOO_HIGH)
    decoder_reason = observation.decoder_invalid_reason
    if decoder_reason in _CONFIDENCE_DECODER_INVALID_REASONS:
        evidence_reasons.append(GateReason.DECODER_CONFIDENCE_THRESHOLD_EXCEEDED)
    elif decoder_reason is not None:
        evidence_reasons.append(GateReason.DECODER_STRUCTURAL_INVALID)

    field_ok = not field_reasons
    geometry_ok = not geometry_reasons and finite_tip is not None
    evidence_ok = not evidence_reasons
    reasons = tuple((*field_reasons, *geometry_reasons, *evidence_reasons))
    marginal_evidence_only = _evidence_failures_are_marginal(
        config,
        observation,
        evidence_reasons,
    )
    return GateDecision(
        accepted=field_ok and geometry_ok and evidence_ok,
        field_ok=field_ok,
        geometry_ok=geometry_ok,
        evidence_ok=evidence_ok,
        reasons=reasons,
        williams_eligible=field_ok and geometry_ok and marginal_evidence_only,
        tip_jump_mm=tip_jump,
        max_tip_jump_mm=max_tip_jump,
        roi_margin_mm=roi_margin,
        search_margin_mm=search_margin,
    )


def _evidence_failures_are_marginal(
    config: GateConfig,
    observation: RoiObservation,
    evidence_reasons: list[GateReason],
) -> bool:
    """Return whether every evidence failure lies in an explicit near band."""

    if not evidence_reasons:
        return False
    marginal_reasons = {
        GateReason.MASK_SCORE_TOO_LOW,
        GateReason.HEAD_DISAGREEMENT_TOO_LARGE,
        GateReason.DECODER_UNCERTAINTY_TOO_HIGH,
        GateReason.DECODER_CONFIDENCE_THRESHOLD_EXCEEDED,
    }
    reasons = set(evidence_reasons)
    if not reasons.issubset(marginal_reasons):
        return False
    if GateReason.MASK_SCORE_TOO_LOW in reasons:
        score = observation.mask_mean_score
        if (
            score is None
            or not math.isfinite(score)
            or score
            < config.min_mask_mean_score
            - config.mask_score_marginal_band
            - _GEOMETRY_TOLERANCE
        ):
            return False
    if GateReason.HEAD_DISAGREEMENT_TOO_LARGE in reasons:
        disagreement = observation.head_disagreement_fraction
        if (
            disagreement is None
            or not math.isfinite(disagreement)
            or disagreement
            > config.max_head_disagreement_fraction
            + config.head_disagreement_marginal_band
            + _GEOMETRY_TOLERANCE
        ):
            return False
    if (
        GateReason.DECODER_UNCERTAINTY_TOO_HIGH in reasons
        or GateReason.DECODER_CONFIDENCE_THRESHOLD_EXCEEDED in reasons
    ):
        uncertainty_limit = config.max_decoder_uncertainty
        uncertainty = observation.decoder_uncertainty
        if (
            uncertainty_limit is None
            or not math.isfinite(uncertainty)
            or uncertainty <= uncertainty_limit
            or uncertainty
            > uncertainty_limit
            + config.decoder_uncertainty_marginal_band
            + _GEOMETRY_TOLERANCE
        ):
            return False
    return True


def _evaluate_head_point(
    point: PointMm | None,
    *,
    missing_reason: GateReason,
    invalid_reason: GateReason,
    reasons: list[GateReason],
) -> None:
    """Append the appropriate evidence reason for one optional detector head."""

    if point is None:
        reasons.append(missing_reason)
    elif not _point_is_finite(point):
        reasons.append(invalid_reason)


def _evaluate_minimum_fraction(
    value: float | None,
    *,
    minimum: float,
    missing_reason: GateReason,
    invalid_reason: GateReason,
    low_reason: GateReason,
    reasons: list[GateReason],
) -> None:
    """Append one stable reason for a required lower-bounded fraction."""

    if value is None:
        reasons.append(missing_reason)
    elif not math.isfinite(value) or not 0.0 <= value <= 1.0:
        reasons.append(invalid_reason)
    elif value < minimum:
        reasons.append(low_reason)


def _evaluate_minimum_non_negative(
    value: float | None,
    *,
    minimum: float,
    missing_reason: GateReason,
    invalid_reason: GateReason,
    low_reason: GateReason,
    reasons: list[GateReason],
) -> None:
    """Gate one required rule-specific score without assuming an upper bound."""

    if value is None:
        reasons.append(missing_reason)
    elif not math.isfinite(value) or value < 0.0:
        reasons.append(invalid_reason)
    elif value < minimum:
        reasons.append(low_reason)


def _point_is_finite(point: PointMm) -> bool:
    """Return whether both coordinates of a canonical numeric point are finite."""

    return math.isfinite(point[0]) and math.isfinite(point[1])


def _optional_cycle_count(value: float | None) -> float | None:
    """Validate an optional absolute non-negative cycle count."""

    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError("cycle_count must be finite and non-negative")
    return result


def _append_unique_plan(
    planned: list[tuple[RoiState, PhysicalRoi]],
    skipped: list[RoiState],
    *,
    state: RoiState,
    roi: PhysicalRoi,
) -> None:
    """Append an actual detector attempt only when its geometry adds coverage."""

    if any(existing_roi.same_geometry(roi) for _, existing_roi in planned):
        skipped.append(state)
        return
    planned.append((state, roi))


def _validate_observation_matches_attempt(
    observation: RoiObservation,
    attempt: RoiAttempt,
) -> None:
    """Reject stale or cross-sequence observations before they can mutate state."""

    if not isinstance(observation, RoiObservation):
        raise TypeError("observation must be RoiObservation")
    if observation.frame_id != attempt.frame_id or observation.attempt_id != attempt.attempt_id:
        raise ValueError("observation does not match the active attempt")
    if not observation.applied_roi.same_geometry(attempt.roi):
        raise ValueError("observation ROI does not match the active attempt")
    expected_delta = attempt.cycle_delta_from_last_accepted
    observed_delta = observation.cycle_delta_from_last_accepted
    if expected_delta is None or observed_delta is None:
        if expected_delta is not observed_delta:
            raise ValueError("observation cycle delta does not match the active attempt")
    elif not math.isclose(
        expected_delta,
        observed_delta,
        abs_tol=_GEOMETRY_TOLERANCE,
        rel_tol=0.0,
    ):
        raise ValueError("observation cycle delta does not match the active attempt")

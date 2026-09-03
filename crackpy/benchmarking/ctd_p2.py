"""Leakage-safe evidence adapters and sequence metrics for CTD P2.

The module sits outside :mod:`crackpy.crack_detection.adaptive_roi` on
purpose: the controller receives only observations, while references are
attached afterwards for evaluation and can never change a tracking decision.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Mapping

import numpy as np
from scipy.stats import beta

from crackpy.benchmarking.ctd_decoders import DecoderConfig, DecoderOutput
from crackpy.crack_detection.adaptive_roi import (
    AdaptiveRoiController,
    FrameResult,
    GateConfig,
    GateDecision,
    LegacySideAdapter,
    PhysicalBounds,
    PhysicalRoi,
    RoiAttempt,
    RoiObservation,
    RoiState,
    P2Variant,
)


P2_RAW_SIGNAL_SEMANTICS: dict[str, dict[str, str]] = {
    "candidate_tip_xy_mm": {
        "source": "DecoderOutput mask/coordinate heads plus DecoderConfig.fusion_weight",
        "meaning": "ungated frozen-decoder fusion in absolute specimen coordinates",
        "normalization": (
            "each head crosses LegacySideAdapter, then RoiObservation.from_decoder_heads "
            "applies the frozen fusion weight"
        ),
    },
    "mask_mean_score": {
        "source": "DecoderOutput.mask_confidence",
        "meaning": "bounded neural region score; not a calibrated probability",
        "normalization": "none",
    },
    "region_selection_score": {
        "source": "DecoderOutput.selected_region_score",
        "meaning": "raw rule-specific region-ranking signal",
        "normalization": "none; units depend on the frozen region rule",
    },
    "mask_area_fraction": {
        "source": "DecoderOutput.selected_region_area",
        "meaning": "selected connected-component support",
        "normalization": "selected_region_area / (rows * columns)",
    },
    "head_disagreement_fraction": {
        "source": "absolute mask and coordinate head points",
        "meaning": "physical distance between frozen decoder heads",
        "normalization": "physical head distance / applied ROI physical diagonal",
    },
    "decoder_uncertainty": {
        "source": "DecoderOutput.uncertainty",
        "meaning": "validation-ranked P1 uncertainty signal",
        "normalization": "frozen bounded P1 definition",
    },
    "finite_grid_fraction": {
        "source": "DicFieldQuality.finite_grid_fraction",
        "meaning": "share of finite interpolated DIC grid values",
        "normalization": "finite values / all grid values",
    },
    "channel_std_mm": {
        "source": "DicFieldQuality.ux_std_mm, uy_std_mm",
        "meaning": "per-channel DIC displacement variation",
        "normalization": "physical millimetres",
    },
}


@dataclass(frozen=True)
class P1SignalsContract:
    """Validation-frozen P1 inputs that P2 may consume.

    ``decoder_config`` is deliberately ungated, so a confidence warning can
    trigger the P2 fallback ladder without deleting the underlying finite tip.
    ``confidence_threshold`` is kept separately and must originate from the
    validation split.  The remaining fields make that provenance explicit in
    every P2 result artifact.
    """

    resolution_mode: str
    decoder_config: DecoderConfig
    confidence_threshold: float
    calibration_split: str
    test_recalibration_performed: bool
    artifact_schema_version: str
    crackmnist_test_failure_rate_context: float
    model_artifact_sha256: Mapping[str, str]
    source_verification_status: str
    source_artifact_sha256: str | None
    source_path: str | None
    production_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a strict JSON-native representation."""

        return {
            "resolution_mode": self.resolution_mode,
            "decoder_config": self.decoder_config.to_dict(),
            "confidence_threshold": self.confidence_threshold,
            "calibration_split": self.calibration_split,
            "test_recalibration_performed": self.test_recalibration_performed,
            "artifact_schema_version": self.artifact_schema_version,
            "crackmnist_test_failure_rate_context": (
                self.crackmnist_test_failure_rate_context
            ),
            "crackmnist_context_role": (
                "single_image_context_only_never_sequence_comparator"
            ),
            "model_artifact_sha256": dict(self.model_artifact_sha256),
            "source_verification_status": self.source_verification_status,
            "source_artifact_sha256": self.source_artifact_sha256,
            "source_path": self.source_path,
            "production_eligible": self.production_eligible,
        }


@dataclass(frozen=True)
class P2RunConfig:
    """Reproducible policy inputs for the P2 evidence orchestrator.

    ``p1_results`` is the immutable result selected before P2.
    ``primary_sequence_evidence`` chooses the externally prepared real replay
    used for preliminary technical gates; CrackMNIST is intentionally excluded
    because it is not a physical sequence.
    """

    p1_results: str | Path | Mapping[str, Any]
    minimum_safe_margin_mm: float = 0.2
    confident_error_threshold_mm: float = 1.0
    minimum_safe_coverage: float = 0.99
    primary_sequence_evidence: str = "dummy2"
    same_scenario_p1_baselines: Mapping[str, Mapping[str, Any]] | None = None
    allow_unverified_p1_for_tests: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "minimum_safe_margin_mm",
            _finite_non_negative(
                self.minimum_safe_margin_mm,
                name="minimum_safe_margin_mm",
            ),
        )
        object.__setattr__(
            self,
            "confident_error_threshold_mm",
            _finite_non_negative(
                self.confident_error_threshold_mm,
                name="confident_error_threshold_mm",
            ),
        )
        object.__setattr__(
            self,
            "minimum_safe_coverage",
            _bounded_fraction(
                self.minimum_safe_coverage,
                name="minimum_safe_coverage",
            ),
        )
        primary_role, _ = _parse_evidence_set_label(self.primary_sequence_evidence)
        if primary_role not in {"dummy2", "repository_sparse"}:
            raise ValueError(
                "primary_sequence_evidence must identify dummy2 or repository_sparse"
            )
        if not isinstance(self.allow_unverified_p1_for_tests, bool):
            raise TypeError("allow_unverified_p1_for_tests must be boolean")
        baselines = self.same_scenario_p1_baselines
        if baselines is None:
            normalized_baselines: dict[str, Mapping[str, Any]] = {}
        elif not isinstance(baselines, Mapping):
            raise TypeError("same_scenario_p1_baselines must be a mapping")
        else:
            normalized_baselines = {}
            for evidence_set, value in baselines.items():
                if not isinstance(evidence_set, str):
                    raise TypeError("same-scenario baseline keys must be strings")
                role, _ = _parse_evidence_set_label(evidence_set)
                if role == "crackmnist_single_image":
                    raise ValueError(
                        "CrackMNIST cannot be a same-scenario sequence baseline"
                    )
                if not isinstance(value, Mapping):
                    raise TypeError(
                        f"same_scenario_p1_baselines[{evidence_set!r}] must be a mapping"
                    )
                normalized_baselines[evidence_set] = dict(value)
        object.__setattr__(
            self,
            "same_scenario_p1_baselines",
            normalized_baselines,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return policy values while describing, not embedding, the P1 source."""

        source = (
            "in_memory_mapping"
            if isinstance(self.p1_results, Mapping)
            else str(Path(self.p1_results))
        )
        return {
            "p1_results_source": source,
            "minimum_safe_margin_mm": self.minimum_safe_margin_mm,
            "confident_error_threshold_mm": self.confident_error_threshold_mm,
            "minimum_safe_coverage": self.minimum_safe_coverage,
            "primary_sequence_evidence": self.primary_sequence_evidence,
            "same_scenario_p1_baseline_evidence_sets": sorted(
                (self.same_scenario_p1_baselines or {}).keys()
            ),
            "same_scenario_baseline_contract": (
                "prepared P1 fixed-ROI replay of the exact same frames and references"
            ),
            "allow_unverified_p1_for_tests": self.allow_unverified_p1_for_tests,
        }


@dataclass(frozen=True)
class DicFieldQuality:
    """Raw DIC validity signals for exactly one interpolated detector input.

    Values are intentionally not rejected in this adapter because NaNs and
    zero variation are evidence that the controller's field gate must see.
    """

    finite_grid_fraction: float
    ux_std_mm: float
    uy_std_mm: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "finite_grid_fraction", float(self.finite_grid_fraction))
        object.__setattr__(self, "ux_std_mm", float(self.ux_std_mm))
        object.__setattr__(self, "uy_std_mm", float(self.uy_std_mm))


class WilliamsMode(str, Enum):
    """Explicit operational status of the optional Williams seam."""

    OFF = "off"
    DIAGNOSTIC = "diagnostic"
    SELECTIVE = "selective"


class WilliamsOutcome(str, Enum):
    """Stable terminal outcomes for one optional Williams consultation."""

    NOT_ELIGIBLE = "not_eligible"
    DISABLED = "disabled"
    UNEVALUABLE = "unevaluable"
    SOLVER_FAILED = "solver_failed"
    REJECTED = "rejected"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    ADOPTED = "adopted"


@dataclass(frozen=True)
class WilliamsPolicy:
    """Safety policy for a Williams solver call after ROI fallbacks.

    ``mode`` defaults to diagnostic, so a correction can be measured but is
    never the production tip without an explicit prospective policy change.
    ``max_correction_mm`` bounds the physical displacement from the marginal
    neural proposal.  ``calibration_source`` records that this is currently an
    engineering guard rather than independently validated accuracy evidence.
    """

    mode: WilliamsMode | str = WilliamsMode.DIAGNOSTIC
    max_correction_mm: float = 0.5
    calibration_source: str = "P2 engineering safety policy; independent labels pending"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", WilliamsMode(self.mode))
        maximum = float(self.max_correction_mm)
        if not math.isfinite(maximum) or maximum <= 0.0:
            raise ValueError("max_correction_mm must be finite and positive")
        object.__setattr__(self, "max_correction_mm", maximum)
        if not isinstance(self.calibration_source, str) or not self.calibration_source.strip():
            raise ValueError("calibration_source must be a non-empty string")

    def to_dict(self) -> dict[str, Any]:
        """Return the explicit post-cascade policy used by the orchestrator."""

        return {
            "mode": self.mode.value,
            "max_correction_mm": self.max_correction_mm,
            "calibration_source": self.calibration_source,
        }


@dataclass(frozen=True)
class WilliamsSolverResult:
    """Raw, solver-owned Williams result before any P2 safety decision.

    Fields may contain invalid numerical values because malformed solver output
    must become a structured P2 rejection instead of escaping the benchmark.
    """

    converged: bool
    iterations: int
    residual_before: float | None
    residual_after: float | None
    correction_delta_xy_mm: tuple[float, float] | None
    corrected_tip_xy_mm: tuple[float, float] | None
    elapsed_seconds: float
    failure_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-native fields without hiding invalid numerical evidence."""

        return {
            "converged": bool(self.converged),
            "iterations": self.iterations,
            "residual_before": _audit_scalar(self.residual_before),
            "residual_after": _audit_scalar(self.residual_after),
            "correction_delta_xy_mm": _audit_point(self.correction_delta_xy_mm),
            "corrected_tip_xy_mm": _audit_point(self.corrected_tip_xy_mm),
            "elapsed_seconds": _audit_scalar(self.elapsed_seconds),
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True)
class WilliamsDecision:
    """Auditable P2 disposition of one optional Williams result."""

    outcome: WilliamsOutcome
    called: bool
    adopted: bool
    source_attempt_id: int | None
    solver_result: WilliamsSolverResult | None
    rejection_reasons: tuple[str, ...]
    safety_recheck: GateDecision | None
    final_tip_xy_mm: tuple[float, float] | None

    def to_dict(self) -> dict[str, Any]:
        """Return a strict report record."""

        recheck = self.safety_recheck
        return {
            "outcome": self.outcome.value,
            "called": self.called,
            "adopted": self.adopted,
            "source_attempt_id": self.source_attempt_id,
            "solver_result": None if self.solver_result is None else self.solver_result.to_dict(),
            "rejection_reasons": list(self.rejection_reasons),
            "safety_recheck": (
                None
                if recheck is None
                else {
                    "accepted": recheck.accepted,
                    "field_ok": recheck.field_ok,
                    "geometry_ok": recheck.geometry_ok,
                    "evidence_ok": recheck.evidence_ok,
                    "reasons": [reason.value for reason in recheck.reasons],
                    "tip_jump_mm": _audit_scalar(recheck.tip_jump_mm),
                    "max_tip_jump_mm": _audit_scalar(recheck.max_tip_jump_mm),
                    "roi_margin_mm": _audit_scalar(recheck.roi_margin_mm),
                    "search_margin_mm": _audit_scalar(recheck.search_margin_mm),
                }
            ),
            "final_tip_xy_mm": _audit_point(self.final_tip_xy_mm),
        }


@dataclass(frozen=True)
class EvaluatedFrame:
    """A terminal controller result with evaluation-only evidence attached.

    ``reference_tip_xy_mm`` and ``reference_source`` are absent from every
    controller input type and are attached only after ``FrameResult`` exists.
    This type-level boundary prevents a pseudoreference or ground truth from
    affecting ROI choice.  ``williams`` is similarly a post-cascade result.
    """

    result: FrameResult
    reference_tip_xy_mm: tuple[float, float] | None = None
    reference_source: str | None = None
    williams: WilliamsDecision | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.result, FrameResult):
            raise TypeError("result must be FrameResult")
        reference = self.reference_tip_xy_mm
        if reference is not None:
            reference = _optional_finite_point(reference)
            if reference is None:
                raise ValueError("reference_tip_xy_mm must be finite")
            object.__setattr__(self, "reference_tip_xy_mm", reference)
            if not isinstance(self.reference_source, str) or not self.reference_source.strip():
                raise ValueError("a finite reference requires reference_source")
        elif self.reference_source is not None:
            raise ValueError("reference_source requires reference_tip_xy_mm")
        if self.williams is not None and not isinstance(self.williams, WilliamsDecision):
            raise TypeError("williams must be WilliamsDecision or None")


def evaluated_frame_to_dict(record: EvaluatedFrame) -> dict[str, Any]:
    """Serialize every applied decision without exposing references to control.

    Each attempt records the ROI that was actually evaluated and the ROI that
    followed it.  Non-finite raw signals are retained as explicit JSON strings
    rather than silently dropped or emitted as non-standard JSON numbers.
    """

    if not isinstance(record, EvaluatedFrame):
        raise TypeError("record must be EvaluatedFrame")
    result = record.result
    attempts: list[dict[str, Any]] = []
    for index, item in enumerate(result.attempts):
        attempt = item.attempt
        observation = item.observation
        decision = item.decision
        if index + 1 < len(result.attempts):
            next_roi = result.attempts[index + 1].attempt.roi
            next_roi_role = "next_attempt"
        else:
            next_roi = result.next_frame_roi
            next_roi_role = "next_frame"
        attempts.append(
            {
                "attempt_id": attempt.attempt_id,
                "state": attempt.state.value,
                "cycle_count": _audit_scalar(attempt.cycle_count),
                "cycle_delta_from_last_accepted": _audit_scalar(
                    attempt.cycle_delta_from_last_accepted
                ),
                "applied_roi": _roi_to_dict(attempt.roi),
                "next_roi": _roi_to_dict(next_roi),
                "next_roi_role": next_roi_role,
                "signals": {
                    "candidate_tip_xy_mm": _audit_point(
                        observation.candidate_tip_xy_mm
                    ),
                    "mask_tip_xy_mm": _audit_point(observation.mask_tip_xy_mm),
                    "coordinate_tip_xy_mm": _audit_point(
                        observation.coordinate_tip_xy_mm
                    ),
                    "fusion_weight": _audit_scalar(observation.fusion_weight),
                    "mask_mean_score": _audit_scalar(
                        observation.mask_mean_score
                    ),
                    "region_selection_score": _audit_scalar(
                        observation.region_selection_score
                    ),
                    "mask_area_fraction": _audit_scalar(
                        observation.mask_area_fraction
                    ),
                    "head_disagreement_fraction": _audit_scalar(
                        observation.head_disagreement_fraction
                    ),
                    "head_disagreement_mm": _audit_scalar(
                        observation.head_disagreement_mm
                    ),
                    "decoder_uncertainty": _audit_scalar(
                        observation.decoder_uncertainty
                    ),
                    "finite_grid_fraction": _audit_scalar(
                        observation.finite_grid_fraction
                    ),
                    "channel_std_mm": _audit_point(observation.channel_std_mm),
                    "cycle_delta_from_last_accepted": _audit_scalar(
                        observation.cycle_delta_from_last_accepted
                    ),
                    "decoder_invalid_reason": observation.decoder_invalid_reason,
                },
                "elapsed_seconds": _audit_scalar(observation.elapsed_seconds),
                "gate": {
                    "accepted": decision.accepted,
                    "field_ok": decision.field_ok,
                    "geometry_ok": decision.geometry_ok,
                    "evidence_ok": decision.evidence_ok,
                    "reasons": [reason.value for reason in decision.reasons],
                    "williams_eligible": decision.williams_eligible,
                    "tip_jump_mm": _audit_scalar(decision.tip_jump_mm),
                    "max_tip_jump_mm": _audit_scalar(
                        decision.max_tip_jump_mm
                    ),
                    "roi_margin_mm": _audit_scalar(decision.roi_margin_mm),
                    "search_margin_mm": _audit_scalar(
                        decision.search_margin_mm
                    ),
                },
            }
        )
    williams_elapsed_seconds = 0.0
    if (
        record.williams is not None
        and record.williams.called
        and record.williams.solver_result is not None
    ):
        measured = _optional_finite_number(
            record.williams.solver_result.elapsed_seconds
        )
        if measured is not None and measured >= 0.0:
            williams_elapsed_seconds = measured
    controller_elapsed_seconds = float(result.total_elapsed_seconds)
    return {
        "frame_id": result.frame_id,
        "variant": result.variant.value,
        "final_state": result.final_state.value,
        "accepted_tip_xy_mm": _audit_point(result.accepted_tip_xy_mm),
        "effective_tip_xy_mm": _audit_point(_effective_tip(record)),
        "accepted_attempt_state": (
            None
            if result.accepted_attempt_state is None
            else result.accepted_attempt_state.value
        ),
        "attempts": attempts,
        "skipped_states": [state.value for state in result.skipped_states],
        "controller_total_elapsed_seconds": _audit_scalar(
            controller_elapsed_seconds
        ),
        "williams_elapsed_seconds": _audit_scalar(williams_elapsed_seconds),
        "total_elapsed_seconds": _audit_scalar(
            controller_elapsed_seconds + williams_elapsed_seconds
        ),
        "next_frame_roi": _roi_to_dict(result.next_frame_roi),
        "williams_eligible": result.williams_eligible,
        "williams_eligible_attempt_ids": list(
            result.williams_eligible_attempt_ids
        ),
        "williams": None if record.williams is None else record.williams.to_dict(),
        "reference_tip_xy_mm": _audit_point(record.reference_tip_xy_mm),
        "reference_source": record.reference_source,
        "reference_role": (
            None
            if record.reference_tip_xy_mm is None
            else "evaluation_only_after_controller_decision"
        ),
    }


@dataclass(frozen=True)
class SyntheticReplayResult:
    """One deterministic controller stress scenario and its evaluated frames."""

    name: str
    expected_behavior: str
    records: tuple[EvaluatedFrame, ...]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the same full audit representation used for real evidence."""

        return {
            "name": self.name,
            "expected_behavior": self.expected_behavior,
            "frames": [evaluated_frame_to_dict(record) for record in self.records],
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class _SyntheticSignal:
    """Absolute synthetic detector and DIC values for one attempted ROI."""

    candidate_xy_mm: tuple[float, float] | None
    coordinate_offset_xy_mm: tuple[float, float] = (0.0, 0.0)
    mask_mean_score: float | None = 0.8
    region_selection_score: float | None = 0.8
    mask_area_fraction: float | None = 0.02
    uncertainty: float = 0.1
    finite_grid_fraction: float = 1.0
    channel_std_mm: tuple[float, float] = (0.02, 0.02)
    elapsed_seconds: float = 0.001
    invalid_reason: str | None = None


@dataclass(frozen=True)
class _SyntheticFrameSpec:
    """Script one frame by controller state, never by its reference."""

    frame_id: str
    cycle_count: float | None
    reference_tip_xy_mm: tuple[float, float]
    signals: Mapping[RoiState, _SyntheticSignal]
    default_signal: _SyntheticSignal | None = None


def adapt_decoder_output(
    output: DecoderOutput,
    *,
    decoder_config: DecoderConfig,
    attempt: RoiAttempt,
    side_adapter: LegacySideAdapter,
    resolution_px: int | tuple[int, int],
    dic_quality: DicFieldQuality,
    elapsed_seconds: float,
) -> RoiObservation:
    """Translate one frozen P1 result into the controller observation schema.

    Both raw head points cross the existing :class:`LegacySideAdapter` seam
    exactly once, then :meth:`RoiObservation.from_decoder_heads` derives the
    physical candidate and disagreement with the frozen decoder fusion weight.
    Confidence stays separate and therefore cannot erase the candidate before
    fallback.
    """

    if not isinstance(output, DecoderOutput):
        raise TypeError("output must be DecoderOutput")
    if not isinstance(decoder_config, DecoderConfig):
        raise TypeError("decoder_config must be DecoderConfig")
    if not isinstance(attempt, RoiAttempt):
        raise TypeError("attempt must be RoiAttempt")
    if not isinstance(side_adapter, LegacySideAdapter):
        raise TypeError("side_adapter must be LegacySideAdapter")
    if not isinstance(dic_quality, DicFieldQuality):
        raise TypeError("dic_quality must be DicFieldQuality")
    rows, columns = _resolution_shape(resolution_px)
    mask_tip = _point_rc_to_xy_preserving_nonfinite(
        output.mask_point_rc,
        side_adapter=side_adapter,
        attempt=attempt,
        resolution_px=(rows, columns),
    )
    coordinate_tip = _point_rc_to_xy_preserving_nonfinite(
        output.coordinate_point_rc,
        side_adapter=side_adapter,
        attempt=attempt,
        resolution_px=(rows, columns),
    )
    area_fraction = (
        None
        if output.selected_region_area is None
        else float(output.selected_region_area) / float(rows * columns)
    )
    return RoiObservation.from_decoder_heads(
        frame_id=attempt.frame_id,
        attempt_id=attempt.attempt_id,
        applied_roi=attempt.roi,
        mask_tip_xy_mm=mask_tip,
        coordinate_tip_xy_mm=coordinate_tip,
        fusion_weight=decoder_config.fusion_weight,
        mask_mean_score=output.mask_confidence,
        region_selection_score=output.selected_region_score,
        mask_area_fraction=area_fraction,
        decoder_uncertainty=output.uncertainty,
        finite_grid_fraction=dic_quality.finite_grid_fraction,
        channel_std_mm=(dic_quality.ux_std_mm, dic_quality.uy_std_mm),
        cycle_delta_from_last_accepted=attempt.cycle_delta_from_last_accepted,
        elapsed_seconds=elapsed_seconds,
        decoder_invalid_reason=output.invalid_reason,
    )


def evaluate_selective_williams(
    frame_result: FrameResult,
    *,
    gate_config: GateConfig,
    solver: Callable[[RoiObservation], WilliamsSolverResult] | None,
    previous_tip_xy_mm: tuple[float, float] | None,
    policy: WilliamsPolicy | None = None,
) -> WilliamsDecision:
    """Consult Williams only after a completed marginal ROI cascade.

    Eligibility is produced by the independent controller and already means
    field and geometry passed while only explicitly marginal evidence failed.
    The solver is an injected seam; P2 validates convergence, residual
    reduction, correction size and delta consistency, then reruns the field,
    jump, ROI-margin and search-bound gates on the corrected absolute point.
    Even a valid result remains diagnostic under the default policy.
    """

    if not isinstance(frame_result, FrameResult):
        raise TypeError("frame_result must be FrameResult")
    if not isinstance(gate_config, GateConfig):
        raise TypeError("gate_config must be GateConfig")
    selected_policy = WilliamsPolicy() if policy is None else policy
    if not isinstance(selected_policy, WilliamsPolicy):
        raise TypeError("policy must be WilliamsPolicy")

    eligible = (
        frame_result.final_state is RoiState.LOST
        and frame_result.williams_eligible
        and bool(frame_result.williams_eligible_attempt_ids)
    )
    if frame_result.variant is P2Variant.P2_2_EXPANDED_FULL_SEARCH:
        completed_states = {
            *(item.attempt.state for item in frame_result.attempts),
            *frame_result.skipped_states,
        }
        eligible = eligible and RoiState.FULL_SEARCH in completed_states
    if not eligible:
        return _williams_decision(WilliamsOutcome.NOT_ELIGIBLE)
    if selected_policy.mode is WilliamsMode.OFF:
        return _williams_decision(WilliamsOutcome.DISABLED)

    eligible_ids = set(frame_result.williams_eligible_attempt_ids)
    candidates = [
        item
        for item in frame_result.attempts
        if item.attempt.attempt_id in eligible_ids
        and item.decision.field_ok
        and item.decision.geometry_ok
        and item.decision.williams_eligible
    ]
    if not candidates:
        return _williams_decision(
            WilliamsOutcome.NOT_ELIGIBLE,
            rejection_reasons=("eligible_attempt_missing",),
        )
    source = candidates[-1]
    source_id = source.attempt.attempt_id
    if solver is None:
        return _williams_decision(
            WilliamsOutcome.UNEVALUABLE,
            source_attempt_id=source_id,
            rejection_reasons=("solver_not_provided",),
        )
    try:
        solver_result = solver(source.observation)
    except Exception as exc:  # noqa: BLE001 - external numerical seam is reported, not leaked
        return _williams_decision(
            WilliamsOutcome.SOLVER_FAILED,
            called=True,
            source_attempt_id=source_id,
            rejection_reasons=(f"solver_exception:{type(exc).__name__}",),
        )
    if not isinstance(solver_result, WilliamsSolverResult):
        return _williams_decision(
            WilliamsOutcome.SOLVER_FAILED,
            called=True,
            source_attempt_id=source_id,
            rejection_reasons=("invalid_solver_result_type",),
        )

    reasons: list[str] = []
    if not solver_result.converged:
        reasons.append("not_converged")
    if (
        not isinstance(solver_result.iterations, int)
        or isinstance(solver_result.iterations, bool)
        or solver_result.iterations <= 0
    ):
        reasons.append("invalid_iterations")
    if solver_result.failure_reason:
        reasons.append(f"solver_failure:{solver_result.failure_reason}")
    residual_before = _optional_finite_number(solver_result.residual_before)
    residual_after = _optional_finite_number(solver_result.residual_after)
    if (
        residual_before is None
        or residual_after is None
        or residual_before < 0.0
        or residual_after < 0.0
    ):
        reasons.append("invalid_residual")
    elif residual_after >= residual_before:
        reasons.append("residual_not_reduced")

    delta = _optional_finite_point(solver_result.correction_delta_xy_mm)
    corrected = _optional_finite_point(solver_result.corrected_tip_xy_mm)
    if delta is None:
        reasons.append("invalid_correction_delta")
    elif math.hypot(*delta) > selected_policy.max_correction_mm:
        reasons.append("correction_too_large")
    if corrected is None:
        reasons.append("invalid_corrected_tip")
    elapsed = _optional_finite_number(solver_result.elapsed_seconds)
    if elapsed is None or elapsed < 0.0:
        reasons.append("invalid_elapsed_seconds")

    original = _optional_finite_point(source.observation.candidate_tip_xy_mm)
    if original is None:
        reasons.append("invalid_source_tip")
    if original is not None and delta is not None and corrected is not None:
        expected = original[0] + delta[0], original[1] + delta[1]
        x_consistent = math.isclose(
            expected[0], corrected[0], abs_tol=1e-9, rel_tol=0.0
        )
        y_consistent = math.isclose(
            expected[1], corrected[1], abs_tol=1e-9, rel_tol=0.0
        )
        if not x_consistent or not y_consistent:
            reasons.append("correction_delta_inconsistent")

    safety_recheck: GateDecision | None = None
    if corrected is not None:
        if source.decision.tip_jump_mm is not None and previous_tip_xy_mm is None:
            reasons.append("missing_previous_tip_for_recheck")
        else:
            corrected_observation = RoiObservation.from_decoder_heads(
                frame_id=source.observation.frame_id,
                attempt_id=source.observation.attempt_id,
                applied_roi=source.observation.applied_roi,
                mask_tip_xy_mm=corrected,
                coordinate_tip_xy_mm=corrected,
                fusion_weight=source.observation.fusion_weight,
                mask_mean_score=source.observation.mask_mean_score,
                region_selection_score=source.observation.region_selection_score,
                mask_area_fraction=source.observation.mask_area_fraction,
                decoder_uncertainty=source.observation.decoder_uncertainty,
                finite_grid_fraction=source.observation.finite_grid_fraction,
                channel_std_mm=source.observation.channel_std_mm,
                cycle_delta_from_last_accepted=(
                    source.observation.cycle_delta_from_last_accepted
                ),
                elapsed_seconds=source.observation.elapsed_seconds,
                decoder_invalid_reason=source.observation.decoder_invalid_reason,
            )
            try:
                safety_recheck = gate_config.evaluate(
                    corrected_observation,
                    previous_tip_xy_mm=previous_tip_xy_mm,
                )
            except (TypeError, ValueError):
                reasons.append("invalid_previous_tip_for_recheck")
            else:
                if not safety_recheck.field_ok:
                    reasons.append("field_recheck_failed")
                if not safety_recheck.geometry_ok:
                    reasons.append("geometry_recheck_failed")

    if reasons:
        return _williams_decision(
            WilliamsOutcome.REJECTED,
            called=True,
            source_attempt_id=source_id,
            solver_result=solver_result,
            rejection_reasons=tuple(dict.fromkeys(reasons)),
            safety_recheck=safety_recheck,
        )
    if selected_policy.mode is WilliamsMode.DIAGNOSTIC:
        return _williams_decision(
            WilliamsOutcome.DIAGNOSTIC_ONLY,
            called=True,
            source_attempt_id=source_id,
            solver_result=solver_result,
            safety_recheck=safety_recheck,
        )
    return _williams_decision(
        WilliamsOutcome.ADOPTED,
        called=True,
        adopted=True,
        source_attempt_id=source_id,
        solver_result=solver_result,
        safety_recheck=safety_recheck,
        final_tip_xy_mm=corrected,
    )


def clopper_pearson_upper(
    successes: int,
    trials: int,
    *,
    confidence: float = 0.95,
) -> float | None:
    """Return the nominal exact one-sided binomial upper confidence bound.

    The bound assumes independent Bernoulli trials.  P2 reports it together
    with an explicit correlation caveat because adjacent physical frames and
    augmented CrackMNIST samples do not justify that independence claim.
    """

    if (
        not isinstance(successes, int)
        or isinstance(successes, bool)
        or not isinstance(trials, int)
        or isinstance(trials, bool)
        or trials < 0
        or successes < 0
        or successes > trials
    ):
        raise ValueError("successes and trials must satisfy 0 <= successes <= trials")
    level = float(confidence)
    if not math.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    if trials == 0:
        return None
    if successes == trials:
        return 1.0
    if successes == 0:
        return 1.0 - (1.0 - level) ** (1.0 / trials)
    return float(beta.ppf(level, successes + 1, trials - successes))


def aggregate_sequence_metrics(
    frames: tuple[EvaluatedFrame, ...] | list[EvaluatedFrame],
    *,
    minimum_safe_margin_mm: float,
    confidence_threshold: float,
    confident_error_threshold_mm: float,
) -> dict[str, Any]:
    """Aggregate controller, safety, accuracy, confidence and runtime evidence.

    Coverage always uses the first applied ROI and an evaluation-only
    reference, so it describes what was knowable before local detection without
    allowing that reference to choose a window.  End-to-end runtime includes
    every ROI attempt plus any actually called Williams diagnostic.
    """

    records = tuple(frames)
    if any(not isinstance(record, EvaluatedFrame) for record in records):
        raise TypeError("frames must contain EvaluatedFrame values")
    safe_margin = _finite_non_negative(
        minimum_safe_margin_mm,
        name="minimum_safe_margin_mm",
    )
    confidence_gate = _bounded_fraction(
        confidence_threshold,
        name="confidence_threshold",
    )
    error_gate = _finite_non_negative(
        confident_error_threshold_mm,
        name="confident_error_threshold_mm",
    )

    total = len(records)
    reference_count = 0
    inside_count = 0
    safe_count = 0
    first_attempt_count = 0
    fallback_frames = 0
    recovery_count = 0
    controller_lost_count = 0
    final_lost_count = 0
    unnecessary_fallback_count = 0
    boundary_violations = 0
    final_predictions = 0
    fallback_counts = {
        RoiState.START_FALLBACK.value: 0,
        RoiState.EXPANDED_FALLBACK.value: 0,
        RoiState.FULL_SEARCH.value: 0,
    }
    rejection_reasons: dict[str, int] = {}
    errors: list[float] = []
    confident_predictions = 0
    confident_errors = 0
    runtimes: list[float] = []
    williams_calls = 0
    williams_eligible_frames = 0
    williams_decisions = 0
    williams_adopted = 0
    williams_successful = 0
    williams_rejected = 0
    williams_unevaluable = 0
    williams_disabled = 0
    williams_not_assessed_eligible = 0
    williams_outcomes: dict[str, int] = {}
    williams_runtimes: list[float] = []
    williams_error_before: list[float] = []
    williams_error_after: list[float] = []
    williams_error_delta: list[float] = []
    rejected_williams_error_before: list[float] = []
    rejected_williams_error_after: list[float] = []
    rejected_williams_error_delta: list[float] = []

    for record in records:
        result = record.result
        if not result.attempts:
            raise ValueError("every evaluated frame must contain at least one attempt")
        first_attempt = result.attempts[0]
        attempted_states = {item.attempt.state for item in result.attempts}
        fallback_invoked = any(
            state
            in {
                RoiState.START_FALLBACK,
                RoiState.EXPANDED_FALLBACK,
                RoiState.FULL_SEARCH,
            }
            for state in attempted_states
        )
        if fallback_invoked:
            fallback_frames += 1
        for state_name in fallback_counts:
            if RoiState(state_name) in attempted_states:
                fallback_counts[state_name] += 1
        for item in result.attempts:
            if not item.decision.accepted:
                for reason in item.decision.reasons:
                    rejection_reasons[reason.value] = rejection_reasons.get(reason.value, 0) + 1

        accepted_first = (
            result.accepted_tip_xy_mm is not None
            and result.accepted_attempt_state is first_attempt.attempt.state
        )
        if accepted_first:
            first_attempt_count += 1
        if fallback_invoked and result.accepted_tip_xy_mm is not None and not accepted_first:
            recovery_count += 1
        if result.final_state is RoiState.LOST:
            controller_lost_count += 1

        williams = record.williams
        williams_elapsed = 0.0
        if result.williams_eligible:
            williams_eligible_frames += 1
            if williams is None:
                williams_not_assessed_eligible += 1
        if williams is not None:
            williams_decisions += 1
            outcome = williams.outcome.value
            williams_outcomes[outcome] = williams_outcomes.get(outcome, 0) + 1
            called_outcomes = {
                WilliamsOutcome.SOLVER_FAILED,
                WilliamsOutcome.REJECTED,
                WilliamsOutcome.DIAGNOSTIC_ONLY,
                WilliamsOutcome.ADOPTED,
            }
            if williams.called != (williams.outcome in called_outcomes):
                raise ValueError("Williams called flag and outcome are inconsistent")
            if williams.called:
                williams_calls += 1
                solver_result = williams.solver_result
                if solver_result is not None:
                    elapsed = _optional_finite_number(solver_result.elapsed_seconds)
                    if elapsed is not None and elapsed >= 0.0:
                        williams_elapsed = elapsed
                        williams_runtimes.append(elapsed)
                    corrected = _optional_finite_point(solver_result.corrected_tip_xy_mm)
                    source_attempt = next(
                        (
                            item
                            for item in result.attempts
                            if item.attempt.attempt_id == williams.source_attempt_id
                        ),
                        None,
                    )
                    source_tip = (
                        None
                        if source_attempt is None
                        else _optional_finite_point(
                            source_attempt.observation.candidate_tip_xy_mm
                        )
                    )
                    if (
                        record.reference_tip_xy_mm is not None
                        and source_tip is not None
                        and corrected is not None
                    ):
                        before = math.dist(source_tip, record.reference_tip_xy_mm)
                        after = math.dist(corrected, record.reference_tip_xy_mm)
                        if williams.outcome in {
                            WilliamsOutcome.DIAGNOSTIC_ONLY,
                            WilliamsOutcome.ADOPTED,
                        }:
                            williams_error_before.append(before)
                            williams_error_after.append(after)
                            williams_error_delta.append(after - before)
                        elif williams.outcome in {
                            WilliamsOutcome.REJECTED,
                            WilliamsOutcome.SOLVER_FAILED,
                        }:
                            rejected_williams_error_before.append(before)
                            rejected_williams_error_after.append(after)
                            rejected_williams_error_delta.append(after - before)
            if williams.adopted:
                williams_adopted += 1
            if williams.outcome in {
                WilliamsOutcome.DIAGNOSTIC_ONLY,
                WilliamsOutcome.ADOPTED,
            }:
                williams_successful += 1
            elif williams.outcome in {
                WilliamsOutcome.REJECTED,
                WilliamsOutcome.SOLVER_FAILED,
            }:
                williams_rejected += 1
            elif williams.outcome is WilliamsOutcome.UNEVALUABLE:
                williams_unevaluable += 1
            elif williams.outcome is WilliamsOutcome.DISABLED:
                williams_disabled += 1
        runtime = float(result.total_elapsed_seconds) + williams_elapsed
        if not math.isfinite(runtime) or runtime < 0.0:
            raise ValueError("frame runtime must be finite and non-negative")
        runtimes.append(runtime)

        final_tip = _effective_tip(record)
        if final_tip is None:
            final_lost_count += 1
        else:
            final_predictions += 1
            if not first_attempt.attempt.roi.search_bounds.contains(final_tip):
                boundary_violations += 1

        reference = record.reference_tip_xy_mm
        safely_covered = False
        if reference is not None:
            reference_count += 1
            first_roi = first_attempt.attempt.roi
            if first_roi.contains(reference):
                inside_count += 1
            safely_covered = first_roi.contains(reference, minimum_margin_mm=safe_margin)
            if safely_covered:
                safe_count += 1
            if fallback_invoked and safely_covered:
                unnecessary_fallback_count += 1
            if final_tip is not None:
                error = math.dist(final_tip, reference)
                errors.append(error)
                uncertainty = _effective_uncertainty(record)
                if uncertainty is not None and uncertainty <= confidence_gate:
                    confident_predictions += 1
                    if error > error_gate:
                        confident_errors += 1

    error_summary = _distribution_summary(errors)
    runtime_summary = _distribution_summary(runtimes)
    confident_upper = clopper_pearson_upper(confident_errors, confident_predictions)
    return {
        "frames": total,
        "reference_population": {
            "count": reference_count,
            "role": "evaluation_only_after_controller_decision",
        },
        "coverage": {
            "scope": "first_applied_roi_before_local_detection",
            "minimum_safe_margin_mm": safe_margin,
            "inside": _count_rate(inside_count, reference_count),
            "safe": _count_rate(safe_count, reference_count),
        },
        "acceptance": {
            "first_attempt": _count_rate(first_attempt_count, total),
            "fallback_by_stage": {
                name: _count_rate(count, total)
                for name, count in fallback_counts.items()
            },
            "recovery": _count_rate(recovery_count, fallback_frames),
            "controller_lost": _count_rate(controller_lost_count, total),
            "final_lost": _count_rate(final_lost_count, total),
            "unnecessary_fallback": _count_rate(
                unnecessary_fallback_count,
                safe_count,
            ),
        },
        "rejection_reasons": dict(sorted(rejection_reasons.items())),
        "localization_error_mm": error_summary,
        "confident_errors": {
            "confidence_threshold": confidence_gate,
            "error_threshold_mm": error_gate,
            "confident_predictions": confident_predictions,
            "count": confident_errors,
            "rate": _rate(confident_errors, confident_predictions),
            "one_sided_95_upper": confident_upper,
            "interval_method": "nominal one-sided Clopper-Pearson exact binomial",
            "correlation_caveat": (
                "Nominal only: physical sequence frames and augmented samples may be "
                "correlated, so independent Bernoulli coverage is not claimed."
            ),
        },
        "runtime_seconds": {
            "count": runtime_summary["count"],
            "p50": runtime_summary["median"],
            "p95": runtime_summary["p95"],
            "scope": "all_roi_attempts_plus_called_williams",
        },
        "boundary_violations": _count_rate(boundary_violations, final_predictions),
        "williams": {
            "eligible_frames": williams_eligible_frames,
            "decisions": williams_decisions,
            "calls": williams_calls,
            "call_rate": _rate(williams_calls, williams_eligible_frames),
            "call_rate_of_eligible": _rate(
                williams_calls,
                williams_eligible_frames,
            ),
            "successful": williams_successful,
            "success_rate_of_calls": _rate(williams_successful, williams_calls),
            "rejected": williams_rejected,
            "rejection_rate_of_calls": _rate(williams_rejected, williams_calls),
            "unevaluable": williams_unevaluable,
            "unevaluable_rate_of_eligible": _rate(
                williams_unevaluable,
                williams_eligible_frames,
            ),
            "disabled": williams_disabled,
            "disabled_rate_of_eligible": _rate(
                williams_disabled,
                williams_eligible_frames,
            ),
            "not_assessed_eligible": williams_not_assessed_eligible,
            "adopted": williams_adopted,
            "adoption_rate_of_calls": _rate(williams_adopted, williams_calls),
            "outcomes": dict(sorted(williams_outcomes.items())),
            "policy_role": "declared_by_orchestrator_or_evaluation_caller",
            "runtime_seconds": _distribution_summary(williams_runtimes),
            "quality_effect_mm": {
                "comparable_references": len(williams_error_delta),
                "error_before": _distribution_summary(williams_error_before),
                "error_after": _distribution_summary(williams_error_after),
                "after_minus_before": _distribution_summary(williams_error_delta),
                "scope": "diagnostic_only_or_adopted_solver_outputs",
                "interpretation": "negative values improve localization",
            },
            "rejected_solver_outputs_mm": {
                "comparable_references": len(rejected_williams_error_delta),
                "error_before": _distribution_summary(
                    rejected_williams_error_before
                ),
                "error_after": _distribution_summary(
                    rejected_williams_error_after
                ),
                "after_minus_before": _distribution_summary(
                    rejected_williams_error_delta
                ),
                "scope": "rejected_or_solver_failed_outputs_only",
                "interpretation": (
                    "diagnostic audit only; excluded from valid quality effect"
                ),
            },
        },
    }


def build_evidence_manifest() -> dict[str, Any]:
    """Describe P2 evidence roles without upgrading weak labels into truth.

    Dummy2 load phases are descriptive categories inferred from the recorded
    force and cycle signals, not controller inputs.  Crack-info coordinates are
    explicitly pseudoreferences because their annotation method and
    independence are not established.  Mendeley remains qualitative until the
    parallel annotation process yields verified per-frame tips.
    """

    dummy2_common = {
        "reference_kind": "pseudoreference",
        "reference_source": "test_data/crack_detection/crack_info_by_nodemap.txt",
        "signal_source": (
            "test_data/crack_detection/Nodemaps/"
            "Dummy2_WPXXX_DummyVersuch_2_dic_results_1_<stage>.txt"
        ),
    }
    dummy2_frames = [
        {
            **dummy2_common,
            "stage": 52,
            "cycles": 888983.0,
            "force_n": 14985.6119156,
            "load_phase": "peak_load_before_cycle_advance",
            "pseudoreference_left_xy_mm": [-15.43, 0.41],
            "pseudoreference_right_xy_mm": [14.90, 0.66],
        },
        {
            **dummy2_common,
            "stage": 53,
            "cycles": 901098.0,
            "force_n": 1501.60264969,
            "load_phase": "unloaded_cycle_checkpoint",
            "pseudoreference_left_xy_mm": [-15.77, 0.41],
            "pseudoreference_right_xy_mm": [15.70, 0.69],
        },
        {
            **dummy2_common,
            "stage": 54,
            "cycles": 901099.0,
            "force_n": 8231.08863831,
            "load_phase": "reload_ramp",
            "pseudoreference_left_xy_mm": [-15.77, 0.41],
            "pseudoreference_right_xy_mm": [15.70, 0.69],
        },
        {
            **dummy2_common,
            "stage": 55,
            "cycles": 901100.0,
            "force_n": 14993.2546616,
            "load_phase": "peak_load_after_cycle_advance",
            "pseudoreference_left_xy_mm": [-15.77, 0.41],
            "pseudoreference_right_xy_mm": [15.70, 0.69],
        },
    ]
    return {
        "reference_in_controller_input": False,
        "synthetic": {
            "role": "deterministic_state_and_stress_verification",
            "reference_role": "evaluation_only",
            "independent_physical_accuracy_claimed": False,
        },
        "repository_fixtures": {
            "sample_count": 3,
            "side": "left",
            "input_sources": [
                "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_7.txt",
                "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_407.txt",
                "test_data/crack_detection/raw/Nodemaps/AllDataPoints_1_807.txt",
            ],
            "reference_sources": [
                (
                    "test_data/crack_detection/raw/GroundTruth/"
                    "AllDataPoints_1_7_left.txt"
                ),
                (
                    "test_data/crack_detection/raw/GroundTruth/"
                    "AllDataPoints_1_407_left.txt"
                ),
                (
                    "test_data/crack_detection/raw/GroundTruth/"
                    "AllDataPoints_1_807_left.txt"
                ),
            ],
            "trajectory_role": "sparse_historical_replay",
            "reference_role": "evaluation_only",
            "independent_of_training_claimed": False,
        },
        "dummy2": {
            "frames": dummy2_frames,
            "reference_role": "evaluation_only",
            "load_phase_role": "descriptive_evidence_only",
            "load_phase_derivation": "recorded force ordering and cycle signals",
            "all_four_frames_required": True,
        },
        "crackmnist": {
            "resolution_mode": "trained-256",
            "role": "single_image_confidence_only",
            "sequence_accuracy_claimed": False,
            "independence_caveat": (
                "official augmented split lacks source-frame identifiers and is not a "
                "physical trajectory"
            ),
        },
        "mendeley": {
            "dataset": "https://data.mendeley.com/datasets/dywwnjv22h/1",
            "label_status": "pending_verified_tip_labels",
            "quantitative_roi_accuracy_reported": False,
            "status_interpretation": "scientific_evidence_limit_not_implementation_failure",
        },
        "raw_signal_semantics": {
            name: dict(description)
            for name, description in P2_RAW_SIGNAL_SEMANTICS.items()
        },
    }


def run_p2_benchmark(
    config: P2RunConfig,
    *,
    evidence_sets: Mapping[str, tuple[EvaluatedFrame, ...] | list[EvaluatedFrame]]
    | None = None,
    williams_policy: WilliamsPolicy | None = None,
    williams_solver: Callable[[RoiObservation], WilliamsSolverResult] | None = None,
    williams_gate_config: GateConfig | None = None,
) -> dict[str, Any]:
    """Assemble leakage-safe P2 evidence from synthetic and prepared replays.

    This orchestrator deliberately does not hide model inference or DIC file
    loading.  A caller prepares real ``EvaluatedFrame`` sequences through the
    same public controller seam and supplies them under one of three declared
    evidence roles.  Missing evidence remains visibly unevaluable.
    """

    if not isinstance(config, P2RunConfig):
        raise TypeError("config must be P2RunConfig")
    p1_contract = load_p1_signals(config.p1_results)
    if (
        not p1_contract.production_eligible
        and not config.allow_unverified_p1_for_tests
    ):
        raise ValueError(
            "in-memory P1 artifacts are unverified and test-only; provide a "
            "full-split JSON path for a production P2 run"
        )
    allowed_roles = {
        "repository_sparse",
        "dummy2",
        "crackmnist_single_image",
    }
    supplied = {} if evidence_sets is None else dict(evidence_sets)
    parsed_labels: dict[str, tuple[str, P2Variant | None]] = {}
    for label in supplied:
        role, declared_variant = _parse_evidence_set_label(label)
        if role not in allowed_roles:  # pragma: no cover - parser owns vocabulary
            raise ValueError(f"unknown P2 evidence set: {label!r}")
        parsed_labels[label] = role, declared_variant

    selected_williams_policy = (
        WilliamsPolicy(mode=WilliamsMode.OFF)
        if williams_policy is None
        else williams_policy
    )
    if not isinstance(selected_williams_policy, WilliamsPolicy):
        raise TypeError("williams_policy must be WilliamsPolicy or None")
    if williams_solver is not None and not callable(williams_solver):
        raise TypeError("williams_solver must be callable or None")
    if williams_gate_config is not None and not isinstance(
        williams_gate_config,
        GateConfig,
    ):
        raise TypeError("williams_gate_config must be GateConfig or None")

    real_evidence: dict[str, Any] = {}
    baseline_reports: dict[str, Any] = {
        name: {
            "status": "not_evaluable_without_matching_p2_evidence",
            "artifact": _audit_json_value(baseline),
        }
        for name, baseline in (config.same_scenario_p1_baselines or {}).items()
    }
    supplied_roles = {role for role, _ in parsed_labels.values()}
    statuses = {
        role: "not_provided"
        for role in sorted(allowed_roles - supplied_roles)
    }
    for name, values in supplied.items():
        role, declared_variant = parsed_labels[name]
        records = tuple(values)
        if any(not isinstance(record, EvaluatedFrame) for record in records):
            raise TypeError(f"{name} must contain EvaluatedFrame values")
        variants = {record.result.variant for record in records}
        if len(variants) != 1:
            raise ValueError(f"{name} must contain a single P2 variant")
        variant = next(iter(variants))
        if declared_variant is not None and variant is not declared_variant:
            raise ValueError(
                f"{name} declares {declared_variant.value} but contains {variant.value}"
            )
        if role == "repository_sparse":
            if len(records) != 3:
                raise ValueError("repository_sparse requires exactly three historical fixtures")
            if any(record.reference_tip_xy_mm is None for record in records):
                raise ValueError("repository_sparse requires evaluation-only fixture references")
            statuses[name] = "provided_complete"
        elif role == "dummy2":
            stages = tuple(_dummy2_stage(record.result.frame_id) for record in records)
            if stages != (52, 53, 54, 55):
                raise ValueError("dummy2 replay must contain stages 52 through 55 in order")
            if any(record.reference_tip_xy_mm is None for record in records):
                raise ValueError("dummy2 requires declared evaluation-only pseudoreferences")
            if any(
                record.reference_source is None
                or "pseudo" not in record.reference_source.lower()
                for record in records
            ):
                raise ValueError("dummy2 references must be labeled as pseudoreferences")
            statuses[name] = "provided_complete"
        else:
            if not records:
                raise ValueError("CrackMNIST confidence evidence must not be empty")
            if any(record.reference_tip_xy_mm is not None for record in records):
                raise ValueError(
                    "CrackMNIST is restricted to single-image confidence evidence"
                )
            statuses[name] = "provided_single_image_only"
        evaluated_records = _apply_williams_policy(
            records,
            policy=selected_williams_policy,
            solver=williams_solver,
            gate_config=williams_gate_config,
        )
        metrics = aggregate_sequence_metrics(
            evaluated_records,
            minimum_safe_margin_mm=config.minimum_safe_margin_mm,
            confidence_threshold=p1_contract.confidence_threshold,
            confident_error_threshold_mm=config.confident_error_threshold_mm,
        )
        real_evidence[name] = {
            "role": role,
            "variant": variant.value,
            "records": [
                evaluated_frame_to_dict(record) for record in evaluated_records
            ],
            "metrics": metrics,
        }
        baseline = (config.same_scenario_p1_baselines or {}).get(name)
        if baseline is not None:
            baseline_reports[name] = _validate_same_scenario_p1_baseline(
                baseline,
                records=evaluated_records,
                p1_contract=p1_contract,
                allow_unverified_test_source=config.allow_unverified_p1_for_tests,
            )

    primary_evidence = real_evidence.get(config.primary_sequence_evidence)
    primary = None if primary_evidence is None else primary_evidence["metrics"]
    if primary is None:
        technical_gates = {
            "status": "not_evaluable_without_primary_sequence",
            "primary_sequence_evidence": config.primary_sequence_evidence,
            f"safe_coverage_at_least_{config.minimum_safe_coverage}": None,
            "zero_boundary_violations": None,
            "final_failure_not_above_same_scenario_p1": None,
            "same_scenario_p1_failure_rate": None,
            "same_scenario_p1_baseline_status": "not_evaluable",
            "observed_final_failure_rate": None,
            "all_evaluable_passed": None,
        }
    else:
        safe_rate = primary["coverage"]["safe"]["rate"]
        final_failure = primary["acceptance"]["final_lost"]["rate"]
        safe_pass = (
            None
            if safe_rate is None
            else safe_rate >= config.minimum_safe_coverage
        )
        baseline_report = baseline_reports.get(config.primary_sequence_evidence)
        same_scenario_failure = (
            None
            if baseline_report is None
            or baseline_report["status"]
            not in {"verified", "unverified_in_memory_test_only"}
            else baseline_report["failure_rate"]
        )
        failure_pass = (
            None
            if final_failure is None or same_scenario_failure is None
            else final_failure <= same_scenario_failure
        )
        boundary_pass = primary["boundary_violations"]["count"] == 0
        gate_values = (safe_pass, boundary_pass, failure_pass)
        all_passed = (
            None if any(value is None for value in gate_values) else all(gate_values)
        )
        technical_gates = {
            "status": "evaluated" if all_passed is not None else "partially_evaluable",
            "primary_sequence_evidence": config.primary_sequence_evidence,
            f"safe_coverage_at_least_{config.minimum_safe_coverage}": safe_pass,
            "zero_boundary_violations": boundary_pass,
            "final_failure_not_above_same_scenario_p1": failure_pass,
            "same_scenario_p1_failure_rate": same_scenario_failure,
            "same_scenario_p1_baseline_status": (
                "not_provided"
                if baseline_report is None
                else baseline_report["status"]
            ),
            "same_scenario_baseline_role": (
                "prepared fixed-ROI P1 replay on identical frames and references"
            ),
            "observed_final_failure_rate": final_failure,
            "all_evaluable_passed": all_passed,
        }

    synthetic = run_synthetic_replays()
    return {
        "schema_version": 1,
        "stage": "P2",
        "scope": "adaptive_roi_evidence_without_retraining",
        "config": config.to_dict(),
        "p1_contract": p1_contract.to_dict(),
        "reference_in_controller_input": False,
        "synthetic_replays": [result.to_dict() for result in synthetic],
        "real_evidence": real_evidence,
        "real_evidence_status": statuses,
        "same_scenario_p1_baselines": baseline_reports,
        "evidence_manifest": build_evidence_manifest(),
        "technical_gates": technical_gates,
        "scientific_release": {
            "approved": False,
            "reason": (
                "independent verified real sequence tip labels remain unavailable; "
                "Dummy2 crack-info values are pseudoreferences"
            ),
            "mendeley_annotation_status": "pending_verified_tip_labels",
        },
        "deterministic_execution": {
            "training_performed": False,
            "test_recalibration_performed": False,
            "synthetic_reference_used_for_control": False,
            "williams_default": WilliamsMode.OFF.value,
        },
        "williams_execution": {
            "policy": selected_williams_policy.to_dict(),
            "solver_provided": williams_solver is not None,
            "gate_config_provided": williams_gate_config is not None,
            "execution_order": "after_terminal_roi_cascade_only",
            "missing_solver_interpretation": "unevaluable_not_rejected",
        },
    }


def _parse_evidence_set_label(label: str) -> tuple[str, P2Variant | None]:
    """Split an evidence role from its optional, explicit variant suffix."""

    if not isinstance(label, str) or not label.strip():
        raise ValueError("P2 evidence-set labels must be non-empty strings")
    role, separator, suffix = label.partition("@")
    allowed_roles = {
        "repository_sparse",
        "dummy2",
        "crackmnist_single_image",
    }
    if role not in allowed_roles:
        raise ValueError(f"unknown P2 evidence set: {label!r}")
    if not separator:
        return role, None
    if not suffix or "@" in suffix:
        raise ValueError(f"invalid P2 evidence-set variant suffix: {label!r}")
    try:
        variant = P2Variant(suffix)
    except ValueError as exc:
        raise ValueError(f"unknown P2 variant in evidence set: {label!r}") from exc
    return role, variant


def same_scenario_baseline_sha256(baseline: Mapping[str, Any]) -> str:
    """Fingerprint every baseline field except the digest that stores the result."""

    if not isinstance(baseline, Mapping):
        raise TypeError("baseline must be a mapping")
    canonical = {
        str(key): _audit_json_value(value)
        for key, value in baseline.items()
        if key != "baseline_content_sha256"
    }
    encoded = json.dumps(
        canonical,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_same_scenario_p1_baseline(
    baseline: Mapping[str, Any],
    *,
    records: tuple[EvaluatedFrame, ...],
    p1_contract: P1SignalsContract,
    allow_unverified_test_source: bool,
) -> dict[str, Any]:
    """Bind a fixed-ROI P1 comparator to the exact P2 evidence frames."""

    if baseline.get("scenario") != "same_frames_fixed_physical_roi":
        raise ValueError("same-scenario P1 baseline has an invalid scenario")
    if baseline.get("decoder") != "frozen_p1_ungated":
        raise ValueError("same-scenario P1 baseline must use frozen_p1_ungated")
    decoder_config = DecoderConfig.from_dict(
        dict(_mapping_at(baseline, "decoder_config"))
    )
    if decoder_config.uncertainty_threshold is not None:
        raise ValueError("same-scenario P1 baseline decoder must remain ungated")
    if decoder_config != p1_contract.decoder_config:
        raise ValueError("same-scenario P1 baseline decoder does not match P1")
    if baseline.get("pixels") != 256:
        raise ValueError("same-scenario P1 baseline must use trained-256 input")

    model_sha256 = _validated_sha256(
        baseline.get("model_artifact_sha256"),
        name="same-scenario model_artifact_sha256",
    )
    if model_sha256 != p1_contract.model_artifact_sha256["ParallelNets"]:
        raise ValueError("same-scenario P1 baseline model hash does not match P1")

    if p1_contract.source_artifact_sha256 is None:
        if not allow_unverified_test_source:
            raise ValueError("same-scenario baseline requires a verified P1 source")
        source_status = "unverified_in_memory_test_only"
    else:
        baseline_source_sha256 = _validated_sha256(
            baseline.get("p1_source_sha256"),
            name="same-scenario p1_source_sha256",
        )
        if baseline_source_sha256 != p1_contract.source_artifact_sha256:
            raise ValueError("same-scenario baseline P1 source hash does not match")
        source_status = "verified"

    frame_details = baseline.get("frames")
    if not isinstance(frame_details, list) or any(
        not isinstance(item, Mapping) for item in frame_details
    ):
        raise ValueError("same-scenario P1 baseline frames must be a list of objects")
    expected_frame_ids = [record.result.frame_id for record in records]
    baseline_frame_ids = [item.get("frame_id") for item in frame_details]
    if baseline_frame_ids != expected_frame_ids:
        raise ValueError("same-scenario P1 baseline frame IDs do not match P2 evidence")
    success_values = [item.get("success") for item in frame_details]
    if any(not isinstance(success, bool) for success in success_values):
        raise ValueError(
            "same-scenario P1 baseline success flags must be explicit booleans"
        )
    reconstructed_errors: list[float] = []
    for item, record, success in zip(
        frame_details,
        records,
        success_values,
        strict=True,
    ):
        candidate = _validated_optional_artifact_point(
            item.get("candidate_tip_xy_mm"),
            name="same-scenario candidate_tip_xy_mm",
        )
        invalid_reason = item.get("decoder_invalid_reason")
        if invalid_reason is not None and (
            not isinstance(invalid_reason, str) or not invalid_reason.strip()
        ):
            raise ValueError(
                "same-scenario decoder_invalid_reason must be a non-empty string or None"
            )
        reconstructed_success = candidate is not None and invalid_reason is None
        if success is not reconstructed_success:
            raise ValueError(
                "same-scenario P1 baseline success flags must match candidate and "
                "decoder-invalid details"
            )

        reference = _validated_optional_artifact_point(
            item.get("reference_tip_xy_mm"),
            name="same-scenario reference_tip_xy_mm",
        )
        expected_reference = _optional_finite_point(record.reference_tip_xy_mm)
        if not _optional_points_match(reference, expected_reference):
            raise ValueError(
                "same-scenario P1 baseline references do not match P2 evidence"
            )
        expected_reference_role = (
            "none" if expected_reference is None else "evaluation_only"
        )
        if item.get("reference_role") != expected_reference_role:
            raise ValueError(
                "same-scenario P1 baseline reference role does not match P2 evidence"
            )
        if item.get("reference_source") != record.reference_source:
            raise ValueError(
                "same-scenario P1 baseline reference source does not match P2 evidence"
            )

        expected_error = (
            math.dist(candidate, reference)
            if reconstructed_success and reference is not None
            else None
        )
        observed_error = item.get("error_mm")
        if expected_error is None:
            if observed_error is not None:
                raise ValueError(
                    "same-scenario P1 baseline error must be absent without a comparison"
                )
        else:
            observed_error_value = _finite_non_negative(
                observed_error,
                name="same-scenario error_mm",
            )
            if not math.isclose(
                observed_error_value,
                expected_error,
                abs_tol=1e-12,
                rel_tol=1e-12,
            ):
                raise ValueError(
                    "same-scenario P1 baseline error does not match candidate/reference"
                )
            reconstructed_errors.append(expected_error)

    frames_evaluated = baseline.get("frames_evaluated")
    failures = baseline.get("failures")
    if (
        not isinstance(frames_evaluated, int)
        or isinstance(frames_evaluated, bool)
        or frames_evaluated != len(records)
    ):
        raise ValueError("same-scenario P1 baseline frame count does not match")
    if (
        not isinstance(failures, int)
        or isinstance(failures, bool)
        or not 0 <= failures <= frames_evaluated
    ):
        raise ValueError("same-scenario P1 baseline failure count is invalid")
    reconstructed_failures = sum(not success for success in success_values)
    if failures != reconstructed_failures:
        raise ValueError(
            "same-scenario P1 baseline failure count is inconsistent with success flags"
        )
    failure_rate = _bounded_fraction(
        baseline.get("failure_rate"),
        name="same-scenario P1 failure_rate",
    )
    expected_rate = failures / frames_evaluated
    if not math.isclose(failure_rate, expected_rate, abs_tol=1e-12, rel_tol=0.0):
        raise ValueError("same-scenario P1 failure rate is inconsistent with counts")
    observed_localization = baseline.get("localization_error_mm")
    if not isinstance(observed_localization, Mapping):
        raise ValueError("same-scenario localization summary must be an object")
    _validate_distribution_summary(
        observed_localization,
        expected=_distribution_summary(reconstructed_errors),
        name="same-scenario localization_error_mm",
    )

    roi = _mapping_at(baseline, "roi")
    center = _finite_number_sequence(roi.get("center_xy_mm"), length=2)
    extent = _finite_number_sequence(roi.get("extent_xy_mm"), length=2)
    bounds = _finite_number_sequence(roi.get("bounds_mm"), length=4)
    search_bounds = _finite_number_sequence(
        roi.get("search_bounds_mm"),
        length=4,
    )
    valid_side_bounds = {
        (-70.0, 0.0, -35.0, 35.0),
        (0.0, 70.0, -35.0, 35.0),
    }
    expected_center = (
        (bounds[0] + bounds[1]) / 2.0,
        (bounds[2] + bounds[3]) / 2.0,
    )
    if (
        extent != (70.0, 70.0)
        or bounds != search_bounds
        or bounds not in valid_side_bounds
        or center != expected_center
    ):
        raise ValueError("same-scenario P1 baseline must use the complete 70-mm ROI")
    for record in records:
        p2_search_bounds = {
            (
                item.attempt.roi.search_bounds.x_min_mm,
                item.attempt.roi.search_bounds.x_max_mm,
                item.attempt.roi.search_bounds.y_min_mm,
                item.attempt.roi.search_bounds.y_max_mm,
            )
            for item in record.result.attempts
        }
        next_search = record.result.next_frame_roi.search_bounds
        p2_search_bounds.add(
            (
                next_search.x_min_mm,
                next_search.x_max_mm,
                next_search.y_min_mm,
                next_search.y_max_mm,
            )
        )
        if p2_search_bounds != {search_bounds}:
            raise ValueError(
                "same-scenario P1 baseline ROI does not match P2 search bounds or side"
            )

    content_sha256 = _validated_sha256(
        baseline.get("baseline_content_sha256"),
        name="same-scenario baseline_content_sha256",
    )
    if content_sha256 != same_scenario_baseline_sha256(baseline):
        raise ValueError("same-scenario P1 baseline content hash does not match")

    return {
        "status": source_status,
        "failure_rate": failure_rate,
        "frames_evaluated": frames_evaluated,
        "frame_ids_match": True,
        "model_artifact_sha256_match": True,
        "p1_source_sha256_match": (
            p1_contract.source_artifact_sha256 is not None
        ),
        "baseline_content_sha256_verified": True,
        "artifact": _audit_json_value(baseline),
    }


def _apply_williams_policy(
    records: tuple[EvaluatedFrame, ...],
    *,
    policy: WilliamsPolicy,
    solver: Callable[[RoiObservation], WilliamsSolverResult] | None,
    gate_config: GateConfig | None,
) -> tuple[EvaluatedFrame, ...]:
    """Apply one explicit post-cascade policy in sequence order."""

    prepared: list[EvaluatedFrame] = []
    previous_tip_xy_mm: tuple[float, float] | None = None
    for record in records:
        if record.williams is not None:
            raise ValueError(
                "run_p2_benchmark requires raw controller records without a "
                "pre-attached Williams decision"
            )
        result = record.result
        if not result.williams_eligible:
            decision = _williams_decision(WilliamsOutcome.NOT_ELIGIBLE)
        elif policy.mode is WilliamsMode.OFF:
            decision = _williams_decision(
                WilliamsOutcome.DISABLED,
                source_attempt_id=_last_williams_attempt_id(result),
            )
        elif gate_config is None:
            decision = _williams_decision(
                WilliamsOutcome.UNEVALUABLE,
                source_attempt_id=_last_williams_attempt_id(result),
                rejection_reasons=("gate_config_not_provided",),
            )
        else:
            decision = evaluate_selective_williams(
                result,
                gate_config=gate_config,
                solver=solver,
                previous_tip_xy_mm=previous_tip_xy_mm,
                policy=policy,
            )
        evaluated = replace(record, williams=decision)
        prepared.append(evaluated)
        effective_tip = _effective_tip(evaluated)
        if effective_tip is not None:
            previous_tip_xy_mm = effective_tip
    return tuple(prepared)


def _last_williams_attempt_id(result: FrameResult) -> int | None:
    """Return the terminal eligible attempt identifier when one exists."""

    if not result.williams_eligible_attempt_ids:
        return None
    return result.williams_eligible_attempt_ids[-1]


def run_synthetic_replays() -> tuple[SyntheticReplayResult, ...]:
    """Execute the fixed P2 state, geometry, field and confidence stress suite."""

    good_origin = _SyntheticSignal((0.0, 0.0))
    missing = _SyntheticSignal(
        None,
        mask_mean_score=None,
        region_selection_score=None,
        mask_area_fraction=None,
        uncertainty=1.0,
        invalid_reason="synthetic_missing_detection",
    )
    scenarios = (
        (
            "small_jump",
            "small cycle-scaled motion remains on the constant tracking ROI",
            (
                _SyntheticFrameSpec(
                    "small-0",
                    1.0,
                    (0.0, 0.0),
                    {RoiState.START: good_origin},
                ),
                _SyntheticFrameSpec(
                    "small-1",
                    2.0,
                    (0.4, 0.2),
                    {RoiState.TRACKING: _SyntheticSignal((0.4, 0.2))},
                ),
            ),
        ),
        (
            "large_jump",
            "an implausible jump remains rejected through expanded and full search",
            (
                _SyntheticFrameSpec(
                    "large-anchor",
                    1.0,
                    (0.0, 0.0),
                    {RoiState.START: good_origin},
                ),
                _SyntheticFrameSpec(
                    "large-jump",
                    2.0,
                    (6.0, 0.0),
                    {},
                    default_signal=_SyntheticSignal((6.0, 0.0)),
                ),
            ),
        ),
        (
            "edge_recovery",
            "a near-edge local point is accepted only after expanded coverage",
            (
                _SyntheticFrameSpec(
                    "edge",
                    1.0,
                    (4.9, 0.0),
                    {
                        RoiState.START: _SyntheticSignal((4.9, 0.0)),
                        RoiState.EXPANDED_FALLBACK: _SyntheticSignal((4.9, 0.0)),
                    },
                    default_signal=_SyntheticSignal((4.9, 0.0)),
                ),
            ),
        ),
        (
            "expanded_full_recovery",
            "missing local and expanded detections recover only in true full search",
            (
                _SyntheticFrameSpec(
                    "full-recovery",
                    1.0,
                    (15.0, 0.0),
                    {
                        RoiState.START: missing,
                        RoiState.EXPANDED_FALLBACK: missing,
                        RoiState.FULL_SEARCH: _SyntheticSignal((15.0, 0.0)),
                    },
                ),
            ),
        ),
        (
            "nan_zero_variation",
            "non-finite and zero-variation DIC evidence reaches LOST explicitly",
            (
                _SyntheticFrameSpec(
                    "invalid-field",
                    1.0,
                    (0.0, 0.0),
                    {},
                    default_signal=_SyntheticSignal(
                        (float("nan"), 0.0),
                        uncertainty=float("nan"),
                        finite_grid_fraction=float("nan"),
                        channel_std_mm=(0.0, 0.0),
                        invalid_reason="synthetic_nonfinite_field",
                    ),
                ),
            ),
        ),
        (
            "head_conflict",
            "large frozen-head disagreement is marginal but never auto-accepted",
            (
                _SyntheticFrameSpec(
                    "head-conflict",
                    1.0,
                    (0.0, 0.0),
                    {},
                    default_signal=_SyntheticSignal(
                        (0.0, 0.0),
                        coordinate_offset_xy_mm=(8.0, 0.0),
                    ),
                ),
            ),
        ),
        (
            "lost_reset",
            "a lost frame forces the next frame back to the start ROI",
            (
                _SyntheticFrameSpec(
                    "lost",
                    1.0,
                    (0.0, 0.0),
                    {},
                    default_signal=missing,
                ),
                _SyntheticFrameSpec(
                    "reset",
                    2.0,
                    (0.0, 0.0),
                    {RoiState.START: good_origin},
                ),
            ),
        ),
        (
            "confident_wrong",
            "a low-uncertainty but wrong point is counted as a confident error",
            (
                _SyntheticFrameSpec(
                    "confident-wrong",
                    1.0,
                    (4.0, 0.0),
                    {RoiState.START: _SyntheticSignal((0.0, 0.0), uncertainty=0.05)},
                ),
            ),
        ),
    )
    return tuple(
        _run_synthetic_case(name, expected_behavior, frame_specs)
        for name, expected_behavior, frame_specs in scenarios
    )


def _run_synthetic_case(
    name: str,
    expected_behavior: str,
    frame_specs: tuple[_SyntheticFrameSpec, ...],
) -> SyntheticReplayResult:
    """Execute one reference-blind script through a fresh P2.2 controller."""

    controller = AdaptiveRoiController(
        start_roi=PhysicalRoi(
            center_x_mm=0.0,
            center_y_mm=0.0,
            extent_x_mm=10.0,
            extent_y_mm=10.0,
            search_bounds=PhysicalBounds(-20.0, 20.0, -20.0, 20.0),
        ),
        gate_config=_synthetic_gate_config(),
        variant=P2Variant.P2_2_EXPANDED_FULL_SEARCH,
        expanded_scale=2.0,
    )
    records: list[EvaluatedFrame] = []
    for frame_spec in frame_specs:
        attempt = controller.begin_frame(
            frame_spec.frame_id,
            cycle_count=frame_spec.cycle_count,
        )
        while True:
            signal = frame_spec.signals.get(attempt.state, frame_spec.default_signal)
            if signal is None:
                raise RuntimeError(
                    f"synthetic frame {frame_spec.frame_id} has no signal for {attempt.state.value}"
                )
            output = _synthetic_decoder_output(attempt, signal)
            observation = adapt_decoder_output(
                output,
                decoder_config=DecoderConfig.historical(),
                attempt=attempt,
                side_adapter=LegacySideAdapter("right"),
                resolution_px=256,
                dic_quality=DicFieldQuality(
                    signal.finite_grid_fraction,
                    signal.channel_std_mm[0],
                    signal.channel_std_mm[1],
                ),
                elapsed_seconds=signal.elapsed_seconds,
            )
            step = controller.submit(observation)
            if step.frame_result is not None:
                records.append(
                    EvaluatedFrame(
                        step.frame_result,
                        frame_spec.reference_tip_xy_mm,
                        "deterministic_synthetic_reference",
                    )
                )
                break
            if step.next_attempt is None:  # pragma: no cover - RoiStep invariant
                raise RuntimeError("unfinished synthetic frame has no next attempt")
            attempt = step.next_attempt
    frozen_records = tuple(records)
    return SyntheticReplayResult(
        name=name,
        expected_behavior=expected_behavior,
        records=frozen_records,
        metrics=aggregate_sequence_metrics(
            frozen_records,
            minimum_safe_margin_mm=0.2,
            confidence_threshold=0.2,
            confident_error_threshold_mm=1.0,
        ),
    )


def _synthetic_gate_config() -> GateConfig:
    """Return fixed engineering thresholds for deterministic state coverage."""

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
        calibration_source="deterministic P2 stress-policy fixture",
    )


def _synthetic_decoder_output(
    attempt: RoiAttempt,
    signal: _SyntheticSignal,
) -> DecoderOutput:
    """Encode absolute scripted points as frozen-decoder row/column output."""

    candidate_rc = _synthetic_xy_to_rc(signal.candidate_xy_mm, attempt)
    coordinate_xy = None
    if signal.candidate_xy_mm is not None:
        candidate_x, candidate_y = signal.candidate_xy_mm
        offset_x, offset_y = signal.coordinate_offset_xy_mm
        coordinate_xy = candidate_x + offset_x, candidate_y + offset_y
    coordinate_rc = _synthetic_xy_to_rc(coordinate_xy, attempt)
    disagreement_px = (
        None
        if candidate_rc is None or coordinate_rc is None
        else math.dist(candidate_rc, coordinate_rc)
    )
    area = (
        None
        if signal.mask_area_fraction is None
        else int(round(float(signal.mask_area_fraction) * 256 * 256))
    )
    return DecoderOutput(
        point_rc=candidate_rc,
        ungated_point_rc=candidate_rc,
        mask_point_rc=candidate_rc,
        coordinate_point_rc=coordinate_rc,
        mask_confidence=signal.mask_mean_score,
        selected_region_score=signal.region_selection_score,
        selected_region_area=area,
        disagreement_px=disagreement_px,
        uncertainty=signal.uncertainty,
        invalid_reason=signal.invalid_reason,
    )


def _synthetic_xy_to_rc(
    point_xy_mm: tuple[float, float] | None,
    attempt: RoiAttempt,
) -> tuple[float, float] | None:
    """Use the legacy adapter for finite points and retain invalid sentinels."""

    if point_xy_mm is None:
        return None
    x_mm, y_mm = point_xy_mm
    if not math.isfinite(x_mm) or not math.isfinite(y_mm):
        return float(x_mm), float(y_mm)
    return LegacySideAdapter("right").point_xy_to_rc(
        point_xy_mm,
        attempt.roi,
        resolution_px=256,
    )


def load_p1_signals(source: str | Path | Mapping[str, Any]) -> P1SignalsContract:
    """Load the only P1 signal contract admissible for P2.

    The function has no recalibration path and reads only ``trained_256``.
    Any artifact that used test data for selection, made confidence rejection
    the default, or embedded the confidence threshold in the selected decoder
    is rejected before P2 can run.
    """

    (
        payload,
        source_verification_status,
        source_artifact_sha256,
        source_path,
        production_eligible,
    ) = _load_mapping(source)
    if payload.get("schema_version") != "ctd-p1-v1":
        raise ValueError("P2 requires schema_version 'ctd-p1-v1'")
    if payload.get("stage") != "P1":
        raise ValueError("P2 requires a P1 result artifact")
    scope = _mapping_at(payload, "scope")
    if scope.get("full_split") is not True:
        raise ValueError("P2 requires a P1 full split result")
    if scope.get("limit_per_split") is not None:
        raise ValueError("P2 rejects P1 smoke or limited split results")
    provenance = _mapping_at(payload, "provenance_verification")
    if provenance.get("all_checks_passed") is not True:
        raise ValueError("P1 provenance verification must have passed")
    metadata = _mapping_at(payload, "metadata")
    artifact_hashes = _mapping_at(metadata, "artifact_sha256")
    model_artifact_sha256 = {
        model_name: _validated_sha256(
            artifact_hashes.get(model_name),
            name=f"metadata.artifact_sha256.{model_name}",
        )
        for model_name in ("ParallelNets", "UNetPath")
    }
    resolutions = _mapping_at(payload, "resolutions")
    trained = _mapping_at(resolutions, "trained_256")
    if trained.get("resolution_mode") != "trained-256":
        raise ValueError("P2 accepts only the trained_256 P1 resolution")
    if trained.get("decoder_frozen_before_test") is not True:
        raise ValueError("P1 decoder must be frozen before test evaluation")
    if trained.get("test_recalibration_performed") is not False:
        raise ValueError("P2 rejects any P1 test recalibration")

    calibration = _mapping_at(trained, "calibration")
    if calibration.get("source_split") != "validation":
        raise ValueError("P1 calibration source must be validation")
    if calibration.get("test_split_used_for_selection") is not False:
        raise ValueError("P2 rejects test-split decoder selection")
    selected = DecoderConfig.from_dict(
        dict(_mapping_at(calibration, "selected_config"))
    )
    if selected.uncertainty_threshold is not None:
        raise ValueError("P1 selected_config must remain ungated for P2")

    confidence_config = DecoderConfig.from_dict(
        dict(_mapping_at(calibration, "confidence_gated_config"))
    )
    threshold = confidence_config.uncertainty_threshold
    if threshold is None:
        raise ValueError("P1 confidence threshold must be validation-frozen")
    if confidence_config.with_uncertainty_threshold(None) != selected:
        raise ValueError("confidence config must differ only by its threshold")
    risk_coverage = _mapping_at(calibration, "risk_coverage")
    selected_threshold = risk_coverage.get("selected_uncertainty_threshold")
    if selected_threshold is None or float(selected_threshold) != threshold:
        raise ValueError("confidence threshold must match validation risk coverage")

    confidence_policy = _mapping_at(trained, "confidence_policy")
    if confidence_policy.get("threshold_source") != "validation_only":
        raise ValueError("P1 confidence threshold must come from validation only")
    if confidence_policy.get("test_recalibration_performed") is not False:
        raise ValueError("P2 rejects confidence recalibration on test")
    if confidence_policy.get("hard_rejection_is_default") is not False:
        raise ValueError("confidence must trigger fallback, not default hard rejection")
    frozen_test_metrics = _mapping_at(trained, "frozen_test_metrics")
    detection_rate = frozen_test_metrics.get("detection_rate")
    if detection_rate is None:
        raise ValueError("P1 trained_256 test detection rate is required")
    detection_rate = _bounded_fraction(
        detection_rate,
        name="P1 trained_256 detection_rate",
    )

    return P1SignalsContract(
        resolution_mode="trained-256",
        decoder_config=selected,
        confidence_threshold=threshold,
        calibration_split="validation",
        test_recalibration_performed=False,
        artifact_schema_version="ctd-p1-v1",
        crackmnist_test_failure_rate_context=1.0 - detection_rate,
        model_artifact_sha256=model_artifact_sha256,
        source_verification_status=source_verification_status,
        source_artifact_sha256=source_artifact_sha256,
        source_path=source_path,
        production_eligible=production_eligible,
    )


def _load_mapping(
    source: str | Path | Mapping[str, Any],
) -> tuple[Mapping[str, Any], str, str | None, str | None, bool]:
    """Read one artifact and retain its independently reproducible file hash."""

    if isinstance(source, Mapping):
        return source, "in_memory_unverified_test_only", None, None, False
    path = Path(source).resolve()
    encoded = path.read_bytes()
    source_sha256 = hashlib.sha256(encoded).hexdigest()
    payload = json.loads(encoded.decode("utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError("P1 result root must be a JSON object")
    return payload, "file_sha256_verified", source_sha256, str(path), True


def _mapping_at(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Return a required object-valued field with a useful error."""

    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"P1 result field {key!r} must be an object")
    return value


def _validated_sha256(value: Any, *, name: str) -> str:
    """Validate and normalize one provenance digest without recomputing it."""

    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ValueError(f"{name} must be a 64-character SHA256 digest")
    return value.lower()


def _finite_number_sequence(value: Any, *, length: int) -> tuple[float, ...]:
    """Return a fixed-length finite numeric sequence for artifact contracts."""

    if isinstance(value, (str, bytes)):
        raise ValueError(f"expected {length} finite numbers")
    try:
        result = tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected {length} finite numbers") from exc
    if len(result) != length or not all(math.isfinite(item) for item in result):
        raise ValueError(f"expected {length} finite numbers")
    return result


def _resolution_shape(value: int | tuple[int, int]) -> tuple[int, int]:
    """Canonicalize an endpoint-inclusive detector-grid shape."""

    if isinstance(value, bool):
        raise ValueError("resolution_px must contain integers greater than one")
    if isinstance(value, int):
        rows = columns = value
    else:
        try:
            rows, columns = value
        except (TypeError, ValueError) as exc:
            raise ValueError("resolution_px must contain exactly two dimensions") from exc
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


def _point_rc_to_xy_preserving_nonfinite(
    point_rc: tuple[float, float] | None,
    *,
    side_adapter: LegacySideAdapter,
    attempt: RoiAttempt,
    resolution_px: tuple[int, int],
) -> tuple[float, float] | None:
    """Map finite points through the legacy seam and preserve invalid evidence."""

    if point_rc is None:
        return None
    try:
        row, column = point_rc
        row = float(row)
        column = float(column)
    except (TypeError, ValueError) as exc:
        raise ValueError("decoder point must contain two numeric coordinates") from exc
    if not math.isfinite(row) or not math.isfinite(column):
        return row, column
    return side_adapter.point_rc_to_xy(
        (row, column),
        attempt.roi,
        resolution_px=resolution_px,
    )


def _williams_decision(
    outcome: WilliamsOutcome,
    *,
    called: bool = False,
    adopted: bool = False,
    source_attempt_id: int | None = None,
    solver_result: WilliamsSolverResult | None = None,
    rejection_reasons: tuple[str, ...] = (),
    safety_recheck: GateDecision | None = None,
    final_tip_xy_mm: tuple[float, float] | None = None,
) -> WilliamsDecision:
    """Build a complete Williams decision at every early-return boundary."""

    return WilliamsDecision(
        outcome=outcome,
        called=called,
        adopted=adopted,
        source_attempt_id=source_attempt_id,
        solver_result=solver_result,
        rejection_reasons=rejection_reasons,
        safety_recheck=safety_recheck,
        final_tip_xy_mm=final_tip_xy_mm,
    )


def _optional_finite_number(value: float | None) -> float | None:
    """Return a finite scalar or ``None`` for invalid numerical evidence."""

    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _audit_scalar(value: Any) -> float | str | None:
    """Encode one raw number as strict JSON while preserving invalidity."""

    if value is None:
        return None
    result = float(value)
    if math.isnan(result):
        return "NaN"
    if math.isinf(result):
        return "Infinity" if result > 0.0 else "-Infinity"
    return result


def _audit_point(value: Any) -> list[float | str] | None:
    """Encode a two-dimensional raw point without erasing NaN or infinity."""

    if value is None:
        return None
    first, second = value
    first_value = _audit_scalar(first)
    second_value = _audit_scalar(second)
    if first_value is None or second_value is None:  # pragma: no cover - point invariant
        raise ValueError("audit points cannot contain None coordinates")
    return [first_value, second_value]


def _audit_json_value(value: Any) -> Any:
    """Recursively retain an external artifact in strict JSON form."""

    if isinstance(value, Mapping):
        return {str(key): _audit_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_audit_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        return _audit_scalar(value)
    return str(value)


def _bounds_to_dict(bounds: PhysicalBounds) -> dict[str, float]:
    """Return explicit physical edges for an audit record."""

    return {
        "x_min_mm": float(bounds.x_min_mm),
        "x_max_mm": float(bounds.x_max_mm),
        "y_min_mm": float(bounds.y_min_mm),
        "y_max_mm": float(bounds.y_max_mm),
    }


def _roi_to_dict(roi: PhysicalRoi) -> dict[str, Any]:
    """Return centre, extent, edges, and allowed search field for one ROI."""

    return {
        "center_xy_mm": [float(value) for value in roi.center_xy_mm],
        "extent_xy_mm": [float(value) for value in roi.extent_xy_mm],
        "bounds": _bounds_to_dict(roi.bounds),
        "search_bounds": _bounds_to_dict(roi.search_bounds),
        "covers_search_bounds": roi.covers_search_bounds(),
    }


def _optional_finite_point(
    value: tuple[float, float] | None,
) -> tuple[float, float] | None:
    """Return a finite two-dimensional point or ``None``."""

    if value is None:
        return None
    try:
        first, second = value
        first = float(first)
        second = float(second)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(first) or not math.isfinite(second):
        return None
    return first, second


def _validated_optional_artifact_point(
    value: Any,
    *,
    name: str,
) -> tuple[float, float] | None:
    """Validate an optional point without collapsing malformed data into ``None``."""

    if value is None:
        return None
    point = _optional_finite_point(value)
    if point is None:
        raise ValueError(f"{name} must be two finite numbers or None")
    return point


def _optional_points_match(
    first: tuple[float, float] | None,
    second: tuple[float, float] | None,
) -> bool:
    """Compare optional artifact coordinates at serialization precision."""

    if first is None or second is None:
        return first is second
    return all(
        math.isclose(left, right, abs_tol=1e-12, rel_tol=1e-12)
        for left, right in zip(first, second, strict=True)
    )


def _validate_distribution_summary(
    observed: Mapping[str, Any],
    *,
    expected: Mapping[str, float | int | None],
    name: str,
) -> None:
    """Require a stored summary to be exactly reconstructible from frame records."""

    if set(observed) != set(expected):
        raise ValueError(f"{name} fields do not match the canonical summary")
    for key, expected_value in expected.items():
        observed_value = observed.get(key)
        if expected_value is None:
            if observed_value is not None:
                raise ValueError(f"{name}.{key} must be None")
            continue
        if key == "count":
            if (
                not isinstance(observed_value, int)
                or isinstance(observed_value, bool)
                or observed_value != expected_value
            ):
                raise ValueError(f"{name}.count does not match frame records")
            continue
        try:
            numeric = float(observed_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}.{key} must be finite") from exc
        if not math.isfinite(numeric) or not math.isclose(
            numeric,
            float(expected_value),
            abs_tol=1e-12,
            rel_tol=1e-12,
        ):
            raise ValueError(f"{name}.{key} does not match frame records")


def _finite_non_negative(value: float, *, name: str) -> float:
    """Validate a finite non-negative policy value."""

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and non-negative") from exc
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _bounded_fraction(value: float, *, name: str) -> float:
    """Validate a finite value in the unit interval."""

    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return result


def _effective_tip(record: EvaluatedFrame) -> tuple[float, float] | None:
    """Return the final post-Williams tip without changing controller history."""

    williams = record.williams
    if williams is not None and williams.adopted:
        return _optional_finite_point(williams.final_tip_xy_mm)
    return _optional_finite_point(record.result.accepted_tip_xy_mm)


def _effective_uncertainty(record: EvaluatedFrame) -> float | None:
    """Return the neural uncertainty associated with the reported final tip."""

    result = record.result
    williams = record.williams
    source_id = (
        williams.source_attempt_id
        if williams is not None and williams.adopted
        else None
    )
    candidates = []
    for item in result.attempts:
        if source_id is not None and item.attempt.attempt_id == source_id:
            candidates.append(item)
        elif (
            source_id is None
            and result.accepted_attempt_state is not None
            and item.attempt.state is result.accepted_attempt_state
            and item.decision.accepted
        ):
            candidates.append(item)
    if not candidates:
        return None
    value = _optional_finite_number(candidates[-1].observation.decoder_uncertainty)
    if value is None or not 0.0 <= value <= 1.0:
        return None
    return value


def _distribution_summary(values: list[float]) -> dict[str, float | int | None]:
    """Return the stable scalar distribution summary used by P2 reports."""

    if not values:
        return {"count": 0, "median": None, "p95": None, "maximum": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "median": float(np.percentile(array, 50.0)),
        "p95": float(np.percentile(array, 95.0)),
        "maximum": float(np.max(array)),
    }


def _rate(count: int, denominator: int) -> float | None:
    """Return an explicit undefined rate for an empty population."""

    return None if denominator == 0 else count / denominator


def _count_rate(count: int, denominator: int) -> dict[str, int | float | None]:
    """Keep numerator and denominator beside every reported proportion."""

    return {
        "count": count,
        "denominator": denominator,
        "rate": _rate(count, denominator),
    }


def _dummy2_stage(frame_id: str) -> int:
    """Extract an explicit terminal Dummy2 stage without guessing other digits."""

    match = re.search(r"(?:^|[-_])(52|53|54|55)(?:\.txt)?$", frame_id)
    if match is None:
        return -1
    return int(match.group(1))

"""Real-data execution helpers for the CTD P2 adaptive-ROI benchmark.

The policy and state machine live in :mod:`crackpy.crack_detection.adaptive_roi`.
This module owns only dataset-facing concerns: DIC field checks, repository
reference adapters, and bounded analysis of the frozen P1 single-image signals.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
import hashlib
from importlib import resources
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
import torch

from crackpy.benchmarking.ctd_decoders import DecoderConfig, DecoderOutput, decode_tip
from crackpy.benchmarking.ctd_p2 import (
    DicFieldQuality,
    EvaluatedFrame,
    P2RunConfig,
    WilliamsMode,
    WilliamsPolicy,
    aggregate_sequence_metrics,
    adapt_decoder_output,
    clopper_pearson_upper,
    evaluated_frame_to_dict,
    load_p1_signals,
    run_p2_benchmark,
    same_scenario_baseline_sha256,
)
from crackpy.benchmarking.ctd_runtime import (
    collect_run_metadata,
    configure_deterministic_execution,
)
from crackpy.crack_detection.adaptive_roi import (
    AdaptiveRoiController,
    GateConfig,
    LegacySideAdapter,
    P2Variant,
    PhysicalBounds,
    PhysicalRoi,
    RoiAttempt,
    RoiObservation,
    RoiState,
)
from crackpy.crack_detection.data.datapreparation import ground_truth_import
from crackpy.crack_detection.data.optimized_interpolation import interpolate_frame
from crackpy.crack_detection.detection import CrackDetection
from crackpy.crack_detection.inference import FrozenCtdInference
from crackpy.crack_detection.model import get_model
from crackpy.input.input_data import InputData
from crackpy.structure_elements.data_files import Nodemap


_REFERENCE_KINDS = frozenset({"historical_mask_label", "pseudoreference", "none"})
_MENDELEY_FILES = {
    "1. DataFromDIC_CSV.rar": (
        5_814_691_113,
        "4840d888ae4e5e640d693fab1392804b60baaac5232a7bbaff6bfe63f65ade59",
        "required_for_p2_physical_roi",
    ),
    "2. DataAfterInterpolation_PT.rar": (
        1_484_643_198,
        "726f81fdc474688c7a454ed72f07acc6490c7f79c149829dde33c2ecd6aa9244",
        "sequence_inventory_and_128px_signal_evidence",
    ),
    "3. TrainedModel_PT.zip": (
        1_303_694_078,
        "1a5333cb01733a0bd477a5a4e7cc0ebecccf1afc8edc5d6e1660b086e2ba06e1",
        "not_required_for_p2",
    ),
    "4. Cycles vs Crack Length.xlsx": (
        43_064,
        "366be8711993ec0100c1830ca5f57d70ded3855bd12ced818ceec7f0f1c9b053",
        "crack_length_context_not_tip_ground_truth",
    ),
    "5. Readme.txt": (
        633,
        "bfd2334644ac5410a60add43fc6c3232d9d46c4dcc3a75042f740353ce9c8332",
        "dataset_naming_contract",
    ),
}


@dataclass(frozen=True)
class PseudoReference:
    """One evaluation-only crack-info row from the repository fixture."""

    tip_xy_mm: tuple[float, float]
    angle_deg: float
    reference_kind: str = "pseudoreference"


@dataclass(frozen=True)
class P2DicFrame:
    """One ordered real DIC frame and its evaluation-only reference contract."""

    frame_id: str
    data: Any
    side: str
    reference_tip_xy_mm: tuple[float, float] | None
    reference_kind: str
    cycle_count: float | None = None
    load_phase: str | None = None
    reference_source_stage: str | None = None
    reference_derivation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise ValueError("frame_id must be a non-empty string")
        if self.side not in {"left", "right"}:
            raise ValueError("side must be left or right")
        if self.reference_kind not in _REFERENCE_KINDS:
            raise ValueError(
                "reference_kind must be historical_mask_label, pseudoreference, or none"
            )
        if self.reference_tip_xy_mm is not None:
            point = tuple(float(value) for value in self.reference_tip_xy_mm)
            if len(point) != 2 or not all(math.isfinite(value) for value in point):
                raise ValueError("reference_tip_xy_mm must contain two finite coordinates")
            object.__setattr__(self, "reference_tip_xy_mm", point)
        if self.reference_kind == "none" and self.reference_tip_xy_mm is not None:
            raise ValueError("reference_kind none cannot carry a reference tip")
        if self.reference_kind != "none" and self.reference_tip_xy_mm is None:
            raise ValueError("a declared reference_kind requires a reference tip")
        if self.reference_kind == "none" and (
            self.reference_source_stage is not None
            or self.reference_derivation is not None
        ):
            raise ValueError("reference provenance requires a declared reference")
        for name in ("reference_source_stage", "reference_derivation"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{name} must be a non-empty string or None")
        if self.cycle_count is not None:
            cycle_count = float(self.cycle_count)
            if not math.isfinite(cycle_count) or cycle_count < 0.0:
                raise ValueError("cycle_count must be finite and non-negative")
            object.__setattr__(self, "cycle_count", cycle_count)


@dataclass(frozen=True)
class P2AttemptServices:
    """Replaceable numerical boundaries for one real DIC attempt."""

    interpolate: Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray | None]]
    preprocess: Callable[[np.ndarray], torch.Tensor]
    decode_tip: Callable[..., DecoderOutput]
    clock: Callable[[], float]

    @classmethod
    def defaults(cls) -> "P2AttemptServices":
        """Bind the optimized interpolator and frozen P1 preprocessing path."""

        return cls(
            interpolate=interpolate_frame,
            preprocess=CrackDetection.preprocess,
            decode_tip=decode_tip,
            clock=time.perf_counter,
        )


@dataclass(frozen=True)
class P2FullRunConfig:
    """Paths and immutable scope for one canonical P2 execution."""

    repository_root: Path
    p1_results_path: Path
    p0_results_path: Path
    mendeley_cache_root: Path
    device: str
    pixels: int = 256
    expanded_scale: float = 55.0 / 40.0
    verify_mendeley_hashes: bool = True

    def __post_init__(self) -> None:
        for name in (
            "repository_root",
            "p1_results_path",
            "p0_results_path",
            "mendeley_cache_root",
        ):
            object.__setattr__(self, name, Path(getattr(self, name)))
        if not isinstance(self.device, str) or not self.device.strip():
            raise ValueError("device must be a non-empty string")
        if self.pixels != 256:
            raise ValueError("pixels must remain at the original trained 256 resolution")
        scale = float(self.expanded_scale)
        if not math.isfinite(scale) or not 1.0 < scale < 70.0 / 40.0:
            raise ValueError("expanded_scale must create a distinct ROI below full search")
        object.__setattr__(self, "expanded_scale", scale)
        if not isinstance(self.verify_mendeley_hashes, bool):
            raise TypeError("verify_mendeley_hashes must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_root": str(self.repository_root),
            "p1_results_path": str(self.p1_results_path),
            "p0_results_path": str(self.p0_results_path),
            "mendeley_cache_root": str(self.mendeley_cache_root),
            "device": self.device,
            "pixels": self.pixels,
            "expanded_scale": self.expanded_scale,
            "verify_mendeley_hashes": self.verify_mendeley_hashes,
        }


def dic_field_quality(interpolated_displacements: Any) -> DicFieldQuality:
    """Measure finite paired coverage and variation before neural inference."""

    fields = np.asarray(interpolated_displacements, dtype=float)
    if fields.ndim != 3 or fields.shape[0] != 2:
        raise ValueError("interpolated displacements must have shape (2, rows, columns)")
    if fields.shape[1] == 0 or fields.shape[2] == 0:
        raise ValueError("interpolated displacement grids must be non-empty")
    common_finite = np.isfinite(fields).all(axis=0)
    finite_count = int(np.count_nonzero(common_finite))
    finite_fraction = finite_count / common_finite.size
    if finite_count == 0:
        ux_std = uy_std = 0.0
    else:
        ux_std = float(np.std(fields[0][common_finite]))
        uy_std = float(np.std(fields[1][common_finite]))
    return DicFieldQuality(
        finite_grid_fraction=float(finite_fraction),
        ux_std_mm=ux_std,
        uy_std_mm=uy_std,
    )


def execute_dic_attempt(
    frame: P2DicFrame,
    *,
    attempt: RoiAttempt,
    inference: Any,
    decoder_config: DecoderConfig,
    minimum_channel_std_mm: float = 1e-6,
    pixels: int = 256,
    services: P2AttemptServices | None = None,
) -> RoiObservation:
    """Interpolate, precheck, infer and adapt one controller-selected ROI.

    References remain attached to ``frame`` only for later evaluation and are
    never read here.  A non-finite or constant neural input becomes explicit
    gate evidence; it is never sent through the original model.
    """

    if not isinstance(frame, P2DicFrame):
        raise TypeError("frame must be P2DicFrame")
    if not isinstance(attempt, RoiAttempt):
        raise TypeError("attempt must be RoiAttempt")
    if frame.frame_id != attempt.frame_id:
        raise ValueError("frame and attempt identifiers must match")
    if not isinstance(decoder_config, DecoderConfig):
        raise TypeError("decoder_config must be DecoderConfig")
    if not isinstance(pixels, int) or isinstance(pixels, bool) or pixels <= 1:
        raise ValueError("pixels must be an integer greater than one")
    minimum_std = float(minimum_channel_std_mm)
    if not math.isfinite(minimum_std) or minimum_std < 0.0:
        raise ValueError("minimum_channel_std_mm must be finite and non-negative")
    selected_services = P2AttemptServices.defaults() if services is None else services
    if not isinstance(selected_services, P2AttemptServices):
        raise TypeError("services must be P2AttemptServices")

    started = selected_services.clock()
    adapter = LegacySideAdapter(frame.side)
    signed_size, offset = adapter.interpolation_args(attempt.roi)
    _, fields, _ = selected_services.interpolate(
        frame.data,
        size=signed_size,
        offset=offset,
        pixels=pixels,
        include_eps_vm=False,
    )
    quality = dic_field_quality(fields)
    output: DecoderOutput
    if not _safe_neural_field(quality, minimum_channel_std_mm=minimum_std):
        output = _invalid_dic_output("dic_field_precheck_failed")
    else:
        prepared = selected_services.preprocess(fields)
        if not isinstance(prepared, torch.Tensor) or not bool(
            torch.isfinite(prepared).all()
        ):
            output = _invalid_dic_output("dic_preprocessing_nonfinite")
        else:
            prediction = inference.predict(prepared, include_path=False)
            probabilities = prediction.tip_probabilities.detach().to("cpu")
            coordinates = prediction.coordinate_outputs.detach().to("cpu")
            if probabilities.shape[0] != 1 or coordinates.shape[0] != 1:
                raise ValueError("one DIC attempt must produce exactly one prediction")
            output = selected_services.decode_tip(
                probabilities[0],
                coordinates[0],
                config=decoder_config,
                model_pixels=pixels,
                original_pixels=pixels,
            )
    elapsed = selected_services.clock() - started
    return adapt_decoder_output(
        output,
        decoder_config=decoder_config,
        attempt=attempt,
        side_adapter=adapter,
        resolution_px=pixels,
        dic_quality=quality,
        elapsed_seconds=elapsed,
    )


def replay_dic_sequence(
    frames: Sequence[P2DicFrame],
    *,
    start_roi: PhysicalRoi,
    gate_config: GateConfig,
    variant: P2Variant | str,
    inference: Any,
    decoder_config: DecoderConfig,
    pixels: int = 256,
    expanded_scale: float | None = None,
    services: P2AttemptServices | None = None,
) -> tuple[EvaluatedFrame, ...]:
    """Run one ordered real sequence through the reference-free controller."""

    ordered = tuple(frames)
    if not ordered:
        raise ValueError("frames must not be empty")
    if any(not isinstance(frame, P2DicFrame) for frame in ordered):
        raise TypeError("frames must contain P2DicFrame values")
    sides = {frame.side for frame in ordered}
    if len(sides) != 1:
        raise ValueError("one replay sequence must contain exactly one specimen side")
    controller = AdaptiveRoiController(
        start_roi=start_roi,
        gate_config=gate_config,
        variant=variant,
        expanded_scale=expanded_scale,
    )
    results: list[EvaluatedFrame] = []
    for frame in ordered:
        attempt = controller.begin_frame(
            frame.frame_id,
            cycle_count=frame.cycle_count,
        )
        while True:
            observation = execute_dic_attempt(
                frame,
                attempt=attempt,
                inference=inference,
                decoder_config=decoder_config,
                minimum_channel_std_mm=gate_config.min_channel_std_mm,
                pixels=pixels,
                services=services,
            )
            step = controller.submit(observation)
            if step.completed:
                if step.frame_result is None:  # pragma: no cover - controller invariant
                    raise RuntimeError("completed controller step has no frame result")
                reference_source = (
                    None
                    if frame.reference_kind == "none"
                    else _reference_source(frame)
                )
                results.append(
                    EvaluatedFrame(
                        result=step.frame_result,
                        reference_tip_xy_mm=frame.reference_tip_xy_mm,
                        reference_source=reference_source,
                    )
                )
                break
            if step.next_attempt is None:  # pragma: no cover - controller invariant
                raise RuntimeError("incomplete controller step has no next attempt")
            attempt = step.next_attempt
    return tuple(results)


def evaluate_fixed_roi_p1(
    frames: Sequence[P2DicFrame],
    *,
    roi: PhysicalRoi,
    inference: Any,
    decoder_config: DecoderConfig,
    model_artifact_sha256: str,
    p1_source_sha256: str,
    minimum_channel_std_mm: float = 1e-6,
    pixels: int = 256,
    services: P2AttemptServices | None = None,
) -> dict[str, Any]:
    """Measure the frozen ungated P1 decoder on the exact comparison frames.

    This is the only valid failure-rate comparator for an adaptive replay.
    P2 evidence gates are intentionally absent; the baseline asks only whether
    the original fixed-ROI decoder produced a finite candidate.
    """

    ordered = tuple(frames)
    if not ordered:
        raise ValueError("frames must not be empty")
    if pixels != 256:
        raise ValueError("same-scenario P1 baseline requires the trained 256 pixels")
    if any(not isinstance(frame, P2DicFrame) for frame in ordered):
        raise TypeError("frames must contain P2DicFrame values")
    sides = {frame.side for frame in ordered}
    if len(sides) != 1:
        raise ValueError("same-scenario P1 baseline requires one specimen side")
    side = next(iter(sides))
    if (
        not roi.covers_search_bounds()
        or not math.isclose(roi.extent_x_mm, 70.0, abs_tol=1e-9, rel_tol=0.0)
        or not math.isclose(roi.extent_y_mm, 70.0, abs_tol=1e-9, rel_tol=0.0)
    ):
        raise ValueError("same-scenario P1 baseline requires the complete 70-mm ROI")
    expected_bounds = side_rois(side)[1].bounds
    if roi.bounds != expected_bounds:
        raise ValueError("fixed P1 ROI does not match the declared specimen side")
    if decoder_config.uncertainty_threshold is not None:
        raise ValueError("same-scenario P1 baseline requires the ungated decoder")
    for name, value in (
        ("model_artifact_sha256", model_artifact_sha256),
        ("p1_source_sha256", p1_source_sha256),
    ):
        if not _is_sha256(value):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    details: list[dict[str, Any]] = []
    errors: list[float] = []
    failures = 0
    for frame in ordered:
        attempt = RoiAttempt(
            frame_id=frame.frame_id,
            attempt_id=0,
            state=RoiState.START,
            roi=roi,
            cycle_count=frame.cycle_count,
            cycle_delta_from_last_accepted=None,
        )
        observation = execute_dic_attempt(
            frame,
            attempt=attempt,
            inference=inference,
            decoder_config=decoder_config,
            minimum_channel_std_mm=minimum_channel_std_mm,
            pixels=pixels,
            services=services,
        )
        candidate = observation.candidate_tip_xy_mm
        succeeded = bool(
            candidate is not None
            and all(math.isfinite(value) for value in candidate)
            and observation.decoder_invalid_reason is None
        )
        error_mm: float | None = None
        if not succeeded:
            failures += 1
        elif frame.reference_tip_xy_mm is not None:
            error_mm = math.dist(candidate, frame.reference_tip_xy_mm)
            errors.append(error_mm)
        details.append(
            {
                "frame_id": frame.frame_id,
                "success": succeeded,
                "candidate_tip_xy_mm": None if candidate is None else list(candidate),
                "reference_tip_xy_mm": (
                    None
                    if frame.reference_tip_xy_mm is None
                    else list(frame.reference_tip_xy_mm)
                ),
                "reference_role": (
                    "none" if frame.reference_kind == "none" else "evaluation_only"
                ),
                "reference_source": _reference_source(frame),
                "error_mm": error_mm,
                "decoder_invalid_reason": observation.decoder_invalid_reason,
                "mask_mean_score": observation.mask_mean_score,
                "region_selection_score": observation.region_selection_score,
                "mask_area_fraction": observation.mask_area_fraction,
                "head_disagreement_fraction": observation.head_disagreement_fraction,
                "finite_grid_fraction": observation.finite_grid_fraction,
                "channel_std_mm": list(observation.channel_std_mm),
                "elapsed_seconds": observation.elapsed_seconds,
            }
        )
    result: dict[str, Any] = {
        "scenario": "same_frames_fixed_physical_roi",
        "decoder": "frozen_p1_ungated",
        "decoder_config": decoder_config.to_dict(),
        "pixels": pixels,
        "model_artifact_sha256": model_artifact_sha256,
        "p1_source_sha256": p1_source_sha256,
        "roi": _roi_dict(roi),
        "frames_evaluated": len(ordered),
        "failures": failures,
        "failure_rate": failures / len(ordered),
        "localization_error_mm": _distribution(errors),
        "frames": details,
    }
    result["baseline_content_sha256"] = same_scenario_baseline_sha256(result)
    return result


def reference_tip_from_mask(
    mask: Any,
    *,
    side_adapter: LegacySideAdapter,
    full_roi: PhysicalRoi,
) -> tuple[float, float]:
    """Map the unique repository label ``2`` to absolute physical coordinates."""

    values = np.asarray(mask)
    if values.ndim != 2 or min(values.shape) <= 1:
        raise ValueError("reference mask must be a two-dimensional endpoint grid")
    tips = np.argwhere(values == 2)
    if tips.shape != (1, 2):
        raise ValueError("reference mask must contain exactly one crack-tip label")
    point_rc = float(tips[0, 0]), float(tips[0, 1])
    return side_adapter.point_rc_to_xy(
        point_rc,
        full_roi,
        resolution_px=(int(values.shape[0]), int(values.shape[1])),
    )


def parse_crack_info_rows(
    lines: Iterable[str],
) -> dict[tuple[str, str], PseudoReference]:
    """Parse repository crack-info rows without treating them as controller input."""

    reader = csv.reader(lines, skipinitialspace=True)
    rows = iter(reader)
    try:
        header = [item.strip().lower() for item in next(rows)]
    except StopIteration as error:
        raise ValueError("crack-info data is empty") from error
    expected = [
        "filename",
        "crack tip x [mm]",
        "crack tip y [mm]",
        "crack angle",
        "side",
    ]
    if header != expected:
        raise ValueError("crack-info header does not match the expected five columns")
    result: dict[tuple[str, str], PseudoReference] = {}
    for row_number, row in enumerate(rows, start=2):
        if not row or not any(item.strip() for item in row):
            continue
        if len(row) != 5:
            raise ValueError(f"crack-info row {row_number} must contain five columns")
        filename, x_text, y_text, angle_text, side_text = (
            item.strip() for item in row
        )
        side = side_text.lower()
        if side not in {"left", "right"}:
            raise ValueError(f"crack-info row {row_number} has an invalid side")
        try:
            x_mm, y_mm, angle_deg = map(float, (x_text, y_text, angle_text))
        except ValueError as error:
            raise ValueError(f"crack-info row {row_number} is not numeric") from error
        if not all(math.isfinite(value) for value in (x_mm, y_mm, angle_deg)):
            raise ValueError(f"crack-info row {row_number} contains non-finite values")
        key = filename, side
        if key in result:
            raise ValueError(f"duplicate crack-info row for {filename} and {side}")
        result[key] = PseudoReference((x_mm, y_mm), angle_deg)
    return result


def load_repository_fixture_sequence(
    repository_root: str | Path,
) -> tuple[P2DicFrame, ...]:
    """Load the three labelled left-side repository fields in stage order."""

    root = Path(repository_root)
    data_root = root / "test_data" / "crack_detection" / "raw"
    nodemap_root = data_root / "Nodemaps"
    ground_truth_root = data_root / "GroundTruth"
    full_roi = PhysicalRoi.from_bounds(
        bounds=_left_full_bounds(),
    )
    adapter = LegacySideAdapter("left")
    frames: list[P2DicFrame] = []
    for stage in ("7", "407", "807"):
        filename = f"AllDataPoints_1_{stage}.txt"
        data = InputData(Nodemap(name=filename, folder=nodemap_root))
        mask = ground_truth_import(
            str(ground_truth_root / filename),
            "left",
        )
        reference = reference_tip_from_mask(
            mask,
            side_adapter=adapter,
            full_roi=full_roi,
        )
        frames.append(
            P2DicFrame(
                frame_id=f"repository-left-{stage}",
                data=data,
                side="left",
                reference_tip_xy_mm=reference,
                reference_kind="historical_mask_label",
                reference_source_stage=stage,
                reference_derivation="direct_historical_mask_label",
            )
        )
    return tuple(frames)


def load_dummy2_sequences(
    repository_root: str | Path,
) -> dict[str, tuple[P2DicFrame, ...]]:
    """Load every Dummy2 stage for both sides with evaluation-only pseudo-labels."""

    root = Path(repository_root)
    fixture_root = root / "test_data" / "crack_detection"
    nodemap_root = fixture_root / "Nodemaps"
    references = parse_crack_info_rows(
        (fixture_root / "crack_info_by_nodemap.txt").read_text(
            encoding="utf-8"
        ).splitlines()
    )
    load_phases = {
        "52": "peak_load_before_cycle_advance",
        "53": "unloaded_cycle_checkpoint",
        "54": "reload_ramp",
        "55": "peak_load_after_cycle_advance",
    }
    data_by_stage: dict[str, tuple[str, InputData]] = {}
    for stage in load_phases:
        filename = f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt"
        data_by_stage[stage] = (
            filename,
            InputData(Nodemap(name=filename, folder=nodemap_root)),
        )
    sequences: dict[str, tuple[P2DicFrame, ...]] = {}
    for side in ("left", "right"):
        frames: list[P2DicFrame] = []
        for stage, load_phase in load_phases.items():
            filename, data = data_by_stage[stage]
            reference = references[(filename, side)]
            frames.append(
                P2DicFrame(
                    frame_id=f"dummy2-{side}-{stage}",
                    data=data,
                    side=side,
                    reference_tip_xy_mm=reference.tip_xy_mm,
                    reference_kind=reference.reference_kind,
                    cycle_count=_optional_non_negative(data.cycles),
                    load_phase=load_phase,
                    reference_source_stage=(
                        "55" if stage in {"53", "54"} else stage
                    ),
                    reference_derivation=(
                        "propagated_by_legacy_pipeline"
                        if stage in {"53", "54"}
                        else "direct_pseudoreference"
                    ),
                )
            )
        sequences[side] = tuple(frames)
    return sequences


def p2_candidate_gate_config() -> GateConfig:
    """Return the frozen P2 candidate policy without test-set tuning.

    Score, area, and disagreement limits are broad validation-split support
    limits from the P1 trained-256 records.  Physical margins and jump limits
    are explicit engineering guards and therefore remain provisional until
    independent real sequence labels are accepted.
    """

    return GateConfig(
        min_mask_mean_score=0.85,
        min_region_selection_score=0.85,
        min_mask_area_fraction=7.0 / (256 * 256),
        max_mask_area_fraction=43.0 / (256 * 256),
        max_head_disagreement_fraction=16.55 / (math.sqrt(2.0) * 127.0),
        max_decoder_uncertainty=0.20,
        mask_score_marginal_band=0.05,
        head_disagreement_marginal_band=0.02,
        decoder_uncertainty_marginal_band=0.05,
        min_tip_roi_margin_mm=1.0,
        min_tip_search_margin_mm=0.5,
        min_finite_grid_fraction=1.0,
        min_channel_std_mm=1e-6,
        jump_noise_mm=0.5,
        max_growth_mm_per_cycle=0.002,
        max_jump_without_cycles_mm=20.0,
        max_jump_cap_mm=20.0,
        calibration_source=(
            "P1 validation trained-256 raw-signal support limits; P2 physical "
            "margins and jump bounds are provisional engineering policy"
        ),
    )


def side_rois(side: str) -> tuple[PhysicalRoi, PhysicalRoi]:
    """Return the 40-mm tracking ROI and complete 70-mm side search domain."""

    if side == "right":
        search = PhysicalBounds(0.0, 70.0, -35.0, 35.0)
        start_bounds = PhysicalBounds(0.0, 40.0, -20.0, 20.0)
    elif side == "left":
        search = PhysicalBounds(-70.0, 0.0, -35.0, 35.0)
        start_bounds = PhysicalBounds(-40.0, 0.0, -20.0, 20.0)
    else:
        raise ValueError("side must be left or right")
    return (
        PhysicalRoi.from_bounds(start_bounds, search_bounds=search),
        PhysicalRoi.from_bounds(search),
    )


def mendeley_evidence_manifest(
    cache_root: str | Path,
    *,
    verify_hashes: bool,
) -> dict[str, Any]:
    """Report downloaded assets and the annotation boundary for Mendeley v1."""

    root = Path(cache_root)
    files: dict[str, Any] = {}
    for filename, (expected_size, expected_sha256, policy) in _MENDELEY_FILES.items():
        path = root / filename
        partial = root / f"{filename}.part"
        observed_size: int | None = None
        observed_sha256: str | None = None
        if path.is_file():
            observed_size = path.stat().st_size
            if observed_size != expected_size:
                status = "size_mismatch"
            elif verify_hashes:
                observed_sha256 = _sha256(path)
                status = (
                    "verified"
                    if observed_sha256 == expected_sha256
                    else "sha256_mismatch"
                )
            else:
                status = "present_size_verified"
        elif partial.is_file():
            observed_size = partial.stat().st_size
            status = "partial_download"
        else:
            status = "not_downloaded"
        files[filename] = {
            "expected_size_bytes": expected_size,
            "expected_sha256": expected_sha256,
            "observed_size_bytes": observed_size,
            "observed_sha256": observed_sha256,
            "status": status,
            "download_policy": policy,
        }
    return {
        "dataset_url": "https://data.mendeley.com/datasets/dywwnjv22h/1",
        "doi": "10.17632/dywwnjv22h.1",
        "version": 1,
        "license": "CC BY 4.0",
        "files": files,
        "interpolated_pt_inspection": {
            "experiments": 19,
            "chunks": 186,
            "frames": 17_897,
            "dtype": "float32",
            "shape": [1, 2, 128, 128],
            "load_failures": 0,
            "nonfinite_frames": 1,
            "nonfinite_frame": "E_0Deg_15%_#1 frame 3600",
            "publication_frame_count": 17_925,
            "frame_count_difference_is_open_provenance_question": True,
        },
        "raw_csv_role": "required_for_new_physical_roi_interpolation",
        "tip_label_status": "pending_annotation_and_adjudication",
        "crack_length_workbook_is_tip_ground_truth": False,
        "quantitative_roi_accuracy_reported": False,
        "annotation_manifest": {
            "tables": {
                "experiments": [
                    "dataset_doi",
                    "version",
                    "experiment_id",
                    "experiment_group_id",
                    "crack_type",
                    "initial_angle_deg",
                    "load_fraction_ultimate",
                    "specimen_id",
                    "split",
                    "split_policy_id",
                    "source_asset_sha256",
                ],
                "frames": [
                    "frame_id",
                    "experiment_group_id",
                    "archive_member",
                    "chunk_offset",
                    "sequence_ordinal",
                    "fatigue_cycles",
                    "dic_quality",
                    "calibration_id",
                ],
                "calibrations": [
                    "calibration_id",
                    "status",
                    "pixel_convention",
                    "pixel_to_specimen_mm_3x3",
                    "physical_bounds_mm",
                    "reviewer",
                ],
                "tip_annotations": [
                    "annotation_id",
                    "frame_id",
                    "crack_id",
                    "side",
                    "tip_x_px",
                    "tip_y_px",
                    "visibility",
                    "uncertainty_radius_px",
                    "path_polyline_px",
                    "review_status",
                    "reviewer_id",
                ],
            },
            "split_invariants": [
                "All frames, sides, chunks, resolutions and augmentations of one "
                "experiment_group_id remain in the same split.",
                "Physical tip coordinates are derived from an accepted calibration, "
                "never entered independently by hand.",
                "Only accepted annotations qualify as ground truth.",
            ],
        },
    }


def run_p2_full_benchmark(config: P2FullRunConfig) -> dict[str, Any]:
    """Execute frozen P1 baselines plus P2.1/P2.2 on all local real evidence."""

    if not isinstance(config, P2FullRunConfig):
        raise TypeError("config must be P2FullRunConfig")
    started = time.perf_counter()
    deterministic = configure_deterministic_execution(0)
    p1_contract = load_p1_signals(config.p1_results_path)
    if not p1_contract.production_eligible:
        raise ValueError("canonical P2 requires a verified full-split P1 artifact")
    if p1_contract.source_artifact_sha256 is None:
        raise ValueError("verified P1 artifact must expose its source SHA-256")

    artifact_paths = _model_artifact_paths()
    observed_model_hashes = {
        name: _sha256(path) for name, path in artifact_paths.items()
    }
    if observed_model_hashes != dict(p1_contract.model_artifact_sha256):
        raise RuntimeError("packaged CTD model hashes differ from the frozen P1 result")

    model_started = time.perf_counter()
    tip_model = get_model(
        "ParallelNets",
        map_location=torch.device("cpu"),
    )
    inference = FrozenCtdInference(
        tip_model,
        None,
        device=config.device,
    )
    model_loading_seconds = time.perf_counter() - model_started

    repository_frames = load_repository_fixture_sequence(config.repository_root)
    dummy2_sequences = load_dummy2_sequences(config.repository_root)
    gate_config = p2_candidate_gate_config()
    decoder_config = p1_contract.decoder_config
    model_hash = observed_model_hashes["ParallelNets"]
    p1_hash = p1_contract.source_artifact_sha256
    input_artifacts = p2_input_artifact_manifest(
        config.repository_root,
        p0_results_path=config.p0_results_path,
        p1_results_path=config.p1_results_path,
    )

    repository_baseline = evaluate_fixed_roi_p1(
        repository_frames,
        roi=side_rois("left")[1],
        inference=inference,
        decoder_config=decoder_config,
        model_artifact_sha256=model_hash,
        p1_source_sha256=p1_hash,
        minimum_channel_std_mm=gate_config.min_channel_std_mm,
        pixels=config.pixels,
    )
    dummy2_baselines = {
        side: evaluate_fixed_roi_p1(
            frames,
            roi=side_rois(side)[1],
            inference=inference,
            decoder_config=decoder_config,
            model_artifact_sha256=model_hash,
            p1_source_sha256=p1_hash,
            minimum_channel_std_mm=gate_config.min_channel_std_mm,
            pixels=config.pixels,
        )
        for side, frames in dummy2_sequences.items()
    }

    repository_replays = _variant_replays(
        repository_frames,
        side="left",
        inference=inference,
        decoder_config=decoder_config,
        gate_config=gate_config,
        config=config,
    )
    dummy2_replays = {
        side: _variant_replays(
            frames,
            side=side,
            inference=inference,
            decoder_config=decoder_config,
            gate_config=gate_config,
            config=config,
        )
        for side, frames in dummy2_sequences.items()
    }
    high_load_sequences = {
        side: (frames[0], frames[-1])
        for side, frames in dummy2_sequences.items()
    }
    high_load_baselines = {
        side: evaluate_fixed_roi_p1(
            frames,
            roi=side_rois(side)[1],
            inference=inference,
            decoder_config=decoder_config,
            model_artifact_sha256=model_hash,
            p1_source_sha256=p1_hash,
            minimum_channel_std_mm=gate_config.min_channel_std_mm,
            pixels=config.pixels,
        )
        for side, frames in high_load_sequences.items()
    }
    high_load_replays = {
        side: _variant_replays(
            frames,
            side=side,
            inference=inference,
            decoder_config=decoder_config,
            gate_config=gate_config,
            config=config,
        )
        for side, frames in high_load_sequences.items()
    }

    repository_keys = {
        variant: _evidence_key("repository_sparse", variant)
        for variant in P2Variant
    }
    dummy2_keys = {
        variant: _evidence_key("dummy2", variant)
        for variant in P2Variant
    }
    core_evidence: dict[str, tuple[EvaluatedFrame, ...]] = {}
    same_scenario_baselines: dict[str, Mapping[str, Any]] = {}
    for variant, records in repository_replays.items():
        key = repository_keys[variant]
        core_evidence[key] = records
        same_scenario_baselines[key] = repository_baseline
    for variant, records in dummy2_replays["right"].items():
        key = dummy2_keys[variant]
        core_evidence[key] = records
        same_scenario_baselines[key] = dummy2_baselines["right"]
    primary_key = repository_keys[P2Variant.P2_2_EXPANDED_FULL_SEARCH]
    core_result = run_p2_benchmark(
        P2RunConfig(
            p1_results=config.p1_results_path,
            minimum_safe_margin_mm=gate_config.min_tip_roi_margin_mm,
            confident_error_threshold_mm=1.0,
            minimum_safe_coverage=0.99,
            primary_sequence_evidence=primary_key,
            same_scenario_p1_baselines=same_scenario_baselines,
        ),
        evidence_sets=core_evidence,
        williams_policy=WilliamsPolicy(
            mode=WilliamsMode.OFF,
            calibration_source=(
                "P0 Williams run has no independent accuracy evidence and does not "
                "provide the residual contract required for safe P2 adoption"
            ),
        ),
        williams_solver=None,
        williams_gate_config=gate_config,
    )

    p1_payload = json.loads(config.p1_results_path.read_text(encoding="utf-8"))
    signal_evidence = _crackmnist_signal_evidence(
        p1_payload,
        gate_config=gate_config,
    )
    core_comparisons = {
        name: compare_same_scenario(
            core_evidence[name],
            same_scenario_baselines[name],
        )
        for name in core_result["real_evidence"]
    }
    supplementary = {
        "dummy2_left_all_load_phases": {
            variant.value: _summary_with_comparison(
                records,
                baseline=dummy2_baselines["left"],
                p1_contract=p1_contract,
                gate_config=gate_config,
            )
            for variant, records in dummy2_replays["left"].items()
        },
        "dummy2_operational_peak_load_only": {
            side: {
                "same_scenario_p1_baseline": high_load_baselines[side],
                "variants": {
                    variant.value: _summary_with_comparison(
                        records,
                        baseline=high_load_baselines[side],
                        p1_contract=p1_contract,
                        gate_config=gate_config,
                    )
                    for variant, records in variants.items()
                },
            }
            for side, variants in high_load_replays.items()
        },
    }
    all_real_comparisons = {
        **core_comparisons,
        **{
            f"dummy2_left_all_load_phases@{variant.value}": value[
                "same_scenario_comparison"
            ]
            for variant, value in (
                (
                    variant,
                    supplementary["dummy2_left_all_load_phases"][variant.value],
                )
                for variant in P2Variant
            )
        },
        **{
            f"dummy2_peak_load_only_{side}@{variant.value}": supplementary[
                "dummy2_operational_peak_load_only"
            ][side]["variants"][variant.value]["same_scenario_comparison"]
            for side in ("left", "right")
            for variant in P2Variant
        },
    }
    optimization_supported = all(
        comparison["optimization_supported"] is True
        for comparison in all_real_comparisons.values()
    )
    metadata_value = collect_run_metadata(
        seed=0,
        device=config.device,
        artifact_paths=artifact_paths,
        git_root=config.repository_root,
    )
    metadata = (
        metadata_value.to_dict()
        if hasattr(metadata_value, "to_dict")
        else dict(metadata_value)
    )
    core_result.update(
        {
            "schema_version": "ctd-p2-v1",
            "full_run_config": config.to_dict(),
            "metadata": metadata,
            "deterministic_execution": {
                **core_result["deterministic_execution"],
                "runtime_configuration": deterministic.to_dict(),
            },
            "model_lifecycle": {
                "tip_model_loads": 1,
                "path_model_loads": 0,
                "persistent_device_residency": True,
                "torch_inference_mode": True,
                "tip_model_loading_seconds": model_loading_seconds,
                "parallel_nets_sha256": model_hash,
            },
            "input_artifacts": input_artifacts,
            "candidate_gate_config": _gate_config_dict(gate_config),
            "same_scenario_p1_baselines_by_population": {
                "repository_sparse_left": repository_baseline,
                "dummy2_all_load_phases": dummy2_baselines,
                "dummy2_peak_load_only": high_load_baselines,
            },
            "same_scenario_comparisons": core_comparisons,
            "supplementary_real_evidence": supplementary,
            "crackmnist_raw_signal_evidence": signal_evidence,
            "historical_williams_evidence": _historical_williams_evidence(
                config.p0_results_path
            ),
            "mendeley_evidence": mendeley_evidence_manifest(
                config.mendeley_cache_root,
                verify_hashes=config.verify_mendeley_hashes,
            ),
            "optimization_decision": {
                "controller_technical_gates_passed": core_result[
                    "technical_gates"
                ]["all_evaluable_passed"],
                "same_scenario_localization_non_degraded_across_real_replays": (
                    optimization_supported
                ),
                "promote_p2_1_as_default": False,
                "promote_p2_2_as_default": False,
                "recommended_default": "retain frozen fixed-70-mm P1",
                "adaptive_roi_status": "implemented_experimental_not_promoted",
                "reason": (
                    "Safety and failure gates pass, but the 40-mm adaptive policy "
                    "does not improve same-frame localization against fixed P1 and "
                    "independent sequence labels remain unavailable."
                ),
            },
            "full_run_elapsed_seconds": time.perf_counter() - started,
        }
    )
    return core_result


def analyze_p1_signal_records(
    records: Sequence[Mapping[str, Any]],
    *,
    model_pixels: int,
    original_pixels: int,
    min_mask_score: float,
    min_mask_area_fraction: float,
    max_mask_area_fraction: float,
    max_head_disagreement_fraction: float,
    confident_error_threshold_px: float,
) -> dict[str, Any]:
    """Audit frozen P1 raw gates as single-image evidence only.

    The denominator deliberately remains all successful mask detections.
    Missing coordinate heads therefore lower gate coverage rather than silently
    disappearing from the result.
    """

    if model_pixels <= 1 or original_pixels <= 1:
        raise ValueError("pixel resolutions must be greater than one")
    area_denominator = float(model_pixels * model_pixels)
    disagreement_denominator = math.sqrt(2.0) * (original_pixels - 1)
    successful = 0
    evaluable = 0
    passed = 0
    confident_errors = 0
    passed_errors: list[float] = []
    for record in records:
        if record.get("point_rc") is None:
            continue
        successful += 1
        score = _optional_finite(record.get("mask_confidence"))
        area = _optional_finite(record.get("selected_region_area"))
        disagreement = _optional_finite(record.get("disagreement_px"))
        coordinate = record.get("coordinate_point_rc")
        if score is None or area is None or disagreement is None or coordinate is None:
            continue
        evaluable += 1
        area_fraction = area / area_denominator
        disagreement_fraction = disagreement / disagreement_denominator
        gate_passed = (
            score >= min_mask_score
            and min_mask_area_fraction <= area_fraction <= max_mask_area_fraction
            and disagreement_fraction <= max_head_disagreement_fraction
        )
        if not gate_passed:
            continue
        passed += 1
        error = _optional_finite(record.get("error_px"))
        if error is not None:
            passed_errors.append(error)
            if error > confident_error_threshold_px:
                confident_errors += 1
    confident_bound = (
        clopper_pearson_upper(confident_errors, len(passed_errors))
        if passed_errors
        else None
    )
    return {
        "role": "single_image_confidence_only",
        "sequence_accuracy_claimed": False,
        "samples": len(records),
        "successful_detections": successful,
        "raw_gate_evaluable": evaluable,
        "raw_gate_passed": passed,
        "raw_gate_coverage_of_successful": _rate(passed, successful),
        "raw_gate_coverage_of_evaluable": _rate(passed, evaluable),
        "confident_error_threshold_px": float(confident_error_threshold_px),
        "confident_error_count": confident_errors,
        "confident_error_denominator": len(passed_errors),
        "confident_error_one_sided_95_upper": confident_bound,
        "correlation_caveat": (
            "Nominal sample-level bound; CrackMNIST augmentations may be correlated."
        ),
        "gate": {
            "min_mask_score": float(min_mask_score),
            "min_mask_area_fraction": float(min_mask_area_fraction),
            "max_mask_area_fraction": float(max_mask_area_fraction),
            "max_head_disagreement_fraction": float(
                max_head_disagreement_fraction
            ),
        },
    }


def compare_same_scenario(
    adaptive_records: Sequence[EvaluatedFrame],
    fixed_p1_baseline: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare paired adaptive/fixed outcomes on exact frames and references."""

    records = tuple(adaptive_records)
    if not records or any(not isinstance(item, EvaluatedFrame) for item in records):
        raise ValueError("adaptive_records must contain EvaluatedFrame values")
    baseline_frames = fixed_p1_baseline.get("frames")
    if not isinstance(baseline_frames, list) or any(
        not isinstance(item, Mapping) for item in baseline_frames
    ):
        raise ValueError("fixed P1 baseline frames must be a list of objects")
    adaptive_ids = [record.result.frame_id for record in records]
    baseline_ids = [item.get("frame_id") for item in baseline_frames]
    if adaptive_ids != baseline_ids:
        raise ValueError("fixed and adaptive frame IDs do not match")
    frames_evaluated = fixed_p1_baseline.get("frames_evaluated")
    if (
        not isinstance(frames_evaluated, int)
        or isinstance(frames_evaluated, bool)
        or frames_evaluated != len(records)
    ):
        raise ValueError("fixed P1 frame count does not match adaptive records")

    adaptive_success_ids: set[str] = set()
    baseline_success_ids: set[str] = set()
    adaptive_errors: list[float] = []
    baseline_errors: list[float] = []
    paired_deltas: list[float] = []
    paired_rows: list[dict[str, Any]] = []
    for record, baseline_frame in zip(records, baseline_frames, strict=True):
        reference = record.reference_tip_xy_mm
        baseline_reference = _optional_point(
            baseline_frame.get("reference_tip_xy_mm"),
            name="fixed P1 reference_tip_xy_mm",
        )
        if not _points_equal(reference, baseline_reference):
            raise ValueError("fixed and adaptive reference coordinates do not match")
        if baseline_frame.get("reference_source") != record.reference_source:
            raise ValueError("fixed and adaptive reference sources do not match")

        adaptive_tip = _effective_record_tip(record)
        adaptive_success = adaptive_tip is not None
        baseline_success = baseline_frame.get("success")
        if not isinstance(baseline_success, bool):
            raise ValueError("fixed P1 success flags must be explicit booleans")
        baseline_tip = _optional_point(
            baseline_frame.get("candidate_tip_xy_mm"),
            name="fixed P1 candidate_tip_xy_mm",
        )
        invalid_reason = baseline_frame.get("decoder_invalid_reason")
        if invalid_reason is not None and (
            not isinstance(invalid_reason, str) or not invalid_reason.strip()
        ):
            raise ValueError("fixed P1 decoder invalid reason is malformed")
        reconstructed_baseline_success = (
            baseline_tip is not None and invalid_reason is None
        )
        if baseline_success is not reconstructed_baseline_success:
            raise ValueError("fixed P1 success does not match candidate details")
        frame_id = record.result.frame_id
        if adaptive_success:
            adaptive_success_ids.add(frame_id)
        if baseline_success:
            baseline_success_ids.add(frame_id)

        adaptive_error = None
        baseline_error = None
        if reference is not None and adaptive_tip is not None:
            adaptive_error = math.dist(adaptive_tip, reference)
        if reference is not None and baseline_tip is not None and baseline_success:
            baseline_error = math.dist(baseline_tip, reference)
        if adaptive_error is not None and baseline_error is not None:
            adaptive_errors.append(adaptive_error)
            baseline_errors.append(baseline_error)
            paired_deltas.append(adaptive_error - baseline_error)
        paired_rows.append(
            {
                "frame_id": frame_id,
                "adaptive_success": adaptive_success,
                "fixed_p1_success": baseline_success,
                "adaptive_error_mm": adaptive_error,
                "fixed_p1_error_mm": baseline_error,
                "adaptive_minus_fixed_error_mm": (
                    None
                    if adaptive_error is None or baseline_error is None
                    else adaptive_error - baseline_error
                ),
            }
        )

    adaptive_failure = 1.0 - len(adaptive_success_ids) / len(records)
    baseline_failure = 1.0 - len(baseline_success_ids) / len(records)
    stored_failures = fixed_p1_baseline.get("failures")
    reconstructed_failures = len(records) - len(baseline_success_ids)
    if (
        not isinstance(stored_failures, int)
        or isinstance(stored_failures, bool)
        or stored_failures != reconstructed_failures
    ):
        raise ValueError("fixed P1 failure count does not match frame details")
    stored_baseline_failure = _optional_finite(fixed_p1_baseline.get("failure_rate"))
    if stored_baseline_failure is None or not math.isclose(
        stored_baseline_failure,
        baseline_failure,
        abs_tol=1e-12,
        rel_tol=0.0,
    ):
        raise ValueError("fixed P1 failure rate does not match frame details")
    content_sha256 = fixed_p1_baseline.get("baseline_content_sha256")
    if not _is_sha256(content_sha256) or content_sha256 != (
        same_scenario_baseline_sha256(fixed_p1_baseline)
    ):
        raise ValueError("fixed P1 baseline content hash does not match")
    failure_non_degraded = adaptive_failure <= baseline_failure + 1e-12
    success_population_same = adaptive_success_ids == baseline_success_ids
    adaptive_distribution = _distribution(adaptive_errors)
    baseline_distribution = _distribution(baseline_errors)
    delta_distribution = _distribution(paired_deltas)
    adaptive_median = _optional_finite(adaptive_distribution["median"])
    baseline_median = _optional_finite(baseline_distribution["median"])
    adaptive_p95 = _optional_finite(adaptive_distribution["p95"])
    baseline_p95 = _optional_finite(baseline_distribution["p95"])
    median_delta = (
        None
        if adaptive_median is None or baseline_median is None
        else adaptive_median - baseline_median
    )
    p95_delta = (
        None
        if adaptive_p95 is None or baseline_p95 is None
        else adaptive_p95 - baseline_p95
    )
    localization_non_degraded = (
        None
        if median_delta is None or p95_delta is None
        else (
            success_population_same
            and median_delta <= 1e-12
            and p95_delta <= 1e-12
        )
    )
    optimization_supported = (
        None
        if failure_non_degraded is None or localization_non_degraded is None
        else failure_non_degraded and localization_non_degraded
    )
    return {
        "same_frames_and_references": True,
        "success_population_same": success_population_same,
        "paired_comparable_frames": len(paired_deltas),
        "paired_error_delta_mm": delta_distribution,
        "paired_frames": paired_rows,
        "adaptive_failure_rate": adaptive_failure,
        "fixed_p1_failure_rate": baseline_failure,
        "failure_rate_non_degraded": failure_non_degraded,
        "adaptive_median_error_mm": adaptive_median,
        "fixed_p1_median_error_mm": baseline_median,
        "median_error_delta_mm": median_delta,
        "adaptive_p95_error_mm": adaptive_p95,
        "fixed_p1_p95_error_mm": baseline_p95,
        "p95_error_delta_mm": p95_delta,
        "localization_non_degraded": localization_non_degraded,
        "optimization_supported": optimization_supported,
        "reference_caveat": (
            "Repository labels are sparse historical fixtures and Dummy2 values are "
            "partly propagated pseudoreferences, not independent release evidence."
        ),
    }


def _optional_finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _optional_point(value: Any, *, name: str) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain two finite coordinates or None")
    try:
        point = tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two finite coordinates or None") from exc
    if len(point) != 2 or not all(math.isfinite(item) for item in point):
        raise ValueError(f"{name} must contain two finite coordinates or None")
    return point


def _points_equal(
    first: tuple[float, float] | None,
    second: tuple[float, float] | None,
) -> bool:
    if first is None or second is None:
        return first is second
    return all(
        math.isclose(left, right, abs_tol=1e-12, rel_tol=1e-12)
        for left, right in zip(first, second, strict=True)
    )


def _effective_record_tip(record: EvaluatedFrame) -> tuple[float, float] | None:
    williams = record.williams
    if williams is not None and williams.adopted:
        return williams.final_tip_xy_mm
    return record.result.accepted_tip_xy_mm


def _optional_non_negative(value: Any) -> float | None:
    result = _optional_finite(value)
    if result is not None and result < 0.0:
        raise ValueError("cycle metadata must be non-negative")
    return result


def _left_full_bounds() -> PhysicalBounds:
    return PhysicalBounds(-70.0, 0.0, -35.0, 35.0)


def _variant_replays(
    frames: Sequence[P2DicFrame],
    *,
    side: str,
    inference: Any,
    decoder_config: DecoderConfig,
    gate_config: GateConfig,
    config: P2FullRunConfig,
) -> dict[P2Variant, tuple[EvaluatedFrame, ...]]:
    start_roi, _ = side_rois(side)
    return {
        P2Variant.P2_1_START_RESET: replay_dic_sequence(
            frames,
            start_roi=start_roi,
            gate_config=gate_config,
            variant=P2Variant.P2_1_START_RESET,
            inference=inference,
            decoder_config=decoder_config,
            pixels=config.pixels,
        ),
        P2Variant.P2_2_EXPANDED_FULL_SEARCH: replay_dic_sequence(
            frames,
            start_roi=start_roi,
            gate_config=gate_config,
            variant=P2Variant.P2_2_EXPANDED_FULL_SEARCH,
            expanded_scale=config.expanded_scale,
            inference=inference,
            decoder_config=decoder_config,
            pixels=config.pixels,
        ),
    }


def _evidence_key(role: str, variant: P2Variant) -> str:
    return f"{role}@{variant.value}"


def _summarize_records(
    records: Sequence[EvaluatedFrame],
    *,
    p1_contract: Any,
    gate_config: GateConfig,
) -> dict[str, Any]:
    values = tuple(records)
    variants = {record.result.variant for record in values}
    if len(variants) != 1:
        raise ValueError("supplementary replay must contain one P2 variant")
    return {
        "variant": next(iter(variants)).value,
        "records": [evaluated_frame_to_dict(record) for record in values],
        "metrics": aggregate_sequence_metrics(
            values,
            minimum_safe_margin_mm=gate_config.min_tip_roi_margin_mm,
            confidence_threshold=p1_contract.confidence_threshold,
            confident_error_threshold_mm=1.0,
        ),
    }


def _summary_with_comparison(
    records: Sequence[EvaluatedFrame],
    *,
    baseline: Mapping[str, Any],
    p1_contract: Any,
    gate_config: GateConfig,
) -> dict[str, Any]:
    summary = _summarize_records(
        records,
        p1_contract=p1_contract,
        gate_config=gate_config,
    )
    summary["same_scenario_comparison"] = compare_same_scenario(
        records,
        baseline,
    )
    return summary


def _crackmnist_signal_evidence(
    p1_payload: Mapping[str, Any],
    *,
    gate_config: GateConfig,
) -> dict[str, Any]:
    trained = p1_payload["resolutions"]["trained_256"]
    calibration_samples = trained["calibration"]["selection_metrics"]["samples"]
    test_samples = trained["frozen_test_metrics"]["samples"]
    error_threshold = float(
        p1_payload["p0_reference_and_policy"]["maximum_p95_error_px"]
    )
    arguments = {
        "model_pixels": 256,
        "original_pixels": 128,
        "min_mask_score": gate_config.min_mask_mean_score,
        "min_mask_area_fraction": gate_config.min_mask_area_fraction,
        "max_mask_area_fraction": gate_config.max_mask_area_fraction,
        "max_head_disagreement_fraction": (
            gate_config.max_head_disagreement_fraction
        ),
        "confident_error_threshold_px": error_threshold,
    }
    return {
        "threshold_source": "P1 validation only plus provisional engineering policy",
        "validation": analyze_p1_signal_records(calibration_samples, **arguments),
        "frozen_test_audit": analyze_p1_signal_records(test_samples, **arguments),
        "interpretation": (
            "single-image signal audit only; no physical sequence or adaptive-ROI "
            "accuracy claim"
        ),
    }


def _historical_williams_evidence(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    b2 = payload["b2"]
    initial = tuple(float(value) for value in b2["initial_ai_tip_mm"])
    final = tuple(float(value) for value in b2["final_tip_mm"])
    pseudo_reference = (14.90, 0.66)
    return {
        "source_p0_sha256": _sha256(path),
        "source_stage": "Dummy2 right stage 52",
        "policy_in_p2": "off",
        "reason": (
            "No independent ground truth and no residual-before/after contract; the "
            "historical correction is therefore not eligible for P2 adoption."
        ),
        "initial_tip_xy_mm": list(initial),
        "corrected_tip_xy_mm": list(final),
        "correction_vector_mm": list(b2["correction_vector_mm"]),
        "iterations": int(b2["iterations"]),
        "median_runtime_seconds": (
            float(b2["runtime"]["phases"]["williams_correction"]["median_ms"])
            / 1000.0
        ),
        "dummy2_pseudoreference_xy_mm": list(pseudo_reference),
        "error_to_pseudoreference_before_mm": math.dist(initial, pseudo_reference),
        "error_to_pseudoreference_after_mm": math.dist(final, pseudo_reference),
        "pseudoreference_used_for_control": False,
        "independent_accuracy_claim_supported": False,
    }


def _gate_config_dict(config: GateConfig) -> dict[str, Any]:
    return {
        name: getattr(config, name)
        for name in config.__dataclass_fields__
    }


def _model_artifact_paths() -> dict[str, Path]:
    folder = Path(str(resources.files("crackpy").joinpath("crack_detection/models")))
    return {
        "ParallelNets": folder / "ParallelNets.pth",
        "UNetPath": folder / "UNetPath.pth",
    }


def p2_input_artifact_manifest(
    repository_root: str | Path,
    *,
    p0_results_path: str | Path,
    p1_results_path: str | Path,
) -> dict[str, Any]:
    """Hash every local file that supplies a real P2 input or reference."""

    root = Path(repository_root)
    fixture_root = root / "test_data" / "crack_detection"
    raw_root = fixture_root / "raw"
    paths: dict[str, Path] = {
        "p0_results": Path(p0_results_path),
        "p1_results": Path(p1_results_path),
        "dummy2/crack_info_by_nodemap": fixture_root
        / "crack_info_by_nodemap.txt",
    }
    for stage in ("7", "407", "807"):
        paths[f"repository/raw_nodemap/{stage}"] = (
            raw_root / "Nodemaps" / f"AllDataPoints_1_{stage}.txt"
        )
        paths[f"repository/historical_mask/{stage}"] = (
            raw_root / "GroundTruth" / f"AllDataPoints_1_{stage}_left.txt"
        )
    for stage in ("52", "53", "54", "55"):
        paths[f"dummy2/nodemap/{stage}"] = (
            fixture_root
            / "Nodemaps"
            / f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt"
        )
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "P2 input artifact is missing: " + ", ".join(sorted(missing))
        )
    return {
        "content_addressed": True,
        "artifacts": {
            name: {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for name, path in sorted(paths.items())
        },
    }


def _safe_neural_field(
    quality: DicFieldQuality,
    *,
    minimum_channel_std_mm: float,
) -> bool:
    return bool(
        math.isfinite(quality.finite_grid_fraction)
        and quality.finite_grid_fraction == 1.0
        and math.isfinite(quality.ux_std_mm)
        and quality.ux_std_mm >= minimum_channel_std_mm
        and math.isfinite(quality.uy_std_mm)
        and quality.uy_std_mm >= minimum_channel_std_mm
    )


def _invalid_dic_output(reason: str) -> DecoderOutput:
    return DecoderOutput(
        point_rc=None,
        ungated_point_rc=None,
        mask_point_rc=None,
        coordinate_point_rc=None,
        mask_confidence=None,
        selected_region_score=None,
        selected_region_area=None,
        disagreement_px=None,
        uncertainty=1.0,
        invalid_reason=reason,
    )


def _rate(count: int, denominator: int) -> float | None:
    return None if denominator == 0 else count / denominator


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "median": None, "p95": None, "maximum": None}
    array = np.asarray(values, dtype=float)
    return {
        "count": int(array.size),
        "median": float(np.percentile(array, 50.0)),
        "p95": float(np.percentile(array, 95.0)),
        "maximum": float(np.max(array)),
    }


def _reference_source(frame: P2DicFrame) -> str:
    parts = [frame.reference_kind, "evaluation-only"]
    if frame.reference_derivation is not None:
        parts.append(frame.reference_derivation)
    if frame.reference_source_stage is not None:
        parts.append(f"source-stage={frame.reference_source_stage}")
    return "; ".join(parts)


def _roi_dict(roi: PhysicalRoi) -> dict[str, Any]:
    bounds = roi.bounds
    search = roi.search_bounds
    return {
        "center_xy_mm": list(roi.center_xy_mm),
        "extent_xy_mm": list(roi.extent_xy_mm),
        "bounds_mm": [
            bounds.x_min_mm,
            bounds.x_max_mm,
            bounds.y_min_mm,
            bounds.y_max_mm,
        ],
        "search_bounds_mm": [
            search.x_min_mm,
            search.x_max_mm,
            search.y_min_mm,
            search.y_max_mm,
        ],
    }


def _is_sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

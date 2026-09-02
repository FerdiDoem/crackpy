"""Phase-resolved runtime sweeps for persistent frozen P1 inference."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from enum import Enum
import math
import time
from typing import Any

import numpy as np
import torch
from skimage.morphology import skeletonize
from torch import nn

from crackpy.benchmarking.ctd_baseline import (
    FIXTURE_WINDOW_MM,
    ResolutionMode,
    prepare_crackmnist_inputs,
)
from crackpy.benchmarking.ctd_decoders import DecoderConfig, decode_tip
from crackpy.benchmarking.ctd_runtime import benchmark_phases
from crackpy.crack_detection.detection import CrackAngleEstimation, CrackDetection
from crackpy.crack_detection.data.interpolation import interpolate as legacy_interpolate
from crackpy.crack_detection.data.optimized_interpolation import interpolate_frame
from crackpy.crack_detection.inference import FrozenCtdInference


class P1InferenceMode(str, Enum):
    """P1 inference products whose costs must be reported independently."""

    TIP_ONLY = "tip_only"
    TIP_PATH_ANGLE = "tip_path_angle"


def measure_p1_model_loading(
    model_loader: Callable[[], nn.Module],
    *,
    phase_name: str,
    first_in_process: bool,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> tuple[dict[str, Any], nn.Module]:
    """Measure one CPU model load before that model is prepared for a device.

    Separate calls let the orchestrator defer both loading and device residency
    of UNetPath until the path-and-angle benchmark actually begins.
    """

    if not isinstance(phase_name, str) or not phase_name.strip():
        raise ValueError("phase_name must be non-empty")
    loaded: nn.Module | None = None

    def load_once() -> None:
        nonlocal loaded
        if loaded is not None:
            raise RuntimeError("P1 model loader was invoked more than once")
        candidate = model_loader()
        if not isinstance(candidate, nn.Module):
            raise TypeError("model_loader must return one torch.nn.Module")
        loaded = candidate

    runtime = benchmark_phases(
        {phase_name: load_once},
        warmup_iterations=0,
        measured_iterations=1,
        device="cpu",
        clock_ns=clock_ns,
    )
    if loaded is None:
        raise RuntimeError("model loader completed without returning models")
    return {
        "phase_name": phase_name,
        "first_in_process": bool(first_in_process),
        "models_prepared_for_device": False,
        "runtime": runtime.to_dict(),
    }, loaded


def measure_p1_model_phases(
    inference: FrozenCtdInference,
    *,
    raw_inputs: torch.Tensor | np.ndarray,
    mode: P1InferenceMode | str,
    resolution_mode: ResolutionMode | str,
    tip_decoder_config: DecoderConfig | None = None,
    sample_sides: Sequence[str] | None = None,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    """Measure one pre-gridded batch without plotting or result writing.

    Path-angle postprocessing retains CrackPy's historical 256-pixel geometry.
    Lower resolutions are therefore accepted only for the genuine tip-only path.
    """

    selected_mode = P1InferenceMode(mode)
    selected_resolution = ResolutionMode(resolution_mode)
    selected_decoder = (
        DecoderConfig.historical()
        if tip_decoder_config is None
        else tip_decoder_config
    )
    if not isinstance(selected_decoder, DecoderConfig):
        raise TypeError("tip_decoder_config must be a DecoderConfig or None")
    fields = torch.as_tensor(raw_inputs, dtype=torch.float32, device="cpu")
    if fields.ndim != 4 or tuple(fields.shape[1:]) != (2, 128, 128):
        raise ValueError("raw_inputs must have shape (n, 2, 128, 128)")
    if len(fields) == 0:
        raise ValueError("raw_inputs must contain at least one image")
    sides = _validated_sample_sides(sample_sides, len(fields))
    if selected_mode is P1InferenceMode.TIP_ONLY and inference.path_model is not None:
        raise ValueError("tip_only timing requires a path-free inference instance")
    if selected_mode is P1InferenceMode.TIP_PATH_ANGLE:
        if selected_resolution is not ResolutionMode.TRAINED_256:
            raise ValueError("tip_path_angle retains the historical 256-pixel geometry")
        if inference.path_model is None:
            raise ValueError("tip_path_angle requires a path model")

    state: dict[str, Any] = {}

    def normalization_resize_preprocess() -> None:
        prepared, model_pixels = prepare_crackmnist_inputs(fields, selected_resolution)
        state["prepared"] = prepared
        state["model_pixels"] = model_pixels

    def host_to_device() -> None:
        state["device_inputs"] = state["prepared"].to(inference.device)

    def tip_forward() -> None:
        state["tip_device_outputs"] = inference.forward_tip(state["device_inputs"])

    def tip_device_to_host() -> None:
        probabilities, coordinates = state["tip_device_outputs"]
        state["tip_probabilities"] = probabilities.detach().to("cpu")
        state["tip_coordinates"] = coordinates.detach().to("cpu")

    def selected_tip_decoder() -> None:
        probabilities = state["tip_probabilities"]
        coordinates = state["tip_coordinates"]
        output_pixels = (
            state["model_pixels"]
            if selected_mode is P1InferenceMode.TIP_PATH_ANGLE
            else 128
        )
        state["tip_points"] = [
            decode_tip(
                probabilities[index],
                coordinates[index],
                config=selected_decoder,
                model_pixels=state["model_pixels"],
                original_pixels=output_pixels,
            ).point_rc
            for index in range(len(probabilities))
        ]

    phases: dict[str, Callable[[], None]] = {
        "normalization_resize_preprocess": normalization_resize_preprocess,
        "host_to_device": host_to_device,
        "tip_forward": tip_forward,
        "tip_device_to_host": tip_device_to_host,
        "selected_tip_decoder": selected_tip_decoder,
    }

    if selected_mode is P1InferenceMode.TIP_PATH_ANGLE:

        def path_forward() -> None:
            probabilities = inference.forward_path(state["device_inputs"])
            if probabilities is None:
                raise RuntimeError("configured path model returned no path probabilities")
            state["path_device_probabilities"] = probabilities

        def path_device_to_host() -> None:
            state["path_probabilities"] = state["path_device_probabilities"].detach().to("cpu")

        def threshold_skeleton() -> None:
            probabilities = state["path_probabilities"]
            masks = [
                np.asarray(probabilities[index, 0] >= 0.5, dtype=np.uint8)
                for index in range(len(probabilities))
            ]
            state["path_masks"] = masks
            state["path_skeletons"] = [
                np.asarray(skeletonize(mask, method="lee"), dtype=np.uint8) for mask in masks
            ]

        def angle_postprocessing() -> None:
            detections = {
                side: CrackDetection(
                    side=side,
                    detection_window_size=FIXTURE_WINDOW_MM,
                    angle_det_radius=10.0,
                    device=inference.device,
                )
                for side in set(sides)
            }
            state["angles"] = [
                _angle_from_path_mask(detections[side], mask, tip)
                for side, mask, tip in zip(
                    sides,
                    state["path_masks"],
                    state["tip_points"],
                    strict=True,
                )
            ]

        phases.update(
            {
                "path_forward": path_forward,
                "path_device_to_host": path_device_to_host,
                "threshold_skeleton": threshold_skeleton,
                "angle_postprocessing": angle_postprocessing,
            }
        )

    runtime = benchmark_phases(
        phases,
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(inference.device),
        torch_module=torch_module,
        clock_ns=clock_ns,
    )
    batches_per_second = float(runtime.throughput_per_second)
    images_per_second = float(batches_per_second * len(fields))
    if not math.isfinite(batches_per_second) or not math.isfinite(images_per_second):
        raise RuntimeError("runtime throughput must be finite")

    return {
        "status": "completed",
        "mode": selected_mode.value,
        "resolution_mode": selected_resolution.value,
        "batch_size": int(len(fields)),
        "tip_decoder_config": selected_decoder.to_dict(),
        "sample_sides": sorted(set(sides)),
        "runtime": runtime.to_dict(),
        "throughput": {
            "batch_iterations_per_second": batches_per_second,
            "images_per_second": images_per_second,
        },
        "phase_availability": {
            "interpolation": "not_applicable_pregridded_input",
            "path": "measured" if selected_mode is P1InferenceMode.TIP_PATH_ANGLE else "skipped_tip_only",
        },
        "plotting": {"requested": False, "status": "disabled_not_requested"},
        "result_writing": {"requested": False, "status": "disabled_not_requested"},
    }


def run_p1_runtime_sweep(
    runner: Callable[[P1InferenceMode, int], dict[str, Any]],
    *,
    modes: Sequence[P1InferenceMode | str],
    batch_sizes: Sequence[int],
) -> list[dict[str, Any]]:
    """Run every mode/batch variant and retain CUDA OOM as structured evidence."""

    if not modes or not batch_sizes:
        raise ValueError("modes and batch_sizes must be non-empty")
    results: list[dict[str, Any]] = []
    for mode_value in modes:
        mode = P1InferenceMode(mode_value)
        for batch_size in batch_sizes:
            if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
                raise ValueError("batch sizes must be positive integers")
            try:
                result = dict(runner(mode, batch_size))
            except torch.OutOfMemoryError as error:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                results.append(
                    {
                        "status": "cuda_out_of_memory",
                        "mode": mode.value,
                        "batch_size": batch_size,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
                continue
            result["status"] = "completed"
            result.setdefault("mode", mode.value)
            result.setdefault("batch_size", batch_size)
            results.append(result)
    return results


def benchmark_interpolation_frames(
    frames: Mapping[str, Any],
    *,
    signed_sizes: Sequence[float] = (70.0, -70.0),
    pixels: int = 256,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
    tip_inference: FrozenCtdInference | None = None,
    tip_decoder_config: DecoderConfig | None = None,
) -> dict[str, Any]:
    """Compare three legacy ``griddata`` calls with one frame-local triangulation."""

    if not frames or not signed_sizes:
        raise ValueError("frames and signed_sizes must be non-empty")
    if not isinstance(pixels, int) or isinstance(pixels, bool) or pixels <= 1:
        raise ValueError("pixels must be an integer greater than one")

    variants: list[dict[str, Any]] = []
    for frame_name, frame in frames.items():
        for signed_size in signed_sizes:
            if not np.isfinite(signed_size) or signed_size == 0:
                raise ValueError("signed interpolation sizes must be finite and non-zero")
            legacy_result = legacy_interpolate(frame, size=float(signed_size), pixels=pixels)
            optimized_result = interpolate_frame(frame, size=float(signed_size), pixels=pixels)
            float64_parity = _interpolation_results_equal(legacy_result, optimized_result)
            legacy_input = CrackDetection.preprocess(legacy_result[1])
            optimized_input = CrackDetection.preprocess(optimized_result[1])
            normalized_parity = bool(
                torch.equal(torch.isnan(legacy_input), torch.isnan(optimized_input))
                and torch.allclose(
                    legacy_input,
                    optimized_input,
                    atol=0.0,
                    rtol=0.0,
                    equal_nan=True,
                )
            )
            tip_probability_parity: bool | None = None
            coordinate_head_parity: bool | None = None
            tip_decision_parity: bool | None = None
            if tip_inference is not None:
                legacy_prediction = tip_inference.predict(legacy_input, include_path=False)
                optimized_prediction = tip_inference.predict(optimized_input, include_path=False)
                legacy_probabilities = legacy_prediction.tip_probabilities.detach().to("cpu")
                optimized_probabilities = optimized_prediction.tip_probabilities.detach().to("cpu")
                legacy_coordinates = legacy_prediction.coordinate_outputs.detach().to("cpu")
                optimized_coordinates = optimized_prediction.coordinate_outputs.detach().to("cpu")
                tip_probability_parity = bool(
                    torch.equal(legacy_probabilities, optimized_probabilities)
                )
                coordinate_head_parity = bool(
                    torch.equal(legacy_coordinates, optimized_coordinates)
                )
                selected_decoder = (
                    DecoderConfig.historical()
                    if tip_decoder_config is None
                    else tip_decoder_config
                )
                legacy_tip = decode_tip(
                    legacy_probabilities,
                    legacy_coordinates[0],
                    config=selected_decoder,
                    model_pixels=pixels,
                    original_pixels=pixels,
                ).point_rc
                optimized_tip = decode_tip(
                    optimized_probabilities,
                    optimized_coordinates[0],
                    config=selected_decoder,
                    model_pixels=pixels,
                    original_pixels=pixels,
                ).point_rc
                tip_decision_parity = bool(
                    tip_probability_parity
                    and coordinate_head_parity
                    and legacy_tip == optimized_tip
                )
            runtime = benchmark_phases(
                {
                    "legacy_three_griddata": lambda frame=frame, signed_size=signed_size: legacy_interpolate(
                        frame,
                        size=float(signed_size),
                        pixels=pixels,
                    ),
                    "shared_triangulation": lambda frame=frame, signed_size=signed_size: interpolate_frame(
                        frame,
                        size=float(signed_size),
                        pixels=pixels,
                    ),
                },
                warmup_iterations=warmup_iterations,
                measured_iterations=measured_iterations,
                device="cpu",
                clock_ns=clock_ns,
            )
            runtime_dict = runtime.to_dict()
            legacy_median = runtime_dict["phases"]["legacy_three_griddata"]["median_ms"]
            optimized_median = runtime_dict["phases"]["shared_triangulation"]["median_ms"]
            variants.append(
                {
                    "frame": str(frame_name),
                    "side": "right" if signed_size > 0 else "left",
                    "signed_size": float(signed_size),
                    "pixels": pixels,
                    "float64_parity": float64_parity,
                    "normalized_float32_parity": normalized_parity,
                    "tip_model_checked": tip_inference is not None,
                    "tip_decoder_config": (
                        None
                        if tip_inference is None
                        else selected_decoder.to_dict()
                    ),
                    "tip_probability_parity": tip_probability_parity,
                    "coordinate_head_parity": coordinate_head_parity,
                    "tip_decision_parity": tip_decision_parity,
                    "median_speedup": float(legacy_median / optimized_median),
                    "runtime": runtime_dict,
                }
            )
    return {
        "triangulation_scope": "one_per_frame_and_roi",
        "cross_frame_cache": False,
        "variants": variants,
    }


def _validated_sample_sides(
    values: Sequence[str] | None,
    sample_count: int,
) -> tuple[str, ...]:
    """Return one explicit physical side per batch sample."""

    if values is None:
        return ("right",) * sample_count
    sides = tuple(str(value).strip().lower() for value in values)
    if len(sides) != sample_count:
        raise ValueError("sample_sides must contain one side per input")
    if any(side not in {"left", "right"} for side in sides):
        raise ValueError("sample_sides values must be 'left' or 'right'")
    return sides


def _interpolation_results_equal(
    legacy: tuple[np.ndarray, np.ndarray, np.ndarray | None],
    optimized: tuple[np.ndarray, np.ndarray, np.ndarray | None],
) -> bool:
    """Apply the P1 Float64 parity contract to all available fields."""

    for legacy_field, optimized_field in zip(legacy, optimized, strict=True):
        if legacy_field is None or optimized_field is None:
            if legacy_field is not optimized_field:
                return False
            continue
        if not np.allclose(
            legacy_field,
            optimized_field,
            atol=1e-12,
            rtol=1e-12,
            equal_nan=True,
        ):
            return False
    return True


def _angle_from_path_mask(
    detection: CrackDetection,
    path_mask: np.ndarray,
    tip: tuple[float, float] | None,
) -> float | None:
    """Apply the unchanged CrackPy local-angle calculation to one 256 mask."""

    if tip is None or not np.any(path_mask):
        return None
    estimator = CrackAngleEstimation(detection, torch.tensor(tip, dtype=torch.float32))
    masked = estimator.apply_circular_mask(torch.as_tensor(path_mask))
    largest = estimator.get_largest_region(masked)
    angle = estimator.predict_angle(largest)
    if angle is None or not np.isfinite(angle):
        return None
    return float(angle)

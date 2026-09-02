"""Phase-resolved runtime sweeps for persistent frozen P1 inference."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import Enum
import math
import time
from typing import Any

import numpy as np
import torch
from skimage.morphology import skeletonize

from crackpy.benchmarking.ctd_baseline import (
    FIXTURE_WINDOW_MM,
    ResolutionMode,
    decode_historical_tip,
    prepare_crackmnist_inputs,
)
from crackpy.benchmarking.ctd_runtime import benchmark_phases
from crackpy.crack_detection.detection import CrackAngleEstimation, CrackDetection
from crackpy.crack_detection.inference import FrozenCtdInference


class P1InferenceMode(str, Enum):
    """P1 inference products whose costs must be reported independently."""

    TIP_ONLY = "tip_only"
    TIP_PATH_ANGLE = "tip_path_angle"


def measure_p1_model_phases(
    inference: FrozenCtdInference,
    *,
    raw_inputs: torch.Tensor | np.ndarray,
    mode: P1InferenceMode | str,
    resolution_mode: ResolutionMode | str,
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
    fields = torch.as_tensor(raw_inputs, dtype=torch.float32, device="cpu")
    if fields.ndim != 4 or tuple(fields.shape[1:]) != (2, 128, 128):
        raise ValueError("raw_inputs must have shape (n, 2, 128, 128)")
    if len(fields) == 0:
        raise ValueError("raw_inputs must contain at least one image")
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

    def historical_tip_decoder() -> None:
        probabilities = state["tip_probabilities"]
        state["tip_points"] = [
            decode_historical_tip(probabilities[index:index + 1])
            for index in range(len(probabilities))
        ]

    phases: dict[str, Callable[[], None]] = {
        "normalization_resize_preprocess": normalization_resize_preprocess,
        "host_to_device": host_to_device,
        "tip_forward": tip_forward,
        "tip_device_to_host": tip_device_to_host,
        "historical_tip_decoder": historical_tip_decoder,
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
            detection = CrackDetection(
                side="right",
                detection_window_size=FIXTURE_WINDOW_MM,
                angle_det_radius=10.0,
                device=inference.device,
            )
            state["angles"] = [
                _angle_from_path_mask(detection, mask, tip)
                for mask, tip in zip(state["path_masks"], state["tip_points"], strict=True)
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

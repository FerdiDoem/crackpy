"""Phase-resolved B0/B1 fixture timings for the frozen CTD P0 baseline.

This additive adapter deliberately measures the existing models and historical
decoder without changing their inference implementation.  It reports model
loading as one clearly labelled first-in-process value and keeps every steady
state B0/B1 boundary as a distinct CUDA-synchronised phase.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time
from typing import Any

import numpy as np
import torch
from skimage.morphology import skeletonize
from torch import Tensor, nn

from crackpy.benchmarking.ctd_baseline import FIXTURE_WINDOW_MM, decode_historical_tip
from crackpy.benchmarking.ctd_runtime import benchmark_phases
from crackpy.crack_detection.data.preprocess import normalize
from crackpy.crack_detection.detection import CrackAngleEstimation, CrackDetection


def measure_first_in_process_model_loading(
    model_loader: Callable[[], tuple[nn.Module, nn.Module]],
    *,
    device: str | torch.device,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
    torch_module: Any | None = None,
) -> tuple[dict[str, object], nn.Module, nn.Module]:
    """Load both original models once and expose its cold-start timing.

    The caller must invoke this before constructing either model in the current
    process.  The function itself invokes ``model_loader`` exactly once, never
    warms it up, and freezes both returned models before handing them to the
    steady-state B0/B1 phase measurement.
    """

    loaded_models: tuple[nn.Module, nn.Module] | None = None

    def load_once() -> None:
        nonlocal loaded_models
        if loaded_models is not None:
            raise RuntimeError("first-in-process model loader was invoked more than once")
        candidate = model_loader()
        if not isinstance(candidate, tuple) or len(candidate) != 2:
            raise TypeError("model_loader must return a (tip_model, path_model) tuple")
        tip_model, path_model = candidate
        if not isinstance(tip_model, nn.Module) or not isinstance(path_model, nn.Module):
            raise TypeError("model_loader must return torch.nn.Module instances")
        loaded_models = _freeze_models(tip_model, path_model, device)

    runtime = benchmark_phases(
        {"first_in_process_model_loading": load_once},
        warmup_iterations=0,
        measured_iterations=1,
        device=str(device),
        torch_module=torch_module,
        clock_ns=clock_ns,
    )
    if loaded_models is None:
        raise RuntimeError("model loader completed without returning models")
    return (
        {
            "phase_name": "first_in_process_model_loading",
            "measurement_scope": "first_in_process_loader_invocation",
            "first_in_process": True,
            "runtime": runtime.to_dict(),
            "models_frozen_after_loading": True,
        },
        *loaded_models,
    )


def measure_b0_b1_fixture_phases(
    tip_model: nn.Module,
    path_model: nn.Module,
    *,
    fixture_inputs: Tensor,
    device: str | torch.device,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
    torch_module: Any | None = None,
) -> dict[str, object]:
    """Measure the frozen B0/B1 fixture batch at each observable boundary.

    ``fixture_inputs`` is the unnormalised repository fixture batch.  The
    preprocessing phase therefore records native-256 normalisation, while its
    name preserves the shared normalisation/resize-preprocess category used by
    the P0 report.  Every returned duration is timed by ``benchmark_phases``,
    which synchronizes CUDA before and after each phase.
    """

    _validate_fixture_inputs(fixture_inputs)
    tip_network, path_network = _freeze_models(tip_model, path_model, device)
    state: dict[str, Any] = {}
    batch_size = int(len(fixture_inputs))

    def normalization_resize_preprocess() -> None:
        state["normalized_inputs"] = normalize(fixture_inputs.detach().to("cpu")).to(dtype=torch.float32)

    def host_to_device() -> None:
        state["device_inputs"] = state["normalized_inputs"].to(device)

    def tip_forward() -> None:
        with torch.inference_mode():
            state["tip_device_outputs"] = tip_network(state["device_inputs"])

    def tip_device_to_host() -> None:
        probabilities, coordinates = state["tip_device_outputs"]
        state["tip_host_probabilities"] = probabilities.detach().to("cpu")
        state["tip_host_coordinates"] = coordinates.detach().to("cpu")

    def historical_tip_decoder() -> None:
        probabilities = state["tip_host_probabilities"]
        state["tip_points"] = [
            decode_historical_tip(probabilities[index:index + 1]) for index in range(len(probabilities))
        ]

    def path_forward() -> None:
        with torch.inference_mode():
            state["path_device_probabilities"] = path_network(state["device_inputs"])

    def path_device_to_host() -> None:
        state["path_host_probabilities"] = state["path_device_probabilities"].detach().to("cpu")

    def threshold_skeleton() -> None:
        probabilities = state["path_host_probabilities"]
        state["path_masks"] = [
            np.asarray(probabilities[index, 0] >= 0.5, dtype=np.uint8) for index in range(len(probabilities))
        ]
        state["path_skeletons"] = [
            np.asarray(skeletonize(mask, method="lee"), dtype=np.uint8) for mask in state["path_masks"]
        ]

    def angle_postprocessing() -> None:
        detection = CrackDetection(
            side="right",
            detection_window_size=FIXTURE_WINDOW_MM,
            angle_det_radius=10.0,
            device=device,
        )
        state["path_angles"] = [
            _angle_from_path_mask(detection, mask, tip)
            for mask, tip in zip(state["path_masks"], state["tip_points"], strict=True)
        ]

    runtime = benchmark_phases(
        {
            "normalization_resize_preprocess": normalization_resize_preprocess,
            "host_to_device": host_to_device,
            "tip_forward": tip_forward,
            "tip_device_to_host": tip_device_to_host,
            "historical_tip_decoder": historical_tip_decoder,
            "path_forward": path_forward,
            "path_device_to_host": path_device_to_host,
            "threshold_skeleton": threshold_skeleton,
            "angle_postprocessing": angle_postprocessing,
        },
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
        torch_module=torch_module,
        clock_ns=clock_ns,
    )
    runtime_dict = runtime.to_dict()
    batch_iterations_per_second = float(runtime.throughput_per_second)
    images_per_second = float(batch_iterations_per_second * batch_size)
    if not math.isfinite(batch_iterations_per_second) or not math.isfinite(images_per_second):
        raise RuntimeError("runtime throughput must be finite")
    return {
        "measurement_scope": "prepared_repository_fixture_batch_steady_state",
        "batch_size": batch_size,
        "models": {
            "tip_model": "frozen_eval_mode",
            "path_model": "frozen_eval_mode",
            "frozen": True,
            "training_performed": False,
        },
        "preprocessing": {
            "resize": "not_applied_repository_fixture_already_256",
            "normalization": "CrackPy_normalize",
        },
        "runtime": runtime_dict,
        "throughput": {
            "batch_iterations_per_second": batch_iterations_per_second,
            "images_per_second": images_per_second,
            "batch_size": batch_size,
        },
        "plotting": {
            "status": "disabled_not_requested",
            "requested": False,
        },
        "result_writing": {
            "status": "disabled_not_requested",
            "requested": False,
        },
    }


def _freeze_models(
    tip_model: nn.Module,
    path_model: nn.Module,
    device: str | torch.device,
) -> tuple[nn.Module, nn.Module]:
    """Prevent training-state changes while the original inference models run."""

    for model in (tip_model, path_model):
        model.requires_grad_(False)
        model.to(device)
        model.eval()
    return tip_model, path_model


def _validate_fixture_inputs(fixture_inputs: Tensor) -> None:
    """Reject inputs that cannot represent the fixed B0/B1 repository batch."""

    if fixture_inputs.ndim != 4 or tuple(fixture_inputs.shape[1:]) != (2, 256, 256):
        raise ValueError("fixture_inputs must have shape (n, 2, 256, 256)")
    if len(fixture_inputs) == 0:
        raise ValueError("fixture_inputs must contain at least one sample")


def _angle_from_path_mask(
    detection: CrackDetection,
    path_mask: np.ndarray,
    tip: tuple[float, float] | None,
) -> float | None:
    """Apply CrackPy's existing local path-angle postprocessing to one mask."""

    if tip is None or not np.any(path_mask):
        return None
    estimator = CrackAngleEstimation(detection, torch.tensor(tip, dtype=torch.float32))
    masked = estimator.apply_circular_mask(torch.as_tensor(path_mask))
    largest_region = estimator.get_largest_region(masked)
    angle = estimator.predict_angle(largest_region)
    if angle is None or not np.isfinite(angle):
        return None
    return float(angle)

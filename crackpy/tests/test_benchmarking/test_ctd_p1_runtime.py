"""Contract tests for P1 mode, batch, throughput, and OOM reporting."""

from __future__ import annotations

from collections.abc import Callable

import pytest
import torch
from torch import nn

from crackpy.benchmarking.ctd_baseline import ResolutionMode
from crackpy.benchmarking.ctd_p1_runtime import (
    P1InferenceMode,
    measure_p1_model_phases,
    run_p1_runtime_sweep,
)
from crackpy.crack_detection.inference import FrozenCtdInference


class _TipModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self.calls += 1
        batch, _, height, width = inputs.shape
        masks = torch.zeros((batch, 1, height, width), device=inputs.device)
        masks[:, 0, height // 2, width // 2] = 1.0
        coordinates = torch.zeros((batch, 2), device=inputs.device)
        return masks, coordinates


class _PathModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        self.calls += 1
        batch, _, height, width = inputs.shape
        masks = torch.zeros((batch, 1, height, width), device=inputs.device)
        masks[:, 0, height // 2, : width // 2 + 1] = 1.0
        return masks


def _increasing_clock() -> Callable[[], int]:
    current = -1_000_000

    def clock() -> int:
        nonlocal current
        current += 1_000_000
        return current

    return clock


def test_tip_only_skips_path_and_reports_both_throughput_units() -> None:
    tip = _TipModel()
    path = _PathModel()
    inference = FrozenCtdInference(tip, path, device="cpu")
    inputs = torch.arange(4 * 2 * 128 * 128, dtype=torch.float32).reshape(4, 2, 128, 128)

    result = measure_p1_model_phases(
        inference,
        raw_inputs=inputs,
        mode=P1InferenceMode.TIP_ONLY,
        resolution_mode=ResolutionMode.TRAINED_256,
        warmup_iterations=0,
        measured_iterations=1,
        clock_ns=_increasing_clock(),
    )

    assert list(result["runtime"]["phases"]) == [
        "normalization_resize_preprocess",
        "host_to_device",
        "tip_forward",
        "tip_device_to_host",
        "historical_tip_decoder",
    ]
    assert path.calls == 0
    assert result["mode"] == "tip_only"
    assert result["batch_size"] == 4
    assert result["throughput"]["batch_iterations_per_second"] == pytest.approx(200.0)
    assert result["throughput"]["images_per_second"] == pytest.approx(800.0)
    assert result["phase_availability"]["interpolation"] == "not_applicable_pregridded_input"
    assert result["plotting"]["status"] == "disabled_not_requested"
    assert result["result_writing"]["status"] == "disabled_not_requested"


def test_tip_path_angle_keeps_path_phases_and_requires_256_geometry() -> None:
    tip = _TipModel()
    path = _PathModel()
    inference = FrozenCtdInference(tip, path, device="cpu")
    inputs = torch.arange(2 * 2 * 128 * 128, dtype=torch.float32).reshape(2, 2, 128, 128)

    result = measure_p1_model_phases(
        inference,
        raw_inputs=inputs,
        mode=P1InferenceMode.TIP_PATH_ANGLE,
        resolution_mode=ResolutionMode.TRAINED_256,
        warmup_iterations=0,
        measured_iterations=1,
        clock_ns=_increasing_clock(),
    )

    assert list(result["runtime"]["phases"])[-4:] == [
        "path_forward",
        "path_device_to_host",
        "threshold_skeleton",
        "angle_postprocessing",
    ]
    assert path.calls == 1
    assert result["throughput"]["images_per_second"] == pytest.approx(2000.0 / 9.0)

    with pytest.raises(ValueError, match="256"):
        measure_p1_model_phases(
            inference,
            raw_inputs=inputs,
            mode=P1InferenceMode.TIP_PATH_ANGLE,
            resolution_mode=ResolutionMode.NATIVE_128,
            warmup_iterations=0,
            measured_iterations=1,
        )


def test_runtime_sweep_preserves_requested_order_and_structures_cuda_oom() -> None:
    calls: list[tuple[str, int]] = []

    def runner(mode: P1InferenceMode, batch_size: int) -> dict[str, object]:
        calls.append((mode.value, batch_size))
        if batch_size == 16:
            raise torch.OutOfMemoryError("synthetic OOM")
        return {"mode": mode.value, "batch_size": batch_size}

    results = run_p1_runtime_sweep(
        runner,
        modes=(P1InferenceMode.TIP_ONLY, P1InferenceMode.TIP_PATH_ANGLE),
        batch_sizes=(1, 8, 16, 32),
    )

    assert calls == [
        ("tip_only", 1),
        ("tip_only", 8),
        ("tip_only", 16),
        ("tip_only", 32),
        ("tip_path_angle", 1),
        ("tip_path_angle", 8),
        ("tip_path_angle", 16),
        ("tip_path_angle", 32),
    ]
    assert [entry["status"] for entry in results if entry["batch_size"] == 16] == [
        "cuda_out_of_memory",
        "cuda_out_of_memory",
    ]
    assert all(entry["status"] == "completed" for entry in results if entry["batch_size"] != 16)

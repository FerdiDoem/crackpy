"""Contract tests for the P0 B0/B1 fixture-phase runtime adapter."""

from __future__ import annotations

from collections.abc import Callable
import json

import torch
from torch import nn

from crackpy.benchmarking.ctd_p0_runtime import (
    measure_b0_b1_fixture_phases,
    measure_first_in_process_model_loading,
)


class _TipModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch, _, height, width = inputs.shape
        probabilities = torch.zeros((batch, 1, height, width), device=inputs.device)
        probabilities[:, 0, height // 2, width // 2] = 1.0
        return probabilities, torch.zeros((batch, 2), device=inputs.device)


class _PathModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        batch, _, height, width = inputs.shape
        probabilities = torch.zeros((batch, 1, height, width), device=inputs.device)
        probabilities[:, 0, height // 2, : width // 2] = 1.0
        return probabilities


def _increasing_clock() -> Callable[[], int]:
    current = -1_000_000

    def clock() -> int:
        nonlocal current
        current += 1_000_000
        return current

    return clock


def test_first_in_process_loading_is_measured_once_and_named_explicitly() -> None:
    calls = 0

    def load_original_models() -> tuple[nn.Module, nn.Module]:
        nonlocal calls
        calls += 1
        return _TipModel(), _PathModel()

    result, tip_model, path_model = measure_first_in_process_model_loading(
        load_original_models,
        device="cpu",
        clock_ns=_increasing_clock(),
    )

    assert calls == 1
    assert result["phase_name"] == "first_in_process_model_loading"
    assert result["first_in_process"] is True
    assert result["runtime"]["measured_iterations"] == 1
    assert result["runtime"]["warmup_iterations"] == 0
    assert set(result["runtime"]["phases"]) == {"first_in_process_model_loading"}
    assert tip_model.training is False
    assert path_model.training is False
    assert all(not parameter.requires_grad for parameter in tip_model.parameters())
    json.dumps(result, allow_nan=False)


def test_fixture_phase_runtime_keeps_b0_b1_boundaries_and_throughput_units_explicit() -> None:
    inputs = torch.arange(2 * 2 * 256 * 256, dtype=torch.float32).reshape(2, 2, 256, 256)
    tip_model = _TipModel()
    path_model = _PathModel()

    result = measure_b0_b1_fixture_phases(
        tip_model,
        path_model,
        fixture_inputs=inputs,
        device="cpu",
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
        "path_forward",
        "path_device_to_host",
        "threshold_skeleton",
        "angle_postprocessing",
    ]
    assert result["batch_size"] == 2
    assert result["throughput"]["batch_iterations_per_second"] == 1000.0 / 9.0
    assert result["throughput"]["images_per_second"] == 2000.0 / 9.0
    assert result["plotting"]["status"] == "disabled_not_requested"
    assert result["result_writing"]["status"] == "disabled_not_requested"
    assert result["models"]["frozen"] is True
    assert tip_model.training is False
    assert path_model.training is False
    json.dumps(result, allow_nan=False)

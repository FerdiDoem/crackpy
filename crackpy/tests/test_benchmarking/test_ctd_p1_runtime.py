"""Contract tests for P1 mode, batch, throughput, and OOM reporting."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from crackpy.benchmarking.ctd_baseline import ResolutionMode
from crackpy.benchmarking.ctd_decoders import (
    CoordinateConvention,
    DecoderConfig,
    RegionRule,
)
from crackpy.benchmarking.ctd_p1_runtime import (
    P1InferenceMode,
    benchmark_interpolation_frames,
    measure_p1_model_loading,
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


def test_p1_model_loading_is_a_separate_first_in_process_phase() -> None:
    calls = 0

    def loader() -> nn.Module:
        nonlocal calls
        calls += 1
        return _TipModel()

    result, tip_model = measure_p1_model_loading(
        loader,
        phase_name="first_in_process_tip_model_loading_cpu",
        first_in_process=True,
        clock_ns=_increasing_clock(),
    )

    assert calls == 1
    assert result["phase_name"] == "first_in_process_tip_model_loading_cpu"
    assert result["runtime"]["phases"]["first_in_process_tip_model_loading_cpu"]["median_ms"] == 1.0
    assert result["first_in_process"] is True
    assert result["models_prepared_for_device"] is False
    assert isinstance(tip_model, _TipModel)


def test_selected_decoder_is_part_of_the_measured_runtime_contract() -> None:
    inference = FrozenCtdInference(_TipModel(), device="cpu")
    inputs = torch.arange(2 * 128 * 128, dtype=torch.float32).reshape(1, 2, 128, 128)
    selected = DecoderConfig(
        threshold=0.3,
        region_rule=RegionRule.MEAN_PROBABILITY,
        fusion_weight=0.25,
        coordinate_convention=CoordinateConvention.MODEL_INDEX,
    )

    result = measure_p1_model_phases(
        inference,
        raw_inputs=inputs,
        mode=P1InferenceMode.TIP_ONLY,
        resolution_mode=ResolutionMode.TRAINED_256,
        tip_decoder_config=selected,
        warmup_iterations=0,
        measured_iterations=1,
        clock_ns=_increasing_clock(),
    )

    assert result["tip_decoder_config"] == selected.to_dict()
    assert "selected_tip_decoder" in result["runtime"]["phases"]
    assert "historical_tip_decoder" not in result["runtime"]["phases"]


def test_tip_only_skips_path_and_reports_both_throughput_units() -> None:
    tip = _TipModel()
    path = _PathModel()
    inference = FrozenCtdInference(tip, device="cpu")
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
        "selected_tip_decoder",
    ]
    assert path.calls == 0
    assert result["mode"] == "tip_only"
    assert result["batch_size"] == 4
    assert result["throughput"]["batch_iterations_per_second"] == pytest.approx(200.0)
    assert result["throughput"]["images_per_second"] == pytest.approx(800.0)
    assert result["phase_availability"]["interpolation"] == "not_applicable_pregridded_input"
    assert result["plotting"]["status"] == "disabled_not_requested"
    assert result["result_writing"]["status"] == "disabled_not_requested"

    resident_path = FrozenCtdInference(_TipModel(), path, device="cpu")
    with pytest.raises(ValueError, match="path-free"):
        measure_p1_model_phases(
            resident_path,
            raw_inputs=inputs,
            mode=P1InferenceMode.TIP_ONLY,
            resolution_mode=ResolutionMode.TRAINED_256,
            warmup_iterations=0,
            measured_iterations=1,
        )


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


def test_interpolation_benchmark_reports_parity_and_per_frame_speedup() -> None:
    coor_x = torch.tensor([0.0, 2.0, 0.0, 2.0, 1.0], dtype=torch.float64).numpy()
    coor_y = torch.tensor([-1.0, -1.0, 1.0, 1.0, 0.0], dtype=torch.float64).numpy()
    frame = SimpleNamespace(
        coor_x=coor_x,
        coor_y=coor_y,
        disp_x=2.0 * coor_x + coor_y,
        disp_y=-coor_x + 0.5 * coor_y,
        eps_vm=0.2 * coor_x - 0.1 * coor_y,
    )

    result = benchmark_interpolation_frames(
        {"synthetic": frame},
        signed_sizes=(2.0, -2.0),
        pixels=9,
        measured_iterations=1,
        clock_ns=_increasing_clock(),
        tip_inference=FrozenCtdInference(_TipModel(), device="cpu"),
    )

    assert result["triangulation_scope"] == "one_per_frame_and_roi"
    assert len(result["variants"]) == 2
    assert {entry["side"] for entry in result["variants"]} == {"right", "left"}
    assert all(entry["float64_parity"] for entry in result["variants"])
    assert all(entry["normalized_float32_parity"] for entry in result["variants"])
    assert all(entry["tip_decision_parity"] for entry in result["variants"])
    assert all(entry["median_speedup"] == pytest.approx(1.0) for entry in result["variants"])

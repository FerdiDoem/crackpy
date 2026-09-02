"""End-to-end contract tests for the P1 benchmark orchestrator and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import torch
from torch import nn

from crackpy.benchmarking.ctd_p1 import (
    P1RunConfig,
    P1Services,
    assess_resolution_gate,
    load_p0_reference,
    run_p1_benchmark,
)
from crackpy.benchmarking.ctd_p1_evaluation import CrackMnistTipOutputs
from scripts.crack_detection import benchmark_ctd_p1


class _TipModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch, _, height, width = inputs.shape
        masks = torch.zeros((batch, 1, height, width), device=inputs.device)
        coordinates = torch.zeros((batch, 2), device=inputs.device)
        return masks, coordinates


class _PathModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        batch, _, height, width = inputs.shape
        return torch.zeros((batch, 1, height, width), device=inputs.device)


class _Dataset:
    size = "S"
    pixels = 128
    task = "crack_tip_segmentation"

    def __init__(self, split: str) -> None:
        self.split = split

    def __len__(self) -> int:
        return 40

    def __getitem__(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        image = np.full((2, 128, 128), index, dtype=np.float32)
        target = np.zeros((128, 128), dtype=np.uint8)
        target[63, 63] = 1
        return image, target


def _write_p0(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "ctd-p0-v1",
                "crackmnist": {
                    "variants": {
                        "trained_256": {
                            "b0": {
                                "mask_decoder_primary": {
                                    "detection_rate": 0.998,
                                    "error_px": {"p95": 1.9},
                                }
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _outputs(split: str, resolution_mode: Any, limit: int | None) -> CrackMnistTipOutputs:
    model_pixels = {
        "trained-256": 256,
        "native-128": 128,
        "low-64": 64,
    }[str(getattr(resolution_mode, "value", resolution_mode))]
    count = 2 if limit is None else min(2, limit)
    masks = np.zeros((count, model_pixels, model_pixels), dtype=np.float32)
    model_index = round(63 * (model_pixels - 1) / 127)
    masks[:, model_index, model_index] = 0.99
    coordinates = np.full((count, 2), 2 * model_index / (model_pixels - 1) - 1, dtype=np.float32)
    return CrackMnistTipOutputs(
        split="validation" if split in {"val", "validation"} else "test",
        resolution_mode=str(getattr(resolution_mode, "value", resolution_mode)),
        model_pixels=model_pixels,
        original_pixels=128,
        probability_masks=masks,
        coordinate_heads=coordinates,
        references=tuple((63.0, 63.0) for _ in range(count)),
        collection_seconds=0.01,
    )


def test_p0_reference_defines_absolute_detection_and_p95_gates(tmp_path: Path) -> None:
    p0_path = tmp_path / "p0.json"
    _write_p0(p0_path)

    reference = load_p0_reference(p0_path)
    accepted = assess_resolution_gate(
        detection_rate=0.993,
        p95_error_px=2.9,
        reference=reference,
    )
    rejected = assess_resolution_gate(
        detection_rate=0.9929,
        p95_error_px=2.9001,
        reference=reference,
    )

    assert reference.detection_rate == pytest.approx(0.998)
    assert reference.minimum_detection_rate == pytest.approx(0.993)
    assert reference.maximum_p95_error_px == pytest.approx(2.9)
    assert accepted["accepted_for_default"] is True
    assert rejected["accepted_for_default"] is False
    assert rejected["checks"] == {
        "detection_rate_within_0_5_percentage_points": False,
        "p95_within_1_original_pixel": False,
    }


def test_orchestrator_loads_models_once_and_freezes_each_resolution_before_test(
    tmp_path: Path,
) -> None:
    p0_path = tmp_path / "p0.json"
    _write_p0(p0_path)
    model_loads: list[str] = []
    collection_calls: list[tuple[str, str, str]] = []
    runtime_calls: list[tuple[str, str, int]] = []
    lifecycle_events: list[str] = []

    def load_model(name: str, *, map_location: torch.device) -> nn.Module:
        assert map_location == torch.device("cpu")
        model_loads.append(name)
        lifecycle_events.append(f"load:{name}")
        return _TipModel() if name == "ParallelNets" else _PathModel()

    def measure_model_loading(loader: Any) -> tuple[dict[str, Any], nn.Module, nn.Module]:
        tip_model, path_model = loader()
        return (
            {
                "phase_name": "first_in_process_model_loading_cpu",
                "first_in_process": True,
                "models_prepared_for_device": False,
                "runtime": {"total_measured_ms": 1.0},
            },
            tip_model,
            path_model,
        )

    class _Inference:
        def __init__(self, tip_model: nn.Module, path_model: None, *, device: str) -> None:
            del tip_model
            assert path_model is None
            self.device = torch.device(device)
            self.path_model = None
            lifecycle_events.append("attach:tip_only")

        def attach_path_model(self, path_model: nn.Module) -> None:
            assert self.path_model is None
            self.path_model = path_model
            lifecycle_events.append("attach:UNetPath")

    def collect_outputs(
        inference: Any,
        dataset: _Dataset,
        *,
        resolution_mode: Any,
        batch_size: int,
        mask_storage_path: Path,
        limit: int | None,
    ) -> CrackMnistTipOutputs:
        del inference, batch_size
        mode = str(getattr(resolution_mode, "value", resolution_mode))
        collection_calls.append((dataset.split, mode, mask_storage_path.name))
        lifecycle_events.append(f"collect:{dataset.split}:{mode}")
        return _outputs(dataset.split, resolution_mode, limit)

    def measure_runtime(
        inference: Any,
        *,
        raw_inputs: torch.Tensor,
        mode: Any,
        resolution_mode: Any,
        warmup_iterations: int,
        measured_iterations: int,
    ) -> dict[str, Any]:
        del inference, warmup_iterations, measured_iterations
        mode_value = str(getattr(mode, "value", mode))
        resolution_value = str(getattr(resolution_mode, "value", resolution_mode))
        runtime_calls.append((mode_value, resolution_value, len(raw_inputs)))
        lifecycle_events.append(f"runtime:{mode_value}:{resolution_value}:{len(raw_inputs)}")
        return {
            "status": "completed",
            "mode": mode_value,
            "resolution_mode": resolution_value,
            "batch_size": len(raw_inputs),
        }

    def benchmark_interpolation(frames: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["tip_inference"].path_model is None
        lifecycle_events.append("interpolation:tip_only")
        return {
            "frames": sorted(frames),
            "signed_sizes": list(kwargs["signed_sizes"]),
            "variants": [
                {
                    "float64_parity": True,
                    "normalized_float32_parity": True,
                    "tip_probability_parity": True,
                    "coordinate_head_parity": True,
                    "historical_tip_decision_parity": True,
                }
            ] * 8,
        }

    services = P1Services.defaults().replace(
        load_model=load_model,
        measure_model_loading=measure_model_loading,
        inference_factory=_Inference,
        load_dataset=lambda split, dataset_root: _Dataset(split),
        collect_outputs=collect_outputs,
        measure_model_phases=measure_runtime,
        load_dummy2_frames=lambda repository_root: {
            stage: object() for stage in ("52", "53", "54", "55")
        },
        benchmark_interpolation=benchmark_interpolation,
        collect_metadata=lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {
                "seed": kwargs["seed"],
                "device": kwargs["device"],
                "artifact_sha256": {"ParallelNets": "tip", "UNetPath": "path"},
            }
        ),
    )
    result = run_p1_benchmark(
        P1RunConfig(
            repository_root=tmp_path,
            dataset_root=tmp_path / "data",
            p0_results_path=p0_path,
            device="cpu",
            limit=2,
            calibration_batch_size=2,
            runtime_warmup_iterations=0,
            runtime_measured_iterations=1,
            interpolation_warmup_iterations=0,
            interpolation_measured_iterations=1,
        ),
        services=services,
    )

    assert model_loads == ["ParallelNets", "UNetPath"]
    path_load_index = lifecycle_events.index("load:UNetPath")
    assert path_load_index < lifecycle_events.index("attach:tip_only")
    assert all(
        lifecycle_events.index(f"collect:{split}:{resolution}")
        > lifecycle_events.index("attach:tip_only")
        for split in ("val", "test")
        for resolution in ("trained-256", "native-128", "low-64")
    )
    path_attach_index = lifecycle_events.index("attach:UNetPath")
    assert all(
        lifecycle_events.index(f"runtime:tip_only:{resolution}:{batch}") < path_attach_index
        for resolution in ("trained-256", "native-128", "low-64")
        for batch in (1, 8, 16, 32)
    )
    assert path_attach_index > path_load_index
    assert lifecycle_events.index("interpolation:tip_only") < path_attach_index
    assert all(
        lifecycle_events.index(f"runtime:tip_path_angle:trained-256:{batch}")
        > path_attach_index
        for batch in (1, 8, 16, 32)
    )
    assert [(split, mode) for split, mode, _ in collection_calls] == [
        ("val", "trained-256"),
        ("test", "trained-256"),
        ("val", "native-128"),
        ("test", "native-128"),
        ("val", "low-64"),
        ("test", "low-64"),
    ]
    assert set(result["resolutions"]) == {"trained_256", "native_128", "low_64"}
    for resolution in result["resolutions"].values():
        assert resolution["calibration"]["source_split"] == "validation"
        assert resolution["calibration"]["test_split_used_for_selection"] is False
        assert resolution["calibration"]["minimum_detection_rate"] == pytest.approx(0.995)
        assert resolution["validation_selection_policy"] == {
            "reference_decoder": "historical_mask_decoder_on_validation",
            "reference_detection_rate": 1.0,
            "allowed_absolute_detection_rate_degradation": 0.005,
            "minimum_detection_rate": 0.995,
            "p0_test_metrics_used_for_selection": False,
        }
        assert resolution["frozen_test_metrics"]["split"] == "test"
        assert (
            resolution["frozen_test_metrics"]["config"]
            == resolution["calibration"]["selected_config"]
        )
    expected_runtime_calls = {
        ("tip_only", resolution, batch)
        for resolution in ("trained-256", "native-128", "low-64")
        for batch in (1, 8, 16, 32)
    } | {
        ("tip_path_angle", "trained-256", batch)
        for batch in (1, 8, 16, 32)
    }
    assert set(runtime_calls) == expected_runtime_calls
    assert result["runtime"]["interpolation"]["frames"] == ["52", "53", "54", "55"]
    assert result["runtime"]["interpolation"]["signed_sizes"] == [70.0, -70.0]
    assert result["scope"]["training_performed"] is False
    assert result["scope"]["model_architecture_changed"] is False
    assert result["model_lifecycle"]["path_model_absent_during_tip_only"] is True
    assert result["model_lifecycle"]["execution_order"] == [
        "first_in_process_cpu_model_loading",
        "attach_tip_model_only",
        "validation_calibration_and_frozen_test",
        "tip_only_runtime_sweeps",
        "dummy2_interpolation_and_tip_parity",
        "attach_preloaded_cpu_path_model",
        "trained_256_path_angle_runtime_sweep",
    ]
    assert result["model_lifecycle"]["cpu_loading"]["models_prepared_for_device"] is False
    payload = json.dumps(result, allow_nan=False)
    assert "validation-trained-256.npy" not in payload
    assert "test-trained-256.npy" not in payload


def test_parser_defaults_to_full_data_and_limit_is_an_explicit_smoke_control() -> None:
    parser = benchmark_ctd_p1.build_parser()

    full = parser.parse_args([])
    smoke = parser.parse_args(["--limit", "7"])

    assert full.limit is None
    assert smoke.limit == 7
    with pytest.raises(SystemExit):
        parser.parse_args(["--limit", "0"])


def test_main_writes_strict_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "p1.json"
    monkeypatch.setattr(
        benchmark_ctd_p1,
        "run_p1_benchmark",
        lambda config: {
            "schema_version": "ctd-p1-v1",
            "limit": config.limit,
            "finite": 1.0,
        },
    )

    exit_code = benchmark_ctd_p1.main(
        ["--device", "cpu", "--limit", "3", "--output", str(output)]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["limit"] == 3
    assert "NaN" not in output.read_text(encoding="utf-8")

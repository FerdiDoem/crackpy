"""Contract tests for the frozen CTD P0 B0/B1 evaluation harness."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from torch import nn
from torch.nn import functional as torch_functional

from crackpy.benchmarking import ctd_baseline
from crackpy.benchmarking.ctd_baseline import (
    ResolutionMode,
    build_b2_result,
    classify_b2_correction_status,
    decode_historical_tip,
    denormalize_coordinate_head,
    evaluate_b2_example,
    evaluate_crackmnist,
    evaluate_repository_fixtures,
    map_legacy_decoder_point_to_original,
    map_model_index_point_to_original,
    measure_inference_contracts,
    prepare_crackmnist_inputs,
)
from crackpy.benchmarking.ctd_runtime import benchmark_phases
from crackpy.crack_detection.data.preprocess import normalize
from crackpy.crack_detection.utils.utilityfunctions import find_most_likely_tip_pos


def test_historical_mask_decoder_is_the_unchanged_primary_decoder() -> None:
    probabilities = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    probabilities[0, 0, 0, :2] = 0.6
    probabilities[0, 0, 2, 2] = 0.9

    expected = find_most_likely_tip_pos(probabilities)

    assert decode_historical_tip(probabilities) == pytest.approx(tuple(expected))
    assert decode_historical_tip(torch.zeros_like(probabilities)) is None


def test_model_points_are_mapped_by_their_explicit_coordinate_convention() -> None:
    normalized = torch.tensor([-0.5, 0.5])

    assert denormalize_coordinate_head(normalized, model_pixels=256) == pytest.approx((64.0, 192.0))
    assert map_legacy_decoder_point_to_original(
        (0.0, 256.0), model_pixels=256, original_pixels=128
    ) == pytest.approx((0.0, 127.0))
    assert map_legacy_decoder_point_to_original(
        (128.0, 64.0), model_pixels=256, original_pixels=128
    ) == pytest.approx((63.5, 31.75))
    assert map_legacy_decoder_point_to_original(
        (128.0, 128.0), model_pixels=128, original_pixels=128
    ) == pytest.approx((127.0, 127.0))
    assert map_model_index_point_to_original(
        (0.0, 255.0), model_pixels=256, original_pixels=128
    ) == pytest.approx((0.0, 127.0))
    assert map_model_index_point_to_original(
        (127.5, 63.75), model_pixels=256, original_pixels=128
    ) == pytest.approx((63.5, 31.75))
    assert map_model_index_point_to_original(
        (64.0, 96.0), model_pixels=128, original_pixels=128
    ) == pytest.approx((64.0, 96.0))
    assert map_legacy_decoder_point_to_original(
        None, model_pixels=256, original_pixels=128
    ) is None


def test_trained_resolution_resizes_raw_fields_before_exact_crackpy_normalization() -> None:
    raw = torch.arange(2 * 128 * 128, dtype=torch.float32).reshape(1, 2, 128, 128)
    expected_resized = torch_functional.interpolate(
        raw,
        size=(256, 256),
        mode="bilinear",
        align_corners=True,
    )
    expected = normalize(expected_resized).to(dtype=torch.float32)

    actual, model_pixels = prepare_crackmnist_inputs(raw, ResolutionMode.TRAINED_256)

    assert model_pixels == 256
    assert tuple(actual.shape) == (1, 2, 256, 256)
    torch.testing.assert_close(actual, expected)


def test_native_resolution_is_explicitly_marked_as_sensitivity() -> None:
    raw = torch.arange(2 * 128 * 128, dtype=torch.float32).reshape(1, 2, 128, 128)

    actual, model_pixels = prepare_crackmnist_inputs(raw, ResolutionMode.NATIVE_128)

    assert model_pixels == 128
    assert tuple(actual.shape) == (1, 2, 128, 128)
    torch.testing.assert_close(actual, normalize(raw).to(dtype=torch.float32))


class _FakeCrackMNIST:
    split = "test"
    size = "S"
    pixels = 128
    task = "crack_tip_segmentation"
    download_path = "unused"
    exp_ids = np.asarray([3, 3, 3])
    exp_names = np.asarray(["unused_0", "unused_1", "unused_2", "MT160_2024_TL_1_right"])
    augmentations = np.zeros((3, 4), dtype=float)

    def __init__(self) -> None:
        base = np.indices((128, 128), dtype=np.float32).sum(axis=0)
        self.images = np.stack([np.stack((base + i, base.T - i)) for i in range(3)])
        self.targets = np.zeros((3, 128, 128), dtype=np.uint8)
        self.targets[0, 64, 64] = 1
        self.targets[1, 32, 32] = 1

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        return self.images[index], self.targets[index]


class _FakeParallelNets(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.freeze_probe = nn.Parameter(torch.tensor(1.0))

    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch, _, height, width = inputs.shape
        masks = torch.zeros((batch, 1, height, width), device=inputs.device)
        masks[0, 0, height // 2, width // 2] = 1.0
        if batch > 2:
            masks[2, 0, height // 4, width // 4] = 1.0
        coordinates = torch.zeros((batch, 2), device=inputs.device)
        return masks, coordinates


def test_crackmnist_keeps_failures_missing_references_and_per_sample_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = tmp_path / "experiments_metadata.json"
    metadata.write_text('{"schema": "test"}\n', encoding="utf-8")
    dataset = _FakeCrackMNIST()
    dataset.download_path = str(tmp_path)
    model = _FakeParallelNets()
    monkeypatch.setattr(ctd_baseline, "_installed_distribution_version", lambda name: "2.0.1")

    result = evaluate_crackmnist(
        model,
        dataset,
        device="cpu",
        batch_size=3,
        resolution_mode=ResolutionMode.TRAINED_256,
    )

    primary = result["b0"]["mask_decoder_primary"]
    diagnostic = result["b0"]["coordinate_head_diagnostic"]
    assert primary["references"] == 2
    assert primary["successful_detections"] == 1
    assert primary["detection_failures"] == 1
    assert primary["missing_references"] == 1
    assert diagnostic["references"] == 2
    assert result["dataset"]["split"] == "test"
    assert result["dataset"]["size"] == "S"
    assert result["dataset"]["pixels"] == 128
    assert result["dataset"]["sample_count"] == 3
    assert result["dataset"]["experiment_ids"] == [3]
    assert result["dataset"]["experiment_names"] == ["MT160_2024_TL_1_right"]
    assert result["dataset"]["experiment_sides"] == ["right"]
    assert result["dataset"]["source_sample_id_available"] is False
    assert result["dataset"]["h5_md5"] is None
    assert result["dataset"]["crackmnist_version"] == "2.0.1"
    assert result["dataset"]["metadata_sha256"] == sha256(metadata.read_bytes()).hexdigest()
    assert result["resolution"]["sensitivity_analysis"] is False
    assert result["resolution"]["mask_decoder_mapping"] == "legacy_endpoint_to_index"
    assert result["resolution"]["coordinate_head_mapping"] == "model_index_to_original_index"
    assert len(result["samples"]) == 3
    assert result["samples"][1]["mask_decoder_tip_rc"] is None
    assert result["samples"][1]["mask_decoder_error_px"] is None
    assert result["samples"][2]["reference_available"] is False
    assert result["samples"][2]["dice"] is None
    assert result["samples"][0]["coordinate_head_diagnostic_rc"] == pytest.approx(
        [128.0 * 127.0 / 255.0, 128.0 * 127.0 / 255.0]
    )
    json.dumps(result, allow_nan=False)
    assert all(not parameter.requires_grad for parameter in model.parameters())


def test_crackmnist_rejects_non_official_benchmark_configuration() -> None:
    dataset = _FakeCrackMNIST()
    dataset.split = "train"

    with pytest.raises(ValueError, match="official test split"):
        evaluate_crackmnist(_FakeParallelNets(), dataset, device="cpu")


class _ConstantPathModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        masks = torch.zeros((len(inputs), 1, 256, 256), device=inputs.device)
        masks[:, 0, 128, 30:129] = 1.0
        return masks


class _EmptyPathModel(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return torch.zeros((len(inputs), 1, 256, 256), device=inputs.device)


class _AllTipsParallelNets(nn.Module):
    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        masks = torch.zeros((len(inputs), 1, 256, 256), device=inputs.device)
        masks[:, 0, 128, 128] = 1.0
        coordinates = torch.zeros((len(inputs), 2), device=inputs.device)
        return masks, coordinates


def test_repository_fixture_result_exposes_b0_b1_and_gt_derived_angle() -> None:
    inputs = torch.stack(
        (
            torch.stack(torch.meshgrid(torch.arange(256), torch.arange(256), indexing="ij")),
            torch.stack(torch.meshgrid(torch.arange(256), torch.arange(256), indexing="ij")),
        )
    ).to(dtype=torch.float32)
    targets = torch.zeros((2, 256, 256), dtype=torch.int64)
    targets[:, 128, 30:128] = 1
    targets[:, 128, 128] = 2

    result = evaluate_repository_fixtures(
        _AllTipsParallelNets(),
        _ConstantPathModel(),
        inputs=inputs,
        targets=targets,
        device="cpu",
        batch_size=2,
    )

    assert result["dataset"]["sample_count"] == 2
    assert result["dataset"]["pixel_size_mm"] == pytest.approx(70 / 255)
    assert result["b0"]["mask_decoder_primary"]["error_mm"] is not None
    assert result["b1"]["path"]["successful_predictions"] == 2
    assert result["b1"]["angle"]["reference_source"] == "derived_from_repository_path_gt"
    assert result["b1"]["angle"]["error_degrees"]["count"] == 2
    assert len(result["samples"]) == 2
    json.dumps(result, allow_nan=False)


def test_repository_path_metrics_separate_empty_predictions_and_missing_references() -> None:
    inputs = torch.arange(2 * 2 * 256 * 256, dtype=torch.float32).reshape(2, 2, 256, 256)
    targets = torch.zeros((2, 256, 256), dtype=torch.int64)
    targets[0, 128, 30:128] = 1
    targets[:, 128, 128] = 2

    result = evaluate_repository_fixtures(
        _AllTipsParallelNets(),
        _EmptyPathModel(),
        inputs=inputs,
        targets=targets,
        device="cpu",
        batch_size=2,
    )

    path = result["b1"]["path"]
    assert path["references"] == 1
    assert path["missing_references"] == 1
    assert path["empty_predictions"] == 2
    assert path["empty_prediction_rate"] == 1.0
    assert path["successful_predictions"] == 0
    assert path["prediction_failures"] == 1
    assert result["b1"]["angle"]["successful_predictions"] == 0
    assert result["b1"]["angle"]["not_evaluable"] == 2
    assert result["samples"][0]["path_prediction_empty"] is True
    assert result["samples"][0]["path_reference_available"] is True
    assert result["samples"][1]["path_reference_available"] is False
    json.dumps(result, allow_nan=False)


def test_fixture_loader_contract_requires_matching_256_square_data() -> None:
    with pytest.raises(ValueError, match="inputs must have shape"):
        evaluate_repository_fixtures(
            _FakeParallelNets(),
            _ConstantPathModel(),
            inputs=torch.zeros((1, 2, 128, 128)),
            targets=torch.zeros((1, 128, 128)),
            device="cpu",
        )


def test_runtime_keeps_harness_and_historical_single_image_api_separate() -> None:
    inputs = torch.arange(2 * 2 * 256 * 256, dtype=torch.float32).reshape(2, 2, 256, 256)

    result = measure_inference_contracts(
        _AllTipsParallelNets(),
        _ConstantPathModel(),
        normalized_inputs=normalize(inputs).to(dtype=torch.float32),
        device="cpu",
        warmup_iterations=0,
        measured_iterations=1,
    )

    assert result["batched_evaluation_harness"]["batch_size"] == 2
    assert result["historic_single_image_api"]["batch_size"] == 1
    assert result["batched_evaluation_harness"]["tip"]["measured_iterations"] == 1
    assert result["historic_single_image_api"]["path"]["measured_iterations"] == 1
    json.dumps(result, allow_nan=False)


def test_cli_defaults_to_full_official_split_and_trained_resolution() -> None:
    from scripts.crack_detection.benchmark_ctd_p0 import build_parser

    parser = build_parser()
    defaults = parser.parse_args([])
    smoke = parser.parse_args(
        [
            "--device",
            "cpu",
            "--dataset-root",
            "data",
            "--output",
            "result.json",
            "--limit",
            "7",
            "--batch-size",
            "2",
            "--resolution-mode",
            "native-128",
            "--fixture-only",
            "--include-b2",
        ]
    )

    assert defaults.limit is None
    assert defaults.fixture_only is False
    assert defaults.resolution_mode == "trained-256"
    assert smoke.device == "cpu"
    assert smoke.dataset_root == Path("data")
    assert smoke.output == Path("result.json")
    assert smoke.limit == 7
    assert smoke.batch_size == 2
    assert smoke.resolution_mode == "native-128"
    assert smoke.fixture_only is True
    assert defaults.include_b2 is False
    assert defaults.b2_warmup_iterations == 1
    assert defaults.b2_measured_iterations == 3
    assert smoke.include_b2 is True


def test_b2_result_records_correction_runtime_and_lack_of_independent_ground_truth() -> None:
    clock_values = iter((0, 2_000_000))
    runtime = benchmark_phases(
        {"williams_correction": lambda: None},
        measured_iterations=1,
        clock_ns=lambda: next(clock_values),
    )

    result = build_b2_result(
        initial_tip_mm=(15.0, 0.5),
        initial_angle_degrees=-0.5,
        correction_vector_mm=(0.25, -0.1),
        iteration_count=3,
        runtime=runtime,
        status_code="completed",
    )

    assert result["initial_ai_tip_mm"] == [15.0, 0.5]
    assert result["initial_ai_angle_degrees"] == -0.5
    assert result["correction_vector_mm"] == [0.25, -0.1]
    assert result["final_tip_mm"] == [15.25, 0.4]
    assert result["iterations"] == 3
    assert result["runtime"]["phases"]["williams_correction"]["median_ms"] == 2.0
    assert result["status"] == {"code": "completed", "independent_ground_truth_available": False}
    assert result["accuracy_claim_supported"] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    ("iteration_log", "max_iterations", "expected"),
    [
        (pd.DataFrame(), 100, "williams_fit_failed"),
        (pd.DataFrame([{"dx": 0.001, "dy": 0.0}]), 100, "completed"),
        (pd.DataFrame([{"dx": 0.1, "dy": 0.0}]), 100, "williams_fit_interrupted"),
        (
            pd.DataFrame([{"dx": 0.1, "dy": 0.0}] * 100),
            100,
            "max_iterations_reached",
        ),
    ],
)
def test_b2_status_distinguishes_convergence_internal_failure_and_iteration_limit(
    iteration_log: pd.DataFrame,
    max_iterations: int,
    expected: str,
) -> None:
    assert classify_b2_correction_status(
        iteration_log,
        max_iterations=max_iterations,
        step_tolerance_mm=0.005,
    ) == expected


class _ExplodingB2Model(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        raise RuntimeError("test model inference failed")


class _WarmupThenMissingTipModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self.calls += 1
        masks = torch.zeros((len(inputs), 1, 256, 256), device=inputs.device)
        if self.calls == 1:
            masks[:, 0, 128, 128] = 1.0
        return masks, torch.zeros((len(inputs), 2), device=inputs.device)


class _FastSuccessfulCorrection:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.iteration_log = pd.DataFrame()

    def correct_crack_tip(self, *args: object, **kwargs: object) -> list[float]:
        self.iteration_log = pd.DataFrame([{"dx": 0.001, "dy": 0.0}])
        return [0.001, 0.0]


def test_b2_measured_iteration_cannot_reuse_successful_warmup_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(ctd_baseline, "CrackTipCorrection", _FastSuccessfulCorrection)

    result = evaluate_b2_example(
        _WarmupThenMissingTipModel(),
        _ConstantPathModel(),
        repository_root=repository_root,
        device="cpu",
        warmup_iterations=1,
        measured_iterations=1,
    )

    assert result["status"]["code"] == "initial_ai_tip_unavailable"
    assert result["initial_ai_tip_mm"] is None
    assert result["correction_vector_mm"] is None
    assert result["final_tip_mm"] is None
    assert result["iterations"] == 0


def test_b2_propagates_unexpected_model_errors_for_a_fail_fast_scientific_run() -> None:
    repository_root = Path(__file__).resolve().parents[3]

    with pytest.raises(RuntimeError, match="test model inference failed"):
        evaluate_b2_example(
            _ExplodingB2Model(),
            _ExplodingB2Model(),
            repository_root=repository_root,
            device="cpu",
        )

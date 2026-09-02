"""Contract tests for the persistent frozen CTD inference boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch import nn

from crackpy.crack_detection.data.preprocess import normalize
from crackpy.crack_detection.inference import CtdBatchPrediction, FrozenCtdInference
from crackpy.crack_detection.model import get_model


class _CountingTipModel(nn.Module):
    """Small real module that exposes lifecycle and forward context."""

    def __init__(self) -> None:
        super().__init__()
        self.scale = nn.Parameter(torch.tensor(1.0))
        self.freeze_calls = 0
        self.to_calls = 0
        self.eval_calls = 0
        self.forward_calls = 0
        self.forward_inference_modes: list[bool] = []

    def requires_grad_(self, requires_grad: bool = True) -> _CountingTipModel:
        self.freeze_calls += 1
        return super().requires_grad_(requires_grad)

    def to(self, *args: object, **kwargs: object) -> _CountingTipModel:
        self.to_calls += 1
        return super().to(*args, **kwargs)

    def eval(self) -> _CountingTipModel:
        self.eval_calls += 1
        return super().eval()

    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self.forward_calls += 1
        self.forward_inference_modes.append(torch.is_inference_mode_enabled())
        masks = inputs[:, :1] * self.scale
        coordinates = inputs.mean(dim=(-2, -1))
        return masks, coordinates


class _CountingPathModel(nn.Module):
    """Small real path module that exposes lifecycle and forward context."""

    def __init__(self) -> None:
        super().__init__()
        self.bias = nn.Parameter(torch.tensor(0.25))
        self.freeze_calls = 0
        self.to_calls = 0
        self.eval_calls = 0
        self.forward_calls = 0
        self.forward_inference_modes: list[bool] = []

    def requires_grad_(self, requires_grad: bool = True) -> _CountingPathModel:
        self.freeze_calls += 1
        return super().requires_grad_(requires_grad)

    def to(self, *args: object, **kwargs: object) -> _CountingPathModel:
        self.to_calls += 1
        return super().to(*args, **kwargs)

    def eval(self) -> _CountingPathModel:
        self.eval_calls += 1
        return super().eval()

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        self.forward_calls += 1
        self.forward_inference_modes.append(torch.is_inference_mode_enabled())
        return inputs[:, :1] + self.bias


def test_models_are_prepared_once_and_not_reprepared_per_prediction() -> None:
    tip_model = _CountingTipModel()
    path_model = _CountingPathModel()
    inference = FrozenCtdInference(tip_model, path_model, device="cpu")
    batch = torch.ones((2, 2, 8, 8), dtype=torch.float32)

    inference.predict(batch)
    inference.predict(batch)

    assert inference.device == torch.device("cpu")
    assert inference.tip_model is tip_model
    assert inference.path_model is path_model
    assert tip_model.freeze_calls == 1
    assert tip_model.to_calls == 1
    assert tip_model.eval_calls == 1
    assert path_model.freeze_calls == 1
    assert path_model.to_calls == 1
    assert path_model.eval_calls == 1
    assert tip_model.training is False
    assert path_model.training is False
    assert all(not parameter.requires_grad for parameter in tip_model.parameters())
    assert all(not parameter.requires_grad for parameter in path_model.parameters())


def test_batch_forwards_run_in_inference_mode_and_keep_results_on_device() -> None:
    tip_model = _CountingTipModel()
    path_model = _CountingPathModel()
    inference = FrozenCtdInference(tip_model, path_model, device="cpu")
    batch = torch.arange(3 * 2 * 8 * 8, dtype=torch.float32).reshape(3, 2, 8, 8)

    prediction = inference.predict(batch)

    assert isinstance(prediction, CtdBatchPrediction)
    assert prediction.tip_probabilities.shape == (3, 1, 8, 8)
    assert prediction.coordinate_outputs.shape == (3, 2)
    assert prediction.path_probabilities is not None
    assert prediction.path_probabilities.shape == (3, 1, 8, 8)
    assert prediction.tip_probabilities.device == torch.device("cpu")
    assert tip_model.forward_inference_modes == [True]
    assert path_model.forward_inference_modes == [True]


def test_tip_only_skips_path_and_missing_optional_path_returns_none() -> None:
    batch = torch.ones((2, 2, 8, 8), dtype=torch.float32)
    tip_model = _CountingTipModel()
    path_model = _CountingPathModel()
    inference = FrozenCtdInference(tip_model, path_model, device="cpu")

    tip_only = inference.predict(batch, include_path=False)

    assert tip_only.path_probabilities is None
    assert path_model.forward_calls == 0

    without_path = FrozenCtdInference(_CountingTipModel(), device="cpu")
    missing_optional_path = without_path.predict(batch, include_path=True)

    assert missing_optional_path.path_probabilities is None


def test_path_model_can_be_attached_once_after_genuine_tip_only_measurement() -> None:
    tip_model = _CountingTipModel()
    path_model = _CountingPathModel()
    inference = FrozenCtdInference(tip_model, device="cpu")
    batch = torch.ones((2, 2, 8, 8), dtype=torch.float32)

    inference.predict(batch, include_path=False)
    assert inference.path_model is None
    assert path_model.freeze_calls == 0
    assert path_model.to_calls == 0
    assert path_model.eval_calls == 0

    inference.attach_path_model(path_model)
    prediction = inference.predict(batch, include_path=True)

    assert prediction.path_probabilities is not None
    assert path_model.freeze_calls == 1
    assert path_model.to_calls == 1
    assert path_model.eval_calls == 1
    with pytest.raises(RuntimeError, match="already attached"):
        inference.attach_path_model(_CountingPathModel())


def test_tip_and_path_forwards_can_be_measured_as_separate_device_operations() -> None:
    tip_model = _CountingTipModel()
    path_model = _CountingPathModel()
    inference = FrozenCtdInference(tip_model, path_model, device="cpu")
    batch = torch.ones((4, 2, 8, 8), dtype=torch.float32)

    tip_probabilities, coordinate_outputs = inference.forward_tip(batch)
    path_probabilities = inference.forward_path(batch)

    assert tip_probabilities.shape == (4, 1, 8, 8)
    assert coordinate_outputs.shape == (4, 2)
    assert path_probabilities is not None
    assert path_probabilities.shape == (4, 1, 8, 8)
    assert tip_model.forward_calls == 1
    assert path_model.forward_calls == 1


def test_rejects_inputs_that_are_not_nonempty_two_channel_batches() -> None:
    inference = FrozenCtdInference(_CountingTipModel(), device="cpu")

    with pytest.raises(ValueError, match=r"shape \(batch, 2, height, width\)"):
        inference.predict(torch.zeros((2, 8, 8)))
    with pytest.raises(ValueError, match="at least one sample"):
        inference.predict(torch.zeros((0, 2, 8, 8)))


def test_batch_one_outputs_match_p0_forward_contract_on_repository_fixtures() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    fixture_root = repository_root / "test_data" / "crack_detection" / "interim"
    inputs = torch.cat(
        torch.load(fixture_root / "lInputData_right.pt", map_location="cpu", weights_only=False)
    )
    normalized_inputs = normalize(inputs).to(dtype=torch.float32)
    tip_model = get_model("ParallelNets", map_location=torch.device("cpu"))
    path_model = get_model("UNetPath", map_location=torch.device("cpu"))
    tip_model.eval()
    path_model.eval()

    expected: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = []
    with torch.inference_mode():
        for sample in normalized_inputs.split(1):
            tip_probabilities, coordinate_outputs = tip_model(sample)
            path_probabilities = path_model(sample)
            expected.append((tip_probabilities, coordinate_outputs, path_probabilities))

    inference = FrozenCtdInference(tip_model, path_model, device="cpu")
    for sample, expected_outputs in zip(normalized_inputs.split(1), expected, strict=True):
        actual = inference.predict(sample)
        assert torch.equal(actual.tip_probabilities, expected_outputs[0])
        assert torch.equal(actual.coordinate_outputs, expected_outputs[1])
        assert actual.path_probabilities is not None
        assert torch.equal(actual.path_probabilities, expected_outputs[2])

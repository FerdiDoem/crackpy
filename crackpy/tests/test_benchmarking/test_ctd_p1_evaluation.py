"""Tests for bounded-memory CrackMNIST output collection in P1."""

from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from crackpy.benchmarking.ctd_baseline import ResolutionMode
from crackpy.benchmarking.ctd_p1_evaluation import collect_crackmnist_tip_outputs
from crackpy.crack_detection.inference import FrozenCtdInference


class _Dataset:
    size = "S"
    pixels = 128
    task = "crack_tip_segmentation"

    def __init__(self, split: str) -> None:
        self.split = split
        grid = np.indices((128, 128), dtype=np.float32).sum(axis=0)
        self.images = np.stack([np.stack((grid + index, grid.T - index)) for index in range(3)])
        self.targets = np.zeros((3, 128, 128), dtype=np.uint8)
        self.targets[0, 10, 20] = 1
        self.targets[1, 30:32, 40:42] = 1

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        return self.images[index], self.targets[index]


class _Tip(nn.Module):
    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        probabilities = torch.sigmoid(inputs[:, :1])
        coordinates = torch.zeros((len(inputs), 2), device=inputs.device)
        return probabilities, coordinates


def test_collect_outputs_keeps_validation_identity_references_and_memmap(tmp_path: Path) -> None:
    dataset = _Dataset("val")
    inference = FrozenCtdInference(_Tip(), device="cpu")
    storage = tmp_path / "masks.npy"

    outputs = collect_crackmnist_tip_outputs(
        inference,
        dataset,
        resolution_mode=ResolutionMode.LOW_64,
        batch_size=2,
        mask_storage_path=storage,
    )

    assert outputs.split == "validation"
    assert outputs.model_pixels == 64
    assert outputs.original_pixels == 128
    assert outputs.probability_masks.shape == (3, 64, 64)
    assert outputs.probability_masks.dtype == np.float32
    assert isinstance(outputs.probability_masks, np.memmap)
    assert outputs.coordinate_heads.shape == (3, 2)
    assert outputs.references == ((10.0, 20.0), (30.5, 40.5), None)
    assert outputs.collection_seconds >= 0.0
    assert outputs.to_summary()["missing_references"] == 1


def test_collect_outputs_rejects_training_split_before_inference() -> None:
    dataset = _Dataset("train")
    inference = FrozenCtdInference(_Tip(), device="cpu")

    with pytest.raises(ValueError, match="validation or test"):
        collect_crackmnist_tip_outputs(
            inference,
            dataset,
            resolution_mode=ResolutionMode.TRAINED_256,
            batch_size=1,
        )

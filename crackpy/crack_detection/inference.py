"""Persistent evaluation-only inference for the original CTD models."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class CtdBatchPrediction:
    """Device-resident outputs from one CTD batch.

    ``tip_probabilities`` is the ParallelNets segmentation head used by the
    historical tip decoder.
    ``coordinate_outputs`` is the ParallelNets coordinate head retained for
    diagnostics and later decoder comparison.
    ``path_probabilities`` is optional so tip-only runs can avoid loading or
    executing UNetPath entirely.
    Outputs remain on the inference device so callers can measure and control
    device-to-host transfer separately.
    """

    tip_probabilities: Tensor
    coordinate_outputs: Tensor
    path_probabilities: Tensor | None


class FrozenCtdInference:
    """Own persistent, frozen CrackPy tip and optional path models.

    Models are frozen, moved to ``device`` and put into evaluation mode once
    during construction.
    The separate forward methods accept device-resident batches so benchmark
    code can time transfers independently from model execution.
    """

    def __init__(
        self,
        tip_model: nn.Module,
        path_model: nn.Module | None = None,
        *,
        device: str | torch.device,
    ) -> None:
        self.device = _canonical_device(device)
        self.tip_model = self._prepare_model(tip_model)
        self.path_model = self._prepare_model(path_model) if path_model is not None else None

    @torch.inference_mode()
    def forward_tip(self, device_batch: Tensor) -> tuple[Tensor, Tensor]:
        """Run both ParallelNets heads on an already transferred batch."""

        self._validate_device_batch(device_batch)
        tip_probabilities, coordinate_outputs = self.tip_model(device_batch)
        return tip_probabilities, coordinate_outputs

    @torch.inference_mode()
    def forward_path(self, device_batch: Tensor) -> Tensor | None:
        """Run UNetPath on an already transferred batch when it is available."""

        self._validate_device_batch(device_batch)
        if self.path_model is None:
            return None
        return self.path_model(device_batch)

    @torch.inference_mode()
    def predict(self, batch: Tensor, *, include_path: bool = True) -> CtdBatchPrediction:
        """Transfer and infer a non-empty batch while retaining device outputs."""

        _validate_batch(batch)
        device_batch = batch.to(self.device)
        tip_probabilities, coordinate_outputs = self.forward_tip(device_batch)
        path_probabilities = self.forward_path(device_batch) if include_path else None
        return CtdBatchPrediction(
            tip_probabilities=tip_probabilities,
            coordinate_outputs=coordinate_outputs,
            path_probabilities=path_probabilities,
        )

    def _prepare_model(self, model: nn.Module) -> nn.Module:
        model.requires_grad_(False)
        model.to(self.device)
        model.eval()
        return model

    def _validate_device_batch(self, device_batch: Tensor) -> None:
        _validate_batch(device_batch)
        if device_batch.device != self.device:
            raise ValueError(
                f"device batch must be on {self.device}, got {device_batch.device}"
            )


def _validate_batch(batch: Tensor) -> None:
    if not isinstance(batch, Tensor) or batch.ndim != 4 or batch.shape[1] != 2:
        raise ValueError("inputs must have shape (batch, 2, height, width)")
    if batch.shape[0] == 0:
        raise ValueError("inputs must contain at least one sample")
    if batch.shape[2] == 0 or batch.shape[3] == 0:
        raise ValueError("input height and width must be non-zero")


def _canonical_device(device: str | torch.device) -> torch.device:
    result = torch.device(device)
    if result.type == "cuda" and result.index is None:
        return torch.device("cuda", torch.cuda.current_device())
    return result

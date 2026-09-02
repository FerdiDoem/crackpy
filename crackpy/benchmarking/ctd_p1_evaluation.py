"""Bounded-memory output collection for P1 CrackMNIST calibration and test."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import numpy as np
import torch

from crackpy.benchmarking.ctd_baseline import ResolutionMode, prepare_crackmnist_inputs
from crackpy.crack_detection.inference import FrozenCtdInference

Point = tuple[float, float]


@dataclass(frozen=True)
class CrackMnistTipOutputs:
    """Frozen-head outputs and references for exactly one immutable split.

    ``probability_masks`` may be a disk-backed NumPy memmap so the complete
    256-pixel validation split does not require a second in-memory copy.
    ``coordinate_heads`` retains the original normalized ParallelNets output.
    ``references`` uses the 128-pixel original index grid and keeps empty masks
    as explicit ``None`` values.
    """

    split: str
    resolution_mode: str
    model_pixels: int
    original_pixels: int
    probability_masks: np.ndarray
    coordinate_heads: np.ndarray
    references: tuple[Point | None, ...]
    collection_seconds: float

    def to_summary(self) -> dict[str, Any]:
        """Describe the stored outputs without serializing dense probabilities."""

        return {
            "split": self.split,
            "resolution_mode": self.resolution_mode,
            "model_pixels": self.model_pixels,
            "original_pixels": self.original_pixels,
            "sample_count": len(self.references),
            "missing_references": sum(reference is None for reference in self.references),
            "probability_dtype": str(self.probability_masks.dtype),
            "collection_seconds": self.collection_seconds,
            "training_performed": False,
        }


def collect_crackmnist_tip_outputs(
    inference: FrozenCtdInference,
    dataset: Any,
    *,
    resolution_mode: ResolutionMode | str,
    batch_size: int,
    mask_storage_path: str | Path | None = None,
    limit: int | None = None,
) -> CrackMnistTipOutputs:
    """Run the frozen tip model once and retain exact Float32 outputs.

    Only validation and test are accepted so training data cannot silently
    influence P1 selection.
    """

    split = _canonical_split(getattr(dataset, "split", None))
    _validate_dataset(dataset)
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0
    ):
        raise ValueError("limit must be a positive integer or None")
    sample_count = len(dataset) if limit is None else min(limit, len(dataset))
    if sample_count == 0:
        raise ValueError("dataset must contain at least one sample")

    mode = ResolutionMode(resolution_mode)
    model_pixels = {
        ResolutionMode.TRAINED_256: 256,
        ResolutionMode.NATIVE_128: 128,
        ResolutionMode.LOW_64: 64,
    }[mode]
    mask_shape = (sample_count, model_pixels, model_pixels)
    if mask_storage_path is None:
        probability_masks: np.ndarray = np.empty(mask_shape, dtype=np.float32)
    else:
        storage_path = Path(mask_storage_path)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        probability_masks = np.lib.format.open_memmap(
            storage_path,
            mode="w+",
            dtype=np.float32,
            shape=mask_shape,
        )
    coordinate_heads = np.empty((sample_count, 2), dtype=np.float32)
    references: list[Point | None] = []

    _synchronize(inference.device)
    started = time.perf_counter()
    for start in range(0, sample_count, batch_size):
        stop = min(start + batch_size, sample_count)
        samples = [dataset[index] for index in range(start, stop)]
        raw_inputs = torch.as_tensor(
            np.stack([sample[0] for sample in samples]),
            dtype=torch.float32,
            device="cpu",
        )
        prepared, actual_pixels = prepare_crackmnist_inputs(raw_inputs, mode)
        if actual_pixels != model_pixels:
            raise RuntimeError("prepared input resolution differs from the declared P1 mode")
        prediction = inference.predict(prepared, include_path=False)
        masks = prediction.tip_probabilities.detach().to("cpu").numpy()
        coordinates = prediction.coordinate_outputs.detach().to("cpu").numpy()
        if masks.shape != (stop - start, 1, model_pixels, model_pixels):
            raise ValueError("tip model returned an unexpected probability-mask shape")
        if coordinates.shape != (stop - start, 2):
            raise ValueError("tip model returned an unexpected coordinate-head shape")
        probability_masks[start:stop] = masks[:, 0].astype(np.float32, copy=False)
        coordinate_heads[start:stop] = coordinates.astype(np.float32, copy=False)
        references.extend(_reference_tip(sample[1]) for sample in samples)
    _synchronize(inference.device)
    collection_seconds = float(time.perf_counter() - started)
    if isinstance(probability_masks, np.memmap):
        probability_masks.flush()

    return CrackMnistTipOutputs(
        split=split,
        resolution_mode=mode.value,
        model_pixels=model_pixels,
        original_pixels=128,
        probability_masks=probability_masks,
        coordinate_heads=coordinate_heads,
        references=tuple(references),
        collection_seconds=collection_seconds,
    )


def _canonical_split(value: Any) -> str:
    if value in ("val", "validation"):
        return "validation"
    if value == "test":
        return "test"
    raise ValueError("P1 output collection accepts validation or test splits only")


def _validate_dataset(dataset: Any) -> None:
    if getattr(dataset, "size", None) != "S" or getattr(dataset, "pixels", None) != 128:
        raise ValueError("P1 requires CrackMNIST size S at 128 pixels")
    if getattr(dataset, "task", None) != "crack_tip_segmentation":
        raise ValueError("P1 requires the crack_tip_segmentation task")


def _reference_tip(mask: Any) -> Point | None:
    positions = np.argwhere(np.asarray(mask) > 0)
    if len(positions) == 0:
        return None
    point = np.mean(positions, axis=0)
    return float(point[0]), float(point[1])


def _synchronize(device: torch.device) -> None:
    if device.type == "cuda" and torch.cuda.is_available():
        torch.cuda.synchronize(device)

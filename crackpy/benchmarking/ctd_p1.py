"""Leakage-safe orchestration for the frozen-model CTD P1 benchmark."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from importlib import resources
import json
import math
from pathlib import Path
import tempfile
import time
from typing import Any

import numpy as np
import torch

from crackpy.benchmarking.ctd_baseline import ResolutionMode
from crackpy.benchmarking.ctd_baseline import crackmnist_dataset_summary
from crackpy.benchmarking.ctd_calibration import (
    apply_frozen_decoder,
    calibrate_decoder,
    evaluate_decoder_config,
)
from crackpy.benchmarking.ctd_decoders import DecoderConfig
from crackpy.benchmarking.ctd_p1_evaluation import (
    CrackMnistTipOutputs,
    collect_crackmnist_tip_outputs,
)
from crackpy.benchmarking.ctd_p1_runtime import (
    P1InferenceMode,
    benchmark_interpolation_frames,
    measure_p1_model_loading,
    measure_p1_model_phases,
    run_p1_runtime_sweep,
)
from crackpy.benchmarking.ctd_runtime import (
    collect_run_metadata,
    configure_deterministic_execution,
    sha256_file,
)
from crackpy.crack_detection.inference import FrozenCtdInference
from crackpy.crack_detection.model import get_model
from crackpy.input.input_data import InputData
from crackpy.structure_elements.data_files import Nodemap

P1_RESOLUTIONS = (
    ResolutionMode.TRAINED_256,
    ResolutionMode.NATIVE_128,
    ResolutionMode.LOW_64,
)
P1_BATCH_SIZES = (1, 8, 16, 32)
DETECTION_RATE_DEGRADATION_LIMIT = 0.005
P95_ERROR_INCREASE_LIMIT_PX = 1.0


@dataclass(frozen=True)
class P0Reference:
    """Primary P0 accuracy point from which every P1 gate is derived.

    ``detection_rate`` and ``p95_error_px`` retain the measured 256-pixel P0
    operating point on the original 128-pixel reference grid.
    ``minimum_detection_rate`` is the absolute 0.5-percentage-point floor used
    during validation-only calibration and final test admission.
    ``maximum_p95_error_px`` is the one-original-pixel test ceiling required by
    the P1 resolution policy.
    ``source_sha256`` and ``source_schema_version`` bind the policy to the exact
    baseline artifact rather than an undocumented copied constant.
    """

    detection_rate: float
    p95_error_px: float
    minimum_detection_rate: float
    maximum_p95_error_px: float
    source_sha256: str
    source_schema_version: str | None
    artifact_sha256: Mapping[str, str]
    dataset_identity: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the frozen comparison point and its explicit tolerances."""

        return {
            "variant": "trained_256",
            "decoder": "p0_mask_decoder_primary",
            "detection_rate": self.detection_rate,
            "p95_error_px": self.p95_error_px,
            "allowed_absolute_detection_rate_degradation": (
                DETECTION_RATE_DEGRADATION_LIMIT
            ),
            "allowed_p95_error_increase_original_px": P95_ERROR_INCREASE_LIMIT_PX,
            "minimum_detection_rate": self.minimum_detection_rate,
            "maximum_p95_error_px": self.maximum_p95_error_px,
            "source_sha256": self.source_sha256,
            "source_schema_version": self.source_schema_version,
            "expected_artifact_sha256": dict(self.artifact_sha256),
            "expected_dataset_identity": dict(self.dataset_identity),
        }


@dataclass(frozen=True)
class P1RunConfig:
    """User-controlled scope for one reproducible P1 execution.

    Paths identify the repository, immutable P0 result, and CrackMNIST cache.
    ``device`` is shared by the one persistent model pair.
    ``limit`` bounds both validation and test only for smoke runs; ``None`` is
    deliberately the full-split default.
    The remaining fields separate calibration batching from warm-up and timing
    repetition counts so accuracy scope never changes implicitly with timing.
    """

    repository_root: Path
    dataset_root: Path
    p0_results_path: Path
    device: str
    limit: int | None = None
    calibration_batch_size: int = 8
    runtime_warmup_iterations: int = 1
    runtime_measured_iterations: int = 3
    interpolation_warmup_iterations: int = 1
    interpolation_measured_iterations: int = 3

    def __post_init__(self) -> None:
        """Reject ambiguous run scopes before loading data or models."""

        if self.limit is not None and (
            not isinstance(self.limit, int)
            or isinstance(self.limit, bool)
            or self.limit <= 0
        ):
            raise ValueError("limit must be a positive integer or None")
        _positive_integer("calibration_batch_size", self.calibration_batch_size)
        _non_negative_integer("runtime_warmup_iterations", self.runtime_warmup_iterations)
        _positive_integer("runtime_measured_iterations", self.runtime_measured_iterations)
        _non_negative_integer(
            "interpolation_warmup_iterations",
            self.interpolation_warmup_iterations,
        )
        _positive_integer(
            "interpolation_measured_iterations",
            self.interpolation_measured_iterations,
        )
        if not str(self.device).strip():
            raise ValueError("device must be non-empty")


@dataclass(frozen=True)
class P1Services:
    """Side-effect boundaries used by the orchestrator.

    Production defaults bind CrackMNIST, the original CrackPy model loader,
    phase benchmark, and Dummy2 reader.
    Keeping these boundaries explicit allows the orchestration contract to be
    tested without replacing the scientific decoder and calibration logic.
    """

    load_model: Callable[..., Any]
    measure_model_loading: Callable[..., tuple[dict[str, Any], Any, Any]]
    load_dataset: Callable[[str, Path], Any]
    collect_outputs: Callable[..., CrackMnistTipOutputs]
    inference_factory: Callable[..., FrozenCtdInference]
    measure_model_phases: Callable[..., dict[str, Any]]
    runtime_sweep: Callable[..., list[dict[str, Any]]]
    load_dummy2_frames: Callable[[Path], Mapping[str, InputData]]
    benchmark_interpolation: Callable[..., dict[str, Any]]
    dataset_summary: Callable[[Any, int], dict[str, Any]]
    collect_metadata: Callable[..., Any]

    @classmethod
    def defaults(cls) -> "P1Services":
        """Construct the real, non-training P1 service set."""

        return cls(
            load_model=get_model,
            measure_model_loading=measure_p1_model_loading,
            load_dataset=_load_crackmnist_split,
            collect_outputs=collect_crackmnist_tip_outputs,
            inference_factory=FrozenCtdInference,
            measure_model_phases=measure_p1_model_phases,
            runtime_sweep=run_p1_runtime_sweep,
            load_dummy2_frames=_load_dummy2_frames,
            benchmark_interpolation=benchmark_interpolation_frames,
            dataset_summary=crackmnist_dataset_summary,
            collect_metadata=collect_run_metadata,
        )

    def replace(self, **changes: Any) -> "P1Services":
        """Return a copy with selected external boundaries replaced."""

        return replace(self, **changes)


def load_p0_reference(path: str | Path) -> P0Reference:
    """Read and validate the primary P0 CrackMNIST comparison point."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        primary = payload["crackmnist"]["variants"]["trained_256"]["b0"][
            "mask_decoder_primary"
        ]
        detection_rate = float(primary["detection_rate"])
        p95_error_px = float(primary["error_px"]["p95"])
        artifact_sha256 = {
            name: str(payload["metadata"]["artifact_sha256"][name])
            for name in ("ParallelNets", "UNetPath")
        }
        p0_dataset = payload["crackmnist"]["dataset"]
        dataset_identity = {
            key: p0_dataset[key]
            for key in (
                "h5_md5",
                "metadata_sha256",
                "crackmnist_version",
                "size",
                "pixels",
                "task",
            )
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("P0 result does not contain the trained_256 primary metrics") from error
    if not math.isfinite(detection_rate) or not 0.0 <= detection_rate <= 1.0:
        raise ValueError("P0 detection rate must be finite and within zero and one")
    if not math.isfinite(p95_error_px) or p95_error_px < 0.0:
        raise ValueError("P0 P95 error must be finite and non-negative")
    return P0Reference(
        detection_rate=detection_rate,
        p95_error_px=p95_error_px,
        minimum_detection_rate=max(
            0.0,
            detection_rate - DETECTION_RATE_DEGRADATION_LIMIT,
        ),
        maximum_p95_error_px=p95_error_px + P95_ERROR_INCREASE_LIMIT_PX,
        source_sha256=sha256_file(source),
        source_schema_version=_optional_text(payload.get("schema_version")),
        artifact_sha256=artifact_sha256,
        dataset_identity=dataset_identity,
    )


def verify_p1_provenance(
    reference: P0Reference,
    *,
    current_artifact_sha256: Mapping[str, Any],
    validation_dataset: Mapping[str, Any],
    test_dataset: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail before evaluation if live weights or CrackMNIST differ from P0."""

    checks: dict[str, bool] = {}
    for name, expected in reference.artifact_sha256.items():
        checks[f"artifact_sha256:{name}"] = (
            str(current_artifact_sha256.get(name, "")) == expected
        )
    for key, expected in reference.dataset_identity.items():
        checks[f"validation_dataset:{key}"] = validation_dataset.get(key) == expected
        checks[f"test_dataset:{key}"] = test_dataset.get(key) == expected
    checks["validation_split"] = validation_dataset.get("split") == "validation"
    checks["test_split"] = test_dataset.get("split") == "test"
    failures = sorted(name for name, passed in checks.items() if not passed)
    if failures:
        raise RuntimeError(
            "P1 provenance differs from the P0 baseline: " + ", ".join(failures)
        )
    return {
        "all_checks_passed": True,
        "checks": checks,
        "p0_result_sha256": reference.source_sha256,
        "validation_dataset": dict(validation_dataset),
        "test_dataset": dict(test_dataset),
    }


def assess_resolution_gate(
    *,
    detection_rate: float | None,
    p95_error_px: float | None,
    reference: P0Reference,
) -> dict[str, Any]:
    """Apply the frozen P1 test gate without selecting or changing a decoder."""

    detection_ok = _finite_number(detection_rate) and bool(
        detection_rate >= reference.minimum_detection_rate - 1e-12
    )
    p95_ok = _finite_number(p95_error_px) and bool(
        p95_error_px <= reference.maximum_p95_error_px + 1e-12
    )
    return {
        "accepted_for_default": bool(detection_ok and p95_ok),
        "checks": {
            "detection_rate_within_0_5_percentage_points": detection_ok,
            "p95_within_1_original_pixel": p95_ok,
        },
        "observed": {
            "detection_rate": detection_rate,
            "p95_error_px": p95_error_px,
        },
        "limits": {
            "minimum_detection_rate": reference.minimum_detection_rate,
            "maximum_p95_error_px": reference.maximum_p95_error_px,
        },
        "comparison_grid": "original_128_pixel_indices",
    }


def run_p1_benchmark(
    config: P1RunConfig,
    *,
    services: P1Services | None = None,
) -> dict[str, Any]:
    """Execute P1 with one model load and a validation-locked test protocol."""

    services = P1Services.defaults() if services is None else services
    deterministic = configure_deterministic_execution(0)
    reference = load_p0_reference(config.p0_results_path)
    artifact_paths = _model_artifact_paths()
    metadata_value = services.collect_metadata(
        seed=0,
        device=config.device,
        artifact_paths=artifact_paths,
        git_root=config.repository_root,
    )
    metadata = (
        metadata_value.to_dict()
        if hasattr(metadata_value, "to_dict")
        else dict(metadata_value)
    )

    tip_cpu_loading, tip_model = services.measure_model_loading(
        lambda: services.load_model(
            "ParallelNets",
            map_location=torch.device("cpu"),
        ),
        phase_name="first_in_process_tip_model_loading_cpu",
        first_in_process=True,
    )
    inference = services.inference_factory(
        tip_model,
        None,
        device=config.device,
    )

    validation_dataset = services.load_dataset("val", config.dataset_root)
    test_dataset = services.load_dataset("test", config.dataset_root)
    evaluated_count = lambda dataset: (
        len(dataset) if config.limit is None else min(config.limit, len(dataset))
    )
    validation_dataset_summary = services.dataset_summary(
        validation_dataset,
        evaluated_count(validation_dataset),
    )
    test_dataset_summary = services.dataset_summary(
        test_dataset,
        evaluated_count(test_dataset),
    )
    provenance_verification = verify_p1_provenance(
        reference,
        current_artifact_sha256=metadata.get("artifact_sha256", {}),
        validation_dataset=validation_dataset_summary,
        test_dataset=test_dataset_summary,
    )
    resolution_results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="crackpy-p1-") as cache_directory:
        cache_root = Path(cache_directory)
        for resolution in P1_RESOLUTIONS:
            result = _evaluate_resolution(
                inference,
                validation_dataset,
                test_dataset,
                resolution=resolution,
                reference=reference,
                config=config,
                cache_root=cache_root,
                services=services,
            )
            resolution_results[_resolution_key(resolution)] = result

    selected_configs = {
        resolution: DecoderConfig.from_dict(
            resolution_results[_resolution_key(resolution)]["calibration"][
                "selected_config"
            ]
        )
        for resolution in P1_RESOLUTIONS
    }

    runtime_inputs = _runtime_inputs(test_dataset, max(P1_BATCH_SIZES))
    runtime_sides = _runtime_sample_sides(test_dataset, max(P1_BATCH_SIZES))
    runtime_sweeps = _tip_runtime_sweeps(
        inference,
        runtime_inputs=runtime_inputs,
        sample_sides=runtime_sides,
        selected_configs=selected_configs,
        config=config,
        services=services,
    )
    dummy2_frames = services.load_dummy2_frames(config.repository_root)
    interpolation = services.benchmark_interpolation(
        dummy2_frames,
        signed_sizes=(70.0, -70.0),
        pixels=256,
        warmup_iterations=config.interpolation_warmup_iterations,
        measured_iterations=config.interpolation_measured_iterations,
        tip_inference=inference,
        tip_decoder_config=selected_configs[ResolutionMode.TRAINED_256],
    )

    path_cpu_loading, path_model = services.measure_model_loading(
        lambda: services.load_model(
            "UNetPath",
            map_location=torch.device("cpu"),
        ),
        phase_name="deferred_path_model_loading_cpu",
        first_in_process=False,
    )
    path_model_attach_started = time.perf_counter()
    inference.attach_path_model(path_model)
    path_model_attach_seconds = float(time.perf_counter() - path_model_attach_started)
    runtime_sweeps.extend(
        _path_runtime_sweep(
            inference,
            runtime_inputs=runtime_inputs,
            sample_sides=runtime_sides,
            tip_decoder_config=selected_configs[ResolutionMode.TRAINED_256],
            config=config,
            services=services,
        )
    )
    return {
        "schema_version": "ctd-p1-v1",
        "stage": "P1",
        "scope": {
            "full_split": config.limit is None,
            "limit_per_split": config.limit,
            "training_performed": False,
            "model_architecture_changed": False,
            "original_weights_frozen": True,
            "validation_only_calibration": True,
            "test_used_for_decoder_or_threshold_selection": False,
            "test_used_for_final_default_admission": True,
            "resolutions": [resolution.value for resolution in P1_RESOLUTIONS],
            "runtime_batch_sizes": list(P1_BATCH_SIZES),
            "path_angle_resolution": ResolutionMode.TRAINED_256.value,
        },
        "metadata": metadata,
        "provenance_verification": provenance_verification,
        "deterministic_execution": deterministic.to_dict(),
        "p0_reference_and_policy": reference.to_dict(),
        "model_lifecycle": {
            "tip_model_loads": 1,
            "path_model_loads": 1,
            "persistent_device_residency": True,
            "torch_inference_mode": True,
            "tip_cpu_loading": tip_cpu_loading,
            "path_cpu_loading": path_cpu_loading,
            "path_model_attach_seconds": path_model_attach_seconds,
            "path_model_absent_during_tip_only": True,
            "execution_order": [
                "first_in_process_tip_model_loading_cpu",
                "attach_tip_model_only",
                "validation_calibration_and_frozen_test",
                "tip_only_runtime_sweeps",
                "dummy2_interpolation_and_tip_parity",
                "deferred_path_model_loading_cpu",
                "attach_preloaded_cpu_path_model",
                "trained_256_path_angle_runtime_sweep",
            ],
        },
        "resolutions": resolution_results,
        "runtime": {
            "model_sweeps": runtime_sweeps,
            "interpolation": interpolation,
            "plotting": "disabled",
            "result_writing": "outside_measured_path",
        },
        "evidence_boundaries": {
            "crackmnist": (
                "controlled augmented split evidence; not independent physical sequences"
            ),
            "dummy2_interpolation": "performance and numerical parity only",
            "path_angle": "repository compatibility and runtime evidence at 256 pixels",
        },
    }


def _evaluate_resolution(
    inference: FrozenCtdInference,
    validation_dataset: Any,
    test_dataset: Any,
    *,
    resolution: ResolutionMode,
    reference: P0Reference,
    config: P1RunConfig,
    cache_root: Path,
    services: P1Services,
) -> dict[str, Any]:
    """Calibrate on validation, freeze, then touch test exactly once."""

    validation_outputs = services.collect_outputs(
        inference,
        validation_dataset,
        resolution_mode=resolution,
        batch_size=config.calibration_batch_size,
        mask_storage_path=cache_root / f"validation-{resolution.value}.npy",
        limit=config.limit,
    )
    test_outputs: CrackMnistTipOutputs | None = None
    try:
        validation_reference = evaluate_decoder_config(
            validation_outputs.probability_masks,
            validation_outputs.coordinate_heads,
            validation_outputs.references,
            split=validation_outputs.split,
            config=DecoderConfig.historical(),
            model_pixels=validation_outputs.model_pixels,
            original_pixels=validation_outputs.original_pixels,
        )
        if validation_reference.detection_rate is None:
            raise RuntimeError("validation reference contains no evaluable tip labels")
        validation_minimum_detection_rate = max(
            0.0,
            validation_reference.detection_rate - DETECTION_RATE_DEGRADATION_LIMIT,
        )
        calibration = calibrate_decoder(
            validation_outputs.probability_masks,
            validation_outputs.coordinate_heads,
            validation_outputs.references,
            split=validation_outputs.split,
            model_pixels=validation_outputs.model_pixels,
            original_pixels=validation_outputs.original_pixels,
            minimum_detection_rate=validation_minimum_detection_rate,
        )
        test_outputs = services.collect_outputs(
            inference,
            test_dataset,
            resolution_mode=resolution,
            batch_size=config.calibration_batch_size,
            mask_storage_path=cache_root / f"test-{resolution.value}.npy",
            limit=config.limit,
        )
        frozen_test = apply_frozen_decoder(
            test_outputs.probability_masks,
            test_outputs.coordinate_heads,
            test_outputs.references,
            split=test_outputs.split,
            config=calibration.selected_config,
            model_pixels=test_outputs.model_pixels,
            original_pixels=test_outputs.original_pixels,
        )
        confidence_gated_test = apply_frozen_decoder(
            test_outputs.probability_masks,
            test_outputs.coordinate_heads,
            test_outputs.references,
            split=test_outputs.split,
            config=calibration.confidence_gated_config,
            model_pixels=test_outputs.model_pixels,
            original_pixels=test_outputs.original_pixels,
        )
        gate = assess_resolution_gate(
            detection_rate=frozen_test.detection_rate,
            p95_error_px=frozen_test.p95_error_px,
            reference=reference,
        )
        return {
            "resolution_mode": resolution.value,
            "validation_outputs": validation_outputs.to_summary(),
            "calibration": calibration.to_dict(),
            "validation_selection_policy": {
                "reference_decoder": "historical_mask_decoder_on_validation",
                "reference_detection_rate": validation_reference.detection_rate,
                "allowed_absolute_detection_rate_degradation": (
                    DETECTION_RATE_DEGRADATION_LIMIT
                ),
                "minimum_detection_rate": validation_minimum_detection_rate,
                "p0_test_metrics_used_for_selection": False,
            },
            "test_outputs": test_outputs.to_summary(),
            "frozen_test_metrics": frozen_test.to_dict(),
            "confidence_gated_test_metrics": confidence_gated_test.to_dict(),
            "confidence_policy": {
                "threshold_source": "validation_only",
                "test_recalibration_performed": False,
                "default_action": "trigger_p2_fallback",
                "hard_rejection_is_default": False,
                "reason": (
                    "A confidence warning must not convert a finite P1 tip into a "
                    "detection failure before P2 can attempt recovery."
                ),
            },
            "resolution_gate": gate,
            "decoder_frozen_before_test": True,
            "test_recalibration_performed": False,
        }
    finally:
        _close_output_storage(validation_outputs)
        if test_outputs is not None:
            _close_output_storage(test_outputs)


def _tip_runtime_sweeps(
    inference: FrozenCtdInference,
    *,
    runtime_inputs: torch.Tensor,
    sample_sides: tuple[str, ...],
    selected_configs: Mapping[ResolutionMode, DecoderConfig],
    config: P1RunConfig,
    services: P1Services,
) -> list[dict[str, Any]]:
    """Measure all tip resolutions before a path model occupies the device."""

    results: list[dict[str, Any]] = []
    for resolution in P1_RESOLUTIONS:
        resolution_results = services.runtime_sweep(
            lambda mode, batch_size, resolution=resolution: services.measure_model_phases(
                inference,
                raw_inputs=runtime_inputs[:batch_size],
                mode=mode,
                resolution_mode=resolution,
                tip_decoder_config=selected_configs[resolution],
                sample_sides=sample_sides[:batch_size],
                warmup_iterations=config.runtime_warmup_iterations,
                measured_iterations=config.runtime_measured_iterations,
            ),
            modes=(P1InferenceMode.TIP_ONLY,),
            batch_sizes=P1_BATCH_SIZES,
        )
        for entry in resolution_results:
            entry.setdefault("resolution_mode", resolution.value)
            results.append(entry)
    return results


def _path_runtime_sweep(
    inference: FrozenCtdInference,
    *,
    runtime_inputs: torch.Tensor,
    sample_sides: tuple[str, ...],
    tip_decoder_config: DecoderConfig,
    config: P1RunConfig,
    services: P1Services,
) -> list[dict[str, Any]]:
    """Measure the historical 256 path/angle path after its one-time attach."""

    path_results = services.runtime_sweep(
        lambda mode, batch_size: services.measure_model_phases(
            inference,
            raw_inputs=runtime_inputs[:batch_size],
            mode=mode,
            resolution_mode=ResolutionMode.TRAINED_256,
            tip_decoder_config=tip_decoder_config,
            sample_sides=sample_sides[:batch_size],
            warmup_iterations=config.runtime_warmup_iterations,
            measured_iterations=config.runtime_measured_iterations,
        ),
        modes=(P1InferenceMode.TIP_PATH_ANGLE,),
        batch_sizes=P1_BATCH_SIZES,
    )
    for entry in path_results:
        entry.setdefault("resolution_mode", ResolutionMode.TRAINED_256.value)
    return path_results


def _runtime_inputs(dataset: Any, count: int) -> torch.Tensor:
    """Materialize independent raw fields for the fixed batch-size sweep."""

    if len(dataset) < count:
        raise ValueError(f"runtime sweep requires at least {count} test samples")
    fields = np.stack([np.asarray(dataset[index][0]) for index in range(count)])
    if fields.shape != (count, 2, 128, 128):
        raise ValueError("CrackMNIST runtime inputs must have shape (n, 2, 128, 128)")
    return torch.as_tensor(fields, dtype=torch.float32, device="cpu")


def _runtime_sample_sides(dataset: Any, count: int) -> tuple[str, ...]:
    """Resolve one physical side per runtime sample from dataset metadata."""

    if len(dataset) < count:
        raise ValueError(f"runtime sweep requires at least {count} test samples")
    sides: list[str] = []
    for index in range(count):
        try:
            experiment_id = int(dataset.exp_ids[index])
            name = dataset.exp_names[experiment_id]
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            normalized = str(name).strip().lower()
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            normalized = "right"
        if normalized.endswith("_left"):
            sides.append("left")
        elif normalized.endswith("_right") or normalized == "right":
            sides.append("right")
        else:
            raise ValueError("runtime sample experiment name does not identify left or right")
    return tuple(sides)


def _load_crackmnist_split(split: str, dataset_root: Path) -> Any:
    """Load an official 128-S split without exposing its cache path in results."""

    from crackmnist import CrackMNIST

    return CrackMNIST(
        split=split,
        size="S",
        pixels=128,
        task="crack_tip_segmentation",
        download_path=str(dataset_root),
    )


def _load_dummy2_frames(repository_root: Path) -> dict[str, InputData]:
    """Load the four repository Dummy2 frames required by the P1 comparison."""

    folder = repository_root / "test_data" / "crack_detection" / "Nodemaps"
    return {
        stage: InputData(
            Nodemap(
                name=f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt",
                folder=folder,
            )
        )
        for stage in ("52", "53", "54", "55")
    }


def _model_artifact_paths() -> dict[str, Path]:
    """Resolve the original packaged weights for provenance hashing."""

    folder = Path(str(resources.files("crackpy").joinpath("crack_detection/models")))
    return {
        "ParallelNets": folder / "ParallelNets.pth",
        "UNetPath": folder / "UNetPath.pth",
    }


def _close_output_storage(outputs: CrackMnistTipOutputs) -> None:
    """Release a disk-backed mask array before its temporary directory exits."""

    masks = outputs.probability_masks
    if isinstance(masks, np.memmap):
        masks.flush()
        mmap = getattr(masks, "_mmap", None)
        if mmap is not None:
            mmap.close()


def _resolution_key(resolution: ResolutionMode) -> str:
    """Use stable JSON keys while preserving the public hyphenated mode value."""

    return resolution.value.replace("-", "_")


def _finite_number(value: float | None) -> bool:
    """Return whether an optional metric can participate in a scientific gate."""

    return value is not None and math.isfinite(float(value))


def _optional_text(value: Any) -> str | None:
    """Normalize optional provenance text."""

    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _positive_integer(name: str, value: int) -> None:
    """Validate one positive integer setting."""

    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _non_negative_integer(name: str, value: int) -> None:
    """Validate one non-negative integer setting."""

    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")

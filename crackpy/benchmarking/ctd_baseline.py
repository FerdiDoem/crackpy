"""Frozen B0/B1 evaluation harness for the CTD P0 baseline.

The harness is additive: the historic single-image detector API and its mask
decoder stay unchanged.  Batched ``torch.inference_mode`` execution exists only
to evaluate the frozen artifacts efficiently and is labelled accordingly in
every result.
"""

from __future__ import annotations

from enum import Enum
from hashlib import md5
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from skimage.morphology import skeletonize
from torch import Tensor, nn
from torch.nn import functional as torch_functional

from crackpy.benchmarking.ctd_metrics import (
    angle_error_degrees,
    dice_score,
    distribution_summary,
    hausdorff95_distance,
    intersection_over_union,
    path_distance,
    tip_metrics,
)
from crackpy.benchmarking.ctd_runtime import benchmark_phases, sha256_file
from crackpy.crack_detection.correction import CrackTipCorrection
from crackpy.crack_detection.data.preprocess import normalize
from crackpy.crack_detection.detection import (
    CrackAngleEstimation,
    CrackDetection,
    CrackPathDetection,
    CrackTipDetection,
)
from crackpy.crack_detection.utils.utilityfunctions import find_most_likely_tip_pos
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.input_data import InputData
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material

Point = tuple[float, float]
FIXTURE_PIXELS = 256
FIXTURE_WINDOW_MM = 70.0
FIXTURE_PIXEL_SIZE_MM = FIXTURE_WINDOW_MM / (FIXTURE_PIXELS - 1)
B2_NODEMAP_NAME = "Dummy2_WPXXX_DummyVersuch_2_dic_results_1_52.txt"
B2_MAX_ITERATIONS = 100
B2_STEP_TOLERANCE_MM = 0.005


class ResolutionMode(str, Enum):
    """Supported CrackMNIST input-resolution policies."""

    TRAINED_256 = "trained-256"
    NATIVE_128 = "native-128"
    LOW_64 = "low-64"


def decode_historical_tip(probability_mask: Tensor) -> Point | None:
    """Call CrackPy's unchanged probability-weighted connected-region decoder."""

    decoded = find_most_likely_tip_pos(probability_mask.detach().to("cpu"))
    point = np.asarray(decoded, dtype=float)
    if point.shape != (2,) or not np.all(np.isfinite(point)):
        return None
    return float(point[0]), float(point[1])


def denormalize_coordinate_head(coordinate: Tensor | Sequence[float], *, model_pixels: int) -> Point | None:
    """Decode the ParallelNets coordinate head for diagnostic reporting only."""

    if model_pixels <= 0:
        raise ValueError("model_pixels must be greater than zero")
    values = np.asarray(torch.as_tensor(coordinate).detach().to("cpu"), dtype=float)
    if values.shape != (2,) or not np.all(np.isfinite(values)):
        return None
    decoded = (values + 1.0) * model_pixels / 2.0
    return float(decoded[0]), float(decoded[1])


def map_legacy_decoder_point_to_original(
    point: Point | None,
    *,
    model_pixels: int,
    original_pixels: int,
) -> Point | None:
    """Map CrackPy's endpoint-valued decoder output to original pixel indices.

    The unchanged decoder assigns model index ``i`` the coordinate
    ``i * model_pixels / (model_pixels - 1)``.  Removing that legacy endpoint
    convention and applying the endpoint-inclusive resize mapping collapses to
    ``(original_pixels - 1) / model_pixels``.
    """

    if model_pixels <= 0 or original_pixels <= 0:
        raise ValueError("pixel counts must be greater than zero")
    if point is None:
        return None
    scale = (original_pixels - 1) / model_pixels
    return float(point[0] * scale), float(point[1] * scale)


def map_model_index_point_to_original(
    point: Point | None,
    *,
    model_pixels: int,
    original_pixels: int,
) -> Point | None:
    """Map a true model-grid pixel index through an endpoint-inclusive resize."""

    if model_pixels <= 1 or original_pixels <= 1:
        raise ValueError("pixel counts must be greater than one")
    if point is None:
        return None
    scale = (original_pixels - 1) / (model_pixels - 1)
    return float(point[0] * scale), float(point[1] * scale)


def prepare_crackmnist_inputs(
    raw_fields: Tensor | np.ndarray,
    resolution_mode: ResolutionMode | str = ResolutionMode.TRAINED_256,
) -> tuple[Tensor, int]:
    """Resize raw 128-pixel fields first, then apply exact CrackPy normalization."""

    mode = ResolutionMode(resolution_mode)
    fields = torch.as_tensor(raw_fields, dtype=torch.float32, device="cpu")
    if fields.ndim != 4 or fields.shape[1:] != (2, 128, 128):
        raise ValueError("raw CrackMNIST fields must have shape (n, 2, 128, 128)")
    model_pixels = {
        ResolutionMode.TRAINED_256: 256,
        ResolutionMode.NATIVE_128: 128,
        ResolutionMode.LOW_64: 64,
    }[mode]
    if model_pixels != 128:
        fields = torch_functional.interpolate(
            fields,
            size=(model_pixels, model_pixels),
            mode="bilinear",
            align_corners=True,
        )
    normalized = normalize(fields).to(dtype=torch.float32)
    return normalized, model_pixels


def evaluate_crackmnist(
    tip_model: nn.Module,
    dataset: Any,
    *,
    device: str | torch.device,
    batch_size: int = 8,
    resolution_mode: ResolutionMode | str = ResolutionMode.TRAINED_256,
    limit: int | None = None,
) -> dict[str, Any]:
    """Evaluate frozen ParallelNets on the official CrackMNIST 128-S test split."""

    _validate_crackmnist_dataset(dataset)
    _validate_batch_and_limit(batch_size, limit)
    mode = ResolutionMode(resolution_mode)
    sample_count = len(dataset) if limit is None else min(limit, len(dataset))
    indices = list(range(sample_count))
    model = _freeze_model(tip_model, device)

    primary_points: list[Point | None] = []
    diagnostic_points: list[Point | None] = []
    references: list[Point | None] = []
    sample_records: list[dict[str, Any]] = []
    dice_values: list[float] = []
    iou_values: list[float] = []

    with torch.inference_mode():
        for start in range(0, sample_count, batch_size):
            batch_indices = indices[start:start + batch_size]
            raw_images = torch.as_tensor(np.stack([dataset[index][0] for index in batch_indices]))
            target_masks = [np.asarray(dataset[index][1]) for index in batch_indices]
            prepared, model_pixels = prepare_crackmnist_inputs(raw_images, mode)
            mask_probabilities, coordinate_outputs = model(prepared.to(device))
            mask_probabilities = mask_probabilities.detach().to("cpu")
            coordinate_outputs = coordinate_outputs.detach().to("cpu")
            original_probabilities = _resize_probabilities(mask_probabilities, original_pixels=128)

            for local_index, dataset_index in enumerate(batch_indices):
                reference = _reference_tip(target_masks[local_index])
                model_point = decode_historical_tip(mask_probabilities[local_index:local_index + 1])
                primary = map_legacy_decoder_point_to_original(
                    model_point,
                    model_pixels=model_pixels,
                    original_pixels=128,
                )
                coordinate_model_point = denormalize_coordinate_head(
                    coordinate_outputs[local_index],
                    model_pixels=model_pixels,
                )
                diagnostic = map_model_index_point_to_original(
                    coordinate_model_point,
                    model_pixels=model_pixels,
                    original_pixels=128,
                )
                predicted_binary = np.asarray(original_probabilities[local_index, 0] >= 0.5, dtype=np.uint8)
                experiment_id, experiment_name = _experiment(dataset, dataset_index)
                primary_error = _point_error(primary, reference)
                diagnostic_error = _point_error(diagnostic, reference)
                if reference is None:
                    dice = None
                    iou = None
                else:
                    reference_binary = np.asarray(target_masks[local_index] > 0, dtype=np.uint8)
                    dice = dice_score(predicted_binary, reference_binary)
                    iou = intersection_over_union(predicted_binary, reference_binary)
                    dice_values.append(dice)
                    iou_values.append(iou)
                primary_points.append(primary)
                diagnostic_points.append(diagnostic)
                references.append(reference)
                sample_records.append(
                    {
                        "index": int(dataset_index),
                        "experiment_id": experiment_id,
                        "experiment_name": experiment_name,
                        "reference_available": reference is not None,
                        "reference_tip_rc": _point_list(reference),
                        "mask_decoder_tip_rc": _point_list(primary),
                        "mask_decoder_error_px": primary_error,
                        "coordinate_head_diagnostic_rc": _point_list(diagnostic),
                        "coordinate_head_error_px": diagnostic_error,
                        "dice": dice,
                        "iou": iou,
                    }
                )

    return {
        "evaluation_contract": _evaluation_contract(),
        "dataset": _crackmnist_summary(dataset, sample_count),
        "resolution": {
            "mode": mode.value,
            "model_pixels": model_pixels,
            "original_pixels": 128,
            "resize_before_normalization": model_pixels != 128,
            "align_corners": True if model_pixels != 128 else None,
            "mask_decoder_mapping": "legacy_endpoint_to_index",
            "coordinate_head_mapping": "model_index_to_original_index",
            "sensitivity_analysis": mode is not ResolutionMode.TRAINED_256,
            "millimetre_conversion": None,
        },
        "b0": {
            "model": "ParallelNets_original_weights",
            "mask_decoder_primary": tip_metrics(primary_points, references).to_dict(),
            "coordinate_head_diagnostic": tip_metrics(diagnostic_points, references).to_dict(),
            "mask_dice": distribution_summary(dice_values).to_dict(),
            "mask_iou": distribution_summary(iou_values).to_dict(),
        },
        "samples": sample_records,
    }


def load_repository_fixtures(repository_root: str | Path) -> tuple[Tensor, Tensor]:
    """Load the three unmodified 256-pixel right-side repository fixtures."""

    fixture_root = Path(repository_root) / "test_data" / "crack_detection" / "interim"
    inputs = torch.cat(torch.load(fixture_root / "lInputData_right.pt", map_location="cpu", weights_only=False))
    targets = torch.cat(
        torch.load(fixture_root / "lGroundTruthData_right.pt", map_location="cpu", weights_only=False)
    )
    return inputs, targets


def evaluate_repository_fixtures(
    tip_model: nn.Module,
    path_model: nn.Module,
    *,
    inputs: Tensor,
    targets: Tensor,
    device: str | torch.device,
    batch_size: int = 3,
) -> dict[str, Any]:
    """Evaluate B0/B1 on repository tip/path labels and GT-derived angles."""

    _validate_fixture_data(inputs, targets)
    _validate_batch_and_limit(batch_size, None)
    normalized_inputs = normalize(inputs.to("cpu")).to(dtype=torch.float32)
    tip_network = _freeze_model(tip_model, device)
    path_network = _freeze_model(path_model, device)

    primary_points: list[Point | None] = []
    diagnostic_points: list[Point | None] = []
    references: list[Point | None] = []
    path_distances: list[float] = []
    path_hd95_values: list[float] = []
    path_dice_values: list[float] = []
    path_iou_values: list[float] = []
    angle_errors: list[float] = []
    path_failures = 0
    missing_path_references = 0
    empty_path_predictions = 0
    angle_not_evaluable = 0
    sample_records: list[dict[str, Any]] = []

    with torch.inference_mode():
        for start in range(0, len(inputs), batch_size):
            batch = normalized_inputs[start:start + batch_size].to(device)
            tip_probabilities, coordinate_outputs = tip_network(batch)
            path_probabilities = path_network(batch)
            tip_probabilities = tip_probabilities.detach().to("cpu")
            coordinate_outputs = coordinate_outputs.detach().to("cpu")
            path_probabilities = path_probabilities.detach().to("cpu")

            for local_index in range(len(batch)):
                sample_index = start + local_index
                target = targets[sample_index].detach().to("cpu").numpy()
                reference = _reference_tip(target == 2)
                primary = decode_historical_tip(tip_probabilities[local_index:local_index + 1])
                diagnostic = denormalize_coordinate_head(
                    coordinate_outputs[local_index],
                    model_pixels=FIXTURE_PIXELS,
                )
                predicted_path_mask = np.asarray(path_probabilities[local_index, 0] >= 0.5, dtype=np.uint8)
                reference_path_mask = np.asarray(target == 1, dtype=np.uint8)
                prediction_empty = not bool(np.any(predicted_path_mask))
                reference_available = bool(np.any(reference_path_mask))
                if prediction_empty:
                    empty_path_predictions += 1
                if not reference_available:
                    missing_path_references += 1
                    distance = None
                    hd95 = None
                    path_dice = None
                    path_iou = None
                else:
                    predicted_path = np.argwhere(skeletonize(predicted_path_mask, method="lee"))[:, :2]
                    reference_path = np.argwhere(reference_path_mask)[:, :2]
                    distance = path_distance(predicted_path, reference_path)
                    hd95 = hausdorff95_distance(predicted_path, reference_path)
                    path_dice = dice_score(predicted_path_mask, reference_path_mask)
                    path_iou = intersection_over_union(predicted_path_mask, reference_path_mask)
                    path_dice_values.append(path_dice)
                    path_iou_values.append(path_iou)
                if reference_available and (distance is None or hd95 is None):
                    path_failures += 1
                elif reference_available:
                    path_distances.append(distance)
                    path_hd95_values.append(hd95)
                predicted_angle = _fixture_angle(predicted_path_mask, primary)
                reference_angle = _fixture_angle(reference_path_mask, reference) if reference_available else None
                angle_error = angle_error_degrees(predicted_angle, reference_angle)
                if angle_error is not None:
                    angle_errors.append(angle_error)
                else:
                    angle_not_evaluable += 1

                primary_points.append(primary)
                diagnostic_points.append(diagnostic)
                references.append(reference)
                sample_records.append(
                    {
                        "index": sample_index,
                        "reference_tip_rc": _point_list(reference),
                        "mask_decoder_tip_rc": _point_list(primary),
                        "mask_decoder_error_px": _point_error(primary, reference),
                        "coordinate_head_diagnostic_rc": _point_list(diagnostic),
                        "coordinate_head_error_px": _point_error(diagnostic, reference),
                        "path_prediction_empty": prediction_empty,
                        "path_reference_available": reference_available,
                        "path_distance_px": distance,
                        "path_hd95_px": hd95,
                        "path_dice": path_dice,
                        "path_iou": path_iou,
                        "predicted_angle_degrees": predicted_angle,
                        "reference_angle_degrees": reference_angle,
                        "angle_error_degrees": angle_error,
                    }
                )

    path_references = len(inputs) - missing_path_references
    successful_paths = path_references - path_failures
    return {
        "evaluation_contract": _evaluation_contract(),
        "dataset": {
            "name": "CrackPy_repository_fixtures_right",
            "sample_count": int(len(inputs)),
            "pixels": FIXTURE_PIXELS,
            "window_mm": FIXTURE_WINDOW_MM,
            "pixel_size_mm": FIXTURE_PIXEL_SIZE_MM,
            "tip_reference": "target_label_2",
            "path_reference": "target_label_1",
        },
        "b0": {
            "model": "ParallelNets_original_weights",
            "mask_decoder_primary": tip_metrics(
                primary_points,
                references,
                pixel_size_mm=FIXTURE_PIXEL_SIZE_MM,
            ).to_dict(),
            "coordinate_head_diagnostic": tip_metrics(
                diagnostic_points,
                references,
                pixel_size_mm=FIXTURE_PIXEL_SIZE_MM,
            ).to_dict(),
        },
        "b1": {
            "model": "UNetPath_original_weights",
            "path": {
                "references": int(path_references),
                "missing_references": int(missing_path_references),
                "successful_predictions": successful_paths,
                "prediction_failures": path_failures,
                "empty_predictions": int(empty_path_predictions),
                "empty_prediction_rate": float(empty_path_predictions / len(inputs)),
                "distance_px": distribution_summary(path_distances).to_dict(),
                "distance_mm": distribution_summary(
                    value * FIXTURE_PIXEL_SIZE_MM for value in path_distances
                ).to_dict(),
                "hd95_px": distribution_summary(path_hd95_values).to_dict(),
                "hd95_mm": distribution_summary(
                    value * FIXTURE_PIXEL_SIZE_MM for value in path_hd95_values
                ).to_dict(),
                "dice": distribution_summary(path_dice_values).to_dict(),
                "iou": distribution_summary(path_iou_values).to_dict(),
            },
            "angle": {
                "reference_source": "derived_from_repository_path_gt",
                "method": "CrackPy_local_path_linear_regression",
                "radius_mm": 10.0,
                "successful_predictions": int(len(angle_errors)),
                "not_evaluable": int(angle_not_evaluable),
                "error_degrees": distribution_summary(angle_errors).to_dict(),
            },
        },
        "samples": sample_records,
    }


def measure_inference_contracts(
    tip_model: nn.Module,
    path_model: nn.Module,
    *,
    normalized_inputs: Tensor,
    device: str | torch.device,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
) -> dict[str, Any]:
    """Measure the batched harness apart from CrackPy's historic public API."""

    _validate_fixture_data(
        normalized_inputs,
        torch.zeros((len(normalized_inputs), 256, 256), dtype=torch.int8),
    )
    tip_network = _freeze_model(tip_model, device)
    path_network = _freeze_model(path_model, device)
    batch = normalized_inputs.to(device)

    def harness_tip() -> None:
        with torch.inference_mode():
            tip_network(batch)

    def harness_path() -> None:
        with torch.inference_mode():
            path_network(batch)

    harness_tip_result = benchmark_phases(
        {"model_inference": harness_tip},
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
    )
    harness_path_result = benchmark_phases(
        {"model_inference": harness_path},
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
    )

    detection = CrackDetection(
        side="right",
        detection_window_size=FIXTURE_WINDOW_MM,
        angle_det_radius=10.0,
        device=device,
    )
    historic_tip = CrackTipDetection(detection, tip_network)
    historic_path = CrackPathDetection(detection, path_network)
    single_input = normalized_inputs[:1]
    historic_tip_result = benchmark_phases(
        {"make_prediction": lambda: historic_tip.make_prediction(single_input)},
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
    )
    historic_path_result = benchmark_phases(
        {"make_prediction": lambda: historic_path.make_prediction(single_input)},
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
    )
    return {
        "batched_evaluation_harness": {
            "scope": "frozen_models_under_torch_inference_mode",
            "batch_size": int(len(normalized_inputs)),
            "tip": harness_tip_result.to_dict(),
            "path": harness_path_result.to_dict(),
        },
        "historic_single_image_api": {
            "scope": "unchanged_CrackTipDetection_and_CrackPathDetection_make_prediction",
            "batch_size": 1,
            "tip": historic_tip_result.to_dict(),
            "path": historic_path_result.to_dict(),
        },
    }


def build_b2_result(
    *,
    initial_tip_mm: Point | None,
    initial_angle_degrees: float | None,
    correction_vector_mm: Point | None,
    iteration_count: int,
    runtime: Any | None,
    status_code: str,
) -> dict[str, Any]:
    """Represent one Williams correction without implying an accuracy result.

    ``initial_tip_mm`` and ``initial_angle_degrees`` are the frozen AI outputs
    that seed the correction.  ``correction_vector_mm`` is the displacement
    returned by CrackPy's existing correction routine, and ``final_tip_mm`` is
    their vector sum when both are available.  ``iteration_count`` reports the
    actual Williams fit attempts recorded by that routine.  No independent
    corrected tip label is supplied by the bundled DIC example, so this record
    deliberately reports displacement and runtime only.
    """

    if not isinstance(iteration_count, int) or isinstance(iteration_count, bool) or iteration_count < 0:
        raise ValueError("iteration_count must be a non-negative integer")
    if not isinstance(status_code, str) or not status_code:
        raise ValueError("status_code must be a non-empty string")

    initial = _finite_b2_point(initial_tip_mm, "initial_tip_mm")
    correction = _finite_b2_point(correction_vector_mm, "correction_vector_mm")
    angle = _finite_b2_angle(initial_angle_degrees)
    final = None if initial is None or correction is None else (
        initial[0] + correction[0],
        initial[1] + correction[1],
    )
    return {
        "initial_ai_tip_mm": _point_list(initial),
        "initial_ai_angle_degrees": angle,
        "correction_vector_mm": _point_list(correction),
        "final_tip_mm": _point_list(final),
        "iterations": iteration_count,
        "runtime": None if runtime is None else runtime.to_dict(),
        "status": {
            "code": status_code,
            "independent_ground_truth_available": False,
        },
        "independent_ground_truth_available": False,
        "accuracy_claim_supported": False,
    }


def classify_b2_correction_status(
    iteration_log: Any,
    *,
    max_iterations: int,
    step_tolerance_mm: float,
) -> str:
    """Distinguish convergence from Legacy Williams failures and exhaustion.

    The legacy correction returns ``[0, 0]`` when an internal fit fails, even
    after earlier iterations succeeded.  Its iteration log is therefore the
    only available additive signal: a normal early return must end below the
    step tolerance, while a non-converged full log exhausted the iteration
    budget and any other early return indicates an interrupted fit.
    """

    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    if not np.isfinite(step_tolerance_mm) or step_tolerance_mm <= 0:
        raise ValueError("step_tolerance_mm must be finite and greater than zero")
    iteration_count = int(len(iteration_log))
    if iteration_count == 0:
        return "williams_fit_failed"
    if "dx" not in iteration_log or "dy" not in iteration_log:
        raise ValueError("iteration_log must contain dx and dy columns")
    last_step = iteration_log.iloc[-1]
    step_norm = float(np.hypot(float(last_step["dx"]), float(last_step["dy"])))
    if not np.isfinite(step_norm):
        return "williams_fit_failed"
    if step_norm < step_tolerance_mm:
        return "completed"
    if iteration_count >= max_iterations:
        return "max_iterations_reached"
    return "williams_fit_interrupted"


def evaluate_b2_example(
    tip_model: nn.Module,
    path_model: nn.Module,
    *,
    repository_root: str | Path,
    device: str | torch.device,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
) -> dict[str, Any]:
    """Run the unchanged Williams correction on CrackPy's stage-52 right DIC example.

    The bundled example has no independent corrected-tip annotation.  The
    returned record consequently treats the original AI tip, its correction
    vector, and phase runtimes as reproducibility evidence only, never as an
    accuracy comparison.  Plot generation remains disabled for every call.
    """

    repository_path = Path(repository_root)
    nodemap_path = repository_path / "test_data" / "crack_detection" / "Nodemaps" / B2_NODEMAP_NAME
    if not nodemap_path.is_file():
        return _b2_example_result(
            build_b2_result(
                initial_tip_mm=None,
                initial_angle_degrees=None,
                correction_vector_mm=None,
                iteration_count=0,
                runtime=None,
                status_code="nodemap_missing",
            )
        )

    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    detection = CrackDetection(
        side="right",
        detection_window_size=40,
        offset=(-10, 0),
        angle_det_radius=10,
        device=device,
    )
    nodemap = Nodemap(name=B2_NODEMAP_NAME, folder=str(nodemap_path.parent))
    data = InputData(nodemap)
    data.calc_stresses(material)
    tip_detector = CrackTipDetection(detection, _freeze_model(tip_model, device))
    path_detector = CrackPathDetection(detection, _freeze_model(path_model, device))
    correction_properties = OptimizationProperties(
        angle_gap=10,
        min_radius=3,
        max_radius=8,
        tick_size=0.1,
        terms=[-1, 0, 1, 2],
    )
    state: dict[str, Any] = {}

    def reset_state() -> None:
        """Start every warm-up and measured iteration without prior outputs."""

        state.clear()
        state.update(
            {
                "input": None,
                "initial_tip_pixels": None,
                "initial_tip_mm": None,
                "initial_angle_degrees": None,
                "correction_vector_mm": None,
                "iteration_count": 0,
                "status_code": "completed",
            }
        )

    def preprocess_phase() -> None:
        reset_state()
        interpolated_displacements, _ = detection.interpolate(data)
        state["input"] = detection.preprocess(interpolated_displacements)

    def tip_phase() -> None:
        if state["input"] is None:
            state["status_code"] = "preprocessing_failed"
            return
        with torch.inference_mode():
            prediction = tip_detector.make_prediction(state["input"])
        tip_pixels = tip_detector.find_most_likely_tip_pos(prediction)
        point = _finite_optional_b2_point(tip_pixels)
        if point is None:
            state["status_code"] = "initial_ai_tip_unavailable"
            return
        state["initial_tip_pixels"] = point
        state["initial_tip_mm"] = tip_detector.calculate_position_in_mm(point)

    def path_angle_phase() -> None:
        if state["initial_tip_mm"] is None:
            return
        with torch.inference_mode():
            segmentation, _ = path_detector.predict_path(state["input"])
        estimator = CrackAngleEstimation(
            detection=detection,
            crack_tip_in_px=torch.tensor(state["initial_tip_pixels"]),
        )
        masked = estimator.apply_circular_mask(segmentation)
        largest_region = estimator.get_largest_region(masked)
        angle = estimator.predict_angle(largest_region)
        state["initial_angle_degrees"] = _finite_optional_angle(angle)
        if state["initial_angle_degrees"] is None:
            state["status_code"] = "initial_ai_angle_unavailable"

    def correction_phase() -> None:
        if state["initial_tip_mm"] is None or state["initial_angle_degrees"] is None:
            return
        correction = CrackTipCorrection(
            data,
            state["initial_tip_mm"],
            state["initial_angle_degrees"],
            material,
        )
        vector = correction.correct_crack_tip(
            correction_properties,
            max_iter=B2_MAX_ITERATIONS,
            step_tol=B2_STEP_TOLERANCE_MM,
            damper=1,
            method="symbolic_regression",
            plot_intermediate_results=False,
        )
        state["iteration_count"] = int(len(correction.iteration_log))
        state["status_code"] = classify_b2_correction_status(
            correction.iteration_log,
            max_iterations=B2_MAX_ITERATIONS,
            step_tolerance_mm=B2_STEP_TOLERANCE_MM,
        )
        if state["status_code"] in {"completed", "max_iterations_reached"}:
            state["correction_vector_mm"] = _finite_b2_point(vector, "correction_vector_mm")

    runtime = benchmark_phases(
        {
            "preprocessing": preprocess_phase,
            "tip_inference": tip_phase,
            "path_angle": path_angle_phase,
            "williams_correction": correction_phase,
        },
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        device=str(device),
    )

    return _b2_example_result(
        build_b2_result(
            initial_tip_mm=state["initial_tip_mm"],
            initial_angle_degrees=state["initial_angle_degrees"],
            correction_vector_mm=state["correction_vector_mm"],
            iteration_count=state["iteration_count"],
            runtime=runtime,
            status_code=state["status_code"],
        )
    )


def _freeze_model(model: nn.Module, device: str | torch.device) -> nn.Module:
    """Place an original artifact in evaluation-only state without training logic."""

    model.requires_grad_(False)
    model.to(device)
    model.eval()
    return model


def _resize_probabilities(probabilities: Tensor, *, original_pixels: int) -> Tensor:
    """Return probabilities in the original grid for overlap metrics."""

    if probabilities.shape[-2:] == (original_pixels, original_pixels):
        return probabilities
    return torch_functional.interpolate(
        probabilities,
        size=(original_pixels, original_pixels),
        mode="bilinear",
        align_corners=True,
    )


def _reference_tip(mask: np.ndarray) -> Point | None:
    """Return the centroid of a non-empty binary reference mask."""

    positions = np.argwhere(np.asarray(mask) > 0)
    if len(positions) == 0:
        return None
    point = np.mean(positions, axis=0)
    return float(point[0]), float(point[1])


def _fixture_angle(path_mask: np.ndarray, tip: Point | None) -> float | None:
    """Use CrackPy's local-path angle estimator for prediction and reference."""

    if tip is None or not np.any(path_mask):
        return None
    detection = CrackDetection(
        side="right",
        detection_window_size=FIXTURE_WINDOW_MM,
        angle_det_radius=10.0,
        device="cpu",
    )
    estimator = CrackAngleEstimation(detection, torch.tensor(tip, dtype=torch.float32))
    masked = estimator.apply_circular_mask(torch.as_tensor(path_mask))
    largest = estimator.get_largest_region(masked)
    angle = estimator.predict_angle(largest)
    if angle is None or not np.isfinite(angle):
        return None
    return float(angle)


def _point_error(prediction: Point | None, reference: Point | None) -> float | None:
    """Return Euclidean error only when prediction and reference both exist."""

    if prediction is None or reference is None:
        return None
    return float(np.linalg.norm(np.subtract(prediction, reference)))


def _point_list(point: Point | None) -> list[float] | None:
    """Convert a point to a strict-JSON-native representation."""

    return None if point is None else [float(point[0]), float(point[1])]


def _finite_b2_point(point: Point | None, name: str) -> Point | None:
    """Validate optional B2 coordinates before they enter a JSON artifact."""

    if point is None:
        return None
    values = np.asarray(point, dtype=float)
    if values.shape != (2,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be a finite two-coordinate point or None")
    return float(values[0]), float(values[1])


def _finite_optional_b2_point(point: Any) -> Point | None:
    """Convert decoder output into an optional B2 point without raising on a miss."""

    if point is None:
        return None
    try:
        return _finite_b2_point(point, "point")
    except (TypeError, ValueError):
        return None


def _finite_b2_angle(angle: float | None) -> float | None:
    """Normalize an optional AI angle without fabricating an unavailable value."""

    if angle is None:
        return None
    value = float(angle)
    if not np.isfinite(value):
        raise ValueError("initial_angle_degrees must be finite or None")
    return value


def _finite_optional_angle(angle: Any) -> float | None:
    """Preserve an unavailable legacy angle as ``None`` in the B2 status record."""

    try:
        return _finite_b2_angle(angle)
    except (TypeError, ValueError):
        return None


def _b2_example_result(result: dict[str, Any]) -> dict[str, Any]:
    """Attach immutable example provenance to a B2 measurement record."""

    result["example"] = {
        "nodemap": B2_NODEMAP_NAME,
        "stage": 52,
        "side": "right",
        "detection_window_mm": 40.0,
        "offset_mm": [-10.0, 0.0],
        "correction_method": "symbolic_regression",
        "max_iterations": B2_MAX_ITERATIONS,
        "step_tolerance_mm": B2_STEP_TOLERANCE_MM,
        "plot_generation": False,
    }
    return result


def _experiment(dataset: Any, index: int) -> tuple[int, str]:
    """Read the stable experiment identifier and name exposed by CrackMNIST."""

    experiment_id = int(dataset.exp_ids[index])
    name = dataset.exp_names[experiment_id]
    if isinstance(name, bytes):
        name = name.decode("utf-8")
    return experiment_id, str(name)


def _crackmnist_summary(dataset: Any, sample_count: int) -> dict[str, Any]:
    """Capture dataset identity without claiming augmented-sample independence."""

    experiment_ids = sorted({int(value) for value in np.asarray(dataset.exp_ids[:])})
    experiment_names = sorted({_experiment(dataset, index)[1] for index in range(len(dataset))})
    experiment_sides = sorted(
        {side for name in experiment_names for side in ("left", "right") if name.lower().endswith(f"_{side}")}
    )
    artifact = Path(str(dataset.download_path)) / "crackmnist_128_S.h5"
    metadata_artifact = Path(str(dataset.download_path)) / "experiments_metadata.json"
    return {
        "name": "CrackMNIST",
        "crackmnist_version": _installed_distribution_version("crackmnist"),
        "split": "test",
        "size": "S",
        "pixels": 128,
        "task": "crack_tip_segmentation",
        "sample_count": int(sample_count),
        "total_split_sample_count": int(len(dataset)),
        "h5_md5": _md5_file(artifact) if artifact.is_file() else None,
        "metadata_sha256": sha256_file(metadata_artifact) if metadata_artifact.is_file() else None,
        "experiment_ids": experiment_ids,
        "experiment_names": experiment_names,
        "experiment_sides": experiment_sides,
        "augmentations_present": hasattr(dataset, "augmentations"),
        "source_sample_id_available": False,
        "independence_note": (
            "Augmented samples have no exposed source-sample ID; sample-level independence is not claimed."
        ),
    }


def _installed_distribution_version(distribution_name: str) -> str | None:
    """Return optional package provenance without making CrackMNIST a runtime dependency."""

    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _md5_file(path: Path) -> str:
    """Hash the exact CrackMNIST H5 artifact in bounded memory."""

    digest = md5()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _evaluation_contract() -> dict[str, Any]:
    """Label frozen batched evaluation separately from CrackPy's public API."""

    return {
        "weights": "original_frozen",
        "training_performed": False,
        "primary_tip_output": "historical_mask_decoder",
        "coordinate_head_role": "diagnostic_only",
        "execution": "batched_evaluation_harness",
        "torch_inference_mode": True,
        "historic_single_image_api_modified": False,
        "historic_single_image_api_runtime_reported_separately": True,
    }


def _validate_crackmnist_dataset(dataset: Any) -> None:
    """Reject accidental training, alternate sizes, and non-segmentation tasks."""

    if getattr(dataset, "split", None) != "test":
        raise ValueError("CrackMNIST evaluation requires the official test split")
    if getattr(dataset, "size", None) != "S" or getattr(dataset, "pixels", None) != 128:
        raise ValueError("CrackMNIST evaluation requires size S at 128 pixels")
    if getattr(dataset, "task", None) != "crack_tip_segmentation":
        raise ValueError("CrackMNIST evaluation requires crack_tip_segmentation")


def _validate_fixture_data(inputs: Tensor, targets: Tensor) -> None:
    """Validate the immutable repository fixture tensor layout."""

    if inputs.ndim != 4 or tuple(inputs.shape[1:]) != (2, 256, 256):
        raise ValueError("inputs must have shape (n, 2, 256, 256)")
    if targets.ndim != 3 or tuple(targets.shape[1:]) != (256, 256):
        raise ValueError("targets must have shape (n, 256, 256)")
    if len(inputs) != len(targets):
        raise ValueError("inputs and targets must contain the same number of samples")


def _validate_batch_and_limit(batch_size: int, limit: int | None) -> None:
    """Validate bounded batching and the optional smoke-test sample limit."""

    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0
    ):
        raise ValueError("limit must be a positive integer or None")

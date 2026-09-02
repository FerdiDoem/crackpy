from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from crackpy.crack_detection.data import optimized_interpolation
from crackpy.crack_detection.data.interpolation import interpolate as legacy_interpolate
from crackpy.crack_detection.data.optimized_interpolation import interpolate_frame
from crackpy.crack_detection.detection import CrackDetection
from crackpy.input.input_data import InputData
from crackpy.structure_elements.data_files import Nodemap


def _linear_frame() -> SimpleNamespace:
    coor_x = np.asarray([0.0, 2.0, 0.0, 2.0, 1.0], dtype=np.float64)
    coor_y = np.asarray([-1.0, -1.0, 1.0, 1.0, 0.0], dtype=np.float64)
    return SimpleNamespace(
        coor_x=coor_x,
        coor_y=coor_y,
        disp_x=2.0 * coor_x + 3.0 * coor_y + 1.0,
        disp_y=-1.5 * coor_x + 0.5 * coor_y - 2.0,
        eps_vm=0.25 * coor_x - 0.75 * coor_y + 0.5,
    )


def _left_linear_frame() -> SimpleNamespace:
    coor_x = np.asarray([-2.0, 0.0, -2.0, 0.0, -1.0], dtype=np.float64)
    coor_y = np.asarray([-1.0, -1.0, 1.0, 1.0, 0.0], dtype=np.float64)
    return SimpleNamespace(
        coor_x=coor_x,
        coor_y=coor_y,
        disp_x=2.0 * coor_x + 3.0 * coor_y + 1.0,
        disp_y=-1.5 * coor_x + 0.5 * coor_y - 2.0,
        eps_vm=0.25 * coor_x - 0.75 * coor_y + 0.5,
    )


def test_right_frame_matches_three_legacy_griddata_calls() -> None:
    frame = _linear_frame()

    expected = legacy_interpolate(frame, size=2.0, offset=(0.0, 0.0), pixels=9)
    actual = interpolate_frame(frame, size=2.0, offset=(0.0, 0.0), pixels=9)

    for actual_field, expected_field in zip(actual, expected):
        np.testing.assert_allclose(
            actual_field,
            expected_field,
            atol=1e-12,
            rtol=1e-12,
            equal_nan=True,
        )


def test_left_frame_preserves_legacy_orientation_and_x_sign() -> None:
    frame = _left_linear_frame()

    expected = legacy_interpolate(frame, size=-2.0, offset=(0.0, 0.0), pixels=9)
    actual = interpolate_frame(frame, size=-2.0, offset=(0.0, 0.0), pixels=9)

    for actual_field, expected_field in zip(actual, expected):
        np.testing.assert_allclose(
            actual_field,
            expected_field,
            atol=1e-12,
            rtol=1e-12,
            equal_nan=True,
        )


def test_optional_eps_vm_is_not_required_or_interpolated_when_disabled() -> None:
    full_frame = _linear_frame()
    frame_without_eps_vm = SimpleNamespace(
        coor_x=full_frame.coor_x,
        coor_y=full_frame.coor_y,
        disp_x=full_frame.disp_x,
        disp_y=full_frame.disp_y,
    )

    expected_coors, expected_disps, _ = legacy_interpolate(
        full_frame,
        size=2.0,
        offset=(0.0, 0.0),
        pixels=9,
    )
    actual_coors, actual_disps, actual_eps_vm = interpolate_frame(
        frame_without_eps_vm,
        size=2.0,
        offset=(0.0, 0.0),
        pixels=9,
        include_eps_vm=False,
    )

    np.testing.assert_allclose(actual_coors, expected_coors, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(actual_disps, expected_disps, atol=1e-12, rtol=1e-12)
    assert actual_eps_vm is None


def test_outside_hull_and_field_specific_nan_masks_match_griddata() -> None:
    coor_x = np.asarray([0.0, 2.0, 0.0], dtype=np.float64)
    coor_y = np.asarray([-1.0, -1.0, 1.0], dtype=np.float64)
    frame = SimpleNamespace(
        coor_x=coor_x,
        coor_y=coor_y,
        disp_x=np.asarray([np.nan, 2.0, 4.0], dtype=np.float64),
        disp_y=np.asarray([1.0, 3.0, 5.0], dtype=np.float64),
        eps_vm=np.asarray([0.1, 0.2, 0.3], dtype=np.float64),
    )

    expected = legacy_interpolate(frame, size=2.0, offset=(0.0, 0.0), pixels=11)
    actual = interpolate_frame(frame, size=2.0, offset=(0.0, 0.0), pixels=11)

    for actual_field, expected_field in zip(actual, expected):
        np.testing.assert_array_equal(np.isnan(actual_field), np.isnan(expected_field))
        np.testing.assert_allclose(
            actual_field,
            expected_field,
            atol=1e-12,
            rtol=1e-12,
            equal_nan=True,
        )


def test_each_changed_frame_builds_exactly_one_triangulation(monkeypatch: pytest.MonkeyPatch) -> None:
    real_delaunay = optimized_interpolation.Delaunay
    calls = 0

    def counting_delaunay(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_delaunay(*args, **kwargs)

    monkeypatch.setattr(optimized_interpolation, "Delaunay", counting_delaunay)
    first_frame = _linear_frame()
    second_frame = _linear_frame()
    second_frame.coor_x = second_frame.coor_x + 3.0

    interpolate_frame(first_frame, size=2.0, pixels=9)
    interpolate_frame(second_frame, size=2.0, offset=(3.0, 0.0), pixels=9)

    assert calls == 2


@pytest.fixture(scope="module")
def dummy2_frames() -> dict[str, InputData]:
    root = Path(__file__).resolve().parents[4]
    data_folder = root / "test_data" / "crack_detection" / "Nodemaps"
    return {
        stage: InputData(Nodemap(
            name=f"Dummy2_WPXXX_DummyVersuch_2_dic_results_1_{stage}.txt",
            folder=data_folder,
        ))
        for stage in ("52", "53", "54", "55")
    }


@pytest.mark.parametrize("stage", ("52", "53", "54", "55"))
@pytest.mark.parametrize("signed_size", (70.0, -70.0), ids=("right", "left"))
def test_dummy2_float64_and_normalized_float32_inputs_match_legacy(
        dummy2_frames: dict[str, InputData],
        stage: str,
        signed_size: float,
) -> None:
    frame = dummy2_frames[stage]

    expected = legacy_interpolate(frame, size=signed_size, pixels=256)
    actual = interpolate_frame(frame, size=signed_size, pixels=256)

    for actual_field, expected_field in zip(actual, expected):
        np.testing.assert_array_equal(np.isnan(actual_field), np.isnan(expected_field))
        np.testing.assert_allclose(
            actual_field,
            expected_field,
            atol=1e-12,
            rtol=1e-12,
            equal_nan=True,
        )

    expected_model_input = CrackDetection.preprocess(expected[1])
    actual_model_input = CrackDetection.preprocess(actual[1])
    torch.testing.assert_close(
        actual_model_input,
        expected_model_input,
        atol=0.0,
        rtol=0.0,
        equal_nan=True,
    )

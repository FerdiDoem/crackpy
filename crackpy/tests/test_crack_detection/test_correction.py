from types import SimpleNamespace

import numpy as np
import pytest

from crackpy.crack_detection import correction as correction_module
from crackpy.crack_detection.correction import (
    CrackTipCorrection,
    CrackTipCorrectionGridSearch,
    CrackTipCorrectionResult,
)


class FakeInputData:
    """Minimal data double that records correction-time coordinate transforms."""

    def __init__(self):
        self.transforms = []

    def __deepcopy__(self, memo):
        return self

    def transform_data(self, crack_tip_x, crack_tip_y, crack_angle):
        self.transforms.append((crack_tip_x, crack_tip_y, crack_angle))


def test_correction_result_from_delta_exposes_absolute_estimate_and_audit_delta():
    result = CrackTipCorrectionResult.from_delta(
        method="rethore",
        initial_crack_tip=(10.0, 20.0),
        correction_delta=(1.5, -2.0, 0.25),
        angle_deg=12.0,
    )

    assert result.initial_mm == (10.0, 20.0)
    assert result.corrected_mm == (11.5, 18.0)
    assert result.correction_delta_mm == (1.5, -2.0)
    assert result.angle_deg == 12.0
    assert result.angle_delta_deg == 0.25


def test_correction_result_rejects_delta_without_xy_values():
    with pytest.raises(ValueError, match="dx and dy"):
        CrackTipCorrectionResult.from_delta(
            method="rethore",
            initial_crack_tip=(10.0, 20.0),
            correction_delta=(1.0,),
        )


def test_iterative_correction_result_wraps_legacy_delta(monkeypatch):
    def fake_run_williams_optimization(data, material, opt_props):
        return {-1: -0.5, 1: 2.0}, {-1: 0.0, 1: 1.0}, 0.01

    monkeypatch.setattr(correction_module, "run_williams_optimization", fake_run_williams_optimization)
    correction = CrackTipCorrection(
        data=FakeInputData(),
        crack_tip=[10.0, 20.0],
        crack_angle=0.0,
        material=SimpleNamespace(sig_yield=1.0),
    )

    result = correction.correct_crack_tip_result(
        opt_props=object(),
        max_iter=1,
        method="rethore",
    )

    assert result.method == "rethore"
    assert result.initial_mm == (10.0, 20.0)
    assert result.correction_delta_mm == (0.5, 0.0)
    assert result.corrected_mm == (10.5, 20.0)


def test_optimization_correction_result_wraps_legacy_delta(monkeypatch):
    def fake_minimize(*, fun, x0, args, tol):
        return SimpleNamespace(x=np.array([-1.0, 2.0]), success=True, nfev=1, fun=0.0)

    monkeypatch.setattr(correction_module.optimize, "minimize", fake_minimize)
    correction = CrackTipCorrection(
        data=FakeInputData(),
        crack_tip=[10.0, 20.0],
        crack_angle=30.0,
        material=SimpleNamespace(sig_yield=1.0),
    )

    result = correction.correct_crack_tip_optimization_result(
        opt_props=object(),
        objective="error",
        tol=0.1,
    )

    assert result.method == "optimization:error"
    assert result.initial_mm == (10.0, 20.0)
    assert result.correction_delta_mm == (-1.0, 2.0)
    assert result.corrected_mm == (9.0, 22.0)
    assert result.angle_deg == 30.0
    assert result.angle_delta_deg == 0.0


def test_grid_search_correction_result_keeps_audit_table(monkeypatch):
    audit_table = SimpleNamespace(name="grid")

    def fake_grid_search(self, **kwargs):
        return [0.25, -0.75], audit_table

    monkeypatch.setattr(CrackTipCorrectionGridSearch, "correct_crack_tip_grid_search", fake_grid_search)
    correction = CrackTipCorrectionGridSearch(
        data=FakeInputData(),
        crack_tip=[10.0, 20.0],
        crack_angle=0.0,
        material=SimpleNamespace(sig_yield=1.0),
    )

    result, returned_table = correction.correct_crack_tip_grid_search_result(
        opt_props=object(),
        x_min=-1.0,
        x_max=1.0,
        y_min=-1.0,
        y_max=1.0,
        x_step=0.5,
        y_step=0.5,
    )

    assert result.method == "grid_search"
    assert result.corrected_mm == (10.25, 19.25)
    assert result.correction_delta_mm == (0.25, -0.75)
    assert returned_table is audit_table

"""Fixture-backed vertical slice for fitting methods and provenance artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pytest import approx

from crackpy.fracture_analysis.analysis import FractureAnalysis
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.results.write import OutputWriter
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RELEASE_RESULT_FIXTURE = PROJECT_ROOT / "test_data" / "fracture_analysis" / "results_predef_integral_probs.csv"
NODEMAP_FOLDER = PROJECT_ROOT / "test_data" / "crack_detection" / "Nodemaps"
FIXTURE_OUTPUT_NAME = "Dummy2_WPXXX_DummyVersuch_2_dic_results_1_53_right_Output.txt"


def _release_fixture_row() -> pd.Series:
    results = pd.read_csv(RELEASE_RESULT_FIXTURE)
    fixture_rows = results[results["filename"] == FIXTURE_OUTPUT_NAME]
    if fixture_rows.empty:
        raise AssertionError(f"Missing release fixture row: {FIXTURE_OUTPUT_NAME}")
    return fixture_rows.iloc[0]


def _analysis_from_release_fixture_row(row: pd.Series) -> FractureAnalysis:
    side = "right"
    nodemap_name = row["filename"].replace(f"_{side}_Output.txt", ".txt")
    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    crack_tip = CrackTipInfo(
        crack_tip_x=row["Crack_tip_x"],
        crack_tip_y=row["Crack_tip_y"],
        crack_tip_angle=row["Crack_tip_phi"],
        left_or_right=side,
    )
    nodemap = Nodemap(name=nodemap_name, folder=NODEMAP_FOLDER)
    data = InputData(nodemap)
    data.calc_stresses(material)
    data.transform_data(crack_tip.crack_tip_x, crack_tip.crack_tip_y, crack_tip.crack_tip_angle)

    analysis = FractureAnalysis(
        material=material,
        nodemap=nodemap,
        data=data,
        crack_tip_info=crack_tip,
        integral_properties=None,
        optimization_properties=OptimizationProperties(
            angle_gap=20,
            min_radius=5,
            max_radius=10,
            tick_size=0.01,
            terms=[-3, -2, -1, 0, 1, 2, 3, 4, 5],
        ),
    )
    analysis.run()
    return analysis


def _assert_release_fixture_value(row: pd.Series, column: str, actual: float) -> None:
    assert actual == approx(float(row[column]), abs=1e-4), f"{column} drifted from release fixture"


def test_real_fixture_method_fit_artifacts_match_release_results(tmp_path):
    row = _release_fixture_row()
    analysis = _analysis_from_release_fixture_row(row)

    for symbol, actual in analysis.cjp_res_mm.items():
        _assert_release_fixture_value(row, f"CJP_results_{symbol}", actual)

    for symbol, actual in analysis.williams_fit_res.items():
        _assert_release_fixture_value(row, f"Williams_fit_results_{symbol}", actual)

    for term in analysis.optimization_properties.terms:
        _assert_release_fixture_value(row, f"Williams_fit_results_a_{term}", analysis.williams_fit_a_n[term])
        _assert_release_fixture_value(row, f"Williams_fit_results_b_{term}", analysis.williams_fit_b_n[term])
        _assert_release_fixture_value(row, f"Williams_fit_results_c_{term}", analysis.williams_fit_c_n[term])

    writer = OutputWriter(path=tmp_path, fracture_analysis=analysis)
    williams_paths = writer.write_williams_fit_provenance_artifacts(path=tmp_path)
    cjp_paths = writer.write_cjp_fit_provenance_artifacts(path=tmp_path)

    assert set(williams_paths) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    assert set(cjp_paths) == {"envelope", "kg_statement_bundle", "visualization_graph", "visualization_graph_html"}
    for path in (*williams_paths.values(), *cjp_paths.values()):
        assert path.exists()

    williams_envelope = json.loads(williams_paths["envelope"].read_text(encoding="utf-8"))
    cjp_envelope = json.loads(cjp_paths["envelope"].read_text(encoding="utf-8"))
    williams_quantity_symbols = {quantity["symbol"] for quantity in williams_envelope["results"][0]["quantities"]}
    cjp_methods = {run["method_id"] for run in cjp_envelope["analysis_runs"]}
    cjp_result_symbols_by_run = {
        result["run_id"]: {quantity["symbol"] for quantity in result["quantities"]}
        for result in cjp_envelope["results"]
    }

    assert williams_envelope["input_records"][0]["input_id"] == "input:Dummy2_WPXXX_DummyVersuch_2_dic_results_1_53"
    assert williams_envelope["analysis_runs"][0]["configuration_id"].startswith("configuration:williams_fit:")
    assert {"K_I", "K_II", "K_III", "T", "a_1", "b_1", "c_1"} <= williams_quantity_symbols
    assert cjp_methods == {"crackpy.fracture.cjp_mixed_mode_fit", "crackpy.fracture.cjp_mode_i_fit"}
    assert any({"K_F", "K_R", "K_S", "K_II", "T"} <= symbols for symbols in cjp_result_symbols_by_run.values())
    assert any({"K_F", "K_R", "K_S", "T_x", "T_y"} <= symbols for symbols in cjp_result_symbols_by_run.values())

    for artifact_name in ("kg_statement_bundle", "visualization_graph"):
        assert json.loads(williams_paths[artifact_name].read_text(encoding="utf-8"))
        assert json.loads(cjp_paths[artifact_name].read_text(encoding="utf-8"))

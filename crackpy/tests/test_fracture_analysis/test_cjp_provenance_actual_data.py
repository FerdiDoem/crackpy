from pathlib import Path

from crackpy.fracture_analysis.analysis import FractureAnalysis
from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_analysis
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material


def test_cjp_provenance_vertical_slice_on_simulation_fixture():
    project_root = Path(__file__).resolve().parents[3]
    nodemap = Nodemap(
        name="File_F_10000.0_a_0.5_B_200.0_H_200.0.txt",
        folder=project_root / "test_data" / "simulations" / "Nodemaps",
    )
    material = Material(E=72000, nu_xy=0.33, sig_yield=350)
    crack_tip = CrackTipInfo(50, 0, 0, "right")
    data = InputData(nodemap=nodemap)
    data.calc_stresses(material)
    data.transform_data(crack_tip.crack_tip_x, crack_tip.crack_tip_y, crack_tip.crack_tip_angle)

    analysis = FractureAnalysis(
        material=material,
        nodemap=nodemap,
        data=data,
        crack_tip_info=crack_tip,
        integral_properties=None,
        optimization_properties=OptimizationProperties(
            angle_gap=10,
            min_radius=5,
            max_radius=10,
            tick_size=0.01,
            terms=[-1, 0, 1, 2, 3, 4, 5],
        ),
    )
    analysis.run()

    envelope = build_cjp_fit_envelope_from_analysis(analysis, crackpy_version="test-version")
    payload = envelope.to_dict()
    bundle = envelope_to_kg_statement_bundle(envelope).to_dict()
    quantities_by_method = {}
    runs_by_id = {run["run_id"]: run for run in payload["analysis_runs"]}
    for result in payload["results"]:
        method_id = runs_by_id[result["run_id"]]["method_id"]
        quantities_by_method[method_id] = {quantity["symbol"] for quantity in result["quantities"]}

    assert payload["input_records"][0]["input_id"] == "input:File_F_10000.0_a_0.5_B_200.0_H_200.0"
    assert len(payload["results"]) == 2
    assert {"K_II", "A_r"} <= quantities_by_method["crackpy.fracture.cjp_mixed_mode_fit"]
    assert {"T_y", "A"} <= quantities_by_method["crackpy.fracture.cjp_mode_i_fit"]
    assert "ResultQuantity" in bundle["groups"]

from pathlib import Path

from crackpy.fracture_analysis.analysis import FractureAnalysis
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.fracture_analysis.methods.williams_fit import build_williams_fit_envelope_from_analysis
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material


def test_williams_provenance_vertical_slice_on_simulation_fixture():
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

    envelope = build_williams_fit_envelope_from_analysis(analysis, crackpy_version="test-version")
    payload = envelope.to_dict()
    bundle = envelope_to_kg_statement_bundle(envelope).to_dict()

    assert payload["input_records"][0]["input_id"] == "input:File_F_10000.0_a_0.5_B_200.0_H_200.0"
    assert payload["configurations"][0]["parameter_hash"].startswith("sha256:")
    assert any(quantity["symbol"] == "K_I" for quantity in payload["results"][0]["quantities"])
    assert any(quantity["symbol"] == "a_-1" for quantity in payload["results"][0]["quantities"])
    assert "ResultQuantity" in bundle["groups"]

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from crackpy.fracture_analysis.pipeline import single_run
from crackpy.fracture_analysis.line_integration import IntegralProperties
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.fracture_analysis.workflow import FractureWorkflowInput, run_fracture_analysis_workflow
from crackpy.structure_elements.data_files import NodemapStructure
from crackpy.structure_elements.material import Material


class FakeInputData:
    def __init__(self, nodemap):
        self.nodemap = nodemap
        self.stress_material = None
        self.transform_args = None

    def calc_stresses(self, material):
        self.stress_material = material

    def transform_data(self, x_shift, y_shift, angle):
        self.transform_args = (x_shift, y_shift, angle)


class FakeFractureAnalysis:
    created = []

    def __init__(
            self,
            *,
            material,
            nodemap,
            data,
            crack_tip_info,
            integral_properties,
            optimization_properties,
    ):
        self.material = material
        self.nodemap = nodemap
        self.data = data
        self.crack_tip_info = crack_tip_info
        self.integral_properties = integral_properties
        self.optimization_properties = optimization_properties
        self.run_args = None
        self.created.append(self)

    def run(self, progress, task_id):
        self.run_args = (progress, task_id)


@pytest.fixture(autouse=True)
def clear_fake_analysis():
    FakeFractureAnalysis.created.clear()


def test_legacy_pipeline_row_builds_explicit_crack_tip_id_from_compatibility_side():
    material = Material()
    structure = NodemapStructure()
    integral_properties = IntegralProperties()
    optimization_properties = OptimizationProperties()

    workflow_input = FractureWorkflowInput.from_legacy_pipeline_row(
        {
            "Filename": "Dummy2_WPXXX_DummyVersuch_2_dic_results_1_53.txt",
            "Crack Tip x [mm]": 30.25,
            "Crack Tip y [mm]": -0.5,
            "Crack Angle": 182.0,
            "Side": "left",
        },
        material=material,
        nodemap_folder="nodemaps",
        nodemap_structure=structure,
        integral_properties=integral_properties,
        optimization_properties=optimization_properties,
    )

    assert workflow_input.crack_tip_id == "crack_tip:Dummy2_WPXXX_DummyVersuch_2_dic_results_1_53:left"
    assert workflow_input.compatibility_side == "left"
    assert workflow_input.integral_properties is integral_properties
    assert workflow_input.optimization_properties is optimization_properties


def test_legacy_pipeline_row_prefers_explicit_crack_tip_id_when_available():
    workflow_input = FractureWorkflowInput.from_legacy_pipeline_row(
        {
            "Filename": "nodemap.txt",
            "Crack Tip ID": "crack_tip:specimen-a:notch-2",
            "Crack Tip x [mm]": 1.0,
            "Crack Tip y [mm]": 2.0,
            "Crack Angle": 3.0,
            "Side": "right",
        },
        material=Material(),
        nodemap_folder="nodemaps",
        nodemap_structure=NodemapStructure(),
        integral_properties=None,
        optimization_properties=None,
    )

    assert workflow_input.crack_tip_id == "crack_tip:specimen-a:notch-2"
    assert workflow_input.compatibility_side == "right"


def test_workflow_runner_prepares_analysis_without_writer_or_plotter_policy():
    material = Material()
    integral_properties = IntegralProperties()
    optimization_properties = OptimizationProperties()
    workflow_input = FractureWorkflowInput(
        nodemap_name="nodemap.txt",
        nodemap_folder="nodemaps",
        material=material,
        crack_tip_id="crack_tip:specimen-a:notch-2",
        crack_tip_x=1.0,
        crack_tip_y=2.0,
        crack_tip_angle=3.0,
        compatibility_side="right",
        integral_properties=integral_properties,
        optimization_properties=optimization_properties,
    )
    progress = {}

    with (
        patch("crackpy.fracture_analysis.workflow.InputData", FakeInputData),
        patch("crackpy.fracture_analysis.workflow.FractureAnalysis", FakeFractureAnalysis),
    ):
        result = run_fracture_analysis_workflow(workflow_input, progress=progress, task_id="task-1")

    analysis = FakeFractureAnalysis.created[0]
    assert result.analysis is analysis
    assert result.crack_tip_id == "crack_tip:specimen-a:notch-2"
    assert result.data.stress_material is material
    assert result.data.transform_args == (1.0, 2.0, 3.0)
    assert analysis.crack_tip_info.left_or_right == "right"
    assert analysis.crack_tip_info.crack_tip_id == "crack_tip:specimen-a:notch-2"
    assert analysis.integral_properties is integral_properties
    assert analysis.optimization_properties is optimization_properties
    assert analysis.run_args == (progress, "task-1")


def test_workflow_input_rejects_missing_crack_tip_id():
    with pytest.raises(ValueError, match="crack_tip_id"):
        FractureWorkflowInput(
            nodemap_name="nodemap.txt",
            nodemap_folder="nodemaps",
            material=Material(),
            crack_tip_id="",
            crack_tip_x=1.0,
            crack_tip_y=2.0,
            crack_tip_angle=3.0,
        )


def test_single_run_keeps_legacy_output_policy_outside_workflow_runner(tmp_path):
    analysis = object()
    workflow_input = object()
    writer_calls = []
    plotter_calls = []

    class FakeOutputWriter:
        def __init__(self, *, path, fracture_analysis):
            writer_calls.append(("init", path, fracture_analysis))

        def write_header(self):
            writer_calls.append(("write_header",))

        def write_results(self):
            writer_calls.append(("write_results",))

        def write_json(self, *, path):
            writer_calls.append(("write_json", path))

    class FakePlotter:
        def __init__(self, *, path, fracture_analysis, plot_sets):
            plotter_calls.append(("init", path, fracture_analysis, plot_sets))

        def plot(self):
            plotter_calls.append(("plot",))

    with (
        patch(
            "crackpy.fracture_analysis.pipeline.FractureWorkflowInput.from_legacy_pipeline_row",
            return_value=workflow_input,
        ) as from_row,
        patch(
            "crackpy.fracture_analysis.pipeline.run_fracture_analysis_workflow",
            return_value=SimpleNamespace(analysis=analysis),
        ) as run_workflow,
        patch("crackpy.fracture_analysis.pipeline.OutputWriter", FakeOutputWriter),
        patch("crackpy.fracture_analysis.pipeline.Plotter", FakePlotter),
    ):
        single_run(
            index=4,
            data={
                "Filename": "nodemap.txt",
                "Crack Tip x [mm]": 1.0,
                "Crack Tip y [mm]": 2.0,
                "Crack Angle": 3.0,
                "Side": "right",
            },
            material=Material(),
            nodemap_path="nodemaps",
            nodemap_structure=NodemapStructure(),
            integral_props_by_nodemap={4: "integral"},
            opt_props="optimization",
            output_path=str(tmp_path),
            plot_sets="plots",
            prog={"progress": 1},
            task_id="task-1",
        )

    assert from_row.call_args.kwargs["integral_properties"] == "integral"
    assert from_row.call_args.kwargs["optimization_properties"] == "optimization"
    run_workflow.assert_called_once_with(workflow_input, progress={"progress": 1}, task_id="task-1")
    assert writer_calls == [
        ("init", tmp_path / "txt-files", analysis),
        ("write_header",),
        ("write_results",),
        ("write_json", tmp_path / "json"),
    ]
    assert plotter_calls == [
        ("init", tmp_path / "plots", analysis, "plots"),
        ("plot",),
    ]

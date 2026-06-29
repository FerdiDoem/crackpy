"""Side-effect-light fracture-analysis workflow runners.

This Module is the first C-004 domain workflow runner slice for fracture
analysis.
It owns the scientific single-nodemap sequence but leaves output files,
plotting, progress UI, and execution policy to pipeline compatibility facades
or future adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from crackpy.fracture_analysis.analysis import FractureAnalysis
from crackpy.fracture_analysis.line_integration import IntegralProperties
from crackpy.fracture_analysis.optimization import OptimizationProperties
from crackpy.input.crack_tip_info import CrackTipInfo
from crackpy.input.input_data import InputData
from crackpy.structure_elements.data_files import Nodemap, NodemapStructure
from crackpy.structure_elements.material import Material


@dataclass(frozen=True)
class FractureWorkflowInput:
    """Resolved inputs for one single-nodemap fracture-analysis run.

    `crack_tip_id` is the durable crack-tip identity for this workflow slice.
    `compatibility_side` carries the current `left`/`right` handoff label only
    so legacy `CrackTipInfo`, result filenames, and plots can keep working
    during migration.
    `nodemap_name` and `nodemap_folder` locate the current file-backed input.
    `nodemap_structure` explains how to read that file.
    `material`, crack-tip coordinates, and optional method properties are the
    result-affecting scientific inputs.
    """

    nodemap_name: str
    nodemap_folder: str | Path
    material: Material
    crack_tip_id: str
    crack_tip_x: float
    crack_tip_y: float
    crack_tip_angle: float
    compatibility_side: str | None = None
    nodemap_structure: NodemapStructure = field(default_factory=NodemapStructure)
    integral_properties: IntegralProperties | None = None
    optimization_properties: OptimizationProperties | None = None

    def __post_init__(self) -> None:
        for name, value in {
            "nodemap_name": self.nodemap_name,
            "nodemap_folder": self.nodemap_folder,
            "crack_tip_id": self.crack_tip_id,
        }.items():
            if not value:
                raise ValueError(f"FractureWorkflowInput requires a non-empty {name}.")

    @classmethod
    def from_legacy_pipeline_row(
            cls,
            row: Mapping[str, Any],
            *,
            material: Material,
            nodemap_folder: str | Path,
            nodemap_structure: NodemapStructure,
            integral_properties: IntegralProperties | None,
            optimization_properties: OptimizationProperties | None,
    ) -> "FractureWorkflowInput":
        """Translate the current crack-info CSV row into workflow input.

        Current handoff files still expose `Filename`, crack-tip coordinates,
        `Crack Angle`, and `Side`.
        If a future producer adds `Crack Tip ID`, that ID wins; otherwise this
        adapter derives a deterministic compatibility ID from filename stem and
        side so callers do not have to treat `Side` as durable identity.
        """
        filename = str(row["Filename"])
        compatibility_side = str(row["Side"])
        crack_tip_id = str(row.get("Crack Tip ID") or f"crack_tip:{Path(filename).stem}:{compatibility_side}")
        return cls(
            nodemap_name=filename,
            nodemap_folder=nodemap_folder,
            material=material,
            crack_tip_id=crack_tip_id,
            crack_tip_x=float(row["Crack Tip x [mm]"]),
            crack_tip_y=float(row["Crack Tip y [mm]"]),
            crack_tip_angle=float(row["Crack Angle"]),
            compatibility_side=compatibility_side,
            nodemap_structure=nodemap_structure,
            integral_properties=integral_properties,
            optimization_properties=optimization_properties,
        )

    def crack_tip_info(self) -> CrackTipInfo:
        """Return the legacy crack-tip container required by `FractureAnalysis`.

        This is intentionally a compatibility adapter.
        The workflow identity is `crack_tip_id`; `left_or_right` remains only
        the current output and plotting label until those adapters migrate.
        """
        return CrackTipInfo(
            crack_tip_x=self.crack_tip_x,
            crack_tip_y=self.crack_tip_y,
            crack_tip_angle=self.crack_tip_angle,
            left_or_right=self.compatibility_side,
        )


@dataclass(frozen=True)
class FractureWorkflowResult:
    """Result of one side-effect-light fracture-analysis workflow run.

    `workflow_input` records the resolved input used by the runner.
    `nodemap`, `data`, and `crack_tip_info` expose the prepared compatibility
    objects for callers that still need legacy adapters.
    `analysis` is the executed `FractureAnalysis` instance; output writers and
    plotters may consume it outside this runner.
    """

    workflow_input: FractureWorkflowInput
    nodemap: Nodemap
    data: InputData
    crack_tip_info: CrackTipInfo
    analysis: FractureAnalysis

    @property
    def crack_tip_id(self) -> str:
        """Durable crack-tip identity for frontend and provenance consumers."""
        return self.workflow_input.crack_tip_id


def run_fracture_analysis_workflow(
        workflow_input: FractureWorkflowInput,
        progress: MutableMapping[str, Any] | None = None,
        task_id: Any = None,
) -> FractureWorkflowResult:
    """Run the scientific single-nodemap fracture-analysis sequence.

    The runner performs the domain order that must stay CrackPy-owned:
    create the nodemap descriptor, load input data, calculate stresses,
    transform into crack-tip-centered coordinates, construct `FractureAnalysis`,
    and execute it.
    It deliberately does not write text/JSON files, create plots, create
    folders, select multiprocessing policy, or own progress UI.
    """
    nodemap = Nodemap(
        workflow_input.nodemap_name,
        workflow_input.nodemap_folder,
        structure=workflow_input.nodemap_structure,
    )
    data = InputData(nodemap)

    # Stresses and transformed coordinates are preconditions for line integrals
    # and fitting; keeping the order here prevents adapters from reimplementing it.
    data.calc_stresses(workflow_input.material)
    crack_tip_info = workflow_input.crack_tip_info()
    data.transform_data(
        crack_tip_info.crack_tip_x,
        crack_tip_info.crack_tip_y,
        crack_tip_info.crack_tip_angle,
    )

    analysis = FractureAnalysis(
        material=workflow_input.material,
        nodemap=nodemap,
        data=data,
        crack_tip_info=crack_tip_info,
        integral_properties=workflow_input.integral_properties,
        optimization_properties=workflow_input.optimization_properties,
    )
    analysis.run(progress, task_id)
    return FractureWorkflowResult(
        workflow_input=workflow_input,
        nodemap=nodemap,
        data=data,
        crack_tip_info=crack_tip_info,
        analysis=analysis,
    )

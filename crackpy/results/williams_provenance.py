"""Williams-fit adapter for canonical result/provenance envelopes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import crackpy

from crackpy.fracture_analysis.crack_tip import unit_of_williams_coefficients
from crackpy.results.result_data import (
    WILLIAMS_FIT_CONFIGURATION_SCHEMA,
    WILLIAMS_FIT_RESULT_SCHEMA,
    AnalysisRun,
    CrackTipEstimateResult,
    CrackTipFrame,
    DependencyEdge,
    InputRecord,
    MethodMetadata,
    NormalizedConfiguration,
    ResultEnvelope,
    ResultQuantity,
    ResultRecord,
    to_jsonable,
)

WILLIAMS_METHOD_ID = "crackpy.fracture.williams_fit"
CRACK_TIP_IMPORT_METHOD_ID = "crackpy.crack_tip.manual_import"
WILLIAMS_IMPLEMENTATION_REF = "crackpy.fracture_analysis.analysis.FractureAnalysis._run_williams_optimization"


def _analysis_stem(analysis: Any) -> str:
    return Path(str(getattr(analysis, "nodemap_file", "unknown_input"))).stem or "unknown_input"


def _source_metadata(data: Any) -> dict[str, Any]:
    mapping = {
        "force": "force_N",
        "cycles": "cycles",
        "displacement": "displacement_mm",
        "potential": "potential_V",
        "cracklength": "cracklength_dcpd_mm",
        "time": "timestamp_s",
    }
    metadata: dict[str, Any] = {}
    for attr, key in mapping.items():
        value = getattr(data, attr, None)
        if value is not None:
            metadata[key] = value
    return metadata


def _material_parameters(material: Any) -> dict[str, Any]:
    return {
        "name": getattr(material, "name", None),
        "E_MPa": getattr(material, "E", None),
        "nu_xy": getattr(material, "nu_xy", None),
        "sig_yield_MPa": getattr(material, "sig_yield", None),
        "plane_strain": getattr(material, "plane_strain", None),
        "G_MPa": getattr(material, "G", None),
        "kappa": getattr(material, "kappa", None),
    }


def _optimization_parameters(options: Any) -> dict[str, Any]:
    return {
        "angle_gap_deg": getattr(options, "angle_gap", None),
        "min_radius_mm": getattr(options, "min_radius", None),
        "max_radius_mm": getattr(options, "max_radius", None),
        "tick_size_mm": getattr(options, "tick_size", None),
        "terms": list(getattr(options, "terms", []) or []),
    }


def _parameter_origins(options: Any) -> dict[str, str]:
    return {
        "material": "analysis object",
        "crack_tip_frame": "analysis crack_tip",
        "angle_gap_deg": "resolved optimization property",
        "min_radius_mm": "resolved optimization property",
        "max_radius_mm": "resolved optimization property",
        "tick_size_mm": "resolved optimization property",
        "terms": "resolved optimization property",
    }


def _quantity(
    result_id: str,
    symbol: str,
    description: str,
    value: Any,
    unit: str,
    aliases: list[str],
) -> ResultQuantity:
    return ResultQuantity(
        quantity_id=f"quantity:{result_id}:{symbol}",
        result_id=result_id,
        symbol=symbol,
        description=description,
        value=to_jsonable(value),
        unit=unit,
        method_id=WILLIAMS_METHOD_ID,
        legacy_aliases=aliases,
    )


def _williams_quantities(analysis: Any, result_id: str) -> list[ResultQuantity]:
    if getattr(analysis, "williams_fit_res", None) is None:
        raise ValueError("Williams fit results are missing; run Williams optimization before building provenance.")

    fit_res = analysis.williams_fit_res
    quantities = [
        _quantity(
            result_id,
            "error_xy",
            "Williams fit residual for in-plane displacement components.",
            fit_res["Error_xy"],
            "1",
            ["Williams_fit_results.error_xy", "Error_xy"],
        ),
        _quantity(
            result_id,
            "error_z",
            "Williams fit residual for out-of-plane displacement component.",
            fit_res["Error_z"],
            "1",
            ["Williams_fit_results.error_z", "Error_z"],
        ),
        _quantity(
            result_id,
            "K_I",
            "Mode I stress intensity factor derived from Williams coefficient a_1.",
            fit_res["K_I"],
            "MPa*m^{1/2}",
            ["Williams_fit_results.K_I"],
        ),
        _quantity(
            result_id,
            "K_II",
            "Mode II stress intensity factor derived from Williams coefficient b_1.",
            fit_res["K_II"],
            "MPa*m^{1/2}",
            ["Williams_fit_results.K_II"],
        ),
        _quantity(
            result_id,
            "K_III",
            "Mode III stress intensity factor derived from Williams coefficient c_1.",
            fit_res["K_III"],
            "MPa*m^{1/2}",
            ["Williams_fit_results.K_III"],
        ),
        _quantity(
            result_id,
            "T",
            "T-stress derived from Williams coefficient a_2.",
            fit_res["T"],
            "MPa",
            ["Williams_fit_results.T"],
        ),
    ]

    for family, values in (
        ("a", getattr(analysis, "williams_fit_a_n", {}) or {}),
        ("b", getattr(analysis, "williams_fit_b_n", {}) or {}),
        ("c", getattr(analysis, "williams_fit_c_n", {}) or {}),
    ):
        for term, value in values.items():
            symbol = f"{family}_{term}"
            quantities.append(
                _quantity(
                    result_id,
                    symbol,
                    f"Williams coefficient {symbol}.",
                    value,
                    unit_of_williams_coefficients(term),
                    [f"Williams_fit_results.{symbol}"],
                )
            )
    return quantities


def build_williams_fit_envelope(
    analysis: Any,
    *,
    crackpy_version: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> ResultEnvelope:
    """Build the first-slice Williams-fit result/provenance envelope."""
    stem = _analysis_stem(analysis)
    side = getattr(analysis.crack_tip, "left_or_right", None) or "unknown_side"

    input_id = f"input:{stem}"
    frame_id = f"crack_tip_frame:{stem}:{side}"
    tip_id = f"crack_tip:{stem}:{side}"
    estimate_id = f"crack_tip_estimate:{stem}:{side}"

    result_parameters = {
        "material": _material_parameters(analysis.material),
        "optimization": _optimization_parameters(analysis.optimization_properties),
        "crack_tip_frame": {
            "origin_mm": {
                "x": getattr(analysis.crack_tip, "crack_tip_x", None),
                "y": getattr(analysis.crack_tip, "crack_tip_y", None),
            },
            "angle_deg": getattr(analysis.crack_tip, "crack_tip_angle", None),
            "compatibility_side": getattr(analysis.crack_tip, "left_or_right", None),
        },
    }
    parameter_origins = _parameter_origins(analysis.optimization_properties)
    provisional_configuration = NormalizedConfiguration.create(
        configuration_id="configuration:williams_fit:pending",
        schema_version=WILLIAMS_FIT_CONFIGURATION_SCHEMA,
        result_parameters=result_parameters,
        parameter_origins=parameter_origins,
        adapter_policy={"legacy_alias_scope": "Williams_fit_results"},
    )
    short_hash = provisional_configuration.parameter_hash.removeprefix("sha256:")[:12]
    configuration = NormalizedConfiguration.create(
        configuration_id=f"configuration:williams_fit:{short_hash}",
        schema_version=WILLIAMS_FIT_CONFIGURATION_SCHEMA,
        result_parameters=result_parameters,
        parameter_origins=parameter_origins,
        adapter_policy={"legacy_alias_scope": "Williams_fit_results"},
    )

    run_id = f"run:williams_fit:{stem}:{side}:{short_hash}"
    result_id = f"result:williams_fit:{stem}:{side}:{short_hash}"

    input_record = InputRecord(
        input_id=input_id,
        data_ref=str(getattr(analysis, "nodemap_file", "")),
        source_metadata=_source_metadata(analysis.data),
        source_label=stem,
    )
    method = MethodMetadata(
        method_id=WILLIAMS_METHOD_ID,
        display_name="Williams Fit",
        kind="analysis",
        method_revision="1",
        implementation_ref=WILLIAMS_IMPLEMENTATION_REF,
        aliases=["Williams_fit_results"],
        references=[],
    )
    import_method = MethodMetadata(
        method_id=CRACK_TIP_IMPORT_METHOD_ID,
        display_name="Manual Crack-Tip Import",
        kind="crack_tip_estimate",
        method_revision="1",
        implementation_ref="crackpy.input.crack_tip_info.CrackTipInfo",
        aliases=["crack_info_by_nodemap.txt"],
        references=[],
    )
    frame = CrackTipFrame(
        frame_id=frame_id,
        tip_id=tip_id,
        origin_mm={
            "x": getattr(analysis.crack_tip, "crack_tip_x", None),
            "y": getattr(analysis.crack_tip, "crack_tip_y", None),
        },
        angle_deg=getattr(analysis.crack_tip, "crack_tip_angle", None),
        compatibility_side=getattr(analysis.crack_tip, "left_or_right", None),
    )
    estimate = CrackTipEstimateResult(
        estimate_id=estimate_id,
        input_id=input_id,
        method_id=CRACK_TIP_IMPORT_METHOD_ID,
        configuration_id=configuration.configuration_id,
        frame_id=frame_id,
        source="manual import",
        observed_mm=frame.origin_mm,
        corrected_mm=frame.origin_mm,
        correction_delta_mm={"x": 0.0, "y": 0.0},
    )
    run = AnalysisRun(
        run_id=run_id,
        method_id=WILLIAMS_METHOD_ID,
        method_revision="1",
        input_ids=[input_id],
        configuration_id=configuration.configuration_id,
        parameter_hash=configuration.parameter_hash,
        dependencies=[
            DependencyEdge(run_id, input_id, "used_input", "InputRecord"),
            DependencyEdge(run_id, configuration.configuration_id, "used_configuration", "NormalizedConfiguration"),
            DependencyEdge(run_id, estimate_id, "used_crack_tip_estimate", "CrackTipEstimateResult"),
            DependencyEdge(run_id, frame_id, "used_crack_tip_frame", "CrackTipFrame"),
        ],
        crackpy_version=crackpy_version or getattr(crackpy, "__version__", "unknown"),
        started_at=started_at,
        completed_at=completed_at,
    )
    result = ResultRecord(
        result_id=result_id,
        run_id=run_id,
        result_schema_version=WILLIAMS_FIT_RESULT_SCHEMA,
        quantities=_williams_quantities(analysis, result_id),
        artifacts=[],
    )

    return ResultEnvelope(
        input_records=[input_record],
        methods=[method, import_method],
        configurations=[configuration],
        crack_tip_frames=[frame],
        crack_tip_estimates=[estimate],
        analysis_runs=[run],
        results=[result],
    )

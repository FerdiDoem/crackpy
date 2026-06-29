from __future__ import annotations

import csv
import json
import math
import re
from collections import OrderedDict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "docs" / "inspection" / "crackpy-lab-prototype"
ASSET_DIR = OUT_DIR / "assets"

NODemap_DIR = ROOT / "test_data" / "crack_detection" / "Nodemaps"
CRACK_INFO = ROOT / "test_data" / "crack_info_by_nodemap.txt"
RESULTS_CSV = ROOT / "test_data" / "fracture_analysis" / "results_auto_integral_probs.csv"
RESULT_TEXT_DIR = ROOT / "test_data" / "fracture_analysis" / "txt-files"
GRAPH_JSON = (
    ROOT
    / ".scratch"
    / "williams-export-proof"
    / "File_F_10000.0_a_0.5_B_200.0_H_200.0_right_Output_williams_fit_graph.json"
)
ENVELOPE_JSON = (
    ROOT
    / ".scratch"
    / "williams-export-proof"
    / "File_F_10000.0_a_0.5_B_200.0_H_200.0_right_Output_williams_fit_envelope.json"
)
GRAPH_ARTIFACT_SPECS = [
    {
        "id": "williams-proof-export",
        "label": "Williams proof export",
        "method": "Williams fit",
        "path": GRAPH_JSON,
        "scope": "separate Williams proof export, not the selected Dummy2 fixture frame graph",
    },
    {
        "id": "method-fit-williams",
        "label": "Method-fit demo Williams graph",
        "method": "Williams fit",
        "path": ROOT / ".scratch" / "method_fit_usage_demo" / "method_fit_demo_williams_williams_fit_graph.json",
        "scope": "separate method-fit Williams graph artifact produced by the current method demo",
    },
    {
        "id": "method-fit-cjp",
        "label": "Method-fit demo CJP graph",
        "method": "CJP fit",
        "path": ROOT / ".scratch" / "method_fit_usage_demo" / "method_fit_demo_cjp_cjp_fit_graph.json",
        "scope": "separate method-fit CJP graph artifact produced by the current method demo",
    },
]


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def frame_number(filename: str) -> int:
    match = re.search(r"_(\d+)_(?:left|right)_Output\.txt$", filename)
    if match:
        return int(match.group(1))
    match = re.search(r"_(\d+)\.txt$", filename)
    return int(match.group(1)) if match else 0


def source_nodemap_name(output_filename: str) -> str:
    return output_filename.replace("_left_Output.txt", ".txt").replace("_right_Output.txt", ".txt")


def load_crack_info() -> dict[tuple[str, str], dict[str, float | str]]:
    rows: dict[tuple[str, str], dict[str, float | str]] = {}
    with CRACK_INFO.open(encoding="utf-8", errors="ignore", newline="") as handle:
      reader = csv.reader(handle)
      header = next(reader)
      fields = [field.strip() for field in header]
      for raw in reader:
          if not raw or len(raw) < len(fields):
              continue
          row = {fields[index]: raw[index].strip() for index in range(len(fields))}
          key = (row["Filename"], row["Side"])
          rows[key] = {
              "x": safe_float(row["Crack Tip x [mm]"]),
              "y": safe_float(row["Crack Tip y [mm]"]),
              "angle": safe_float(row["Crack Angle"]),
              "side": row["Side"],
          }
    return rows


def metric(row: dict[str, str], label: str, method: str, column: str, unit: str) -> dict[str, object] | None:
    value = safe_float(row.get(column))
    if value is None:
        return None
    return {
        "label": label,
        "methodSource": method,
        "value": value,
        "unit": unit,
        "sourceColumn": column,
    }


def metrics_from_row(row: dict[str, str]) -> list[dict[str, object]]:
    specs = [
        ("K_F", "CJP model", "CJP_results_K_F", "MPa*m^{1/2}"),
        ("K_R", "CJP model", "CJP_results_K_R", "MPa*m^{1/2}"),
        ("K_S", "CJP model", "CJP_results_K_S", "MPa*m^{1/2}"),
        ("K_II", "CJP model", "CJP_results_K_II", "MPa*m^{1/2}"),
        ("T", "CJP model", "CJP_results_T", "MPa"),
        ("Error", "CJP model", "CJP_results_Error", "1"),
        ("K_I", "Williams fit", "Williams_fit_results_K_I", "MPa*m^{1/2}"),
        ("K_II", "Williams fit", "Williams_fit_results_K_II", "MPa*m^{1/2}"),
        ("K_III", "Williams fit", "Williams_fit_results_K_III", "MPa*m^{1/2}"),
        ("T", "Williams fit", "Williams_fit_results_T", "MPa"),
        ("Error_xy", "Williams fit", "Williams_fit_results_Error_xy", "1"),
        ("Error_z", "Williams fit", "Williams_fit_results_Error_z", "1"),
        ("a_-1", "Williams fit", "Williams_fit_results_a_-1", "MPa*mm^{3/2}"),
        ("a_1", "Williams fit", "Williams_fit_results_a_1", "MPa*mm^{1/2}"),
        ("a_2", "Williams fit", "Williams_fit_results_a_2", "MPa"),
        ("b_1", "Williams fit", "Williams_fit_results_b_1", "MPa*mm^{1/2}"),
        ("J", "J-integral", "SIFs_integral_J_mean", "N/mm"),
        ("K_J", "J-integral", "SIFs_integral_K_J_mean", "MPa*m^{1/2}"),
        ("K_I", "Interaction integral", "SIFs_integral_K_I_interac_mean", "MPa*m^{1/2}"),
        ("K_II", "Interaction integral", "SIFs_integral_K_II_interac_mean", "MPa*m^{1/2}"),
        ("T", "Interaction integral", "SIFs_integral_T_interac_mean", "MPa"),
        ("K_I", "Bueckner-Chen", "SIFs_integral_K_I_Chen_mean", "MPa*m^{1/2}"),
        ("K_II", "Bueckner-Chen", "SIFs_integral_K_II_Chen_mean", "MPa*m^{1/2}"),
        ("T", "Bueckner-Chen", "SIFs_integral_T_Chen_mean", "MPa"),
        ("a_1", "Bueckner-Chen", "Bueckner_Chen_integral_a_1_mean", "MPa*mm^{1/2}"),
        ("a_2", "Bueckner-Chen", "Bueckner_Chen_integral_a_2_mean", "MPa"),
        ("b_1", "Bueckner-Chen", "Bueckner_Chen_integral_b_1_mean", "MPa*mm^{1/2}"),
    ]
    values = [metric(row, *spec) for spec in specs]
    return [value for value in values if value is not None]


def value_from_row(row: dict[str, str], column: str) -> float | None:
    return safe_float(row.get(column))


def method_evidence_from_row(row: dict[str, str]) -> dict[str, list[dict[str, object]]]:
    williams_terms = []
    for family in ("a", "b", "c"):
        for order in range(-3, 6):
            column = f"Williams_fit_results_{family}_{order}"
            value = value_from_row(row, column)
            if value is None:
                continue
            williams_terms.append({
                "family": f"{family}_n",
                "term": f"{family}_{order}",
                "order": order,
                "value": value,
                "unit": "mixed Williams units",
                "sourceColumn": column,
            })

    integral_specs = [
        ("J", "SIFs_integral_J", "N/mm"),
        ("K_J", "SIFs_integral_K_J", "MPa*m^{1/2}"),
        ("K_I interaction", "SIFs_integral_K_I_interac", "MPa*m^{1/2}"),
        ("K_II interaction", "SIFs_integral_K_II_interac", "MPa*m^{1/2}"),
        ("T interaction", "SIFs_integral_T_interac", "MPa"),
        ("K_I Bueckner-Chen", "SIFs_integral_K_I_Chen", "MPa*m^{1/2}"),
        ("K_II Bueckner-Chen", "SIFs_integral_K_II_Chen", "MPa*m^{1/2}"),
        ("T Bueckner-Chen", "SIFs_integral_T_Chen", "MPa"),
    ]
    integral_summary = []
    for label, prefix, unit in integral_specs:
        values = {
            "mean": value_from_row(row, f"{prefix}_mean"),
            "median": value_from_row(row, f"{prefix}_median"),
            "mean_wo_outliers": value_from_row(row, f"{prefix}_mean_wo_outliers"),
        }
        if any(value is not None for value in values.values()):
            integral_summary.append({
                "label": label,
                "unit": unit,
                **values,
                "sourcePrefix": prefix,
            })

    path_specs = [
        ("J", "Path_SIFs_J", "N/mm"),
        ("K_J", "Path_SIFs_K_J", "MPa*m^{1/2}"),
        ("K_I", "Path_SIFs_K_I", "MPa*m^{1/2}"),
        ("K_II", "Path_SIFs_K_II", "MPa*m^{1/2}"),
        ("T interaction", "Path_SIFs_T_Int", "MPa"),
        ("T Bueckner-Chen", "Path_SIFs_T_Chen", "MPa"),
    ]
    path_stability = []
    for label, prefix, unit in path_specs:
        values = {
            "mean": value_from_row(row, f"{prefix}_mean"),
            "median": value_from_row(row, f"{prefix}_median"),
            "q10": value_from_row(row, f"{prefix}_quantile10"),
            "q90": value_from_row(row, f"{prefix}_quantile90"),
            "minimum": value_from_row(row, f"{prefix}_min"),
            "maximum": value_from_row(row, f"{prefix}_max"),
        }
        if any(value is not None for value in values.values()):
            path_stability.append({
                "label": label,
                "unit": unit,
                **values,
                "sourcePrefix": prefix,
            })

    return {
        "williamsTerms": williams_terms,
        "integralSummary": integral_summary,
        "pathStability": path_stability,
    }


def load_result_rows() -> list[dict[str, str]]:
    with RESULTS_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_graph_artifact(spec: dict[str, object]) -> dict[str, object] | None:
    graph_path = spec["path"]
    if not isinstance(graph_path, Path) or not graph_path.exists():
        return None

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = graph.get("nodes", [])
    node_by_id = {node["id"]: node for node in nodes}
    ordered_types = []
    details: dict[str, dict[str, object]] = {}
    colors = {
        "InputRecord": "#155e75",
        "MethodMetadata": "#4338ca",
        "NormalizedConfiguration": "#7c2d12",
        "CrackTipFrame": "#166534",
        "CrackTipEstimateResult": "#166534",
        "AnalysisRun": "#1d4ed8",
        "ResultRecord": "#6d28d9",
        "ResultQuantity": "#b45309",
        "ArtifactRef": "#374151",
    }
    method_label = str(spec["method"])
    roles = {
        "InputRecord": f"Actual input record from the exported {method_label} visualization graph.",
        "MethodMetadata": f"Actual method identity node from the exported {method_label} visualization graph.",
        "NormalizedConfiguration": f"Actual resolved {method_label} configuration and hashes from the exported graph.",
        "CrackTipFrame": "Actual crack-tip frame node linking origin, angle, and side.",
        "CrackTipEstimateResult": f"Actual crack-tip estimate dependency consumed by the {method_label} run.",
        "AnalysisRun": f"Actual {method_label} analysis activity node with method, input, configuration, and crack-tip dependencies.",
        "ResultRecord": "Actual generated result envelope node.",
        "ResultQuantity": "Actual scalar quantity node generated from the result envelope.",
        "ArtifactRef": "Exported artifact reference node.",
    }
    surfaces = {
        "InputRecord": "nodemap input",
        "MethodMetadata": "method registry",
        "NormalizedConfiguration": "resolved config",
        "CrackTipFrame": "local frame",
        "CrackTipEstimateResult": "tip estimate",
        "AnalysisRun": "method run",
        "ResultRecord": "result envelope",
        "ResultQuantity": "scalar quantity",
        "ArtifactRef": "exported artifact",
    }
    for node in nodes:
        node_type = node["type"]
        if node_type not in ordered_types:
            ordered_types.append(node_type)
            details[node_type] = {
                "color": colors.get(node_type, "#374151"),
                "surface": surfaces.get(node_type, node_type),
                "role": roles.get(node_type, "Actual node type from the exported provenance graph."),
                "keyFields": sorted((node.get("data") or {}).keys()),
                "example": node["id"],
                "actualNodeCount": sum(1 for candidate in nodes if candidate["type"] == node_type),
            }

    type_edges: OrderedDict[tuple[str, str, str], dict[str, str]] = OrderedDict()
    for edge in graph.get("edges", []):
        source = node_by_id.get(edge.get("source"))
        target = node_by_id.get(edge.get("target"))
        if not source or not target:
            continue
        key = (source["type"], target["type"], edge.get("role", edge.get("label", "")))
        type_edges.setdefault(key, {
            "from": source["type"],
            "to": target["type"],
            "label": edge.get("label", edge.get("role", "")),
            "role": edge.get("role", ""),
        })

    summary = {
        "id": str(spec["id"]),
        "label": str(spec["label"]),
        "method": method_label,
        "path": str(graph_path.relative_to(ROOT)).replace("\\", "/"),
        "nodeCount": len(nodes),
        "edgeCount": len(graph.get("edges", [])),
        "types": ordered_types,
        "fixture": graph_path.stem,
        "scope": str(spec["scope"]),
    }
    return {
        "id": str(spec["id"]),
        "label": str(spec["label"]),
        "method": method_label,
        "path": summary["path"],
        "nodeCount": summary["nodeCount"],
        "edgeCount": summary["edgeCount"],
        "nodeTypes": ordered_types,
        "edges": list(type_edges.values()),
        "nodeDetails": details,
        "summary": summary,
    }


def load_graph_artifacts() -> list[dict[str, object]]:
    artifacts = [
        artifact
        for spec in GRAPH_ARTIFACT_SPECS
        if (artifact := load_graph_artifact(spec)) is not None
    ]
    return artifacts


def generate_nodemap_asset() -> dict[str, object]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    nodemap_path = NODemap_DIR / "Dummy2_WPXXX_DummyVersuch_2_dic_results_1_52.txt"
    raw = np.genfromtxt(nodemap_path, delimiter=";", comments="#", encoding="windows-1252")
    data = raw[~np.isnan(raw).any(axis=1)]
    x = data[:, 1]
    y = data[:, 2]
    fields = {
        "eps_eqv": data[:, 10] if data.shape[1] > 10 else np.hypot(data[:, 7], data[:, 8]),
        "disp_y": data[:, 5],
        "eps_xy": data[:, 9],
    }
    colormaps = ["turbo", "viridis", "cividis", "magma"]

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        field_assets = {}
        for field_name, values in fields.items():
            field_assets[field_name] = {}
            for colormap in colormaps:
                fig, ax = plt.subplots(figsize=(7.44, 4.52), dpi=100)
                fig.subplots_adjust(0, 0, 1, 1)
                ax.set_position([0, 0, 1, 1])
                fig.patch.set_facecolor("#111719")
                ax.set_facecolor("#111719")
                ax.tricontourf(x, y, values, levels=32, cmap=colormap)
                ax.set_xlim(float(np.nanmin(x)), float(np.nanmax(x)))
                ax.set_ylim(float(np.nanmin(y)), float(np.nanmax(y)))
                ax.set_aspect("equal", adjustable="box")
                ax.set_axis_off()
                filename = "nodemap-field.png" if field_name == "eps_eqv" and colormap == "turbo" else f"nodemap-field-{field_name}-{colormap}.png"
                asset_path = ASSET_DIR / filename
                fig.savefig(asset_path, facecolor=fig.get_facecolor(), edgecolor="none", pad_inches=0)
                field_assets[field_name][colormap] = f"assets/{filename}"
                plt.close(fig)
    except Exception as exc:  # pragma: no cover - fallback for stripped environments
        raise RuntimeError(f"Could not generate actual nodemap asset from {nodemap_path}: {exc}") from exc

    field_stats = {
        field_name: {
            "min": float(np.nanmin(values)),
            "max": float(np.nanmax(values)),
            "mean": float(np.nanmean(values)),
            "std": float(np.nanstd(values)),
            "p01": float(np.nanpercentile(values, 1)),
            "p99": float(np.nanpercentile(values, 99)),
        }
        for field_name, values in fields.items()
    }
    point_columns = ["x", "y", "eps_eqv", "disp_y", "eps_xy"]
    point_rows = np.column_stack([x, y, fields["eps_eqv"], fields["disp_y"], fields["eps_xy"]])
    rounded_rows = [
        [round(float(value), 6) for value in row]
        for row in point_rows
    ]

    return {
        "asset": "assets/nodemap-field.png",
        "fieldAssets": field_assets,
        "fieldStats": field_stats,
        "source": str(nodemap_path.relative_to(ROOT)).replace("\\", "/"),
        "field": "eps_eqv",
        "defaultColormap": "turbo",
        "colormaps": colormaps,
        "pointCount": int(len(data)),
        "pointData": {
            "columns": point_columns,
            "rows": rounded_rows,
        },
        "xRange_mm": [float(np.nanmin(x)), float(np.nanmax(x))],
        "yRange_mm": [float(np.nanmin(y)), float(np.nanmax(y))],
    }


def build_frames(rows: list[dict[str, str]], crack_info: dict[tuple[str, str], dict[str, float | str]]) -> dict[str, list[dict[str, object]]]:
    grouped = {"left": [], "right": []}
    for row in rows:
        filename = row["filename"]
        side = "left" if "_left_" in filename else "right"
        nodemap = source_nodemap_name(filename)
        imported = crack_info.get((nodemap, side), {})
        x = safe_float(row.get("Crack_tip_x"))
        y = safe_float(row.get("Crack_tip_y"))
        angle = safe_float(row.get("Crack_tip_phi"))
        observed_x = imported.get("x", x)
        observed_y = imported.get("y", y)
        observed_angle = imported.get("angle", angle)
        dx = (x - observed_x) if x is not None and isinstance(observed_x, float) else 0.0
        dy = (y - observed_y) if y is not None and isinstance(observed_y, float) else 0.0
        metrics = metrics_from_row(row)
        residual = next(
            (
                value["value"]
                for value in metrics
                if value["label"] in {"Error_xy", "Error_z"} and value["methodSource"] == "Williams fit"
            ),
            None,
        )
        frame = {
            "id": filename.replace("_Output.txt", ""),
            "experimentPresetId": f"dummy2-dic-{side}",
            "label": f"Frame {frame_number(filename)} {side}",
            "imageName": nodemap,
            "sourceKind": "actual CrackPy fixture output",
            "sourcePaths": {
                "nodemap": str((NODemap_DIR / nodemap).relative_to(ROOT)).replace("\\", "/"),
                "crackInfo": str(CRACK_INFO.relative_to(ROOT)).replace("\\", "/"),
                "resultCsv": str(RESULTS_CSV.relative_to(ROOT)).replace("\\", "/"),
                "resultText": str((RESULT_TEXT_DIR / filename).relative_to(ROOT)).replace("\\", "/"),
            },
            "load": safe_float(row.get("Force")),
            "cycles": safe_float(row.get("Cycles")),
            "displacement": safe_float(row.get("Displacement")),
            "crackTipEstimate": {
                "label": "crack-tip estimate",
                "sourceMethodId": "crack_info_by_nodemap.txt",
                "x": observed_x,
                "y": observed_y,
                "angle": observed_angle,
                "confidence": None,
            },
            "correctedCrackTipEstimate": {
                "label": "Crack_tip_x/y from fracture-analysis output",
                "sourceMethodId": "FractureAnalysis output",
                "x": x,
                "y": y,
                "angle": angle,
                "confidence": None,
            },
            "correctionDelta": {
                "label": "output minus crack_info_by_nodemap",
                "sourceMethodId": "fixture comparison",
                "dx": dx,
                "dy": dy,
                "magnitude": float(math.hypot(dx, dy)),
                "units": "mm",
            },
            "metrics": metrics,
            "methodEvidence": method_evidence_from_row(row),
            "residual": residual,
            "provenanceStepIds": ["load-frame", "dic-nodemap", "estimate-tip", "run-fracture-analysis", "read-output-csv", "read-provenance-graph"],
            "warningIds": ["w-actual-fixture", "w-left-right-side" if side == "left" else "w-actual-fixture"],
        }
        grouped[side].append(frame)
    for side in grouped:
        grouped[side].sort(key=lambda item: int(item["label"].split()[1]))
    return grouped


def build_payload() -> dict[str, object]:
    crack_info = load_crack_info()
    rows = load_result_rows()
    frames_by_side = build_frames(rows, crack_info)
    nodemap_asset = generate_nodemap_asset()
    graph_artifacts = load_graph_artifacts()
    primary_graph = graph_artifacts[0] if graph_artifacts else {}
    graph_types = primary_graph.get("nodeTypes", [])
    graph_edges = primary_graph.get("edges", [])
    graph_details = primary_graph.get("nodeDetails", {})
    graph_summary = primary_graph.get("summary", {})

    analysis_methods = [
        {
            "id": "crack-info-import",
            "label": "crack_info_by_nodemap import",
            "methodSource": "actual test_data/crack_info_by_nodemap.txt",
            "outputLabels": ["crack-tip estimate", "side", "angle"],
            "units": {"x": "mm", "y": "mm", "angle": "deg"},
        },
        {
            "id": "fracture-analysis-output",
            "label": "FractureAnalysis output reader",
            "methodSource": "actual results_auto_integral_probs.csv and legacy text outputs",
            "outputLabels": ["CJP", "Williams", "SIF integrals", "Bueckner-Chen", "Path summaries"],
            "units": {"K": "MPa*m^{1/2}", "J": "N/mm", "T": "MPa"},
        },
        {
            "id": "williams-provenance-export",
            "label": "Williams provenance graph export",
            "methodSource": "actual .scratch/williams-export-proof graph JSON",
            "outputLabels": ["InputRecord", "MethodMetadata", "AnalysisRun", "ResultQuantity"],
            "units": {},
        },
    ]
    if any(artifact["id"] == "method-fit-cjp" for artifact in graph_artifacts):
        analysis_methods.append({
            "id": "cjp-provenance-export",
            "label": "CJP provenance graph export",
            "methodSource": "actual .scratch/method_fit_usage_demo graph JSON",
            "outputLabels": ["InputRecord", "MethodMetadata", "AnalysisRun", "ResultQuantity"],
            "units": {},
        })
    graph_source_paths = [artifact["path"] for artifact in graph_artifacts]

    return {
        "schemaVersion": "0.2.0",
        "generatedAt": "2026-06-13T00:00:00Z",
        "dataPolicy": "actual CrackPy repository fixtures; no hand-authored numerical result rows",
        "units": {
            "length": "mm",
            "force": "N",
            "displacement": "mm",
            "stressIntensity": "MPa*m^{1/2}",
            "energyReleaseRate": "N/mm",
            "strain": "%",
            "angle": "deg",
        },
        "actualDataSources": [
            str(RESULTS_CSV.relative_to(ROOT)).replace("\\", "/"),
            str(CRACK_INFO.relative_to(ROOT)).replace("\\", "/"),
            str(NODemap_DIR.relative_to(ROOT)).replace("\\", "/"),
            *graph_source_paths,
            str(ENVELOPE_JSON.relative_to(ROOT)).replace("\\", "/") if ENVELOPE_JSON.exists() else None,
        ],
        "visualizationConfig": {
            "nodemapBaseLayer": {
                **nodemap_asset,
                "fields": ["eps_eqv", "disp_x", "disp_y", "eps_x", "eps_y", "eps_xy"],
                "note": "Generated from an actual nodemap fixture; overlays are drawn above it.",
            },
            "lineIntegralDefaults": {
                "number_of_paths": 9,
                "integral_tick_size_mm": 0.01,
                "number_of_nodes": 100,
                "mask_tolerance": 2,
                "buckner_williams_terms": [1, 2, 3, 4, 5],
            },
            "crackDetectionDefaults": {
                "source": "crackpy.crack_detection.pipeline.pipeline.CrackDetectionSetup",
                "detection_window_size_mm": 40,
                "detection_input_resolution_px": 256,
                "angle_detection_radius_mm": 10,
                "note": "Shown as setup geometry only; no inferred DIC contour is drawn for crack detection.",
            },
            "williamsDefaults": {
                "angle_gap_deg": 20,
                "min_radius_mm": 5,
                "max_radius_mm": 10,
                "tick_size_mm": 0.01,
                "terms": [-1, 1, 2, 3, 4, 5],
                "displayModes": ["aggregate", "a_1", "b_1", "a_2", "higher_terms"],
            },
            "plasticZoneApproximation": {
                "label": "Irwin first-order forward plastic-zone estimate",
                "formula": "r_y = 1/(2*pi) * (K_I / sigma_y)^2 for plane stress; first-order plane-strain view uses 1/(6*pi).",
                "defaultYieldStrength_MPa": 350,
                "defaultConstraint": "plane stress",
                "warning": "Visualization only; CrackPy does not currently expose a dedicated PlasticZone result object.",
            },
        },
        "graphNodeTypes": graph_types,
        "graphEdges": graph_edges,
        "graphNodeDetails": graph_details,
        "actualGraphSummary": graph_summary,
        "graphArtifacts": graph_artifacts,
        "experimentPresets": [
            {
                "id": f"dummy2-dic-{side}",
                "label": f"Dummy2 DIC fracture-analysis fixture ({side} crack)",
                "specimen": {
                    "geometry": "DIC Dummy2 fixture",
                    "material": "fixture output material context",
                    "thickness": None,
                    "width": None,
                    "notchLength": None,
                    "sideGrooves": None,
                },
                "loading": {
                    "load": frames[0]["load"],
                    "cycle": frames[0]["cycles"],
                    "displacement": frames[0]["displacement"],
                },
                "imaging": {
                    "nodemapFolder": str(NODemap_DIR.relative_to(ROOT)).replace("\\", "/"),
                    "fieldAsset": nodemap_asset["asset"],
                    "fieldAssetSource": nodemap_asset["source"],
                },
                "defaultAnalysisMethodIds": ["crack-info-import", "fracture-analysis-output", "williams-provenance-export"],
            }
            for side, frames in frames_by_side.items()
        ],
        "analysisMethods": analysis_methods,
        "resultFrames": [frame for frames in frames_by_side.values() for frame in frames],
        "provenanceSteps": [
            {
                "id": "load-frame",
                "label": "Load actual fixture row",
                "detail": "Frame-level load, cycles, crack tip, and output values are read from results_auto_integral_probs.csv.",
            },
            {
                "id": "dic-nodemap",
                "label": "Load actual DIC nodemap",
                "detail": "The base visualization image is regenerated from test_data/crack_detection/Nodemaps coordinates and eps_eqv values.",
            },
            {
                "id": "estimate-tip",
                "label": "Compare crack_info_by_nodemap estimate",
                "detail": "Imported crack-tip coordinates are compared with the fracture-analysis output tip for the same nodemap and side.",
            },
            {
                "id": "run-fracture-analysis",
                "label": "Read actual FractureAnalysis outputs",
                "detail": "Williams, CJP, SIF/integral, interaction integral, Bueckner-Chen, and path summary values come from current fixture outputs.",
            },
            {
                "id": "read-provenance-graph",
                "label": "Read separate provenance graph artifacts",
                "detail": "Frontend-facing graph nodes and type-level edges are derived from exported graph JSON artifacts under .scratch/williams-export-proof and .scratch/method_fit_usage_demo; these are separate proof artifacts, not the selected Dummy2 frame graph.",
            },
        ],
        "warnings": [
            {
                "id": "w-actual-fixture",
                "severity": "notice",
                "label": "Actual repository fixture",
                "detail": "Displayed values are read from CrackPy test fixture outputs, not generated UI mock data.",
            },
            {
                "id": "w-left-right-side",
                "severity": "notice",
                "label": "Side-specific crack-tip convention",
                "detail": "Left and right fixture outputs share stage numbers but use different crack-tip coordinate conventions.",
            },
        ],
        "tableRows": [],
    }


def main() -> None:
    payload = build_payload()
    data_js = OUT_DIR / "data.js"
    serialized = json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False)
    data_js.write_text(
        "(function () {\n"
        '  "use strict";\n\n'
        f"  window.CrackPyPrototypeData = {serialized};\n"
        "}());\n",
        encoding="utf-8",
    )
    print(f"Wrote {data_js.relative_to(ROOT)}")
    print(f"Actual result frames: {len(payload['resultFrames'])}")
    print(f"Graph node types: {', '.join(payload.get('graphNodeTypes', []))}")


if __name__ == "__main__":
    main()

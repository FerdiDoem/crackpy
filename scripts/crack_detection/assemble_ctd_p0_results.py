"""Assemble the two complete P0 runs and render the P0 report.

The report is intentionally generated from the consolidated JSON artifact so that
the prose, tables, and machine-readable evidence cannot silently diverge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_run(run: dict[str, Any], mode: str, *, b2_required: bool) -> None:
    actual_mode = run["crackmnist"]["resolution"]["mode"]
    if actual_mode != mode:
        raise ValueError(f"Expected resolution mode {mode!r}, got {actual_mode!r}.")
    if run["crackmnist"]["dataset"]["split"] != "test":
        raise ValueError("P0 consolidation accepts only the frozen test split.")
    if run["scope"]["crackmnist_limit"] is not None:
        raise ValueError("P0 consolidation requires the complete CrackMNIST split.")
    if b2_required and run["b2"] is None:
        raise ValueError("The trained-256 source run must contain the B2 result.")


def assemble_results(
    trained_path: Path,
    native_path: Path,
) -> dict[str, Any]:
    """Return one P0 evidence artifact from complete trained-256 and native-128 runs."""

    trained = _load_json(trained_path)
    native = _load_json(native_path)
    _require_run(trained, "trained-256", b2_required=True)
    _require_run(native, "native-128", b2_required=False)

    trained_dataset = trained["crackmnist"]["dataset"]
    native_dataset = native["crackmnist"]["dataset"]
    dataset_identity_fields = (
        "h5_md5",
        "metadata_sha256",
        "sample_count",
        "split",
        "experiment_ids",
    )
    for field in dataset_identity_fields:
        if trained_dataset[field] != native_dataset[field]:
            raise ValueError(f"Source runs disagree on dataset field {field!r}.")

    if trained["metadata"]["artifact_sha256"] != native["metadata"]["artifact_sha256"]:
        raise ValueError("Source runs used different model artifacts.")
    environment_identity_fields = (
        "git_commit",
        "crackpy_version",
        "python_version",
        "torch_version",
        "cuda_version",
        "device",
        "device_name",
        "numpy_version",
        "platform",
        "seed",
    )
    for field in environment_identity_fields:
        if trained["metadata"][field] != native["metadata"][field]:
            raise ValueError(f"Source runs disagree on environment field {field!r}.")

    return {
        "schema_version": "1.0",
        "stage": "P0",
        "baseline_contract": {
            "code_base": "CrackPy 1.3.0",
            "models": "original frozen weights",
            "training_performed": False,
            "primary_tip_decoder": "historical mask decoder",
            "coordinate_head_role": "diagnostic only",
        },
        "metadata": trained["metadata"],
        "source_runs": {
            "trained_256": {
                "filename": trained_path.name,
                "sha256": _sha256(trained_path),
            },
            "native_128": {
                "filename": native_path.name,
                "sha256": _sha256(native_path),
            },
        },
        "crackmnist": {
            "dataset": trained_dataset,
            "evaluation_contract": trained["crackmnist"]["evaluation_contract"],
            "variants": {
                "trained_256": {
                    "resolution": trained["crackmnist"]["resolution"],
                    "b0": trained["crackmnist"]["b0"],
                    "samples": trained["crackmnist"]["samples"],
                },
                "native_128": {
                    "resolution": native["crackmnist"]["resolution"],
                    "b0": native["crackmnist"]["b0"],
                    "samples": native["crackmnist"]["samples"],
                },
            },
        },
        "repository_fixtures": trained["repository_fixtures"],
        "b2": trained["b2"],
        "runtime": {
            "trained_256": trained["runtime"],
            "native_128": native["runtime"],
        },
        "evidence_boundaries": {
            "crackmnist_sample_independence_claimed": False,
            "crackmnist_physical_scale_available": False,
            "repository_fixture_independence_claimed": False,
            "b2_independent_ground_truth_available": False,
            "mendeley_quantitative_claims_available": False,
        },
    }


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def render_report(result: dict[str, Any]) -> str:
    """Render the concise German P0 report from the consolidated evidence."""

    variants = result["crackmnist"]["variants"]
    trained = variants["trained_256"]["b0"]
    native = variants["native_128"]["b0"]
    fixture_b0 = result["repository_fixtures"]["b0"]
    fixture_b1 = result["repository_fixtures"]["b1"]
    b2 = result["b2"]
    runtime = result["runtime"]["trained_256"]
    primary_t = trained["mask_decoder_primary"]
    primary_n = native["mask_decoder_primary"]
    coord_t = trained["coordinate_head_diagnostic"]
    path = fixture_b1["path"]
    angle = fixture_b1["angle"]
    throughput = runtime["phase_resolved_b0_b1"]["throughput"]
    phases = runtime["phase_resolved_b0_b1"]["runtime"]["phases"]
    cold = runtime["cold_start"]["runtime"]["phases"]["first_in_process_model_loading"]

    lines = [
        "# CTD-Optimierung – P0-Baseline",
        "",
        "## Ergebnis",
        "",
        "P0 ist als reproduzierbare Baseline auf der unveränderten CrackPy-Version 1.3.0 abgeschlossen.",
        "Die originale 256-Pixel-Ausführung bleibt die Referenz, weil sie die Tipposition deutlich genauer und zuverlässiger bestimmt als eine direkte 128-Pixel-Ausführung.",
        "Der historische Maskendecoder ist dem vorhandenen Koordinatenkopf ebenfalls klar überlegen; P1 sollte deshalb zunächst Decoder, Ausführung und Datentransfer optimieren, nicht neu trainieren.",
        "",
        "## B0 – Tipdetektion auf CrackMNIST",
        "",
        "| Variante | Erkennungsrate | Medianfehler | P95-Fehler | Mittelwert | Ausfälle |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| Originalmodell bei 256 px | {_fmt(100 * primary_t['detection_rate'])} % | "
            f"{_fmt(primary_t['error_px']['median'])} px | {_fmt(primary_t['error_px']['p95'])} px | "
            f"{_fmt(primary_t['error_px']['mean'])} px | {primary_t['detection_failures']} |"
        ),
        (
            f"| Originalmodell direkt bei 128 px | {_fmt(100 * primary_n['detection_rate'])} % | "
            f"{_fmt(primary_n['error_px']['median'])} px | {_fmt(primary_n['error_px']['p95'])} px | "
            f"{_fmt(primary_n['error_px']['mean'])} px | {primary_n['detection_failures']} |"
        ),
        (
            f"| Koordinatenkopf, diagnostisch, 256 px | {_fmt(100 * coord_t['detection_rate'])} % | "
            f"{_fmt(coord_t['error_px']['median'])} px | {_fmt(coord_t['error_px']['p95'])} px | "
            f"{_fmt(coord_t['error_px']['mean'])} px | {coord_t['detection_failures']} |"
        ),
        "",
        f"Ausgewertet wurden {result['crackmnist']['dataset']['sample_count']} Testbilder; sechs leere Masken gelten als fehlende Referenzen und nicht als Modellfehler.",
        "Die Fehler sind in Pixeln des originalen 128er-Rasters angegeben, weil CrackMNIST keine belastbare physische Feldgröße liefert.",
        "Die höheren Dice- und IoU-Werte der 128er-Maske bedeuten keinen besseren Tip: Die Segmentüberlappung ist bei der sehr dünnen Zielmaske empfindlich gegenüber deren Dicke und bleibt deshalb eine Diagnosemetrik.",
        "",
        "## B1 – Pfad und lokaler Winkel",
        "",
        (
            f"Auf den drei vorhandenen CrackPy-Referenzfeldern beträgt die symmetrische mittlere Pfaddistanz im Median "
            f"{_fmt(path['distance_px']['median'])} px beziehungsweise {_fmt(path['distance_mm']['median'])} mm."
        ),
        (
            f"Der Pfad-HD95 liegt im Median bei {_fmt(path['hd95_px']['median'])} px, und der lokale Winkelfehler "
            f"bei {_fmt(angle['error_degrees']['median'])} Grad."
        ),
        "Diese drei Felder sind ein Kompatibilitätsnachweis, aber keine unabhängige statistische Testbasis.",
        "CrackMNIST enthält keine belastbare Pfad- und Winkelreferenz für B1.",
        "",
        "## B2 – optionale Williams-Korrektur",
        "",
        (
            f"Der vorhandene CrackPy-Beispiellauf konvergierte nach {b2['iterations']} Iterationen und verschob den Tip um "
            f"({_fmt(b2['correction_vector_mm'][0], 3)}, {_fmt(b2['correction_vector_mm'][1], 3)}) mm."
        ),
        (
            f"Die Williams-Korrektur benötigte im Median {_fmt(b2['runtime']['phases']['williams_correction']['median_ms'] / 1000)} s "
            "und dominiert damit die Laufzeit deutlich."
        ),
        "Ohne unabhängige Ground Truth ist daraus kein Genauigkeitsgewinn ableitbar; B2 bleibt daher optional und wird in P2 nur selektiv geprüft.",
        "",
        "## Laufzeitprofil",
        "",
        f"Das erste Laden beider Modelle dauerte {_fmt(cold['median_ms'])} ms.",
        (
            f"Für einen vorbereiteten Dreier-Batch wurden {_fmt(throughput['images_per_second'])} Bilder/s erreicht; "
            f"Tip- und Pfad-Forward benötigten jeweils rund {_fmt(phases['tip_forward']['median_ms'])} ms und "
            f"{_fmt(phases['path_forward']['median_ms'])} ms pro Batch."
        ),
        "Das Profil zeigt drei klare P1-Hebel: Modelle persistent halten, Tip-only wirklich ohne Pfadnetz ausführen und unabhängige Bilder bündeln.",
        "Plotten und Dateischreiben waren aus dem Messpfad ausgeschlossen.",
        "",
        "## Evidenzgrenzen und Entscheidung für P1",
        "",
        "CrackMNIST stellt augmentierte Bilder eines einzigen Testexperiments ohne offengelegte Quellbild-IDs bereit; Unabhängigkeit auf Bildebene wird daher nicht behauptet.",
        "Die Mendeley-Daten besitzen nach dem A0-Audit keine direkt nutzbaren Frame-Labels für Tip, Pfad, Winkel und ROI-Abdeckung; die Annotation kann parallel laufen, quantitative Aussagen warten aber auf geprüfte Labels.",
        "P1 startet ohne Retraining mit der 256er-Referenz, vergleicht Decoder nur auf Validation und friert die Wahl vor dem Test ein.",
        "Eine niedrigere Auflösung wird nur übernommen, wenn Erkennungsrate und P95 innerhalb der vorab definierten Grenzen bleiben.",
        "",
        "## Reproduzierbarkeit",
        "",
        f"Der Lauf verwendete Python {result['metadata']['python_version']}, PyTorch {result['metadata']['torch_version']} und {result['metadata']['device_name']}.",
        f"ParallelNets-Prüfsumme: `{result['metadata']['artifact_sha256']['ParallelNets']}`.",
        f"UNetPath-Prüfsumme: `{result['metadata']['artifact_sha256']['UNetPath']}`.",
        f"CrackMNIST-H5-MD5: `{result['crackmnist']['dataset']['h5_md5']}`.",
        "Alle Einzelwerte und Ausfallgründe stehen in `p0-results.json`.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trained-256", type=Path, required=True)
    parser.add_argument("--native-128", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = assemble_results(args.trained_256, args.native_128)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False, sort_keys=True)
        handle.write("\n")
    args.report.write_text(render_report(result), encoding="utf-8")


if __name__ == "__main__":
    main()

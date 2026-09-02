# CTD P1 – Reproduktionsanleitung

## Zweck

Diese Anleitung reproduziert den vollständigen P1-Lauf auf den originalen CrackPy-1.3.0-Gewichten ohne Training.

## Voraussetzungen

Das Repository muss die originalen Dateien `ParallelNets.pth` und `UNetPath.pth` enthalten.

CrackMNIST 2.0.1 muss mit dem 128-S-Datensatz unter `C:\Users\Admin\.crackmnist` verfügbar sein.

Die erwartete H5-MD5 lautet `3101a618e0837276b1ef4533964fabb3`.

Das P0-Ergebnis unter `docs/ctd-optimization/p0-results.json` ist der unveränderliche Vergleichspunkt.

CUDA ist optional für Funktionsprüfungen, aber für die dokumentierten Laufzeiten erforderlich.

## Vollständiger Lauf

Der folgende Aufruf führt Validation, eingefrorenen Test, Batch-Sweeps und den Dummy2-Interpolationsvergleich aus.

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\benchmark_ctd_p1.py `
  --device cuda:0 `
  --dataset-root C:\Users\Admin\.crackmnist `
  --calibration-batch-size 8 `
  --runtime-warmup-iterations 1 `
  --runtime-measured-iterations 3 `
  --interpolation-warmup-iterations 1 `
  --interpolation-measured-iterations 3 `
  --output .downloads\p1-full.json
```

Der Testsplit beeinflusst weder Decoder noch Confidence-Schwelle.

Er wird ausschließlich zur abschließenden Nichtunterlegenheitsprüfung verwendet.

ParallelNets, CrackMNIST und UNetPath werden gestaffelt gegen die P0-Prüfsummen geprüft.

Ein abweichendes Artefakt beendet den Lauf vor dem jeweils betroffenen wissenschaftlichen Abschnitt.

## Kurzer Kontrolllauf

Der folgende Aufruf prüft denselben Ablauf mit acht Bildern je Split.

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\benchmark_ctd_p1.py `
  --device cuda:0 `
  --dataset-root C:\Users\Admin\.crackmnist `
  --limit 8 `
  --calibration-batch-size 8 `
  --runtime-warmup-iterations 0 `
  --runtime-measured-iterations 1 `
  --interpolation-warmup-iterations 0 `
  --interpolation-measured-iterations 1 `
  --output .downloads\p1-smoke.json
```

Ein Smoke-Lauf ersetzt niemals die vollständigen Genauigkeitsmetriken.

## Fokussierte Tests

```powershell
.\.venv\Scripts\python.exe -m pytest `
  crackpy/tests/test_benchmarking/test_ctd_runtime.py `
  crackpy/tests/test_benchmarking/test_ctd_p1_runtime.py `
  crackpy/tests/test_benchmarking/test_ctd_p1_evaluation.py `
  crackpy/tests/test_benchmarking/test_ctd_metrics.py `
  crackpy/tests/test_benchmarking/test_ctd_decoders.py `
  crackpy/tests/test_benchmarking/test_ctd_calibration.py `
  crackpy/tests/test_benchmarking/test_ctd_baseline.py `
  crackpy/tests/test_benchmarking/test_benchmark_ctd_p1_script.py `
  crackpy/tests/test_crack_detection/test_inference.py `
  crackpy/tests/test_crack_detection/test_data/test_optimized_interpolation.py `
  -q
```

## Erwartete Integritätsmerkmale

`scope.full_split` muss für den vollständigen Lauf `true` sein.

`provenance_verification.all_checks_passed` muss `true` sein.

`decoder_frozen_before_test` muss für alle Auflösungen `true` sein.

`test_recalibration_performed` muss für alle Auflösungen `false` sein.

Alle 16 Einträge unter `runtime.model_sweeps` müssen den Status `completed` besitzen.

Alle acht Interpolationsvarianten müssen Float64-, Float32-, Modell- und Tipparität melden.

Nur `trained_256.resolution_gate.accepted_for_default` darf `true` sein.

## Ergebnisdateien

`docs/ctd-optimization/p1-results.json` ist das kanonische, streng serialisierte P1-Ergebnis.

`docs/ctd-optimization/p1-report.md` enthält Entscheidung und Interpretation.

Das kanonische Ergebnis enthält alle individuellen Validation- und Testdatensätze genau einmal und vermeidet daraus ableitbare Duplikate.

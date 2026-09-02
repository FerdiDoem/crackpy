# CTD P1 Implementation Plan

**Goal:** Die eingefrorenen Originalmodelle von CrackPy 1.3.0 ohne Retraining schneller und robuster ausführen und jede Änderung als Accuracy-Runtime-Pareto gegen P0 bewerten.

**Architecture:** P1 ergänzt einen side-effect-armen Frozen-Inferenzpfad, einen validierungsgebundenen Decodervertrag und eine wiederverwendbare Interpolation pro Frame.
Die historischen Detektoren und Legacy-Fixtures bleiben unverändert und dienen als numerische Kompatibilitätsreferenz.
Kalibrierung verwendet ausschließlich den CrackMNIST-Validierungssplit; der Testsplit wird erst mit eingefrorener Konfiguration ausgewertet.

**Tech Stack:** Python 3.12, PyTorch, NumPy, SciPy, scikit-image, pytest, CrackMNIST 2.0.1 und CrackPy 1.3.0.

---

## Task 1: P1-Vertrag und persistente Frozen-Inferenz

**Files:**

- Create: `crackpy/crack_detection/inference.py`
- Create: `crackpy/tests/test_crack_detection/test_inference.py`
- Extend: `crackpy/benchmarking/__init__.py`

1. Schreibe fehlschlagende Tests dafür, dass jedes Modell genau einmal eingefroren, auf das Zielgerät verschoben und in den Auswertungsmodus gesetzt wird.
2. Teste, dass der gesamte Forward-Aufruf unter `torch.inference_mode()` läuft und ein optional fehlendes Pfadmodell keinen Pfadaufruf erzeugt.
3. Implementiere `FrozenCtdInference` mit einem kleinen Batch-Interface für Tipmaske, Koordinatenkopf und optionale Pfadmaske.
4. Vergleiche Batch-1-Ausgaben auf den drei Repository-Fixtures bitweise oder mit der engsten technisch erreichbaren Toleranz gegen P0.
5. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 2: Tip-only, Batch und korrekte Laufzeitzerlegung

**Files:**

- Create: `crackpy/benchmarking/ctd_p1_runtime.py`
- Create: `crackpy/tests/test_benchmarking/test_ctd_p1_runtime.py`
- Create: `scripts/crack_detection/benchmark_ctd_p1.py`

1. Schreibe fehlschlagende Tests für die Modi `tip_only` und `tip_path_angle`, Batchgrößen 1, 8, 16 und 32 sowie getrennte Bild- und Batchdurchsätze.
2. Implementiere Messphasen für Laden, Interpolation, Normalisierung, Host-zu-Device, Tip-Forward, Pfad-Forward, Device-zu-Host, Decoder, Pfad-/Winkelnachbearbeitung, Plotting und Schreiben.
3. Behandle CUDA-Out-of-Memory als strukturierten Variantenstatus, räume den Cache auf und setze den Sweep fort.
4. Miss Online-Latenz mit Batch 1 und Offline-Durchsatz mit unabhängigen Bildern bei Batch 8, 16 und 32.
5. Übernimm Pinned Memory oder asynchrone Transfers nur, wenn isolierte und End-to-End-Messung denselben Vorteil bestätigen.
6. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 3: Einmalige lineare Interpolation pro Frame

**Files:**

- Create: `crackpy/crack_detection/data/optimized_interpolation.py`
- Create: `crackpy/tests/test_crack_detection/test_data/test_optimized_interpolation.py`
- Extend: `crackpy/benchmarking/ctd_p1_runtime.py`

1. Schreibe fehlschlagende Paritätstests für rechte und linke Orientierung, Punkte innerhalb und außerhalb der konvexen Hülle, NaN-Masken und optionale Felder.
2. Implementiere eine Triangulation pro Frame und verwende ihre baryzentrischen Gewichte für `u_x`, `u_y` und nur bei Bedarf `eps_vm`.
3. Cache nicht frameübergreifend, außer Quellkoordinaten und Zielraster sind nachweislich identisch.
4. Prüfe `allclose(equal_nan=True, atol=1e-12, rtol=1e-12)` in Float64 sowie identische normalisierte Float32-Modellinputs und Tipentscheidungen.
5. Miss alle vier Dummy2-Frames und beide Orientierungen gegen drei einzelne `griddata`-Aufrufe.
6. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 4: Decodervergleich und Validation-only-Kalibrierung

**Files:**

- Create: `crackpy/benchmarking/ctd_decoders.py`
- Create: `crackpy/benchmarking/ctd_calibration.py`
- Create: `crackpy/tests/test_benchmarking/test_ctd_decoders.py`
- Create: `crackpy/tests/test_benchmarking/test_ctd_calibration.py`

1. Schreibe fehlschlagende Tests für historischen Maskendecoder, parametrisierten Schwellenwert, Koordinatenkopf, lineare Fusion, ungültige Koordinaten und Masken-Kopf-Abweichung.
2. Definiere `DecoderConfig` mit Schwellenwert, Regionsregel, Fusionsgewicht, Koordinatenkonvention und optionaler Unsicherheitsschwelle.
3. Dokumentiere jedes Feld dort, wo es eingeführt wird, einschließlich Bedeutung und Grund für seine Existenz.
4. Implementiere die Schwellen 0,30, 0,40, 0,50, 0,60 und 0,70, die festgelegten Regionsregeln und Fusionsgewichte 0, 0,25, 0,50, 0,75 und 1.
5. Verhindere technisch, dass der Kalibrator den CrackMNIST-Testsplit akzeptiert.
6. Wähle die Konfiguration anhand vorab fixierter Ziele aus Erkennungsrate, P95 und Median; löse Gleichstände deterministisch zugunsten der einfacheren Variante.
7. Erzeuge Risk-Coverage-Kurve, Area-under-Risk-Coverage, Fehlerkorrelation und eine ausschließlich auf Validation gewählte Unsicherheitsschwelle.
8. Serialisiere die Konfiguration und wende sie danach unverändert auf den Testsplit an.
9. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 5: Auflösungssweep 256, 128 und 64

**Files:**

- Extend: `crackpy/benchmarking/ctd_baseline.py`
- Extend: `crackpy/benchmarking/ctd_calibration.py`
- Extend: `scripts/crack_detection/benchmark_ctd_p1.py`
- Extend: `crackpy/tests/test_benchmarking/test_ctd_baseline.py`

1. Ergänze eine explizite 64-Pixel-Variante und auflösungsabhängige Index- sowie physische Grid-Geometrie.
2. Skaliere Rohfelder immer vor der Normalisierung und führe alle Resultate indexkorrekt auf das 128-Pixel-Referenzraster zurück.
3. Berichte die historische Legacy-Koordinatenkonvention getrennt von der indexkorrekten Vergleichskonvention.
4. Kalibriere Decoderparameter je Auflösung ausschließlich auf Validation und friere sie für Test ein.
5. Belasse Pfad und Winkel zunächst bei 256 Pixeln, solange die historischen 256er-Geometrieannahmen nicht additiv verallgemeinert und regressionsgeprüft sind.
6. Verwerfe eine niedrigere Default-Auflösung, wenn die Erkennungsrate um mehr als 0,5 Prozentpunkte sinkt oder der P95 um mehr als ein Originalpixel steigt.
7. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 6: Vollständiger P1-Lauf und separater Report

**Files:**

- Create: `docs/ctd-optimization/p1-results.json`
- Create: `docs/ctd-optimization/p1-report.md`
- Create: `docs/ctd-optimization/p1-runbook.md`

1. Führe den vollständigen Validierungs- und anschließenden Testlauf für alle freigegebenen Decoder- und Auflösungsvarianten aus.
2. Führe die Laufzeit-, Batch-, Transfer-, Tip-only- und Interpolationssweeps aus.
3. Speichere Einzelergebnisse, eingefrorene Kalibrierkonfigurationen, Variantenstatus, Laufzeiten, Speicher und Provenienz in strengem JSON.
4. Erzeuge eine inkrementelle und kumulative Accuracy-Runtime-Pareto-Tabelle gegen P0.
5. Trenne unabhängige Testaussagen, interne Fixture-Kompatibilität und reine Leistungsbenchmarks sichtbar voneinander.
6. Führe alle neuen Tests, relevante Legacy-Tests und reproduzierbare CLI-Läufe frisch aus.
7. Lasse die gesamte P1-Differenz gegen Spezifikation und P0 prüfen, behebe wesentliche Befunde und wiederhole die Verifikation.

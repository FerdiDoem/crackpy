# CTD P0 Runbook

## Zweck

Dieses Runbook reproduziert die eingefrorene P0-Baseline mit der originalen CrackPy-Version 1.3.0 und den originalen Modellgewichten.
Es führt kein Training und keine Gewichtsänderung aus.

## Voraussetzungen

Die Python-Umgebung muss CrackPy 1.3.0, CrackMNIST 2.0.1, PyTorch und die Projektabhängigkeiten enthalten.
Der offizielle CrackMNIST-Datensatz `crackmnist_128_S.h5` muss im angegebenen Datenverzeichnis liegen.
Für vergleichbare Laufzeiten wird ein CUDA-Gerät empfohlen; die Genauigkeitsauswertung kann auch auf der CPU laufen.

## Verifikation vor dem Lauf

```powershell
.\.venv\Scripts\python.exe -m pytest crackpy\tests -q
```

Die Modell- und Datensatzprüfsummen werden vom Benchmark in jedes Ergebnisartefakt geschrieben.
Abweichende Prüfsummen bedeuten einen anderen Baseline-Vertrag und dürfen nicht mit diesem P0-Bericht vermischt werden.

## Vollständige Rohläufe

Die 256er-Ausführung ist die primäre Referenz und enthält zusätzlich den optionalen B2-Lauf.

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\benchmark_ctd_p0.py `
  --device cuda:0 `
  --dataset-root C:\Users\Admin\.crackmnist `
  --batch-size 8 `
  --resolution-mode trained-256 `
  --include-b2 `
  --b2-warmup-iterations 1 `
  --b2-measured-iterations 3 `
  --output .downloads\p0-trained256-full.json
```

Die native 128er-Ausführung ist ausschließlich eine Auflösungssensitivität.

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\benchmark_ctd_p0.py `
  --device cuda:0 `
  --dataset-root C:\Users\Admin\.crackmnist `
  --batch-size 8 `
  --resolution-mode native-128 `
  --output .downloads\p0-native128-full.json
```

## Ergebnis und Report erzeugen

Der folgende Schritt prüft Split, Vollständigkeit, Datensatzidentität, Modellprüfsummen und Auflösungsmodi beider Rohläufe.
Er erzeugt den Bericht ausschließlich aus dem konsolidierten JSON-Artefakt.

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\assemble_ctd_p0_results.py `
  --trained-256 .downloads\p0-trained256-full.json `
  --native-128 .downloads\p0-native128-full.json `
  --output docs\ctd-optimization\p0-results.json `
  --report docs\ctd-optimization\p0-report.md
```

## Interpretation

Tipfehler auf CrackMNIST werden in Pixeln des originalen 128er-Rasters berichtet.
Eine Umrechnung in Millimeter ist ohne belastbare physische Feldgröße nicht zulässig.
Leere CrackMNIST-Referenzmasken werden als fehlende Referenz und nicht als Detektionsfehler gezählt.
Die drei Repository-Fixtures prüfen historische Kompatibilität, liefern aber keine unabhängige Teststatistik.
Der B2-Lauf besitzt keine unabhängige Ground Truth und belegt daher nur Ausführbarkeit und Kosten, keinen Genauigkeitsgewinn.

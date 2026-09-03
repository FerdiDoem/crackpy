# CTD P2 Runbook

## Zweck

Dieses Runbook reproduziert die P2-Prüfung der adaptiven physischen ROI mit dem eingefrorenen originalen CrackPy-Modell.

Der Lauf trainiert kein Modell und verändert keine Gewichte.

## Voraussetzungen

Die Projektumgebung muss installiert sein und die CrackPy-Modellartefakte müssen unverändert verfügbar sein.

Für den kanonischen Lauf wird CUDA verwendet, ein CPU-Lauf ist funktional möglich, aber nicht laufzeitvergleichbar.

Die vollständigen P0- und P1-Ergebnisse müssen unter `docs/ctd-optimization/p0-results.json` und `docs/ctd-optimization/p1-results.json` liegen.

Der Mendeley-Cache wird standardmäßig unter `.downloads/mendeley-dywwnjv22h-v1` erwartet.

Benötigt werden das rohe CSV-Archiv, das interpolierte PT-Archiv, die Crack-Length-Tabelle und die Readme.

Das fremde Modellarchiv ist für P2 nicht erforderlich.

## Kanonischer Lauf

Vom Repository-Root wird folgender Befehl ausgeführt:

```powershell
.\.venv\Scripts\python.exe scripts\crack_detection\benchmark_ctd_p2.py --device cuda:0
```

Das Ergebnis wird als striktes JSON nach `docs/ctd-optimization/p2-results.json` geschrieben.

Nichtendliche JSON-Werte führen vor dem Schreiben zu einem Fehler.

Die Mendeley-Dateien werden standardmäßig in Größe und SHA-256 geprüft.

Der Schalter `--skip-mendeley-hash-verification` ist nur für einen ausdrücklich als nicht kanonisch markierten Diagnose-Lauf vorgesehen.

## Frische Verifikation

Die fokussierte P2-Suite wird mit folgendem Befehl ausgeführt:

```powershell
.\.venv\Scripts\python.exe -m pytest crackpy/tests/test_crack_detection/test_adaptive_roi.py crackpy/tests/test_benchmarking/test_ctd_p2.py crackpy/tests/test_benchmarking/test_ctd_p2_runner.py crackpy/tests/test_benchmarking/test_benchmark_ctd_p2_script.py -q
```

Vor einer Freigabe wird zusätzlich die vollständige Testsuite ausgeführt:

```powershell
.\.venv\Scripts\python.exe -m pytest crackpy/tests -q
```

## Erwartete kanonische Identität

Der berichtete Referenzlauf ist an Git-Commit `905be6a6736fef79ee2004b706bd4d54bd5d84c8` gebunden.

Der SHA-256 des kanonischen Ergebnisartefakts lautet `f0485708a756150d145137ad225dca989cdadf9dceccdc174a98dcfce3e719a6`.

Der ParallelNets-Hash lautet `7b548e7299dbd647d35a99fb80f00b7582f040b58c62f5ca8be41e4c19c30f36`.

Der P1-Ergebnishash lautet `801e673dac1de9a965d4dd1670526beaaed76c0fef3a970cb259c6faeab6f259`.

## Erwartete Entscheidung

Die Sicherheitscoverage beträgt auf der primären realen Evidenz 100 Prozent.

Die Zahl der Randverletzungen und endgültigen Ausfälle beträgt null.

Alle beobachteten realen Frames werden im ersten Versuch akzeptiert, sodass P2.1 und P2.2 dort dieselbe Ortsgenauigkeit besitzen.

Die paarweise Ortsgenauigkeit ist gegenüber der festen 70-mm-P1-Baseline überwiegend schlechter.

Das Ergebnis muss deshalb `retain frozen fixed-70-mm P1` als empfohlenen Standard und beide P2-Promotionsflags als falsch ausweisen.

Die wissenschaftliche Freigabe muss bis zu unabhängigen Mendeley-Tiplabels falsch bleiben.

## Interpretationsregeln

Ein bestandenes Sicherheitsgate bedeutet nur, dass die Steuerung ihre Grenzen einhält, nicht dass sie die Ortsgenauigkeit verbessert.

Repository-Masken sind historische Sparse-Evidenz und werden nicht als unabhängig vom Training bezeichnet.

Dummy2-Werte sind Pseudoreferenzen, und die Werte der Stufen 53 und 54 sind im Legacy-Pfad von Stufe 55 fortgeschrieben.

CrackMNIST bewertet nur Einzelbildsignale und darf keine Sequenzgenauigkeit begründen.

Die Mendeley-PT-Tensoren sind auf 128 × 128 festgelegt, während das Roh-CSV-Archiv die erneute physische Interpolation auf 256 × 256 ermöglicht.

Williams bleibt ausgeschaltet, solange unabhängige Labels und ein belastbarer Solver-Residualvertrag fehlen.

## Fehlersuche

Ein Modellhashfehler bedeutet, dass nicht mehr die in P1 eingefrorenen Originalgewichte verwendet werden.

Ein P1-Quellhashfehler bedeutet, dass P2 nicht mehr auf dem kanonischen Full-Split-P1-Artefakt basiert.

Ein Mendeley-Hashfehler bedeutet, dass die lokale Datei unvollständig oder nicht Version 1 des erwarteten Datensatzes ist.

Ein Same-Scenario-Fehler bedeutet, dass Frame, Referenz, ROI, Decoder, Modell oder Baseline-Inhalt nicht mehr paarweise vergleichbar sind.

Ein nicht bestandenes wissenschaftliches Gate bei grünen technischen Gates ist ein erwartbarer Evidenzstatus und kein Implementierungsfehler.

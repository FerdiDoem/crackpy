# CTD P0 Baseline Implementation Plan

**Goal:** Eine eingefrorene und reproduzierbare CTD-Baseline mit den Originalmodellen aus CrackPy 1.3.0 aufbauen, ausführen und als P0-Report abschließen.

**Architecture:** Ein additives Benchmark-Paket kapselt Metriken, Zeitmessung, Provenienz und Ergebnisaggregation, ohne bestehende Detektionsklassen zu verändern.
Ein Kommandozeilenläufer verbindet dieses Paket mit den originalen CrackPy-Modellen, CrackMNIST, den Repository-Testdaten und dem Mendeley-Audit.
Der Report wird ausschließlich aus dem gespeicherten Ergebnisartefakt erzeugt, damit Aussagen und Rohwerte nicht auseinanderlaufen.

**Tech Stack:** Python 3.12, PyTorch, NumPy, SciPy, scikit-image, pytest, CrackMNIST 2.0.1 und CrackPy 1.3.0.

---

## Task 1: Baseline-Vertrag und Metrikkern

**Files:**

- Create: `crackpy/benchmarking/__init__.py`
- Create: `crackpy/benchmarking/ctd_metrics.py`
- Test: `crackpy/tests/test_benchmarking/test_ctd_metrics.py`

1. Schreibe fehlschlagende Tests für Tip-Erfolg und -Ausfall, konditionale Verteilungswerte, Dice, IoU, symmetrische Pfaddistanz, HD95 und Winkelabweichung modulo 180 Grad.
2. Führe nur diese Tests aus und bestätige den erwarteten Fehlschlag.
3. Implementiere kleine, typisierte und serialisierbare Metrikfunktionen mit expliziten leeren Fällen.
4. Führe die Tests erneut aus und bestätige den Erfolg.
5. Committe die abgeschlossene vertikale Scheibe.

## Task 2: Reproduzierbare Inferenz und Laufzeitmessung

**Files:**

- Create: `crackpy/benchmarking/ctd_runtime.py`
- Test: `crackpy/tests/test_benchmarking/test_ctd_runtime.py`

1. Schreibe fehlschlagende Tests für Warm-up-Ausschluss, getrennte Phasen, Perzentile, Durchsatz und JSON-kompatible Laufmetadaten.
2. Führe die Tests aus und bestätige den erwarteten Fehlschlag.
3. Implementiere deterministische Seed-Verwaltung, Gerätesynchronisation, Phasen-Timer, Speichermessung und Hashing.
4. Führe die Tests erneut aus und bestätige den Erfolg.
5. Committe die abgeschlossene vertikale Scheibe.

## Task 3: B0/B1 und CrackMNIST-Adapter

**Files:**

- Create: `crackpy/benchmarking/ctd_baseline.py`
- Create: `scripts/crack_detection/benchmark_ctd_p0.py`
- Test: `crackpy/tests/test_benchmarking/test_ctd_baseline.py`

1. Schreibe fehlschlagende Tests für den originalen Maskendecoder, den diagnostischen Koordinatenkopf, die 128-zu-256-Koordinatenrückführung, explizite Ausfälle und die Ergebnisstruktur.
2. Führe die Tests aus und bestätige den erwarteten Fehlschlag.
3. Implementiere B0 und B1 mit eingefrorenen Modellen, ohne die vorhandene Inferenzlogik zu verändern.
4. Implementiere einen CrackMNIST-Adapter, der den offiziellen Test-Split nutzt und Fehler wieder in Originalpixel zurückführt.
5. Implementiere den Kommandozeilenlauf mit Stichprobenlimit für Rauchtests und vollständigem Split als Standard.
6. Führe Unit- und kleinen Integrationslauf aus und bestätige den Erfolg.
7. Committe die abgeschlossene vertikale Scheibe.

## Task 4: B2 und Mendeley-A0

**Files:**

- Extend: `crackpy/benchmarking/ctd_baseline.py`
- Extend: `scripts/crack_detection/benchmark_ctd_p0.py`
- Create: `docs/ctd-optimization/mendeley-a0-audit.md`
- Create: `docs/ctd-optimization/mendeley-annotation-schema.md`
- Test: `crackpy/tests/test_benchmarking/test_ctd_baseline.py`

1. Schreibe einen fehlschlagenden Test für B2-Status, Korrekturverschiebung, Laufzeit und den expliziten Hinweis bei fehlender unabhängiger Ground Truth.
2. Implementiere den vorhandenen Williams-Korrekturlauf auf dem CrackPy-Beispiel mit deaktivierter Plot-Erzeugung.
3. Prüfe die Mendeley-Veröffentlichung, Dateistruktur, Modalität, Sequenzschlüssel, vorhandene Labels und fehlende Referenzen reproduzierbar.
4. Definiere ein frame- und specimen-basiertes Annotationsschema mit Tip, Pfad, lokalem Winkel, Sichtbarkeit, Unsicherheit, Reviewer und Provenienz.
5. Führe Tests und einen B2-Rauchtest aus.
6. Committe die abgeschlossene vertikale Scheibe.

## Task 5: Vollständiger P0-Lauf und Report

**Files:**

- Create: `docs/ctd-optimization/p0-results.json`
- Create: `docs/ctd-optimization/p0-report.md`
- Create: `docs/ctd-optimization/p0-runbook.md`

1. Lade die unveränderten Originalgewichte und erfasse ihre Prüfsummen.
2. Führe die relevanten bestehenden CrackPy-Tests aus, bevor die Messergebnisse erzeugt werden.
3. Führe B0 und B1 auf dem festgelegten CrackMNIST-Testsplit und den verfügbaren CrackPy-Referenzdaten aus.
4. Führe B2 auf dem CrackPy-DIC-Beispiel aus oder protokolliere den reproduzierbaren Blocker.
5. Speichere Rohwerte, Zusammenfassungen, Ausfälle, Umgebung und Laufzeiten in JSON.
6. Generiere den Report mit klarer Trennung zwischen gemessenen Ergebnissen, Annahmen und nicht belegbaren Aussagen.
7. Führe alle neuen Tests, relevante Legacy-Tests und einen reproduzierbaren CLI-Lauf frisch aus.
8. Lasse die gesamte Branch-Differenz gegen Design und Abnahmekriterien prüfen.
9. Behebe alle wesentlichen Review-Befunde und wiederhole die Verifikation.

# CTD P2 Adaptive ROI Implementation Plan

**Goal:** Die vorhandene sequenzielle Offset-Nachführung ohne Retraining in eine deterministische und abgesicherte adaptive ROI-Steuerung mit expliziten Fallbacks überführen.

**Architecture:** Ein reines Zustandsmodul entscheidet anhand physischer ROI-Geometrie und strukturierter Detektionsbeobachtungen über Annahme, Wiederholung und das nächste Suchfenster.
Die bestehende Detektion bleibt Beobachtungsquelle und wird nicht mit der Zustandslogik vermischt.
P2.1 hält die physische Tracking-Fenstergröße konstant und erlaubt nur einen Start-ROI-Reset; P2.2 untersucht Expanded- und Full-search-ROI mit bewusst veränderter Fenstergröße.

**Tech Stack:** Python 3.12, PyTorch, NumPy, SciPy, pytest, CrackPy 1.3.0 sowie die in P1 eingefrorene Decoder- und Unsicherheitskonfiguration.

---

## Task 1: Physisches ROI-Modell und Seitenadapter

**Files:**

- Create: `crackpy/crack_detection/adaptive_roi.py`
- Create: `crackpy/tests/test_crack_detection/test_adaptive_roi.py`

1. Schreibe fehlschlagende Tests für gültige und ungültige physische ROI-Grenzen, Mittelpunkte, Ausdehnungen, Randabstände und links-rechts-Spiegelung.
2. Implementiere `PhysicalRoi` mit Mittelpunkt, x/y-Ausdehnung und zulässiger Suchfeldgrenze.
3. Implementiere `RoiObservation` mit absolutem Tip, Maskenscore, Maskenfläche, Masken-Kopf-Abweichung, Feldqualität und optionaler Zyklusdifferenz.
4. Implementiere `RoiGateConfig` mit Schwellen, deren Bedeutung, Einheit und Kalibrierursprung direkt dokumentiert sind.
5. Halte `side` an der Legacy-Grenze und verwende intern eine einheitliche physische Orientierung.
6. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 2: P2.1-Zustandsmaschine mit konstanter Fenstergröße

**Files:**

- Extend: `crackpy/crack_detection/adaptive_roi.py`
- Extend: `crackpy/tests/test_crack_detection/test_adaptive_roi.py`

1. Schreibe fehlschlagende Tests für `START`, `TRACKING`, `START_FALLBACK` und `LOST` sowie jeden erlaubten Übergang.
2. Akzeptiere einen lokalen Vorschlag nur bei endlichen Feldern, gültigem ROI, ausreichendem Regionsscore, plausibler Maskenfläche, begrenzter Masken-Kopf-Abweichung, zulässigem Sprung und ausreichendem Randabstand.
3. Leite den maximalen Sprung bei vorhandenen Zyklusinformationen aus der Zyklusdifferenz ab; verwende andernfalls einen explizit konfigurierten konservativen Grenzwert.
4. Wiederhole einen unsicheren lokalen Versuch im Start-ROI desselben Frames und markiere Totalverlust sichtbar, wenn auch dieser Versuch scheitert.
5. Beginne nach Totalverlust den nächsten Frame sicher im Start-ROI.
6. Speichere angewendetes ROI, vorgeschlagenes Folge-ROI, Ablehnungsgründe, Versuchszahl und Laufzeit pro Frame.
7. Prüfe, dass die physische Fenstergröße in P2.1 in jedem Zustand exakt konstant bleibt.
8. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 3: P2.2 mit Expanded- und echter Full-search-Suche

**Files:**

- Extend: `crackpy/crack_detection/adaptive_roi.py`
- Extend: `crackpy/tests/test_crack_detection/test_adaptive_roi.py`

1. Schreibe fehlschlagende Tests für `EXPANDED_FALLBACK` und `FULL_SEARCH` sowie für vollständig geklemmte Suchfeldgrenzen.
2. Trenne Start-ROI, Tracking-ROI und Full-search-ROI begrifflich und im Ergebnisformat.
3. Implementiere Expanded- und Full-search-Versuche erst nach einem fehlgeschlagenen konstanten Versuch.
4. Markiere jede physische Größenänderung als eigene P2.2-Variante, weil ein Start-Reset bei kleinerem Startfenster keine globale Suche ist.
5. Prüfe, dass ein Full-search-ROI das gesamte zulässige Suchfeld tatsächlich abdeckt.
6. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 4: P1-Signale und selektive Williams-Korrektur

**Files:**

- Create: `crackpy/benchmarking/ctd_p2.py`
- Create: `crackpy/tests/test_benchmarking/test_ctd_p2.py`
- Create: `scripts/crack_detection/benchmark_ctd_p2.py`

1. Lade die eingefrorene P1-Decoder- und Unsicherheitskonfiguration und lehne Testsplit-Nachkalibrierung ab.
2. Extrahiere Maskenregionsscore, Maskenfläche, Masken-Kopf-Abweichung, Randabstand und DIC-Feldqualität als strukturierte Beobachtung.
3. Bezeichne Maskenscores nicht als kalibrierte Wahrscheinlichkeiten.
4. Rufe Williams nur nach geometrisch gültigem, aber grenzwertigem Ergebnis und erst nach dem vorgesehenen ROI-Fallback auf.
5. Kapsle Williams in einem strukturierten Ergebnis mit Status, Iterationszahl, Residuum vorher und nachher, Korrekturdelta, absolutem Endtip und eindeutigem Fehlergrund.
6. Prüfe korrigierte Ergebnisse erneut gegen Sprung, Rand und Suchfeldgrenzen.
7. Übernimm Williams nicht als Default, solange unabhängige Labels keinen Genauigkeitsgewinn belegen.
8. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 5: Kontrollierte Sequenz- und Stressprüfung

**Files:**

- Extend: `crackpy/benchmarking/ctd_p2.py`
- Extend: `crackpy/tests/test_benchmarking/test_ctd_p2.py`

1. Erzeuge deterministische synthetische Trajektorien für kleine und große Sprünge, Randkontakte, NaNs, geringe Feldstreuung, Kopfkonflikte und Totalverlust.
2. Prüfe die drei gelabelten Repository-Felder als sparse historische Trajektorie, ohne ihre Unabhängigkeit von den Trainingsdaten zu behaupten.
3. Verarbeite in einem Dummy2-Replay tatsächlich alle vier Frames 52 bis 55 und kennzeichne vorhandene Crack-Info-Werte als Pseudoreferenz.
4. Verwende CrackMNIST-Testfelder nur zur unabhängigen Einzelbildprüfung der P1-Unsicherheitssignale, nicht als reale Sequenzreferenz.
5. Berichte für Mendeley ohne geprüfte Tiplabels keine quantitative ROI-Genauigkeit.
6. Committe diese vertikale Scheibe nach fokussierter Verifikation und Review.

## Task 6: Vollständiger P2-Lauf und separater Report

**Files:**

- Create: `docs/ctd-optimization/p2-results.json`
- Create: `docs/ctd-optimization/p2-report.md`
- Create: `docs/ctd-optimization/p2-runbook.md`

1. Berichte Inside-Coverage und sichere Coverage mit Mindest-Randabstand vor der lokalen Detektion.
2. Berichte Versuchszahl, Start-, Expanded- und Full-search-Fallbackrate, Recovery-Rate, endgültige Ausfallrate, Randverletzungen und Feldqualitätsablehnungen.
3. Berichte Median, P95 und Maximum des Tipfehlers sowie selbstsichere Fehler und deren 95-Prozent-Unsicherheitsgrenze.
4. Berichte Williams-Aufruf-, Erfolgs- und Verwerfungsrate sowie seine getrennte Qualitäts- und Laufzeitwirkung.
5. Berichte End-to-End-Zeit P50 und P95 einschließlich aller Wiederholungsversuche.
6. Bewerte die technische Abnahme vollständig, trenne sie aber von einer wissenschaftlichen Freigabe auf unabhängigen realen Sequenzlabels.
7. Verwende vorläufig mindestens 99 Prozent sichere ROI-Coverage, null Randverletzungen und keine gegenüber P1 erhöhte endgültige Ausfallrate als Refinement-Gates.
8. Kennzeichne fehlende Mendeley-Labels als Evidenzgrenze und nicht als technischen Implementierungsfehler.
9. Führe alle neuen Tests, relevante Legacy-Tests und reproduzierbare CLI-Läufe frisch aus.
10. Lasse die gesamte P2-Differenz prüfen, behebe wesentliche Befunde und wiederhole die Verifikation.

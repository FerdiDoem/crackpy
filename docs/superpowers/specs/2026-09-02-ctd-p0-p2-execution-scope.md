# CTD P0 bis P2 Execution Scope

## Verbindliche Hauptlinie

Das Projekt optimiert die bestehende Crack-Tip Detection von CrackPy 1.3.0 in drei aufeinander aufbauenden Stufen.
Jede Stufe erzeugt ein eigenes Ergebnisartefakt und einen eigenständigen Report.
Mendeley-Annotation läuft als parallele Datenspur und ersetzt keine Optimierungsstufe.
P1 und die erste P2-Ausbaustufe verändern keine Modellarchitektur und trainieren keine Gewichte neu.

## P0: Eingefrorene Originalbaseline

P0 friert Code, Originalgewichte, Daten, Umgebung und Metriken ein.
P0 misst Tip-only, Tip plus Pfad und Winkel sowie die optionale Williams-Korrektur.
CrackMNIST dient als kontrollierter Tip-Benchmark und CrackPy-Fixtures dienen der historischen Pipeline- und Laufzeitreferenz.
Mendeley A0 liefert Inventar, Datenlücken und den Vertrag für die parallel beginnende Annotation.

## P1: Sichere Optimierungen ohne Modelländerung

P1 optimiert zuerst Modelllebenszyklus, Gerätepersistenz und Inferenzmodus.
Danach trennt P1 Tip-only und Tip-plus-Pfad, damit unnötige Modelle im CTD-only-Betrieb vollständig entfallen.
Batch-Verarbeitung wird für unabhängige Bilder und Probenseiten untersucht.
Interpolation, CPU-GPU-Transfers, Plotting und Dateioperationen werden als getrennte End-to-End-Anteile gemessen und nur bei nachgewiesenem Engpass optimiert.

P1 vergleicht den historischen Maskendecoder, den bereits vorhandenen Koordinatenkopf und klar benannte Fusionsvarianten.
Die Abweichung zwischen Maske und Koordinatenkopf wird als mögliches Unsicherheitssignal geprüft.
Die eingefrorenen Gewichte werden auf 256, 128 und 64 Pixeln untersucht, ohne daraus eine höhere physikalische Auflösung abzuleiten.
Schwellenwert und Regionsauswahl werden ausschließlich auf einem Validierungssplit kalibriert und danach unverändert auf dem Testsplit geprüft.

P1 liefert eine Accuracy-Runtime-Pareto-Tabelle für jede einzelne Änderung.
Eine Änderung wird nur übernommen, wenn sie die vereinbarte Robustheit erhält oder ihren Qualitätsverlust als bewussten Pareto-Tausch sichtbar macht.
P1 gibt kein Retraining frei und verändert keine Modellarchitektur.

## P2: Abgesichertes adaptives ROI

P2 erweitert die vorhandene sequenzielle Offset-Nachführung und ersetzt sie nicht durch ein neues Modell.
Die erste Ausbaustufe hält die physische Fenstergröße konstant und führt nur dessen Position nach.
Der erste Frame verwendet das Start-ROI.
Ein unsicherer lokaler Versuch darf in P2.1 nur auf dieses gleich große Start-ROI zurückgesetzt werden.
Ein Start-Reset ist ausdrücklich kein globaler Fallback, wenn das Start-ROI nicht das gesamte zulässige Suchfeld abdeckt.

Ein lokaler Vorschlag wird nur akzeptiert, wenn Maskensicherheit, Masken-Koordinaten-Konsistenz, maximaler Bewegungssprung, Tip-Randabstand und DIC-Feldqualität die festgelegten Grenzen erfüllen.
Bei einem verletzten Kriterium wird P2.1 auf das Start-ROI zurückgesetzt.
Erst P2.2 darf ein größeres Expanded-ROI oder ein das gesamte Suchfeld abdeckendes Full-search-ROI verwenden.
Eine Williams-Korrektur darf als selektive Option für unsichere Fälle getestet werden, muss aber getrennt in Qualität und Laufzeit erscheinen.

Variable physische Fenstergrößen werden erst nach der konstanten Nachführung untersucht.
Ein kleineres physisches Fenster verbessert Zentrierung und lokalen Informationsgehalt, beschleunigt ein weiterhin 256-mal-256 großes CNN aber nicht automatisch.
Wenn die eingefrorenen Gewichte auf der veränderten Skala messbar versagen, wird die Variante verworfen oder als späterer Fine-Tuning-Kandidat markiert.

P2 berichtet ROI-Coverage vor lokaler Detektion, Fallbackrate, selbstsichere Fehlentscheidungen, endgültigen Tip-Fehler, Randverletzungen und End-to-End-Laufzeit.
Die reale Sequenzaussage bleibt auf die vorhandenen unabhängigen Referenzen begrenzt.
Mendeley darf erst nach geprüften Tip-Labels als quantitative ROI-Evidenz verwendet werden.

## Nicht Bestandteil von P1 oder P2

Ein neues Tiny U-Net, ein neuer Gaussian-Heatmap-Head, ein direkter Winkelkopf und ein neues Multi-Task-Modell benötigen Training und gehören in eine spätere Modellentscheidung.
FEM und Virtual DIC bleiben ein optionaler Daten- und Vortrainingstrack für Pfad, Winkel und Domänenabdeckung.
Mixed Precision, Kompilierung, ONNX und TensorRT gehören in eine spätere Deployment-Stufe.

## Berichtspflicht je Stufe

Jeder Report vergleicht die Stufe mit der vorherigen freigegebenen Referenz.
Er zeigt die Wirkung jedes Refinements einzeln, typische und schlimmste Fehlfälle, Genauigkeit, Robustheit, Laufzeit und Speicher.
Er trennt Messwerte, Annahmen, interne Kompatibilitätsreferenzen und wissenschaftlich unabhängige Ground Truth.
Er endet mit einer begründeten Entscheidung, welche Varianten übernommen, nachgeschärft oder verworfen werden.

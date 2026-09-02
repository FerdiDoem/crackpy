# CTD-Optimierung P1 – Abschlussbericht

## Ergebnis in einem Satz

P1 beschleunigt und entkoppelt die originale CrackPy-1.3.0-Ausführung ohne Retraining, behält 256 Pixel als Standard bei und verwirft 128 sowie 64 Pixel wegen klarer Genauigkeitsverluste.

## Entscheidung

Der freigegebene P1-Pfad verwendet weiterhin die originalen Gewichte und die trainierte Auflösung von 256 Pixeln.

Das Tipmodell bleibt persistent auf dem Zielgerät, während das Pfadmodell im echten Tip-only-Betrieb weder geladen noch auf das Zielgerät verschoben wird.

Das Pfadmodell wird erst vor der Pfad- und Winkelauswertung geladen.

Die validierungsgewählte Tipauswertung bleibt maskenbasiert und verwendet keine Fusion mit dem Koordinatenkopf.

Niedrige Konfidenz wird nicht als fehlende Detektion behandelt, sondern als möglicher Auslöser für die P2-Fallback-Suche.

Ein neues Training oder eine Änderung der Modellarchitektur ist nach P1 nicht begründet.

## Was P1 umgesetzt hat

### P1.1 Persistente und echte Tip-only-Ausführung

ParallelNets wird einmal geladen, eingefroren und unter dem Inferenzmodus wiederverwendet.

UNetPath bleibt während Kalibrierung, Tipauswertung, Tip-Laufzeitmessung und Interpolationsvergleich vollständig außerhalb des Betriebs.

Der erste Tip-Ladevorgang dauerte 130,14 ms.

Der später ausgeführte Pfad-Ladevorgang dauerte 116,47 ms und das anschließende Anbinden an das Zielgerät 35,08 ms.

Die Gewichts- und Datensatzprüfsummen werden gestaffelt nach der jeweiligen Lademessung geprüft, damit weder ein falsches Artefakt weiterläuft noch das Prüfen die Cold-Load-Messung künstlich verbessert.

### P1.2 Einmalige Interpolation pro Frame und ROI

Die drei bisherigen linearen Interpolationen für die DIC-Kanäle teilen sich nun eine Triangulation.

Über Dummy2 Stufen 52 bis 55 und beide Seiten betrug der Median der Beschleunigung 3,008-fach.

Die Einzelwerte lagen zwischen 2,958-fach und 3,040-fach.

Float64-Felder, normalisierte Float32-Modelleingaben, Tipwahrscheinlichkeiten, Koordinatenkopf und finale Tipentscheidung waren in allen acht Varianten gleich.

Es gibt bewusst keinen frameübergreifenden Cache.

### P1.3 Validierungsgebundener Decodervergleich

Alle Schwellen, Regionsregeln und Fusionsgewichte wurden ausschließlich auf dem CrackMNIST-Validierungssplit verglichen.

Der Testsplitt wurde erst nach dem Einfrieren der Konfiguration geöffnet.

Für 256 Pixel wurde ein Maskendecoder mit Schwelle 0,30 und Auswahl nach mittlerer Regionswahrscheinlichkeit gewählt.

Der Fusionsanteil des Koordinatenkopfs ist 0,00.

Damit liefert der Koordinatenkopf Diagnose- und Konsistenzsignale, verschiebt aber nicht den akzeptierten Tip.

Koordinaten außerhalb des Modellrasters zählen als ungültige Kopfausgabe und nicht als scheinbar erfolgreiche Detektion.

Das kombinierte Unsicherheitssignal korreliert auf dem Testsplit nur schwach mit dem Fehler und wird deshalb nicht als kalibrierte Wahrscheinlichkeit bezeichnet.

Für 256 Pixel betragen Pearson- und Spearman-Korrelation 0,141 beziehungsweise 0,137.

Die korrigierte Validierung wählt für 256 Pixel eine Unsicherheitsschwelle von 1,0, weshalb eine harte Confidence-Ablehnung keinen Zusatznutzen besitzt.

P2 verwendet daher getrennte Rohsignale wie Kopfgültigkeit, Maskenfläche, Maskenmittel, Kopfabweichung, Randabstand und DIC-Feldqualität.

### P1.4 Auflösungsvergleich

Alle Fehlerwerte werden auf das originale 128-Pixel-Referenzraster zurückgeführt.

| Variante | Detektionsrate Test | Medianfehler | P95-Fehler | Entscheidung |
|---|---:|---:|---:|---|
| P0, 256 Pixel, historisch | 99,832 % | 0,973 px | 1,975 px | Referenz |
| P1, 256 Pixel | 99,832 % | 0,971 px | 1,973 px | angenommen |
| P1, 128 Pixel | 97,238 % | 2,345 px | 4,475 px | verworfen |
| P1, 64 Pixel | 69,468 % | 5,820 px | 12,867 px | verworfen |

Die 256-Pixel-Variante erfüllt sowohl die erlaubte Verschlechterung der Detektionsrate von höchstens 0,5 Prozentpunkten als auch den P95-Grenzwert von P0 plus einem Originalpixel.

Die minimale Änderung der 256-Pixel-Fehlerverteilung ist kein Beleg für einen substanziellen Genauigkeitsgewinn.

Sie belegt jedoch, dass die Ausführungsoptimierungen die P0-Qualität erhalten.

## Laufzeit und Pareto

Die Laufzeitmessung enthält Normalisierung und Resize, Transfer, Forward-Pass, Rücktransfer und genau den je Auflösung eingefrorenen Decoder.

Plotting und Ergebnisschreiben liegen außerhalb des Messpfads.

| Produkt | Batch | Durchsatz | GPU-Spitzenspeicher |
|---|---:|---:|---:|
| Tip-only, 256 Pixel | 1 | 135,20 Bilder/s | 0,252 GiB |
| Tip-only, 256 Pixel | 8 | 176,57 Bilder/s | 1,259 GiB |
| Tip-only, 256 Pixel | 16 | 188,94 Bilder/s | 2,410 GiB |
| Tip-only, 256 Pixel | 32 | 192,96 Bilder/s | 4,710 GiB |
| Tip, Pfad und Winkel, 256 Pixel | 1 | 92,01 Bilder/s | 0,327 GiB |
| Tip, Pfad und Winkel, 256 Pixel | 32 | 98,82 Bilder/s | 4,792 GiB |

Batch 1 entspricht beim Tip-only-Pfad ungefähr 7,40 ms je Bild im gemessenen Vertrag.

Batch 32 maximiert den 256-Pixel-Tipdurchsatz, erhöht aber den Speicherbedarf deutlich.

Für Online-Verarbeitung ist Batch 1 die relevante Betriebsart.

Für unabhängige Offline-Felder sind Batch 16 und 32 die Durchsatzoptionen.

Die höheren Durchsätze von 128 und 64 Pixeln bilden keinen Pareto-Punkt, weil beide Varianten die festgelegten Genauigkeitsgrenzen verfehlen.

P0 und P1 besitzen unterschiedliche End-to-End-Messverträge, weshalb kein künstlich exakter Gesamtspeedup zwischen beiden angegeben wird.

Der 3,008-fache Interpolationsgewinn ist dagegen ein direkter Vergleich derselben Felder und derselben Ausgabe.

## Metriken und ihr Zweck

Die Detektionsrate ist der Anteil gültiger Referenzen mit einem endlichen akzeptierten Tip und verhindert, dass Fehlerstatistiken Ausfälle verstecken.

Median und P95 des Tipfehlers beschreiben typische beziehungsweise ungünstige erfolgreiche Lokalisierungen.

Der Mittelwert bleibt als ergänzende, ausreißerempfindliche Größe erhalten.

Risk-Coverage, AURC sowie Pearson- und Spearman-Korrelation prüfen, ob das Unsicherheitssignal Fehler sinnvoll ordnet.

Durchsatz, Batchlatenz und GPU-Spitzenspeicher beschreiben die Betriebsoptionen.

Numerische Parität und finale Tipparität sichern die Interpolationsänderung ab.

## Evidenzgrenzen

CrackMNIST enthält augmentierte Einzelbilder ohne öffentliches Quellbildkennzeichen und belegt deshalb keine statistisch unabhängige reale Sequenzleistung.

Die Repository-Fixtures sichern Kompatibilität, sind aber keine unabhängige Feldstudie.

Dummy2 belegt in P1 ausschließlich Interpolationsleistung und numerische Gleichheit.

Pfad und Winkel wurden nicht neu trainiert und bleiben bei der originalen 256-Pixel-Geometrie.

Die Mendeley-Daten werden erst nach geprüfter Tipannotation quantitativ ausgewertet.

## Verifikation und Artefakte

Der vollständige Lauf verwendete 5.944 Validierungs- und 5.944 Testbilder je Auflösung auf einer NVIDIA GeForce RTX 5070 Ti mit CUDA 13.0.

Alle 16 Laufzeitvarianten wurden abgeschlossen und alle acht Interpolationsvarianten bestanden die vollständige Paritätsprüfung.

115 fokussierte P0/P1-Tests bestanden frisch.

Ein nachgelagerter CUDA-Smoke auf Commit `2f313c9` bestätigte die gestaffelte Fail-fast-Provenienzprüfung und die kompakte, nicht duplizierte Serialisierung.

Das kanonische Ergebnis steht in `p1-results.json` und hat SHA-256 `801e673dac1de9a965d4dd1670526beaaed76c0fef3a970cb259c6faeab6f259`.

Der unveränderte vollständige Roh-Lauf hat SHA-256 `19c3063ff9f8046a7e47183edfca89061068e58dbe42383124c5ced6618e7683`.

Im kanonischen Ergebnis sind die Einzelergebnisse für Validation und Test je einmal enthalten; daraus ableitbare Confidence-Kopien wurden nicht doppelt gespeichert.

## P1-Abschluss

P1 ist technisch abgeschlossen.

Der nächste sinnvolle Schritt ist keine weitere Auflösungsreduktion und kein Retraining, sondern P2 mit physisch konstantem Tracking-ROI, expliziten Qualitätsgates und gestufter Recovery.

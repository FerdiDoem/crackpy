# CTD-Optimierung – P0-Baseline

## Ergebnis

P0 ist als reproduzierbare Baseline auf der unveränderten CrackPy-Version 1.3.0 abgeschlossen.
Die originale 256-Pixel-Ausführung bleibt die Referenz, weil sie die Tipposition deutlich genauer und zuverlässiger bestimmt als eine direkte 128-Pixel-Ausführung.
Der historische Maskendecoder ist dem vorhandenen Koordinatenkopf ebenfalls klar überlegen; P1 sollte deshalb zunächst Decoder, Ausführung und Datentransfer optimieren, nicht neu trainieren.

## B0 – Tipdetektion auf CrackMNIST

| Variante | Erkennungsrate | Medianfehler | P95-Fehler | Mittelwert | Ausfälle |
|---|---:|---:|---:|---:|---:|
| Originalmodell bei 256 px | 99,83 % | 0,97 px | 1,98 px | 1,06 px | 10 |
| Originalmodell direkt bei 128 px | 97,49 % | 2,35 px | 4,49 px | 2,72 px | 149 |
| Koordinatenkopf, diagnostisch, 256 px | 100,00 % | 2,70 px | 8,90 px | 3,51 px | 0 |

Ausgewertet wurden 5944 Testbilder; sechs leere Masken gelten als fehlende Referenzen und nicht als Modellfehler.
Die Fehler sind in Pixeln des originalen 128er-Rasters angegeben, weil CrackMNIST keine belastbare physische Feldgröße liefert.
Die höheren Dice- und IoU-Werte der 128er-Maske bedeuten keinen besseren Tip: Die Segmentüberlappung ist bei der sehr dünnen Zielmaske empfindlich gegenüber deren Dicke und bleibt deshalb eine Diagnosemetrik.

## B1 – Pfad und lokaler Winkel

Auf den drei vorhandenen CrackPy-Referenzfeldern beträgt die symmetrische mittlere Pfaddistanz im Median 0,68 px beziehungsweise 0,19 mm.
Der Pfad-HD95 liegt im Median bei 3,11 px, und der lokale Winkelfehler bei 5,06 Grad.
Diese drei Felder sind ein Kompatibilitätsnachweis, aber keine unabhängige statistische Testbasis.
CrackMNIST enthält keine belastbare Pfad- und Winkelreferenz für B1.

## B2 – optionale Williams-Korrektur

Der vorhandene CrackPy-Beispiellauf konvergierte nach 8 Iterationen und verschob den Tip um (1,110, 0,107) mm.
Die Williams-Korrektur benötigte im Median 15,72 s und dominiert damit die Laufzeit deutlich.
Ohne unabhängige Ground Truth ist daraus kein Genauigkeitsgewinn ableitbar; B2 bleibt daher optional und wird in P2 nur selektiv geprüft.

## Laufzeitprofil

Das erste Laden beider Modelle dauerte 313,04 ms.
Für einen vorbereiteten Dreier-Batch wurden 81,58 Bilder/s erreicht; Tip- und Pfad-Forward benötigten jeweils rund 12,76 ms und 12,72 ms pro Batch.
Das Profil zeigt drei klare P1-Hebel: Modelle persistent halten, Tip-only wirklich ohne Pfadnetz ausführen und unabhängige Bilder bündeln.
Plotten und Dateischreiben waren aus dem Messpfad ausgeschlossen.

## Evidenzgrenzen und Entscheidung für P1

CrackMNIST stellt augmentierte Bilder eines einzigen Testexperiments ohne offengelegte Quellbild-IDs bereit; Unabhängigkeit auf Bildebene wird daher nicht behauptet.
Die Mendeley-Daten besitzen nach dem A0-Audit keine direkt nutzbaren Frame-Labels für Tip, Pfad, Winkel und ROI-Abdeckung; die Annotation kann parallel laufen, quantitative Aussagen warten aber auf geprüfte Labels.
P1 startet ohne Retraining mit der 256er-Referenz, vergleicht Decoder nur auf Validation und friert die Wahl vor dem Test ein.
Eine niedrigere Auflösung wird nur übernommen, wenn Erkennungsrate und P95 innerhalb der vorab definierten Grenzen bleiben.

## Reproduzierbarkeit

Der Lauf verwendete Python 3.12.13, PyTorch 2.14.0+cu130 und NVIDIA GeForce RTX 5070 Ti.
ParallelNets-Prüfsumme: `7b548e7299dbd647d35a99fb80f00b7582f040b58c62f5ca8be41e4c19c30f36`.
UNetPath-Prüfsumme: `c8431c23541e3560236f8ba570d2854ecd5a729512338273be2cd0d6c7385092`.
CrackMNIST-H5-MD5: `3101a618e0837276b1ef4533964fabb3`.
Alle Einzelwerte und Ausfallgründe stehen in `p0-results.json`.

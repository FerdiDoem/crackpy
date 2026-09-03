# CTD-Optimierung P2: Adaptive ROI

## Ergebnis in einem Satz

Die adaptive ROI-Steuerung ist vollständig implementiert und technisch abgesichert, wird aber nicht als neuer Standard übernommen, weil sie auf den verfügbaren paarweisen Realreplays trotz fehlerfreier Ausführung eine schlechtere Tip-Lokalisierung als die feste 70-mm-P1-Baseline liefert.

## Entscheidung

Der empfohlene Standard bleibt die in P1 eingefrorene Detektion mit fester physischer 70-mm-ROI und dem originalen CrackPy-Modell.

P2.1 und P2.2 bleiben als experimentelle, reproduzierbare Optionen im Projekt erhalten.

Für P2 wurde kein Modell neu trainiert.

Diese Entscheidung ist kein Scheitern der Zustandsmaschine, sondern das beabsichtigte Ergebnis eines Optimierungsgates, das eine technisch funktionierende Änderung nicht automatisch mit einer besseren Messung gleichsetzt.

## Was P2 ergänzt

P2 trennt die neuronale Detektion von einer deterministischen Steuerung des physischen Suchfensters.

Die Detektion liefert nur einen Kandidaten und rohe Qualitätssignale, während die Steuerung über Annahme, Fallback und das Fenster des nächsten Frames entscheidet.

Referenzwerte werden erst nach Abschluss der Entscheidung zur Auswertung angehängt und können die ROI-Wahl daher nicht beeinflussen.

P2.1 verwendet ein konstantes 40-mm-Trackingfenster und fällt bei Unsicherheit auf das 40-mm-Startfenster zurück.

P2.2 ergänzt danach ein 55-mm-Fenster und als letzte Stufe die vollständige 70-mm-Suche.

Nach Totalverlust beginnt der nächste Frame wieder im sicheren Startzustand.

Jeder Versuch speichert das tatsächlich angewendete Fenster, den Folgezustand, Rohsignale, Ablehnungsgründe, Laufzeit und die abschließende Entscheidung.

## Warum die Reihenfolge sinnvoll ist

Die kleine ROI soll zunächst nur den lokalen Maßstab verbessern und Rechenarbeit reduzieren.

Ein Fallback wird erst ausgelöst, wenn Feldqualität, Netzsignale, Geometrie, Sprungplausibilität oder Randabstand gegen eine Annahme sprechen.

Die größere Suche ist bewusst nachgeordnet, weil eine permanente Vollsuche keinen adaptiven Vorteil hätte.

Williams ist noch später eingeordnet und standardmäßig deaktiviert, weil eine physikalische Korrektur erst nach einer geometrisch plausiblen Detektion sinnvoll wäre und derzeit keinen belegten Genauigkeitsgewinn besitzt.

## Bewertungsmetriken

| Frage | Metrik | Warum sie benötigt wird |
|---|---|---|
| Liegt die Referenz vor der Detektion sicher im Fenster? | Inside-Coverage und sichere Coverage mit 1 mm Rand | Ein Treffer am Fensterrand ist für stabile Nachführung nicht ausreichend. |
| Arbeitet die Fallback-Kaskade? | Erstrate, Fallbackrate je Stufe, Recovery-Rate und endgültige Ausfallrate | Damit wird zwischen lokaler Unsicherheit, erfolgreicher Erholung und Totalverlust unterschieden. |
| Verletzt eine Vorhersage die Geometrie? | Randverletzungen, Mindestabstand und Sprungplausibilität | Diese Metriken verhindern physisch unmögliche oder abgeschnittene Ergebnisse. |
| Wird die Position besser? | Paarweiser Median-, P95- und Maximalfehler auf identischen Frames | Aggregierte Erfolgsraten allein könnten eine Verschlechterung der Lokalisierung verdecken. |
| Sind P1 und P2 wirklich vergleichbar? | Identische Frame-IDs, Referenzen, Erfolgsmenge, Decoder-, Modell- und ROI-Provenienz | Nur ein Same-Scenario-Vergleich darf ein Optimierungsgate beeinflussen. |
| Wie teuer ist die Kaskade? | End-to-End-Laufzeit P50 und P95 einschließlich Wiederholungen | Ein Fallback muss in die reale Laufzeit eingehen. |
| Wie belastbar ist die Evidenz? | Referenzart, unabhängige Labels, Datenhashes und Freigabestatus | Technische Abnahme und wissenschaftliche Freigabe dürfen nicht vermischt werden. |

## Technische Abnahme

| Gate | Kanonisches Ergebnis | Status |
|---|---:|---|
| Sichere Coverage mindestens 99 % | 100 % auf der primären realen Sequenzevidenz | Bestanden |
| Randverletzungen | 0 | Bestanden |
| Endgültige Ausfallrate nicht höher als Same-Scenario-P1 | P2 0 % gegenüber P1 0 % | Bestanden |
| Alle auswertbaren technischen Gates | wahr | Bestanden |

Alle realen Frames wurden im ersten Versuch akzeptiert.

Deshalb betrugen die beobachteten realen Fallback- und Totalverlustraten jeweils null, während es weder Recovery-Gelegenheiten noch Recovery-Ereignisse gab und die Recovery-Rate folglich nicht auswertbar ist.

Die synthetischen Stressfälle prüfen die Fallback- und Verlustpfade, die kleine reale Evidenzmenge hat diese Pfade jedoch nicht ausgelöst.

## Paarweiser Realvergleich

P2.1 und P2.2 liefern auf allen beobachteten Realframes dieselben Ortsfehler, weil kein Expanded- oder Full-search-Fallback benötigt wurde.

| Population | Frames | P1 Median / P95 [mm] | P2 Median / P95 [mm] | Delta Median / P95 [mm] | Bewertung |
|---|---:|---:|---:|---:|---|
| Repository, links, historische Masken | 3 | 0,434 / 0,594 | 0,746 / 0,758 | +0,311 / +0,164 | Schlechter |
| Dummy2, rechts, alle Lastphasen | 4 | 0,187 / 0,261 | 0,393 / 0,536 | +0,206 / +0,275 | Schlechter |
| Dummy2, links, Peak-Load | 2 | 0,148 / 0,149 | 0,440 / 0,560 | +0,292 / +0,411 | Schlechter |
| Dummy2, rechts, Peak-Load | 2 | 0,147 / 0,150 | 0,470 / 0,550 | +0,323 / +0,400 | Schlechter |

Beim linken Dummy2-Replay über alle vier Lastphasen verbessert P2 zwar den P95 von 1,335 mm auf 0,703 mm, verschlechtert aber den Median von 0,148 mm auf 0,481 mm.

Diese Vier-Frame-Auswertung enthält entlastete Zwischenstufen und teils von Stufe 55 fortgeschriebene Pseudoreferenzen und ist deshalb keine tragfähige Grundlage für eine Promotion.

Die operativ relevanteren Peak-Load-Teilmengen verschlechtern sich auf beiden Seiten eindeutig.

Damit besteht die adaptive Steuerung ihre Sicherheitsprüfung, aber nicht das Genauigkeitsgate.

## Laufzeit

Die End-to-End-P50 liegt bei den 40-mm-Replays je nach Population ungefähr zwischen 0,74 und 0,87 Sekunden pro Frame.

P2.2 zeigt ohne ausgelösten Fallback keinen Genauigkeitsvorteil und nur Messrauschen bei der Laufzeit.

Die Laufzeit ist hier kein Entscheidungsgrund, weil die Lokalisierungsqualität bereits gegen eine Promotion spricht.

## CrackMNIST und die 128-Pixel-Frage

CrackMNIST bleibt für P2 ein Einzelbild-Signalaudit und keine physische Sequenzevidenz.

Auf dem Validierungssplit passieren 98,95 % der auswertbaren Detektionen das rohe Kandidatengate, auf dem Testsplit sind es 98,61 %.

Die nominalen einseitigen 95-Prozent-Obergrenzen für selbstsichere Fehler liegen bei 0,493 % auf Validierung und 0,717 % auf Test.

Diese Grenzen sind wegen korrelierter Augmentationen nicht als unabhängige Sequenzgarantie zu interpretieren.

Die auf 128 × 128 vorbereiteten Mendeley-Tensoren lösen das Auflösungsproblem nicht, weil sie bereits auf ein festes Raster interpoliert sind.

Der verifizierte Roh-CSV-Download löst dagegen die infrastrukturelle Seite des Problems, weil daraus beliebige physische ROIs erneut auf die originalen 256 × 256 Modelleingaben interpoliert werden können.

## Mendeley-Datensatz

Der Datensatz `10.17632/dywwnjv22h.1` wurde in Version 1 erfasst.

Das 5,81-GB-Roh-CSV-Archiv, das 1,48-GB-PT-Archiv, die Crack-Length-Tabelle und die Readme wurden jeweils in Größe und SHA-256 verifiziert.

Das fremde Modellarchiv wurde bewusst nicht geladen, weil P2 auf der originalen CrackPy-Version und ihren eingefrorenen Gewichten basiert.

Im PT-Archiv wurden 19 Experimente, 186 Chunks und 17.897 Frames mit Form `1 × 2 × 128 × 128` gefunden.

Ein Frame enthält nichtendliche Werte, und die Differenz zur publizierten Zahl von 17.925 Frames bleibt als offene Provenienzfrage dokumentiert.

Die Crack-Length-Tabelle enthält keine Tip- oder Pfadlabels.

Deshalb ist der Datensatz technisch für neue physische ROI-Interpolationen vorbereitet, aber noch nicht für eine quantitative adaptive ROI-Freigabe annotiert.

Das Ergebnis enthält bereits ein Annotationsschema für Experimente, Frames, physische Kalibrierungen und Tip-/Pfadannotation sowie die Regel, alle Ableitungen eines Experiments im selben Split zu halten.

## Williams, Winkel und Pfad

Die historische Williams-Korrektur verschob den Dummy2-Tip von 0,740 mm auf 1,807 mm Abstand zur vorhandenen Pseudoreferenz und benötigte im Median 15,716 Sekunden.

Da weder unabhängige Ground Truth noch ein belastbarer Residuenvertrag vorliegen, bleibt Williams in P2 ausgeschaltet.

Das Pfadmodell wurde im kanonischen P2-Lauf nicht geladen, weil die verfügbare Realevidenz weder Pfad noch Winkel unabhängig labelt.

Pfad und Winkel sollten nach der Mendeley-Annotation zunächst als unveränderte Originalmodell-Baseline ausgewertet werden.

FEM oder Virtual DIC sind danach sinnvoll, um seltene Geometrien und kontrollierte Risspfade abzudecken, dürfen reale unabhängige Labels aber nicht ersetzen.

## Müssen Modelle neu trainiert werden?

Für die beantwortete P2-Frage war Retraining weder nötig noch methodisch sinnvoll, weil zuerst isoliert geprüft werden musste, ob allein die ROI-Steuerung das eingefrorene Originalmodell verbessert.

Das negative Lokalisierungsergebnis zeigt, dass eine kleinere ROI nicht automatisch einen günstigeren Maßstab für das vorhandene Modell erzeugt.

Retraining sollte erst erwogen werden, wenn verifizierte Mendeley-Tiplabels zeigen, ob der Fehler aus Maßstab, Interpolation, Domänenverschiebung oder dem eigentlichen Modell stammt.

Falls die kleinere ROI auf unabhängigen Labels systematisch schlechter bleibt, ist ein skalenbewusstes Fine-Tuning oder ein Modell mit expliziter physischer ROI-Konditionierung plausibler als weiteres Schwellwert-Tuning.

## Empfohlenes Refinement

1. Die Mendeley-Annotation sollte parallel nach Experimentgruppen und mit überprüfter Pixel-zu-Millimeter-Kalibrierung durchgeführt werden.
2. Auf der akzeptierten Annotation sollten feste 70 mm, adaptive 40 mm sowie 40/55/70 mm paarweise auf exakt denselben Frames verglichen werden.
3. ROI- und Gateparameter dürfen nur auf einer gruppengetrennten Validierungsmenge angepasst werden.
4. Erst danach sollte entschieden werden, ob ein skalenbewusstes Fine-Tuning erforderlich ist.
5. Pfad und Winkel sollten zunächst mit den originalen CrackPy-Gewichten als Baseline gemessen werden.
6. FEM oder Virtual DIC sollten nur zur gezielten Erweiterung von Randfällen eingesetzt werden.

## Reproduzierbarkeit

Der kanonische Lauf verwendete Python 3.12.13, PyTorch 2.14.0 mit CUDA 13.0 und eine NVIDIA GeForce RTX 5070 Ti.

Der Lauf ist an Git-Commit `905be6a6736fef79ee2004b706bd4d54bd5d84c8` gebunden.

Das Ergebnisartefakt hat SHA-256 `f0485708a756150d145137ad225dca989cdadf9dceccdc174a98dcfce3e719a6`.

Alle 13 lokalen P0/P1-, DIC- und Referenzartefakte sowie die benötigten Mendeley-Dateien sind im Ergebnis separat inhaltsadressiert.

Die technische Implementierung ist abgeschlossen, die wissenschaftliche Freigabe bleibt bis zu unabhängigen realen Sequenzlabels bewusst geschlossen.

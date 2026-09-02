# CTD P0 Baseline Design

## Ziel

P0 schafft eine reproduzierbare, unveränderte Ausgangslinie für die spätere Optimierung der Crack-Tip Detection auf Basis von CrackPy 1.3.0 und den veröffentlichten Originalgewichten.
P0 optimiert noch kein Modell und trainiert kein Modell neu.
Es beantwortet belastbar, wie gut, wie zuverlässig und wie schnell der vorhandene Stand unter klar benannten Bedingungen ist.

## Abgrenzung

Die Implementierung bleibt additiv und verändert weder die vorhandene CrackPy-Inferenz noch alte numerische Referenzen.
Understand Anything, Wissensgraphen und die allgemeine Architektur-Refaktorierung gehören nicht zu P0.
Adaptive ROI wird in P0 als vorhandene sequenzielle Offset-Nachführung dokumentiert, aber noch nicht neu entwickelt.
Ein datengetriebenes adaptives ROI-Verfahren ist Gegenstand einer späteren Stufe und benötigt Mendeley-Annotationen oder eine gleichwertige Referenz.

## Baseline-Modi

### B0: Tip-only

B0 verwendet das eingefrorene `ParallelNets`-Modell und den originalen maskenbasierten CrackPy-Decoder.
Der ungenutzte Koordinatenkopf wird zusätzlich als Diagnose ausgewertet, ohne die historische Baseline umzudefinieren.

### B1: Tip, Pfad und Winkel

B1 ergänzt das eingefrorene `UNetPath`-Modell.
Der Winkel wird wie in CrackPy aus der segmentierten lokalen Pfadgeometrie abgeleitet und nicht als eigenständige Modellvorhersage bezeichnet.

### B2: Tip plus Williams-Korrektur

B2 führt die vorhandene Williams-basierte Korrektur auf dem mit CrackPy ausgelieferten DIC-Beispiel aus.
Ohne unabhängige korrigierte Ground Truth wird B2 als Funktions-, Laufzeit- und Verschiebungsreferenz berichtet, nicht als belegter Genauigkeitsgewinn.

## Datenrollen

CrackMNIST 2.0.1 ist der kontrollierte quantitative Tip-Benchmark.
Die 128-mal-128-Variante wird ohne Informationsgewinn auf die native Modellgröße 256-mal-256 skaliert, wodurch die Baseline-Kompatibilität geprüft wird, aber keine höhere Messauflösung entsteht.
Fehler werden deshalb primär in Originalpixeln berichtet.
Eine nominelle Umrechnung in Millimeter darf nur separat und mit offengelegter FOV-Annahme erscheinen.

Die originalen CrackPy-Testdaten dienen als Reproduktions-, Pfad-, Winkel- und Korrekturprüfung.
Sie ersetzen keine unabhängige Generalisierungsstudie.

Der Mendeley-Datensatz wird in P0 nicht zum Training genutzt.
P0 erzeugt dafür einen reproduzierbaren Daten-Audit und ein Annotationsschema, damit Tip, Pfad, lokaler Winkel, Unsicherheit und Sequenzbezug parallel annotiert werden können.
Die späteren Datenaufteilungen müssen auf vollständigen Proben beziehungsweise Versuchsreihen beruhen und dürfen keine benachbarten Frames auf Training und Test verteilen.

## Metriken

Die Tip-Auswertung berichtet Erkennungsrate, Ausfallrate sowie euklidischen Fehler als Mittelwert, Median und 95. Perzentil.
Fehlerstatistiken werden sowohl konditional für erfolgreiche Vorhersagen als auch mit expliziter Ausfallzählung dargestellt.
Dice und IoU beschreiben ergänzend die Tip-Maske, ersetzen aber nicht die Positionsmetrik.

Die Pfadauswertung berichtet symmetrische mittlere Konturdistanz, Hausdorff-95-Distanz, Dice, IoU und die Rate leerer Pfadvorhersagen.
Die Winkelauswertung berichtet den kleinsten absoluten Richtungsfehler modulo 180 Grad und zählt nicht auswertbare Fälle separat.

Die Laufzeitauswertung trennt Kaltstart, Vorverarbeitung, Modellinferenz, Nachverarbeitung, optionale Pfadinferenz und Williams-Korrektur.
Warmlaufzeiten werden nach Warm-up mit Gerätesynchronisation als Median und 95. Perzentil berichtet.
Zusätzlich werden Durchsatz, Prozessspeicher und GPU-Spitzenspeicher erfasst, soweit die Plattform diese Werte bereitstellt.

## Reproduzierbarkeit und Artefakte

Jeder Lauf speichert Git-Stand, Python-, PyTorch- und CrackPy-Version, Gerät, Seeds, Datensatzvariante, Split, Stichprobenzahl und SHA-256-Prüfsummen der Modellgewichte.
Die maschinenlesbaren Einzelergebnisse werden als JSON gespeichert.
Der P0-Report fasst Befunde, Grenzen und die Entscheidung für P1 zusammen.
Ein fehlender Datensatz, Downloadfehler oder nicht auswertbarer Modus muss als sichtbarer Status erscheinen und darf nicht stillschweigend aus der Statistik verschwinden.

## P0-Abnahmekriterien

P0 ist abgeschlossen, wenn die Originalmodelle ohne Retraining geladen wurden, B0 und B1 auf den verfügbaren Referenzdaten durchgelaufen sind, B2 entweder reproduzierbar ausgeführt oder mit einem konkreten technischen Blocker belegt wurde und der CrackMNIST-Benchmark maschinenlesbare Ergebnisse erzeugt hat.
Der Mendeley-Audit und das Annotationsschema müssen vorliegen.
Alle neuen Tests und die unveränderten relevanten CrackPy-Tests müssen erfolgreich sein.
Der Report muss Messergebnisse, Ausfälle, Einschränkungen und eine begründete P1-Empfehlung enthalten.

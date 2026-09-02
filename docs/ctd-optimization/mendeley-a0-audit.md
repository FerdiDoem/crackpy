# Mendeley A0 Data Audit

## Ergebnis

Der Datensatz `dywwnjv22h.1` ist als zusätzlicher Sequenz- und Domänen-Datensatz geeignet, liefert aber keine dokumentierte Ground Truth für Crack-Tip-Koordinaten, Risspfad, lokalen Winkel oder ROI.
Er kann deshalb parallel annotiert werden, darf in P0 jedoch nicht als quantitative Tip-, Pfad- oder Winkelreferenz ausgegeben werden.

## Identität und Lizenz

- Titel: *Data for Mixed-mode fatigue crack propagation path prediction using deep learning*.
- DOI: [10.17632/dywwnjv22h.1](https://doi.org/10.17632/dywwnjv22h.1).
- Version: 1.
- Lizenz: CC BY 4.0.
- Veröffentlichungsseite: [Mendeley Data](https://data.mendeley.com/datasets/dywwnjv22h/1).

## Veröffentlichte Dateien

| Datei | Größe | Dokumentierter Inhalt |
|---|---:|---|
| `1. DataFromDIC_CSV.rar` | 5.814.691.113 Byte | Roh-DIC-Verschiebungsfelder als CSV |
| `2. DataAfterInterpolation_PT.rar` | 1.484.643.198 Byte | Interpolierte Verschiebungsfelder als PyTorch-Tensoren |
| `3. TrainedModel_PT.zip` | 1.303.694.078 Byte | Vortrainierte Modelle der Veröffentlichung |
| `4. Cycles vs Crack Length.xlsx` | 43.064 Byte | Zyklen-Risslängen-Werte für vier Proben |
| `5. Readme.txt` | 633 Byte | Namenskonvention und Frame-Zyklus-Bezug |

Das öffentliche Dateiinventar ist über die [Mendeley-API](https://data.mendeley.com/public-api/datasets/dywwnjv22h/files?folder_id=root&version=1) prüfbar.
Die veröffentlichte Namenskonvention ist direkt im [Readme](https://data.mendeley.com/public-files/datasets/dywwnjv22h/files/2c1c5dc2-dfc3-49a8-8e40-19a220f01bff/file_downloaded) beschrieben.

## Sicher feststellbare Struktur

Der Herausgeber nennt 19 Proben.
Die Ordnernamen kodieren Rissart, Anfangswinkel, Lastniveau, Proben-ID sowie Start- und End-Frame.
`C` bezeichnet einen zentralen Riss und `E` einen Randriss.
Die dokumentierten Anfangswinkel sind 0, 15 und 30 Grad.
Die dokumentierten Lastniveaus sind 15, 17,5 und 20 Prozent.
Ein Bild entspricht laut Readme 30 Zyklen.
Framebereiche und Zyklusregel sprechen für echte zeitliche Sequenzen, was hier ausdrücklich als Inferenz und nicht als publiziertes Sequenzmanifest behandelt wird.

## Vorhandene und fehlende Referenzen

Rohfelder, interpolierte Tensoren, Versuchskontext und eingeschränkte Risslängeninformationen sind vorhanden.
Die Risslängentabelle deckt laut Herausgeber nur vier Proben ab.
Eine Risslänge allein bestimmt ohne Ursprung, Seitenkonvention und Pfadgeometrie weder einen zweidimensionalen Tip noch einen lokalen Winkel.
Es sind keine pro Frame dokumentierten Tip-Koordinaten, Pfadpolylinien, Tangentenwinkel, ROI-Grenzen oder Unsicherheitslabels veröffentlicht.

## Grenzen des A0-Fernaudits

Ohne vollständigen Download sind Inventar, Dateigrößen, Lizenz, Checksums, publizierte Formate und die Readme-Metadaten prüfbar.
Tensorformen, tatsächliche CSV-Spalten, vollständige Ordnerliste, physisches Sichtfeld, Pixel-zu-Millimeter-Skalierung und nicht dokumentierte Inhalte der Archive bleiben bis zum lokalen A1-Ingest offen.
Diese offenen Punkte müssen vor der ersten Annotation anhand mindestens einer vollständig entpackten Probe geklärt werden.

## P0-Entscheidung

Die Mendeley-Annotation kann parallel zu Frozen-Model-Benchmarks beginnen, sobald der A1-Ingest Koordinatensystem und Skalierung bestätigt hat.
Die Aufteilung in Training, Validierung und Test wird vorher auf Probenebene eingefroren.
Kein Frame, Crop, augmentiertes Derivat oder Modell-Pseudolabel einer Probe darf in einem anderen Split landen.

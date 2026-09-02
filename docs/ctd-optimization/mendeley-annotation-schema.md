# Mendeley Annotation Schema

## Zweck

Das Schema ermöglicht die parallele Erfassung von Crack Tip, Pfad, lokalem Winkel und adaptiver ROI, ohne spätere Modell- oder Pixelkonventionen vorwegzunehmen.
Die kanonische Annotation ist ein JSONL-Datensatz mit genau einem Datensatz pro Frame.
Koordinaten werden in Millimetern gespeichert und durch eine explizite Transformation mit der Bildmatrix verbunden.

## Pflichtidentität

| Feld | Bedeutung und Grund |
|---|---|
| `schema_version` | Hält spätere Schemaänderungen nachvollziehbar. |
| `source_dataset` | Verweist stabil auf `10.17632/dywwnjv22h.1`. |
| `specimen_id` | Ist die primäre Gruppierungs- und Split-Einheit. |
| `frame_id` | Identifiziert das Einzelbild innerhalb der Probe. |
| `cycle_count` | Verbindet den Frame mit dem Ermüdungsverlauf. |
| `crack_type` | Bewahrt die publizierte Unterscheidung zwischen zentralem und Randriss. |
| `initial_angle_deg` | Bewahrt die publizierte Versuchskonfiguration. |
| `load_level_percent` | Bewahrt das publizierte Lastniveau. |
| `source_file` | Macht die Annotation zur konkreten Roh- oder Tensorquelle rückverfolgbar. |
| `source_sha256` | Erkennt vertauschte oder nachträglich veränderte Quelldateien. |

## Koordinatenrahmen

| Feld | Bedeutung und Grund |
|---|---|
| `field_shape_yx` | Dokumentiert Zeilen und Spalten des annotierten Feldes. |
| `coordinate_unit` | Ist für die kanonische Fassung immer `mm`. |
| `origin_xy_mm` | Definiert den Ursprung der Feldkoordinaten. |
| `x_axis_direction` | Verhindert eine unbemerkte Links-Rechts-Spiegelung. |
| `y_axis_direction` | Verhindert eine unbemerkte Bild-zu-Mechanik-Spiegelung. |
| `pixel_to_physical_affine` | Bildet homogene Pixelkoordinaten reproduzierbar auf Millimeter ab. |
| `fov_width_height_mm` | Macht ROI-Größen und Auflösungsvergleiche interpretierbar. |

## Crack-Tip-Annotation

| Feld | Bedeutung und Grund |
|---|---|
| `tip_xy_mm` | Ist die kanonische zweidimensionale Tip-Position. |
| `tip_visibility` | Unterscheidet sichtbar, teilweise sichtbar, außerhalb des Feldes und nicht bestimmbar. |
| `tip_confidence` | Erfasst die annotatorische Sicherheit von 0 bis 1. |
| `tip_boundary_distance_mm` | Zeigt, ob die Referenz für lokales Recropping ausreichend Rand besitzt. |

## Pfad- und Winkelannotation

| Feld | Bedeutung und Grund |
|---|---|
| `path_polyline_xy_mm` | Speichert den geordneten Risspfad als Punkte in physikalischen Koordinaten. |
| `path_visibility` | Trennt einen nicht sichtbaren Pfad von einer leeren oder fehlerhaften Annotation. |
| `local_angle_deg` | Beschreibt die lokale ungerichtete Tangente am Tip modulo 180 Grad. |
| `angle_window_mm` | Definiert die physikalische Pfadlänge, aus der der Winkel bestimmt wurde. |
| `angle_method` | Dokumentiert, ob der Winkel manuell, per lokaler Regression oder per Spline ermittelt wurde. |

## ROI-Annotation

| Feld | Bedeutung und Grund |
|---|---|
| `roi_center_xy_mm` | Definiert das ideale Zentrum für einen lokalen Refiner. |
| `roi_width_height_mm` | Beschreibt die physikalische Fenstergröße unabhängig von der Pixelauflösung. |
| `roi_tip_margin_mm` | Misst den kleinsten Abstand des Tips zum ROI-Rand. |
| `roi_contains_visible_path` | Prüft, ob das Fenster neben dem Tip genügend Pfad für die Winkelbestimmung enthält. |

## Qualitäts- und Reviewfelder

| Feld | Bedeutung und Grund |
|---|---|
| `quality_flags` | Erfasst fehlendes Feld, Dekorrelation, Randnähe, Mehrdeutigkeit und mehrere Risse getrennt. |
| `annotation_status` | Unterscheidet Entwurf, Erstprüfung, Konflikt und freigegeben. |
| `annotator_id` | Erlaubt Inter-Annotator-Auswertung ohne Klarnamen im Datensatz. |
| `reviewer_id` | Belegt eine unabhängige Prüfung. |
| `annotation_timestamp` | Macht den Entstehungsstand nachvollziehbar. |
| `notes` | Nimmt kurze Ausnahmebegründungen auf und darf keine fehlenden strukturierten Felder ersetzen. |

## Minimaler Beispieldatensatz

```json
{
  "schema_version": "1.0.0",
  "source_dataset": "10.17632/dywwnjv22h.1",
  "specimen_id": "example_only",
  "frame_id": 0,
  "cycle_count": 0,
  "crack_type": "central",
  "initial_angle_deg": 15.0,
  "load_level_percent": 17.5,
  "source_file": "to_be_verified",
  "source_sha256": "to_be_computed",
  "field_shape_yx": [0, 0],
  "coordinate_unit": "mm",
  "origin_xy_mm": [0.0, 0.0],
  "x_axis_direction": "to_be_verified",
  "y_axis_direction": "to_be_verified",
  "pixel_to_physical_affine": null,
  "fov_width_height_mm": null,
  "tip_xy_mm": null,
  "tip_visibility": "not_reviewed",
  "tip_confidence": null,
  "tip_boundary_distance_mm": null,
  "path_polyline_xy_mm": [],
  "path_visibility": "not_reviewed",
  "local_angle_deg": null,
  "angle_window_mm": null,
  "angle_method": null,
  "roi_center_xy_mm": null,
  "roi_width_height_mm": null,
  "roi_tip_margin_mm": null,
  "roi_contains_visible_path": null,
  "quality_flags": [],
  "annotation_status": "draft",
  "annotator_id": null,
  "reviewer_id": null,
  "annotation_timestamp": null,
  "notes": "Template only; no measurement values are asserted."
}
```

## Split- und Leakage-Regeln

Alle Frames derselben Probe müssen vollständig in genau einem Split verbleiben.
Zeitfenster, Crops, Augmentationen, Interpolationen und Pseudolabels erben immer den Split ihrer Probe.
Die Splitliste wird vor jeder Augmentation und vor jedem Modell-Fine-Tuning festgeschrieben.
Ein kausales Sequenzmodell darf bei der Vorhersage eines Frames keine späteren Frames verwenden.
Der finale Test reserviert vollständig unberührte Proben und nach Möglichkeit zusätzlich mindestens eine gehaltene Kombination aus Rissart, Winkel und Lastniveau.

## Reviewverfahren

Eine Erstannotation erfasst Tip und Pfad gemeinsam, damit beide geometrisch konsistent bleiben.
Der lokale Winkel wird aus der freigegebenen Pfadpolylinie mit einem festen physikalischen Fenster abgeleitet und nur bei sichtbarer Geometrie manuell überschrieben.
Mindestens eine geschichtete Teilmenge wird doppelt annotiert, um Tip-Abstand, Pfaddistanz und Winkelabweichung zwischen Annotatoren zu quantifizieren.
Konfliktfälle werden nicht gemittelt, sondern von einer unabhängigen Person entschieden und als Konflikt protokolliert.

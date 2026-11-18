# 0004: Erkennung (T3): Detektor-Port, RF-DETR als Hauptdetektor, Kachel-Variante

Datum: 2026-11-18

## Was
- **Port:** `application/detector.py` legt fest: Ein Detektor bekommt ein Bild (RGB-Array) und liefert
  Personenboxen (`Detection`: x, y, Breite, Höhe, Score) in Pixeln dieses Bildes. Die Pipeline und die
  Messung kennen nur diesen Port.
- **Umsetzungen** (`infrastructure/`): `RfDetrDetector` (Apache 2.0, Hauptdetektor) und `YoloDetector`
  (AGPL-3.0, nur optionale Zusatzabhängigkeit `[yolo]`). Beide filtern auf die COCO-Klasse "Person".
- **Kacheln:** Eigene Funktion statt SAHI. `domain/tiling.py` berechnet die Rechtecke, `TiledDetector`
  (`application/tiling.py`) verpackt jeden Detektor: Kacheln erkennen, Boxen zurückrechnen, Doppelte
  per NMS (IoU 0,5) zusammenführen. Start: 640 px, 20 % Überlappung (Konfiguration).
- **Messung:** `domain/metrics.py` setzt die Messregeln der Spezifikation um (Treffer ab IoU 0,5, jede
  Beschriftung nur einmal, Zuordnung nach Score). Alle vier Klassen des Testsets zählen als "Person".
  Nah/fern-Grenze = Median der Boxhöhen der Beschriftungen (52,06 px, vom Entwickler bestätigt).
  Befehl: `matchstats evaluate --out <Ordner>`.
- **Abhängigkeiten:** `numpy` und `pillow` (Kern), `rfdetr` (Extra `detect`), `ultralytics` (Extra
  `yolo`). torch kommt als CPU-Version, unter Python 3.13 geprüft (torch 2.15, rfdetr 1.12).

## Messergebnis (60 Testbilder, Score 0,3, RF-DETR Small / YOLO11s)
Zeiten mit Aufwärmlauf vor der Messung, ein einzelner Lauf auf dem Entwicklungsrechner (schwankt).

| Variante | Recall | Precision | Recall nah | Recall fern | s/Bild |
|---|---|---|---|---|---|
| rfdetr-whole | 81,7 % | 72,2 % | 95,4 % | 67,9 % | 0,49 |
| rfdetr-tiles | 95,0 % | 36,2 % | 96,9 % | 93,0 % | 3,53 |
| yolo-whole | 59,5 % | 85,7 % | 85,7 % | 33,3 % | 0,18 |
| yolo-tiles | 88,0 % | 52,6 % | 94,8 % | 81,2 % | 1,93 |

Die niedrige Precision der Kacheln kommt zu einem großen Teil von echten, aber nicht beschrifteten
Personen (Zuschauer, Ordner, Bank). Das ist ein Messartefakt; ein Spielfeld-Filter (Kalibrierung,
Woche 2) würde es beheben. Die endgültige Entscheidung "Kacheln ja/nein, welcher Detektor" fällt in T7.

## Warum
- **Port:** YOLO und RF-DETR sind austauschbar, die Lizenzfrage (AGPL) bleibt auf `infrastructure/`
  begrenzt, und die Messung läuft mit einem Fake-Detektor ohne Modell im Test.
- **RF-DETR zuerst:** Apache 2.0 (Repo wird wahrscheinlich öffentlich) und in der Messung besser bei
  fernen Spielern als YOLO.
- **Eigene Kachelfunktion:** ca. 40 Zeilen, keine weitere Abhängigkeit (SAHI hätte opencv und shapely
  nachgezogen).
- **Median als Grenze:** Die Spezifikation verlangt eine Grenze nach Sichtung der Daten; der Median
  teilt die Beschriftungen in zwei gleich große Gruppen.

## Alternativen
- **SAHI-Bibliothek:** fertig, aber zusätzliche Abhängigkeiten und Detektor-spezifische Adapter.
- **Nur YOLO:** schneller (0,11 s/Bild), aber AGPL und schwächer bei fernen Spielern.
- **Feste Grenze (z. B. 50 px):** einfacher, aber nicht aus den Daten abgeleitet.

## Offen
- Der Score 0,3 ist fest und wurde nicht variiert; er verschiebt Recall und Precision.
- Kachel-Zusammenführung nur per IoU-NMS: eine am Kachelrand halb abgeschnittene Person kann neben der
  ganzen als Doppelter bleiben. Nicht gesondert gemessen.
- RF-DETR meldet "nicht für Inferenz optimiert"; mögliche Beschleunigung nicht untersucht.
- YOLO11s wurde gemessen; neuere YOLO-Versionen nicht geprüft.
- Rechenzeit: Kacheln mit RF-DETR brauchen ca. 3,5 s pro Bild. Mit `detect_every=5` sind das etwa 0,7 s
  Rechenzeit je Videosekunde (rechnerisch, nicht am Clip gemessen).

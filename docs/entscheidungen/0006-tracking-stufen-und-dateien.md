# 0006: Tracking in Stufen mit Dateien, eigener Tracker hinter Port (T4)

Datum: 2026-11-18

## Was
- Das Tracking läuft in zwei Stufen. Jede schreibt eine Datei in den Lauf-Ordner: `detections.json` (Erkennung auf jedem N-ten Bild) und `tracks.json` (Spuren). Dazu `summary.json` (Kennzahlen, Laufzeiten) und `render\` (Video und Kontaktbögen als Zählhilfe).
- Der Tracker ist ein Port `Tracker` in `application/tracker.py`. Die Umsetzung `ByteTrackLikeTracker` steht im selben Modul. Sie ist reine Rechnung mit numpy und scipy (`linear_sum_assignment` für die Zuordnung per IoU). Wie ByteTrack ordnet sie zuerst hohe Scores zu, dann niedrige nur gegen bestätigte Spuren.
- Bewegungsmodell: konstante Geschwindigkeit der Boxmitte, Boxgröße = letzte Messung. Zwischen zwei Treffern wird linear interpoliert (`visible: false`).
- Stufen-Cache: `detections.json` wird nur wiederverwendet, wenn die Erkennungsparameter und das Video (Dateiname, Bildanzahl, Bildgröße) gleich sind. Das Tracking läuft immer neu, es liest nur die Datei.
- Dateiformate tragen je eigene `schema_version`. `tracks.json` ist Version 2; Version 1 wird mit klarer Meldung abgelehnt. `detections.json`, `summary.json` und `run.json` sind Version 1. Detektor- und Bibliotheksversionen stehen in `detections.json` und `tracks.json`.
- Kamerabewegung ist nicht Teil von T4.
- Standardwerte in `default.toml`: `track_high_score` 0,4 und `track_min_hits` 3.

## Warum
- **Stufen mit Dateien:** Die Erkennung ist der teure Teil. Im Lauf run-003 dauerte sie 557 s, das Tracking 3,5 s (Quelle: `summary.json` von run-003). Tracker-Parameter lassen sich so beliebig oft ohne neue Erkennung prüfen. Das folgt der Vorgabe "Rechenzeit minimal" aus der Spezifikation (Entwurf T4).
- **Tracker als Port:** Die Stufen kennen nur den Port. Ein anderer Tracker (z. B. mit Kalman-Filter) lässt sich ohne Umbau der Stufen einsetzen.
- **Eigene Umsetzung:** Die Logik ist überschaubar und mit künstlichen Daten testbar (`tests/test_tracker_rules.py`).
- **Konstantes Geschwindigkeitsmodell statt Kalman:** einfacher zu lesen und zu prüfen. Ob das bei Schwenks reicht, ist nicht gemessen; genau dafür ist die Handzählung (AK T4) gedacht.
- **Cache über Parameter plus Videoidentität:** Name, Bildanzahl und Größe sind schnell zu prüfen. Ein Inhalts-Hash über das ganze Video wurde nicht gemessen; er wäre bei großen Clips vermutlich langsamer.
- **`tracks.json` Version 2 statt Erweiterung von Version 1:** Neue Pflichtfelder (`fps`, `frame_count`, `versions`). Eine alte Datei ohne sie würde sonst still unvollständig gelesen.

### Probeläufe für die Standardwerte (Clip1, 60 s, RF-DETR Ganzbild)
Quelle: `summary.json` der Läufe im Repo. Clip-Länge 1 Minute, daher sind Spuren je Minute gleich der Spurenzahl.

| Lauf | track_high_score / track_min_hits | Spuren | mittlere Spurlänge (s) | Anteil gesehen |
|---|---|---|---|---|
| run-002 | 0,5 / 2 | 191 | 4,68 | 19,6 % |
| run-003 | 0,4 / 3 | 226 | 5,40 | 19,8 % |
| (kein Lauf im Repo) | 0,3 / 3 | **unklar** | **unklar** | **unklar** |

Zusätzlich gab es einen einmaligen Probelauf (nur Tracking, auf den gespeicherten Erkennungen von run-002, mit einem Wegwerf-Skript, nicht im Repo gespeichert). Dort ist **Median** statt Mittelwert der Spurlänge berichtet, daher passen die Zahlen nicht zur Tabelle oben:

| track_high_score / track_min_hits | Spuren | Median Spurlänge (s) | Spuren je Bild (Mittel) |
|---|---|---|---|
| 0,5 / 2 | 191 | 2,0 | 14,9 |
| 0,5 / 3 | 153 | 2,4 | 12,9 |
| 0,4 / 2 | 270 | 2,0 | 21,2 |
| 0,4 / 3 | 226 | 2,6 | 20,3 |
| 0,3 / 2 | 374 | 1,8 | 27,5 |
| 0,3 / 3 | 300 | 2,4 | 25,7 |

Die Spurenzahlen stimmen mit `summary.json` überein (191 bei 0,5/2; 226 bei 0,4/3 in run-003, das neu erkannt wurde). Die Probezahlen sind nicht reproduzierbar abgelegt. Die Zahlen sind nur Hilfszahlen, keine Messung der Zuordnung. Die Entscheidung über die Standardwerte liegt beim Entwickler. Die Messung der ID-Wechsel (Handzählung) ist noch offen, siehe `docs/berichte/t4-zaehlung.md`.

## Alternativen
- **ultralytics bzw. boxmot:** verworfen. Nach Entwurf T4 sind beide AGPL-3.0; diese Lizenzangabe habe ich im Repo nicht geprüft. Das Projekt hält YOLO nur optional.
- **supervision:** verworfen, bringt viele Abhängigkeiten für einen kleinen Teil.
- **Kalman-Filter:** nicht gewählt. Die Umsetzung bleibt einfach; ein Kalman-Filter kann später hinter demselben Port ergänzt werden.
- **Alles in einer Stufe (wie die Pipeline):** verworfen. Jede Tracker-Änderung würde dann die Erkennung neu berechnen.
- **Video-Hash als Cache-Schlüssel:** nicht gewählt (siehe Warum).
- **Kacheln sofort mit T4:** verschoben. Die Option `--variant tiles` existiert, ist aber nicht am echten Clip getestet.

## Folgen
- Tracker-Parameter lassen sich ohne neue Erkennung prüfen. Der Lauf `--run` nutzt die Einstellungen aus `run.json`.
- Die Dateiformate sind ein Vertrag: Eine Änderung verlangt eine höhere `schema_version` und eine Entscheidung.
- Die Darstellung (`render/`) wird in T6 erweitert, nicht neu gebaut.
- **Entschieden (19.11.2026, Option A):** Der Tracker (`ByteTrackLikeTracker`) bleibt in `application/`, obwohl CLAUDE.md Implementierungen von Ports sonst nach `infrastructure/` legt. Grund: reine Rechnung ohne Dateien, Video oder Modelle (nur numpy und scipy). Er ist über den Port `Tracker` austauschbar; ein Tracker mit Außenwelt-Zugriff (z. B. ein Modell) käme nach `infrastructure/`. Ausnahme bewusst, der Schichtentest prüft das nicht.
- **Offen:** Ob Kamerabewegung (T4b) nötig ist, entscheidet die Handzählung der ID-Wechsel. Bis dahin ist sie nicht umgesetzt.

# matchstats: Systemkarte

Stand: 2026-11-25, nach T5b1 (Teams je Spur mit `teams.json`, noch nicht an `track` angebunden; davor T5a Teamzuordnung als Messung, T4b). Zwei Teile:
- **Teil A: Zielbild** (abgeleitet aus `docs/workflow-spielanalyse.md`): wie das fertige System aufgebaut ist. Ein **Entwurf zur Bestätigung**, keine Spezifikation. Er ändert weder die Schichten aus CLAUDE.md noch die Woche-1-Spezifikation.
- **Teil B: Stand heute**: was im Repo existiert. Was nicht als *(geplant)* markiert ist, existiert. **unklar** = im Repo nicht gefunden oder nicht entschieden.

# Teil A: Zielbild

## A1. Fachliche Bausteine (Begriffe des Workflows)

```
Spiel (Match)
 └─ Clip  (Video einer Halbzeit/eines Abschnitts + Aufnahme-Profil)
     └─ Lauf (Run)  = ein Verarbeitungsdurchgang mit festen Parametern
         ├─ Erkennungen  → Spuren → Teams
         ├─ Kalibrierung → Feldspuren (Positionen in Metern)
         ├─ Kennzahlen → Bericht
         └─ Korrekturen (getrennt von den Rohdaten)
```
- **Rohdaten sind unveränderlich.** Jede Stufe schreibt eine neue Datei; Korrekturen des Anwenders liegen in einer eigenen Datei und werden beim Lesen darübergelegt.
- **Alles ist abgeleitet:** Ändert sich ein Parameter, entsteht ein neuer Lauf. Neue Kennzahlen brauchen nur die letzte Stufe (Leitprinzip Daten → Erkenntnisse → Darstellung).
- **Messung = Wert + Sichtbarkeit + Unsicherheit.** Unbekannt ist `null`, nie 0.

## A2. Pipeline-Stufen (je Clip und Lauf)

Jede Stufe liest nur Dateien der Vorstufen und schreibt genau ihre eigenen. Bildverarbeitung steckt nur in den Stufen 1 bis 4 (Modelle); ab Stufe 5 wird nur gerechnet.

| Nr | Stufe | Eingabe | Ausgabe | Austauschbar über Port | Stand |
|---|---|---|---|---|---|
| 0 | Import und Aufbereitung | Rohvideo | `clip.mp4`, `clip.json` | `Library`, später `VideoPreparer` (Deinterlacen) | Import da, Deinterlacen manuell |
| 1 | Aufnahmeprüfung: Abschnitte, Kamerabewegung | Video | `segments.json`, `camera.json` | `SegmentClassifier`, `CameraMotionEstimator` | Kamerabewegung **vorhanden** (T4b, `camera.json`); Abschnitte **geplant** |
| 2 | Erkennung | Video (jedes N-te Bild) | `detections.json` | `Detector` (RF-DETR, YOLO) | **vorhanden** |
| 3 | Spurbildung | `detections.json` (+ `camera.json`) | `tracks.json` | `Tracker` | **vorhanden** (T4) |
| 4 | Teamzuordnung und Rollen | Video-Ausschnitte der Spuren, `tracks.json` | `teams.json` (Team, Torhüter, Schiedsrichter, Unsicherheit) | `TeamClassifier` | **Stufe vorhanden** (T5b1: `team_stage`, `teams.json`, Cache), **noch nicht an `track` angebunden** (T5b2); Farbverfahren als Messung seit T5a (`evaluate-teams`) |
| 5 | Kalibrierung und Projektion | Schlüsselbilder (manuell), `tracks.json` | `calibration.json`, `pitch_tracks.json` | `Calibrator` | geplant (Woche 2) |
| 6 | Qualitätsprüfung | alle Vorstufen | `quality.json` | `QualityCheck` (Regeln) | geplant |
| 7 | Kennzahlen | `pitch_tracks.json`, `teams.json`, `corrections.json` | `metrics.json` | `Metric` (eine Klasse je Kennzahl) | geplant |
| 8 | Darstellung und Bericht | Kennzahlen, Spuren | Heatmap-PNG, Minimap-Video, `report.md` | `Renderer` | Spuren-Video da (`render/`), Rest geplant (T6, T7) |

Stufen 1 bis 3 wirken auf das Video, Stufe 7 und 8 **nie** (nur auf Daten). Das ist die Garantie, dass neue Kennzahlen keinen Bildlauf brauchen.

**Stufenkette und Cache:** Jede Stufe hat `stage_params` (ihre Parameter), und die Dateien der Vorstufen. Passt beides zur gespeicherten Datei, wird die Stufe übersprungen. Heute gilt das für Erkennung und Kamerabewegung (Abschnitt 3); die Verallgemeinerung kommt erst, wenn die zweite teure Stufe (Kalibrierung oder Teams) existiert (Bremse: nicht vorher bauen).

## A3. Anwendungsfälle und Einstiegspunkte

Die Fachlogik liegt als **Anwendungsfälle** in `application/`. Jede Oberfläche ruft dieselben auf:

| Anwendungsfall (Workflow-Schritt) | Heute | Später |
|---|---|---|
| Spiel anlegen / Clip importieren (1, 2) | CLI `match add`, `clip import` | Upload in der Weboberfläche |
| Verarbeitung starten (5) | CLI `track` | API-Aufruf, Auftrag in Warteschlange, Worker führt Stufen aus |
| Kalibrieren (4) | | Kalibrierwerkzeug (Bild anklicken) |
| Korrigieren (7) | | Viewer schreibt `corrections.json` |
| Kennzahlen/Bericht (8 bis 10) | | Viewer, Export |
| Qualität und Vergleich (6, 11) | | Prüfstand, Analyse-Agenten |

Aufbau, damit das ohne Umbau wächst:
```
Einstiegspunkte:  CLI (heute) | Web-API (später) | Worker/Warteschlange (später) | Agenten (später)
                        │ rufen dieselben Anwendungsfälle auf
Anwendung:        Anwendungsfälle (Pipeline, Lauf starten, Kalibrieren, Kennzahlen ...) + Ports
Domäne:           Spiel, Clip, Lauf, Spur, Messung, Kalibrierung, Kennzahl (reine Daten und Regeln)
Infrastruktur:    Dateien/Bibliothek, Video, Modelle, Renderer (später: Objektspeicher, Datenbank)
```
Die vier Schichten aus CLAUDE.md bleiben unverändert (`cli -> infrastructure -> application -> domain`). Neue Einstiegspunkte (API, Worker) wären wie `cli.py` Verdrahtung und kämen nach Rücksprache und Eintrag in `docs/entscheidungen/` dazu. Agenten lesen Kennzahlen und Qualitätsberichte aus den Dateien und erkennen nichts im Bild.

## A4. Querschnitt (gilt für alle Stufen)
- **Speicher:** Heute Dateien in `data\library\` (kein Git). Die Bibliothek ist ein Port; später Objektspeicher plus Datenbank ohne Änderung der Stufen.
- **Konfiguration:** Standard, eigene Datei, Aufnahme-Profil, Aufruf-Argumente; das Ergebnis steht in `run.json`. Neue Aufnahme-Profile sind Daten, kein Code.
- **Versionen:** `schema_version` in jeder Datei; Modell- und Bibliotheksversionen im Ergebnis eines Laufs.
- **Fortschritt und Wiederaufnahme:** Jeder Lauf zeigt je Stufe "fertig/offen"; ein Abbruch lässt sich ab der letzten fertigen Stufe fortsetzen. Heute nicht vollständig (Abschnitt 6, "Lauf-Ordner").
- **Qualität und Messbarkeit:** Prüfstände (Testset, ID-Wechsel-Kandidaten, später beschriftete Spuren) laufen gegen dieselben Dateien wie der Anwender.
- **Datenschutz:** Keine Namen, keine Rohdaten im Git oder bei externen Diensten.

## A5. Abweichungen und Lücken gegenüber dem heutigen Stand (zur Entscheidung)
1. **Mannschaften im Spiel** (`match.json`) fehlen. Entschieden: Der Anwender wählt seine Mannschaft, Auswertung aus deren Sicht. Umsetzung als Vorschlag in `docs/entwuerfe/zielbild-entscheidungen.md`.
2. **Korrekturen** als eigene Datei sind in keiner Spezifikation vorgesehen. Ohne sie bleiben Fehlzuordnungen dauerhaft in den Kennzahlen.
3. **Aufnahmeprüfung (Stufe 1)** steht in der Woche-1-Spezifikation nur als T4b (Kamerabewegung, umgesetzt). Abschnitte und das Ausschließen von Jubel-/Zoomabschnitten sind im Brief verlangt, in keiner Aufgabe verplant.
4. **Spielfeldfilter** (Woche 2) braucht die Kalibrierung; bis dahin verfälschen Ordner/Bank die Spurzahlen.
5. **Tracker in `application/`** statt `infrastructure/` (siehe Abschnitt 6): Bei mehreren Trackern wird das wieder aktuell.
6. **`matchstats run`** ist der älteste Pfad und duplizierte den Ablauf von `track`. Bei der ersten Stufe, die ihn berührt (T5/T6), sollte er entweder auf den neuen Ablauf zeigen oder entfallen.

Zielbild (Teil A) von dir bestätigt am 2026-11-20. Die Umsetzung jeder Lücke bleibt eine eigene Entscheidung, Vorschläge in `docs/entwuerfe/zielbild-entscheidungen.md`.

# Teil B: Stand heute

## 1. Schichten

Abhängigkeiten zeigen nur nach innen: `cli` -> `infrastructure` -> `application` -> `domain`. `tests/test_architecture.py` prüft das automatisch.

| Schicht | Ordner in `src/matchstats/` | Inhalt heute | darf importieren |
|---|---|---|---|
| domain | `domain/` | Reine Datentypen und Regeln: `Settings`, `RunResult`, `Detection` (IoU, NMS), Tracking-Typen (`tracking.py`: `FrameDetections`, `TrackPoint`, `Track`, `DetectionsDoc`), Kamera-Typen (`camera.py`: `CameraMotion`, `CameraPath`, `NO_CAMERA`, `CameraDoc`), Team-Typen (`teams.py`: `TeamPrediction`, Verwechslungstabelle, Trefferquote, beste A/B-Zuordnung; T5b1: `TrackTeam`, `TeamsDoc`, `vote_track`, `select_sample_points`, `tracks_fingerprint`, `class_change_share`), Bibliotheks-, Testset-, Mess- und Kachel-Typen. Keine Dateizugriffe | nur domain |
| application | `application/` | Ablauf und Ports: `run_pipeline` (leer), Port `Detector`, `TiledDetector`, `evaluate_detector`, Port `Library`, Port `Tracker` mit `ByteTrackLikeTracker` (`tracker.py`), Stufen `detect_stage`, `camera_stage` und `track_stage` mit den Ports `FrameSource`, `CameraMotionEstimator` und `StageStore` (`tracking_stages.py`), `summarize_tracks`, Port `TeamClassifier` (`team_classifier.py`), Teammessung `evaluate_teams` (`team_evaluation.py`), Stufe `team_stage` mit eigenem Port `TeamsStore` (`team_stage.py`) | domain, application |
| infrastructure | `infrastructure/` | Außenwelt: Parameter laden, Video bildweise lesen (OpenCV), Detektoren (RF-DETR, YOLO), Dateien schreiben und lesen, Darstellung (Video, Kontaktbögen), Bibliothek als Dateien, Kamera-Schätzung (`opencv_camera.py`), Verdrahtung des Track-Laufs (`tracking_job.py`), Farbverfahren der Teamzuordnung (`color_team_classifier.py`, reines NumPy), Teambericht (`team_report.py`), Verdrahtung der Teammessung (`evaluation_job.py`: `run_team_evaluation`) | domain, application |
| cli | `cli.py`, `__main__.py` | Argumente lesen, Schichten verdrahten, Ergebnis melden. Keine Logik | alles |

Begriffe:
- **Port**: Schnittstelle, also die Festlegung, was ein Baustein können muss. Die Stufen kennen nur den Port, nicht die Umsetzung (RF-DETR, OpenCV).
- **Stufe**: ein Verarbeitungsschritt mit fester Ein- und Ausgabedatei. Heute: Erkennung und Spurbildung.
- **Spur (Track)**: Folge von Boxen einer Person mit gleichbleibender ID über die Zeit. Bilder ohne Erkennung werden überbrückt und als `visible: false` markiert.
- **Kamerabewegung und Kamerapfad**: Schwenk, Drehung und Zoom der Kamera von einem Bild zum nächsten, als 2x3-Matrix. Dazu werden Bildpunkte mit Lucas-Kanade (verfolgt Punkte von Bild zu Bild) verfolgt und mit RANSAC (passt eine Bewegung an und verwirft Ausreißer wie bewegte Spieler) geschätzt. Der Kamerapfad verkettet die Schritte. Fehlt eine Schätzung, steht `null` (unbekannt, nicht "keine Bewegung").
- **Stufen-Cache**: Die Erkennung wird wiederverwendet, wenn die gespeicherte Datei zu Parametern und Video passt. Siehe Abschnitt 3.
- **Bibliothek**: Ordner `data\library\` mit Spielen, Clips und Läufen, als JSON-Dateien, keine Datenbank.
- **Spiel / Clip / Lauf**: Spiel (ID, Name, Datum); Clip (Video eines Spiels, mit Halbzeit und Aufnahme-Profil); Lauf (`run-001`, ... Ordner für einen Verarbeitungslauf auf einem Clip).
- **Parameter-Schichtung**: Standard (`default.toml`), dann eigene Datei (`--config`), dann Profil (`clip.json`), dann Aufruf-Argumente. Die spätere Schicht gewinnt. Unbekannte Schlüssel werden mit Namen abgelehnt.
- **schema_version**: Zahl in jeder JSON-Datei. Eine andere Version führt zu einer klaren Fehlermeldung, nie zu einem Raten.

## 2. Bausteine (CLI-Befehle und Module)

| Baustein | Datei | Eingabe | Ausgabe |
|---|---|---|---|
| CLI `track` (neu in T4) | `cli.py` -> `infrastructure/tracking_job.py` | `--game`, `--clip`, `--variant whole\|tiles`, `--run run-NNN` (optional), `--no-render`, `--camera`/`--no-camera`, `--config`, `--library` | Neuer Lauf (oder bestehender) im Clip-Ordner, siehe Abschnitt 3 |
| CLI `run` | `cli.py`, `application/pipeline.py` | Video, `--out`, `--config` | `tracks.json` (Version 2, **leer**). Nutzt Bibliothek und Tracking **nicht** |
| CLI `match add`, `clip import`, `clip list` | `cli.py`, `file_library.py`, `clip_table.py` | Spiel-ID, Video, Profil | `match.json`, Clip-Ordner mit Kopie des Videos und `clip.json` (fps, Auflösung, Länge per ffprobe) |
| CLI `evaluate` | `cli.py`, `evaluation_job.py` | `--game --half` (Bibliothek) oder `--testset --images` (alt) | `report.json`, `report.md`, `overlays\` |
| CLI `evaluate-teams` (neu in T5a) | `cli.py`, `evaluation_job.py` (`run_team_evaluation`), `application/team_evaluation.py` | `--game --half --out` (Pflicht), `--overlays` (Standard 6), `--config`, `--library` | `team_report.json`, `team_report.md`, `overlays\` (Fehler zuerst, rot) |
| Stufe Teams je Spur (T5b1) | `application/team_stage.py` (`team_stage`, Port `TeamsStore`), Typen und Abstimmung in `domain/teams.py`, Dateien in `infrastructure/stage_files.py` | `tracks.json` (als `RunResult`), Video (`FrameSource`), `TeamClassifier` | `teams.json`. **Noch kein CLI-Befehl und keine Anbindung an `track`** (T5b2) |
| Teamzuordnung (T5a) | Port `application/team_classifier.py` (`TeamClassifier`), Umsetzung `infrastructure/color_team_classifier.py`, Typen `domain/teams.py` | Mengen pro Clip: Bilder und Boxen (Box i in Bild i) | je Box Klasse (`team_a`, `team_b`, `goalkeeper`, `referee`) und Sicherheit, oder `None` (unbekannt) |
| CLI `sample-frames` | `cli.py`, `frame_sampler.py` | Videos, `--out`, `--count` | PNGs + `manifest.json`. **Nicht** an die Bibliothek angebunden (siehe 6) |
| Stufe Erkennung | `application/tracking_stages.py` (`detect_stage`) | `FrameSource` (jedes N-te Bild), `Detector`, `StageStore` | `detections.json` |
| Stufe Kamerabewegung (T4b) | `application/tracking_stages.py` (`camera_stage`), Port `application/camera_estimator.py`, Umsetzung `infrastructure/opencv_camera.py` | Video, jedes Bild (verkleinertes Graubild) | `camera.json` (je Bild 2x3-Matrix oder `null`) |
| Kamerapfad | `domain/camera.py` (`CameraPath`, `NO_CAMERA`) | `camera.json` | verkettet die Bewegungen zwischen zwei Bildern; Tracker verschiebt seine Vorhersage damit |
| Stufe Spurbildung | `application/tracking_stages.py` (`track_stage`) + `application/tracker.py` | `detections.json` und `camera.json` (optional), `Tracker` | `tracks.json` |
| Kennzahlen | `application/track_summary.py` | Spuren, Kandidaten | Teil von `summary.json` |
| ID-Wechsel-Kandidaten | `domain/id_switch.py` (`find_id_switch_candidates`) | Spuren, fps, Bildgröße, Parameter `switch_*` | `id_switch_candidates.json`, Vergleichsbilder `render\switches\switch_NNN.png` |
| Videoquelle | `infrastructure/video_source.py` (`OpenCvFrameSource`) | Video | Bild für Bild (ein Bild im Speicher), prüft, ob das Video vollständig lesbar ist |
| Dateien der Stufen | `infrastructure/stage_files.py` (`FileStageStore`) | Lauf-Ordner | `detections.json`, `camera.json`, `teams.json` (T5b1) lesen/schreiben; `tracks.json` über `result_store.py` |
| JSON ohne halbe Dateien | `infrastructure/json_io.py` | Daten | Erst `.tmp`, dann umbenannt |
| Darstellung | `infrastructure/track_render.py` | Video, Spuren | `render\tracks.mp4` (halbe Geschwindigkeit, Box + ID; gesehene Boxen dick, überbrückte dünn), `render\sheet_*.png` (alle 2 s). Deterministisch aus den Spuren |
| Verdrahtung Track-Lauf | `infrastructure/tracking_job.py` (`run_track_job`) | Bibliothek, Clip, Variante, Konfiguration | Lauf-Ordner, `summary.json`. Baut den Detektor erst, wenn wirklich erkannt werden muss |
| Detektor-Port und Detektoren | `application/detector.py`; `infrastructure/rfdetr_detector.py`, `yolo_detector.py` | Bild (RGB) | Personenboxen (`Detection`: Box in Pixeln, Score). RF-DETR ist Hauptdetektor; YOLO nur mit Extra `[yolo]` (AGPL) |
| Kacheln | `domain/tiling.py`, `application/tiling.py` (`TiledDetector`) | Bild | Boxen im Bild-Koordinatensystem, Doppelte per NMS entfernt. **Im `track`-Befehl nicht am echten Clip getestet** |
| Messregeln | `domain/metrics.py`, `application/evaluation.py` | Erkennungen, Beschriftungen | Treffer (IoU >= 0,5), Recall, Precision, nah/fern. Fehlende Werte bleiben `None` |
| Parameter | `domain/settings.py`, `infrastructure/config_loader.py` (`load_settings`), `infrastructure/default.toml` | Dateien, Profil, Aufruf | `Settings` (Abschnitt 4) |
| Bibliothek | `domain/library.py`, `application/library.py` (Port), `infrastructure/file_library.py` | Bibliotheksordner | Liest und schreibt die JSON-Dateien. Import überschreibt nie einen Clip |
| Testset | `domain/testset.py`, `infrastructure/testset_loader.py` | `coco.json` | Beschriftete Bilder; Formatfehler werden gemeldet |
| Beschriftungswerkzeug (extern) | `tools/start_labelstudio.ps1`, `docs/labelstudio/config.xml` | Bilder | COCO-Export. Kein eigener Code |
| Migration (einmalig) | `tools/migrate_t3b.py` | alte T1 bis T3-Ordner | `spiel-001` mit clip1 bis clip3 |

`python -m matchstats ...` startet dasselbe wie das Kommando (`__main__.py`).

## 3. Datenfluss

**Track-Lauf (T4 mit Kamerabewegung aus T4b, `matchstats track --game spiel-001 --clip clip1`):**
```
data\library\spiel-001\clip1\clip.mp4 + clip.json   (Video nur lesen; Profil-Überschreibungen gelten bei neuem Lauf)
  |  Neuer Lauf: Settings = default.toml + --config + clip.json; run.json wird angelegt
  |  Mit --run run-NNN: Settings aus run.json (--config wird mit Warnung ignoriert)
  v
Stufe 1  Erkennung (detect_stage): jedes detect_every-te Bild -> RF-DETR -> Filter detect_min_score
         Cache: detections.json wird wiederverwendet, wenn stage_params (Detektor, Variante, Modell,
         detect_every, detect_min_score, Kachelwerte) UND Video (Dateiname, Bildanzahl, Bildgröße) gleich sind.
         Dann wird weder das Video gelesen noch der Detektor gebaut (summary: detections_reused = true).
  -> run-NNN\detections.json
  v
Stufe 1b Kamerabewegung (camera_stage, nur wenn `camera_compensation` an ist): liest jedes Bild des Videos, schätzt Schwenk/Zoom
         Cache: camera.json wird wiederverwendet, wenn `camera_downscale`, `camera_min_quality`, `camera_max_features` und das Video gleich sind.
  -> run-NNN\camera.json
  v
Stufe 2  Spurbildung (track_stage): liest detections.json und camera.json (ohne Ausgleich: nur detections.json), läuft immer neu (Sekunden)
  -> run-NNN\tracks.json
  v
Darstellung (optional, --no-render schaltet ab)
  -> run-NNN\render\tracks.mp4, render\sheet_NNNNNN.png
  v
Kennzahlen -> run-NNN\summary.json (Spuren, pro Minute, mittlere Länge, Anteil gesehen, ID-Wechsel-Kandidaten pro Spur-Minute, Laufzeiten)
```
Regel: Jede Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden aus gespeicherten Daten berechnet, nicht aus dem Video.

**Bibliotheks-Ast (T3b, Messung):** `matchstats evaluate --game spiel-001 --half 1` misst alle Clips der Halbzeit mit Testset in einem Bericht (eine nah/fern-Grenze). Schreibt in `--out`, nicht in den Lauf.

**Team-Ast (T5a, Messung, `matchstats evaluate-teams --game spiel-001 --half 1 --out ...`):**
```
testset\coco.json + Bilder (je Clip der Halbzeit, beschriftete Boxen mit Klasse)
  -> TeamClassifier (je Clip ein Aufruf über alle Boxen): Oberkörper, Rasen per HSV entfernt, Medianfarbe, k-Means
  -> Gruppen: zwei größte = Teams, weitere große -> näheres Team, kleine -> Schiedsrichter/Torwart
  -> je Clip bessere A/B- und Torwart/Schiedsrichter-Zuordnung anhand der Wahrheit (Orakel, optimistisch)
  -> --out\team_report.json, team_report.md, overlays\
```
Keine Stufe im Lauf-Ordner, kein Video, nicht an Spuren angebunden. Begriff **Orakel**: Die Zuordnung "welche Farbgruppe ist Team A" wird mit der Wahrheit festgelegt; echte Läufe haben diese Hilfe nicht.

**Teams je Spur (T5b1, Stufe `team_stage`, noch nicht in `matchstats track` verdrahtet):**
```
tracks.json (RunResult) + Video (ein Durchlauf, nur Bilder mit gemeinsamer Schrittweite per gcd)
  -> je Spur bis zu team_samples_per_track gesehene Punkte (visible), gleichmäßig gewählt
  -> Ausschnitte (Kopien) um die Boxen; ein classify-Aufruf je Clip (TeamClassifier gruppiert über alle Stichproben)
  -> Abstimmung je Spur: Mehrheit der bekannten Stimmen, mindestens team_min_votes, sonst label null
  -> run-NNN\teams.json
```
Cache: `teams.json` wird wiederverwendet, wenn `stage_params` (alle `team_*` plus Klassifikatorname), Videoidentität (Dateiname, Bildanzahl) und der Spur-Fingerabdruck (sha256 über id, frame, x, y, w, h, visible) gleich sind; dann wird das Video nicht gelesen. Kein Orakel: "team_a" ist die größere Farbgruppe, nur die Trennung A gegen B zählt.

**Testset-Ast (T2) und Mess-Ast (T3, alt):** `sample-frames` -> Label Studio -> `coco.json` -> `evaluate --testset ... --images ...`.

**Ältester Ast (`run`):** Video (nur auf Existenz geprüft) -> `run_pipeline` (leer) -> `tracks.json` in `--out`. Das Video wird nicht geöffnet.

**Geplant:**
```
Quelle (.MTS 1080i25) --T0, manuell mit ffmpeg/yadif--> Clips, progressiv 1080p25
  -> T5b2 Teams im Lauf: `track` ruft `team_stage`, summary.json v4, Render in Teamfarbe  *(geplant; T5b1 = Stufe vorhanden)*
  -> T6 Ausgabe: annotiertes Video + Spurdatei (Sichtbarkeit, Unsicherheit)  *(geplant; erweitert render/, baut nicht neu)*
  -> T7 Bericht: Kennzahlen, Laufzeiten, Beispielbilder        *(geplant)*
```

## 4. Dateiformate

Gemeinsam: UTF-8, Einrückung 2, `schema_version` als erstes Feld. Fehlende Werte sind `null`, nie 0. Pfade in der Bibliothek sind relativ zu `data\library\` und nutzen "/".

- `match.json` (v1): `{schema_version, id, name, date (JJJJ-MM-TT) oder null, notes}`.
- `clip.json` (v1): `{schema_version, id, match_id, half (1, 2 oder null), source_file, fps, width, height, duration_s, profile: {angle, camera_motion, notes}, settings: {}}`. `settings` sind Profil-Überschreibungen; der Import schreibt heute immer `{}`.
- `run.json` (v1): `{schema_version, id ("run-001"), created, clip_id, settings: {aufgelöste Parameter, inkl. track_*}}`.
- `detections.json` (v1, `domain/tracking.py`): `source`, `detector` (z. B. `rfdetr-small-whole`), `fps`, `frame_count`, `frame_size`, `stage_params` (Cache-Schlüssel), `versions` (Bibliotheken, Modell), `frames: [{frame, detections: [{x, y, w, h, score}]}]`. Nur Bilder mit `detect_every`, nur Scores >= `detect_min_score`.
- `camera.json` (v1, `domain/camera.py`, nur mit Kameraausgleich): `source`, `fps`, `frame_count`, `frame_size`, `stage_params` (Cache-Schlüssel), `versions`, `motions: [{frame, matrix, quality}]`. `frame` = Bild f (ab 1), `matrix` = 2x3-Matrix von Bild f-1 nach Bild f oder `null` (Schätzung fehlgeschlagen oder zu schwach, nicht 0), `quality` = Anteil der zur Bewegung passenden Punkte (0 bis 1) oder `null`.
- `tracks.json` (**v2**, `domain/result.py`): `source`, `config` (aufgelöste Parameter; Schlüssel heißt hier `config`), `fps`, `frame_count`, `versions`, `tracks: [{id, points: [{frame, x, y, w, h, visible, score, uncertainty}]}]`. Punkte von erstem bis letztem Treffer; Lücken linear interpoliert (`visible: false`, `score: null`). `uncertainty` ist in T4 immer `null` (Platzhalter für T6). Version 1 wird mit Meldung abgelehnt.
- `id_switch_candidates.json` (v1): Liste `candidates` mit `old_id`, `new_id`, `end_frame`, `start_frame`, `distance_in_heights`. Nur Kandidaten, keine bestätigten Wechsel.
- `summary.json` (v3, `infrastructure/tracking_job.py`; neu in v3: `camera_compensation` an/aus und `camera_null_share`, der Anteil der Bilder ohne Kameraschätzung; `null` = ohne Ausgleich gelaufen, nicht 0): `id_switch_candidates`, `track_minutes`, `id_switch_candidates_per_track_minute` und `track_count`, `tracks_per_minute`, `mean_track_seconds`, `visible_share`, `stage_seconds` (`detection`, `tracking`, `render`; `null` = Stufe nicht gelaufen), `detections_reused`. Ohne Spuren oder ohne fps bleiben Kennzahlen `null`.
- `team_report.json` (v1, `infrastructure/team_report.py`, Ausgabe von `evaluate-teams`): `versions` (python, numpy), `near_far_height_px` (Median der Boxhöhe), `parameters` (alle `team_*`), `clip_mappings` (je Clip: vorhergesagt -> gezählt als), `clip_groups` (je Clip: Boxen je Farbgruppe), `accuracy` (`total`, `per_class`, `near`, `far`; `null` ohne Boxen), `unknown` (Zahl, zählt als falsch), `confusion` (`total`, `near`, `far`; Zeilen = beschriftet, Spalten = vorhergesagt inkl. `unbekannt`). `team_report.md` ist die lesbare Fassung. Nicht Teil eines Laufs.
- `teams.json` (v1, `domain/teams.py`, `infrastructure/stage_files.py`, Stufe 4, T5b1): `source`, `fps`, `frame_count`, `frame_size`, `stage_params` (Cache-Schlüssel: alle `team_*` plus `classifier`), `tracks_fingerprint`, `versions`, `note`, `tracks: [{id, label, uncertainty, samples, votes}]`. `label` = `team_a`, `team_b`, `goalkeeper`, `referee` oder `null` (weniger als `team_min_votes` bekannte Stimmen, nicht eine Zufallsklasse). `uncertainty` = 1 minus Anteil der Siegerklasse an den bekannten Stimmen (0 bis 1, `null` ohne bekannte Stimme). `samples` = Zahl klassifizierter Stichproben, `votes` = Klasse -> Anzahl plus `unbekannt`. Gleichstand entscheidet die Reihenfolge `team_a, team_b, goalkeeper, referee`. Eine fehlende oder abgeschnittene Datei lädt als `None`, eine falsche Version als `ValueError`.
- Erlaubte Profilwerte (`domain/library.py`): `angle` = `tribuene_hoch`, `seitenlinie`, `ecke`, `hinter_tor`, `sonstige`; `camera_motion` = `fest`, `schwenkt`, `schwenkt_und_zoomt` (ohne Angabe gilt `unbekannt`, mit Ausgleich an).

Parameter (`domain/settings.py`, Standardwerte, auch in `default.toml`):
- Erkennung: `detect_every` 5, `detector_model` "small", `score_threshold` 0,3, `tile_size` 640, `tile_overlap` 0,2, `nms_iou` 0,5.
- Kamera (T4b): `camera_compensation` (an/aus; Voreinstellung aus dem Aufnahme-Profil über `[camera_motion_presets]` in `default.toml`: fest = aus, schwenkt, schwenkt_und_zoomt, unbekannt = an). Schichtung: Standard -> Datei -> Aufnahme-Profil -> `clip.json` -> Aufruf (`track --camera`/`--no-camera`). `camera_downscale` 0,5, `camera_min_quality` 0,5, `camera_max_features` 300 (Startwerte, geraten).
- Tracking (T4): `detect_min_score` 0,1 (Filter bei der Erkennung), `track_high_score` 0,4 (ab hier darf eine Spur eröffnet werden), `track_match_iou` 0,3 (Mindest-Überlappung der Zuordnung), `track_max_lost_seconds` 1,5, `track_min_hits` 3 (Treffer bis zur Bestätigung), `track_edge_margin_px` 40 (Spur am Bildrand endet sofort).

- Teamzuordnung (T5a, alle `team_*`, Startwerte geraten): `team_upper_body_fraction` 0,5, `team_min_box_height_px` 24, `team_min_box_width_px` 8, `team_grass_hue_range` [35, 85], `team_grass_min_saturation` 40, `team_cluster_count` 4, `team_outlier_max_share` 0,15, `team_min_cluster_distance` 0,2, `team_min_pixels` 30.
- Teams je Spur (T5b1, Startwerte geraten): `team_samples_per_track` 8 (höchstens so viele gesehene Punkte je Spur), `team_min_votes` 3 (Mindestzahl bekannter Stimmen für eine Klasse).

## 5. Wo was liegt

```
data\library\                          Bibliothek (Standard von --library), nie im Git
  spiel-001\
    match.json
    clip1\  clip.mp4, clip.json, testset\ (coco.json, images\)
            runs\run-001\  run.json, t3-ergebnis\                      (Migration)
            runs\run-002\  run.json, detections.json, tracks.json, summary.json, render\
            runs\run-003\  wie run-002
            runs\run-004\  wie run-003, ohne Kameraausgleich (T4b-Vergleich)
            runs\run-005\  wie run-002, mit camera.json (Kameraausgleich an)
    clip2\, clip3\  clip.mp4, clip.json, testset\
data\clips\, data\testset\, data\ergebnis\t3\   alte Ordner (T1 bis T3), unverändert
data\ergebnis\t5a_h1\                  Teammessung Halbzeit 1: team_report.json, team_report.md, overlays\ (nicht im Git)
```
- `src/matchstats/`: Code nach Schichten (Abschnitt 1). Neu in T4: `domain/tracking.py`, `domain/id_switch.py`, `application/tracker.py`, `application/tracking_stages.py`, `application/track_summary.py`, `infrastructure/video_source.py`, `stage_files.py`, `json_io.py`, `track_render.py`, `tracking_job.py`. Neu in T4b: `domain/camera.py`, `application/camera_estimator.py`, `infrastructure/opencv_camera.py`; `camera_stage` in `tracking_stages.py`, `camera.json` in `stage_files.py`. Hilfsskript `tools/plot_camera_motion.py` (Diagramm, nicht Teil der Pipeline).
- `tests/` (T4): `test_tracker_rules.py` (Zuordnungsregeln), `test_tracking_stages.py` (Stufen und Cache), `test_tracking_files.py` (Dateiformate), `test_track_settings.py`, `test_track_summary.py`, `test_id_switch_candidates.py`, `test_track_render.py`, `test_video_source.py`, `test_track_cli.py`, `test_cli_imports.py` (cv2/scipy erst beim `track`-Befehl geladen). T4b: `test_camera_domain.py`, `test_camera_estimator.py`, `test_camera_files.py`, `test_camera_settings.py`, `test_camera_stage.py`, `test_tracker_camera.py`. Dazu die älteren Tests und `test_architecture.py`.
- `pyproject.toml`: Extra `track` = `scipy` (BSD) und `opencv-python` (Apache 2.0). Für den echten Lauf braucht `track` zusätzlich Extra `detect` (RF-DETR, siehe README Zeile 69). Ob eine frische Umgebung mit `.[track]` allein läuft, ist **unklar** (nicht geprüft).
- `docs/entscheidungen/`: 0001 Schichten, 0002 Agententeam, 0003 Testset und Label Studio, 0004 Detektor und Kacheln, 0005 Bibliothek, 0006 Tracking in Stufen, 0007 ID-Wechsel-Kandidaten, 0008 Kamerabewegung (T4b), 0009 Teamzuordnung (T5a), 0010 Teams je Spur (T5b1).
- Neu in T5a: `domain/teams.py`, `application/team_classifier.py`, `application/team_evaluation.py`, `infrastructure/color_team_classifier.py`, `infrastructure/team_report.py`; erweitert `evaluation_job.py`, `image_io.py` (`save_team_overlay`), `settings.py`, `config_loader.py`, `default.toml`, `cli.py`. Tests: `test_teams_domain.py`, `test_color_team_classifier.py`, `test_team_evaluation.py`, `test_team_report.py`, `test_team_cli.py`.
- Neu in T5b1: `application/team_stage.py`; erweitert `domain/teams.py`, `infrastructure/stage_files.py` (`load_teams`/`save_teams`), `domain/settings.py`, `default.toml`. Tests: `test_teams_vote.py` (Abstimmung, Stichprobenwahl, Fingerabdruck), `test_team_crop.py` (Ausschnitt, gleiche Vorhersage wie Ganzbild), `test_team_stage.py` (Stufe und Cache), `test_stage_files_teams.py` (Dateiformat).

## 6. Noch nicht umgesetzt oder unklar

- **ID-Wechsel (AK T4):** nur als automatischer Indikator (Kandidaten pro Spur-Minute), **nicht** von Hand gezählt; `docs/berichte/t4-zaehlung.md` bleibt eine leere Vorlage (Archiv). Auf run-003: 59 Kandidaten, 2,9 pro Spur-Minute. Von 8 per Auge angesehenen Kandidaten wirken 6 echt und 2 falsch (Kamerabewegung, Gedränge). Das ist keine Messung der echten Fehlerrate; die Standardschwellen (1,0 s, 1,0 Boxhöhen) sind geraten.
- **Kamerabewegung (T4b): umgesetzt, nur der Teil Kamerabewegung.** Der Tracker verschiebt seine Vorhersage mit dem Kamerapfad. Interpolation der Zwischenbilder und Kandidatensuche rechnen weiter ohne Kamera. Abschnitte und das Ausschließen von Jubel-/Zoomabschnitten bleiben geplant.
  - Ergebnis clip1 (gleiche Erkennungen): ohne Ausgleich run-004: 59 Kandidaten, 2,90 pro Spur-Minute, 226 Spuren, mittlere Spurlänge 5,4 s (identisch zu run-003). Mit Ausgleich run-005: 6 Kandidaten, 0,25 pro Spur-Minute, 73 Spuren, mittlere Spurlänge 19,7 s. Null-Anteil 0 %. Kamera-Schätzung 65 s für 60 s Video.
  - Grenzen: Die Kandidaten erfassen nur Abrisse, keine Verwechslungen. In der Stichprobe (Kontaktbogen 30 s) ist eine Spur auf einen falschen Spieler gerutscht. Das ist ein Indiz, keine Fehlerrate. Die Startwerte für Kameraschätzung sind geraten.
- **Spielfeldfilter (Woche 2):** Zuschauer, Ordner und Bank erzeugen heute Spuren und verfälschen die Zahlen.
- **Kacheln (`--variant tiles`)** laufen im `track`-Befehl, sind aber nicht am echten Clip getestet. Laufzeit und Ergebnis sind **unklar**.
- **Stufen-Cache:** prüft Name, Bildanzahl und Größe des Videos, keinen Inhalts-Hash. Die gespeicherten `versions` werden beim Wiederverwenden nicht verglichen. Mit `--run` wird `detections.json` im selben Lauf überschrieben, wenn die Parameter nicht passen.
- **`--run`** nutzt die Einstellungen aus `run.json`; `--config` wird dann ignoriert (Warnung).
- **Lauf-Ordner** wird vor der Erkennung angelegt (aus dem Code abgeleitet, nicht getestet). Bricht die Erkennung ab, bleibt ein Lauf ohne `summary.json` zurück.
- **Tracker-Umsetzung:** `ByteTrackLikeTracker` liegt in `application/` (wie im Entwurf beschlossen), nicht in `infrastructure/`. CLAUDE.md verlangt Implementierungen in `infrastructure/`. **Offen, Entscheidung des Leads.** Der Schichtentest prüft das nicht.
- **Probeläufe:** Im Repo belegt sind nur run-002 (0,5/2) und run-003 (0,4/3) über `summary.json`. Die Standardwerte stützen sich auf Probeläufe, deren Zahlen für 0,3/3 **unklar** (nicht im Repo) sind. Siehe `docs/entscheidungen/0006-tracking-stufen-und-dateien.md`.
- **Profil-Überschreibungen** (`clip.json` `settings`) wirken jetzt beim `track`-Befehl für neue Läufe. Der Import schreibt heute immer `{}`.
- **`matchstats run`** nutzt Erkennung und Tracking nicht und liefert eine leere `tracks.json`.
- **`sample-frames`** kennt keine Bibliothek (kein `--game`/`--clip`). Abweichung von T3b (AK 3), offen beim Lead. Wie das Testset eines neuen Clips im CLI entsteht, ist **unklar**.
- **Läufe:** Außer `track` legt kein CLI-Befehl einen Lauf an. `run-001` entstand durch die Migration.
- **Bewusst verschoben:** Verweis statt Kopie (`--link`), Deinterlacen und Schneiden beim Import, Oberfläche, Datenbank.
- **Messung:** eine Perspektive, ein Spiel (Testset), Score-Schwelle für die Messung fest 0,3.
- **Teamzuordnung (T5a): nur Messung auf beschrifteten Boxen, nicht auf Spuren.** Basislinie Halbzeit 1 (clip1 bis clip3): gesamt 66,1 %, nah 73,1 %, fern 59,2 %; team_a 84,4 %, team_b 66,9 %, Torwart 10,5 %, Schiedsrichter 0 %; 75 Boxen unbekannt. Torwart und Schiedsrichter sind praktisch nicht getrennt (nur über Gruppengröße unterschieden). In allen Clips gibt es eine dritte große Farbgruppe (87 bis 133 Boxen), Ursache **offen**. Parameter geraten. Die Zuordnung je Clip nutzt die Wahrheit (Orakel), die Zahlen sind optimistisch. Die Verbesserung ist als Punkt für T5b oder später vorgesehen. Siehe `docs/entscheidungen/0009-teamzuordnung-t5a.md`.
- **Teams je Spur (T5b1): Stufe vorhanden, aber nicht an `matchstats track` angebunden** (kein CLI-Befehl, keine Zeile in `summary.json`, kein Render in Teamfarbe; kommt mit T5b2). Handlauf clip1 (run-005): 73 Spuren, team_a 24, team_b 49, Torwart 0, Schiedsrichter 0, `null` 0; **Anteil Spuren mit wechselnder Klasse 45,2 %** (573 Stichproben, 14,6 s, Cache-Treffer 0,38 s). Das ist hoch (Schwelle 30 % geraten); ob die Schwelle oder das Verfahren der Maßstab ist, ist **offen** und vor T5b2 zu klären. Gruppierung je Spur-Stichproben statt je Bild wie in T5a, daher ist das Gewicht von `team_outlier_max_share` verändert (Messrisiko). Siehe `docs/entscheidungen/0010-teams-je-spur-t5b1.md`.
- **Ausgabe (T6), Bericht (T7):** geplant, nicht vorhanden.

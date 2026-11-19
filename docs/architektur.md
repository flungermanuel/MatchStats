# matchstats: Systemkarte

Stand: 2026-11-18, nach T4 (Tracking, noch nicht committet). Was nicht als *(geplant)* markiert ist, existiert im Repo. **unklar** = im Repo nicht gefunden oder nicht entschieden.

## 1. Schichten

Abhängigkeiten zeigen nur nach innen: `cli` -> `infrastructure` -> `application` -> `domain`. `tests/test_architecture.py` prüft das automatisch.

| Schicht | Ordner in `src/matchstats/` | Inhalt heute | darf importieren |
|---|---|---|---|
| domain | `domain/` | Reine Datentypen und Regeln: `Settings`, `RunResult`, `Detection` (IoU, NMS), Tracking-Typen (`tracking.py`: `FrameDetections`, `TrackPoint`, `Track`, `DetectionsDoc`), Bibliotheks-, Testset-, Mess- und Kachel-Typen. Keine Dateizugriffe | nur domain |
| application | `application/` | Ablauf und Ports: `run_pipeline` (leer), Port `Detector`, `TiledDetector`, `evaluate_detector`, Port `Library`, Port `Tracker` mit `ByteTrackLikeTracker` (`tracker.py`), Stufen `detect_stage` und `track_stage` mit den Ports `FrameSource` und `StageStore` (`tracking_stages.py`), `summarize_tracks` | domain, application |
| infrastructure | `infrastructure/` | Außenwelt: Parameter laden, Video bildweise lesen (OpenCV), Detektoren (RF-DETR, YOLO), Dateien schreiben und lesen, Darstellung (Video, Kontaktbögen), Bibliothek als Dateien, Verdrahtung des Track-Laufs (`tracking_job.py`) | domain, application |
| cli | `cli.py`, `__main__.py` | Argumente lesen, Schichten verdrahten, Ergebnis melden. Keine Logik | alles |

Begriffe:
- **Port**: Schnittstelle, also die Festlegung, was ein Baustein können muss. Die Stufen kennen nur den Port, nicht die Umsetzung (RF-DETR, OpenCV).
- **Stufe**: ein Verarbeitungsschritt mit fester Ein- und Ausgabedatei. Heute: Erkennung und Spurbildung.
- **Spur (Track)**: Folge von Boxen einer Person mit gleichbleibender ID über die Zeit. Bilder ohne Erkennung werden überbrückt und als `visible: false` markiert.
- **Stufen-Cache**: Die Erkennung wird wiederverwendet, wenn die gespeicherte Datei zu Parametern und Video passt. Siehe Abschnitt 3.
- **Bibliothek**: Ordner `data\library\` mit Spielen, Clips und Läufen, als JSON-Dateien, keine Datenbank.
- **Spiel / Clip / Lauf**: Spiel (ID, Name, Datum); Clip (Video eines Spiels, mit Halbzeit und Aufnahme-Profil); Lauf (`run-001`, ... Ordner für einen Verarbeitungslauf auf einem Clip).
- **Parameter-Schichtung**: Standard (`default.toml`), dann eigene Datei (`--config`), dann Profil (`clip.json`), dann Aufruf-Argumente. Die spätere Schicht gewinnt. Unbekannte Schlüssel werden mit Namen abgelehnt.
- **schema_version**: Zahl in jeder JSON-Datei. Eine andere Version führt zu einer klaren Fehlermeldung, nie zu einem Raten.

## 2. Bausteine (CLI-Befehle und Module)

| Baustein | Datei | Eingabe | Ausgabe |
|---|---|---|---|
| CLI `track` (neu in T4) | `cli.py` -> `infrastructure/tracking_job.py` | `--game`, `--clip`, `--variant whole\|tiles`, `--run run-NNN` (optional), `--no-render`, `--config`, `--library` | Neuer Lauf (oder bestehender) im Clip-Ordner, siehe Abschnitt 3 |
| CLI `run` | `cli.py`, `application/pipeline.py` | Video, `--out`, `--config` | `tracks.json` (Version 2, **leer**). Nutzt Bibliothek und Tracking **nicht** |
| CLI `match add`, `clip import`, `clip list` | `cli.py`, `file_library.py`, `clip_table.py` | Spiel-ID, Video, Profil | `match.json`, Clip-Ordner mit Kopie des Videos und `clip.json` (fps, Auflösung, Länge per ffprobe) |
| CLI `evaluate` | `cli.py`, `evaluation_job.py` | `--game --half` (Bibliothek) oder `--testset --images` (alt) | `report.json`, `report.md`, `overlays\` |
| CLI `sample-frames` | `cli.py`, `frame_sampler.py` | Videos, `--out`, `--count` | PNGs + `manifest.json`. **Nicht** an die Bibliothek angebunden (siehe 6) |
| Stufe Erkennung | `application/tracking_stages.py` (`detect_stage`) | `FrameSource` (jedes N-te Bild), `Detector`, `StageStore` | `detections.json` |
| Stufe Spurbildung | `application/tracking_stages.py` (`track_stage`) + `application/tracker.py` | `detections.json` (nur Datei), `Tracker` | `tracks.json` |
| Kennzahlen | `application/track_summary.py` | Spuren | Teil von `summary.json` |
| Videoquelle | `infrastructure/video_source.py` (`OpenCvFrameSource`) | Video | Bild für Bild (ein Bild im Speicher), prüft, ob das Video vollständig lesbar ist |
| Dateien der Stufen | `infrastructure/stage_files.py` (`FileStageStore`) | Lauf-Ordner | `detections.json` lesen/schreiben; `tracks.json` über `result_store.py` |
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

**Track-Lauf (T4, `matchstats track --game spiel-001 --clip clip1`):**
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
Stufe 2  Spurbildung (track_stage): liest nur detections.json, läuft immer neu (Sekunden)
  -> run-NNN\tracks.json
  v
Darstellung (optional, --no-render schaltet ab)
  -> run-NNN\render\tracks.mp4, render\sheet_NNNNNN.png
  v
Kennzahlen -> run-NNN\summary.json (Spuren, pro Minute, mittlere Länge, Anteil gesehen, Laufzeiten)
```
Regel: Jede Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden aus gespeicherten Daten berechnet, nicht aus dem Video.

**Bibliotheks-Ast (T3b, Messung):** `matchstats evaluate --game spiel-001 --half 1` misst alle Clips der Halbzeit mit Testset in einem Bericht (eine nah/fern-Grenze). Schreibt in `--out`, nicht in den Lauf.

**Testset-Ast (T2) und Mess-Ast (T3, alt):** `sample-frames` -> Label Studio -> `coco.json` -> `evaluate --testset ... --images ...`.

**Ältester Ast (`run`):** Video (nur auf Existenz geprüft) -> `run_pipeline` (leer) -> `tracks.json` in `--out`. Das Video wird nicht geöffnet.

**Geplant:**
```
Quelle (.MTS 1080i25) --T0, manuell mit ffmpeg/yadif--> Clips, progressiv 1080p25
  -> T5 Teamzuordnung: Klasse je Spieler                       *(geplant)*
  -> T6 Ausgabe: annotiertes Video + Spurdatei (Sichtbarkeit, Unsicherheit)  *(geplant; erweitert render/, baut nicht neu)*
  -> T7 Bericht: Kennzahlen, Laufzeiten, Beispielbilder        *(geplant)*
```

## 4. Dateiformate

Gemeinsam: UTF-8, Einrückung 2, `schema_version` als erstes Feld. Fehlende Werte sind `null`, nie 0. Pfade in der Bibliothek sind relativ zu `data\library\` und nutzen "/".

- `match.json` (v1): `{schema_version, id, name, date (JJJJ-MM-TT) oder null, notes}`.
- `clip.json` (v1): `{schema_version, id, match_id, half (1, 2 oder null), source_file, fps, width, height, duration_s, profile: {angle, camera_motion, notes}, settings: {}}`. `settings` sind Profil-Überschreibungen; der Import schreibt heute immer `{}`.
- `run.json` (v1): `{schema_version, id ("run-001"), created, clip_id, settings: {aufgelöste Parameter, inkl. track_*}}`.
- `detections.json` (v1, `domain/tracking.py`): `source`, `detector` (z. B. `rfdetr-small-whole`), `fps`, `frame_count`, `frame_size`, `stage_params` (Cache-Schlüssel), `versions` (Bibliotheken, Modell), `frames: [{frame, detections: [{x, y, w, h, score}]}]`. Nur Bilder mit `detect_every`, nur Scores >= `detect_min_score`.
- `tracks.json` (**v2**, `domain/result.py`): `source`, `config` (aufgelöste Parameter; Schlüssel heißt hier `config`), `fps`, `frame_count`, `versions`, `tracks: [{id, points: [{frame, x, y, w, h, visible, score, uncertainty}]}]`. Punkte von erstem bis letztem Treffer; Lücken linear interpoliert (`visible: false`, `score: null`). `uncertainty` ist in T4 immer `null` (Platzhalter für T6). Version 1 wird mit Meldung abgelehnt.
- `summary.json` (v1, `infrastructure/tracking_job.py`): `track_count`, `tracks_per_minute`, `mean_track_seconds`, `visible_share`, `stage_seconds` (`detection`, `tracking`, `render`; `null` = Stufe nicht gelaufen), `detections_reused`. Ohne Spuren oder ohne fps bleiben Kennzahlen `null`.
- Erlaubte Profilwerte (`domain/library.py`): `angle` = `tribuene_hoch`, `seitenlinie`, `ecke`, `hinter_tor`, `sonstige`; `camera_motion` = `fest`, `schwenkt`, `schwenkt_und_zoomt`.

Parameter (`domain/settings.py`, Standardwerte, auch in `default.toml`):
- Erkennung: `detect_every` 5, `detector_model` "small", `score_threshold` 0,3, `tile_size` 640, `tile_overlap` 0,2, `nms_iou` 0,5.
- Tracking (T4): `detect_min_score` 0,1 (Filter bei der Erkennung), `track_high_score` 0,4 (ab hier darf eine Spur eröffnet werden), `track_match_iou` 0,3 (Mindest-Überlappung der Zuordnung), `track_max_lost_seconds` 1,5, `track_min_hits` 3 (Treffer bis zur Bestätigung), `track_edge_margin_px` 40 (Spur am Bildrand endet sofort).

## 5. Wo was liegt

```
data\library\                          Bibliothek (Standard von --library), nie im Git
  spiel-001\
    match.json
    clip1\  clip.mp4, clip.json, testset\ (coco.json, images\)
            runs\run-001\  run.json, t3-ergebnis\                      (Migration)
            runs\run-002\  run.json, detections.json, tracks.json, summary.json, render\
            runs\run-003\  wie run-002
    clip2\, clip3\  clip.mp4, clip.json, testset\
data\clips\, data\testset\, data\ergebnis\t3\   alte Ordner (T1 bis T3), unverändert
```
- `src/matchstats/`: Code nach Schichten (Abschnitt 1). Neu in T4: `domain/tracking.py`, `application/tracker.py`, `application/tracking_stages.py`, `application/track_summary.py`, `infrastructure/video_source.py`, `stage_files.py`, `json_io.py`, `track_render.py`, `tracking_job.py`.
- `tests/` (T4): `test_tracker_rules.py` (Zuordnungsregeln), `test_tracking_stages.py` (Stufen und Cache), `test_tracking_files.py` (Dateiformate), `test_track_settings.py`, `test_track_summary.py`, `test_track_render.py`, `test_video_source.py`, `test_track_cli.py`, `test_cli_imports.py` (cv2/scipy erst beim `track`-Befehl geladen). Dazu die älteren Tests und `test_architecture.py`.
- `pyproject.toml`: Extra `track` = `scipy` (BSD) und `opencv-python` (Apache 2.0). Für den echten Lauf braucht `track` zusätzlich Extra `detect` (RF-DETR, siehe README Zeile 69). Ob eine frische Umgebung mit `.[track]` allein läuft, ist **unklar** (nicht geprüft).
- `docs/entscheidungen/`: 0001 Schichten, 0002 Agententeam, 0003 Testset und Label Studio, 0004 Detektor und Kacheln, 0005 Bibliothek, 0006 Tracking in Stufen.

## 6. Noch nicht umgesetzt oder unklar

- **Zählung (AK T4) ist nicht erledigt:** `docs/berichte/t4-zaehlung.md` ist eine leere Vorlage. Die ID-Wechsel pro Minute sind **nicht** von Hand gezählt. Nur die automatischen Hilfszahlen von run-003 stehen darin.
- **Kamerabewegung (T4b):** nicht umgesetzt. Die Vorhersage nimmt keine Schwenk- oder Zoombewegung heraus. Umsetzung nur, wenn die Zählung deutlich schlecht ist.
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
- **Teamzuordnung (T5), Ausgabe (T6), Bericht (T7):** geplant, nicht vorhanden.

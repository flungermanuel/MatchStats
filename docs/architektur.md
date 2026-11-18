# matchstats: Systemkarte

Stand: 2026-11-18, nach T3b (Bibliothek Spiel/Clip/Lauf, Messung je Halbzeit). Was nicht als *(geplant)* markiert ist, existiert im Repo. **unklar** = im Repo nicht gefunden oder nicht entschieden.

## 1. Schichten

Abhängigkeiten zeigen nur nach innen: `cli` -> `infrastructure` -> `application` -> `domain`. `tests/test_architecture.py` prüft das automatisch.

| Schicht | Ordner in `src/matchstats/` | Inhalt heute | darf importieren |
|---|---|---|---|
| domain | `domain/` | `Settings`, `RunResult`, Bildauswahl, Testset-Typen, `Detection` (IoU, NMS), Messregeln, Kachel-Geometrie, Bibliotheks-Typen (`library.py`: `Match`, `Clip`, `RecordingProfile`, `RunInfo`). Keine Dateizugriffe | nur domain |
| application | `application/` | `run_pipeline`, Port `Detector`, `TiledDetector`, `evaluate_detector`, Port `Library` und `LibraryError` | domain, application |
| infrastructure | `infrastructure/` | Parameter laden (Schichtung), Ergebnis speichern, Bilder aus Videos, ffprobe, Testset lesen, Detektoren (RF-DETR, YOLO), Bibliothek als Dateien (`file_library.py`), Messbericht, Clip-Tabelle | domain, application |
| cli | `cli.py`, `__main__.py` | Argumente lesen, Schichten verdrahten | alles |

Begriffe:
- **Port**: Schnittstelle, also die Festlegung, was ein Baustein können muss. Die Pipeline kennt nur den Port, nicht die Umsetzung (YOLO, RF-DETR, ffmpeg).
- **Bibliothek**: Ordner `data\library\` mit Spielen, Clips und Läufen. Ablage als JSON-Dateien, keine Datenbank.
- **Spiel**: ein Ligaspiel (ID, Name, Datum). **Clip**: ein Video eines Spiels, mit Halbzeit (1, 2 oder unbekannt) und Aufnahme-Profil.
- **Aufnahme-Profil**: Blickwinkel, Kameraverhalten, Notiz. Reine Daten ohne Logik; unbekannt bleibt `null`.
- **Lauf** (`run-001`, `run-002`, ...): Ordner für einen Verarbeitungslauf auf einem Clip, mit den aufgelösten Parametern in `run.json`.
- **Parameter-Schichtung**: Standard (`default.toml`), dann eigene Datei (`--config`), dann Profil (`clip.json`), dann Aufruf-Argumente. Die spätere Schicht gewinnt. Unbekannte Schlüssel werden mit Namen abgelehnt.
- **Schema-Version**: Zahl (aktuell 1) in jeder JSON-Datei. Eine andere Version führt zu einer klaren Fehlermeldung, nie zu einem Raten.

## 2. Bausteine

| Baustein | Datei | Eingabe | Ausgabe |
|---|---|---|---|
| CLI `run` | `cli.py` | Video, `--out`, optional `--config` | `tracks.json`. Nutzt die Bibliothek **nicht** |
| CLI `sample-frames` | `cli.py` | Videos, `--out`, `--count`, `--config` | PNGs + `manifest.json` im Ordner `--out`. **Nicht** an die Bibliothek angebunden (siehe 6) |
| CLI `evaluate` (alt) | `cli.py` | `--testset`, `--images`, `--out`, `--detectors`, `--overlays` | `report.json`, `report.md`, `overlays\` |
| CLI `evaluate --game <id> --half <n>` | `cli.py` | Bibliothek (`--library`, Standard `data\library`), `--out` | Ein Bericht über alle Clips der Halbzeit mit Testset. Schreibt nicht in die Bibliothek |
| CLI `match add` | `cli.py` | Spiel-ID, `--name`, `--date`, `--notes` | `match.json` |
| CLI `clip import` | `cli.py` | Video, `--game`, `--clip`, `--half`, `--angle`, `--camera-motion`, `--notes` | Clip-Ordner mit Kopie des Videos und `clip.json` (fps, Auflösung, Länge per ffprobe) |
| CLI `clip list` | `cli.py`, `clip_table.py` | `--game`, optional `--half` | Texttabelle; unbekannte Werte als "-" |
| Bibliothek | `infrastructure/file_library.py` (Port `application/library.py`, Typen `domain/library.py`) | Bibliotheksordner | Liest und schreibt die JSON-Dateien. Import überschreibt nie einen Clip; JSON wird erst in eine Hilfsdatei geschrieben, dann ersetzt (nie halbe Dateien). IDs nur mit Buchstaben, Ziffern, `_` und `-` |
| Lauf anlegen | `FileLibrary.create_run` | Clip, Parameter | `runs\run-NNN\run.json`. **Nur Migration und Tests rufen das auf; kein CLI-Befehl** |
| Parameter laden | `infrastructure/config_loader.py` (`load_settings`) | Datei, Profil-Überschreibungen, Aufruf-Werte | `Settings`. Erweitert um die Profil- und Aufruf-Schicht |
| Messung je Halbzeit | `infrastructure/evaluation_job.py` (`run_library_evaluation`) | Clips der Halbzeit mit `testset\coco.json` | Ein Bericht, eine nah/fern-Grenze über alle Bilder. Bildschlüssel `clip1/<Datei>`, damit gleiche Dateinamen nicht kollidieren |
| Migration (einmalig) | `tools/migrate_t3b.py` | `data\clips`, `data\testset`, `data\ergebnis\t3` | `spiel-001` mit clip1 bis clip3, Testset je Clip, T3-Ergebnisse als `clip1\runs\run-001\t3-ergebnis\`. Nicht Teil der CLI; ein zweiter Lauf braucht vorher Löschen von `spiel-001` von Hand |
| Messung (alt) | `application/evaluation.py`, `infrastructure/evaluation_job.py` (`run_evaluation`), `evaluation_report.py`, `image_io.py` | Testset-Datei, Bilderordner, Detektor-Varianten | Kennzahlen und Zeit je Bild und Variante, Bericht, Bilder mit Boxen |
| Detektor-Port | `application/detector.py` | Bild (RGB-Array) | Liste `Detection` (Box in Pixeln, Score) |
| Detektoren | `infrastructure/rfdetr_detector.py`, `yolo_detector.py` | Bild | Personenboxen. YOLO nur mit optionalem Extra `[yolo]` (AGPL) |
| Kacheln | `domain/tiling.py`, `application/tiling.py` | Bild, Kachelgröße, Überlappung | Boxen im Koordinatensystem des ganzen Bildes, Doppelte per NMS entfernt |
| Messregeln | `domain/metrics.py` | Erkennungen, Beschriftungen, nah/fern-Grenze | Treffer (IoU >= 0,5, je Box einmal), Recall, Precision, nah/fern. Fehlende Werte bleiben `None` |
| Settings | `domain/settings.py` | Werte aus der Konfiguration | `detect_every` (5), `frames_per_clip` (20), `detector_model` (small), `score_threshold` (0,3), `tile_size` (640), `tile_overlap` (0,2), `nms_iou` (0,5) |
| Auswahlregeln, Bilder ziehen | `domain/sampling.py`, `infrastructure/frame_sampler.py` | Clip, Ausgabeordner, Anzahl | Bilder + Manifest. Nutzt `ffprobe` (Dauer, Bildrate, Auflösung) und `ffmpeg` (Einzelbilder) |
| Testset-Typen und -Lader | `domain/testset.py`, `infrastructure/testset_loader.py` | `coco.json` | Liste `LabeledImage`. Formatfehler werden gemeldet, nie übergangen |
| Pipeline | `application/pipeline.py` | Videoname, `Settings` | `RunResult` mit leerer Spurliste. Das Video wird **nicht** geöffnet |
| Speichern | `infrastructure/result_store.py` | `RunResult`, Ausgabeordner | `tracks.json` |
| Beschriftungswerkzeug (extern) | `tools/start_labelstudio.ps1`, `docs/labelstudio/config.xml` | Bilder aus `data\testset\images` | COCO-Export. Kein eigener Code |

`python -m matchstats ...` startet dasselbe wie das Kommando (`__main__.py`).

## 3. Datenfluss

**Bibliotheks-Ast (T3b, heute):**
```
data\clips\clip1.mp4                      (Original, wird nur gelesen)
   |  matchstats clip import --game spiel-001 --clip clip1 --half 1 --angle ... --camera-motion ...
   |  ffprobe: fps, Auflösung, Länge; Kopie des Videos
data\library\spiel-001\clip1\clip.mp4 + clip.json
   |  Testset je Clip: testset\coco.json + testset\images\
   |     (heute nur durch tools\migrate_t3b.py gefüllt; ein CLI-Weg dafür fehlt, siehe 6)
   |  matchstats evaluate --game spiel-001 --half 1 --out <Ordner>
   |  alle Clips der Halbzeit mit coco.json; eine nah/fern-Grenze (Median) über alle Bilder
   v
<Ordner>\report.json, report.md, overlays\<variante>\*.png
```
Der Lauf `runs\run-001\` (durch die Migration angelegt) enthält die T3-Ergebnisse als Kopie. `evaluate --game` schreibt bisher nicht dorthin.

**Testset-Ast (T2, alt, unverändert):**
```
data\clips\clip1..3.mp4  -->  matchstats sample-frames  -->  data\testset\images\*.png + manifest.json
  -->  Beschriften in Label Studio  -->  Export COCO  -->  data\testset\coco.json
```

**Mess-Ast (T3, alt, unverändert):**
```
data\testset\coco.json + images\  -->  matchstats evaluate --out data\ergebnis\t3  -->  report.*, overlays\
```

**Pipeline-Ast (unverändert):**
```
clip.mp4 (nur geprüft: existiert die Datei?)
  -->  cli: load_settings(default.toml [+ --config])  -->  Settings
  -->  run_pipeline (keine Stufen, leeres Ergebnis)
  -->  save_result  -->  <out>\tracks.json
```

**Geplant (laut Spezifikation):**
```
Quelle (.MTS 1080i25) --T0, manuell mit ffmpeg/yadif--> Clips, progressiv 1080p25
  -> T4 Tracking: konstante IDs, Lücken werden überbrückt -> Spuren   *(geplant, baut auf der Bibliothek auf)*
  -> T5 Teamzuordnung: Klasse je Spieler                              *(geplant)*
  -> T6 Ausgabe: annotiertes Video + Spurdatei (Sichtbarkeit, Unsicherheit)  *(geplant)*
  -> T7 Bericht: Kennzahlen, Laufzeiten, Beispielbilder               *(geplant)*
```
Regel: Jede Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden aus gespeicherten Daten berechnet, nicht aus dem Video.

## 4. Dateiformate

Gemeinsam für die Bibliothek: UTF-8, Einrückung 2, `schema_version` (1) als erstes Feld. Pfade sind relativ zu `data\library\` und nutzen "/". Fehlende Werte sind `null`, nie 0.

- `match.json`: `{schema_version, id, name, date (JJJJ-MM-TT) oder null, notes}`.
- `clip.json`: `{schema_version, id, match_id, half (1, 2 oder null), source_file (z. B. "spiel-001/clip1/clip.mp4"), fps, width, height, duration_s, profile: {angle, camera_motion, notes}, settings: {}}`. `settings` sind die Profil-Überschreibungen; heute immer leer (siehe 6).
- `run.json`: `{schema_version, id ("run-001"), created (ISO-Zeit), clip_id, settings: {aufgelöste Parameter}}`.
- Erlaubte Profilwerte (Quelle `domain/library.py`): `angle` = `tribuene_hoch`, `seitenlinie`, `ecke`, `hinter_tor`, `sonstige`; `camera_motion` = `fest`, `schwenkt`, `schwenkt_und_zoomt`.
- Testset je Clip: `testset\coco.json` (COCO-Format wie in T2, Dateinamen ohne Label-Studio-Präfix) und `testset\images\`.
- Unverändert vorhanden: `manifest.json`, PNG-Bilder, `coco.json` (alt, global), Konfiguration (TOML), `report.json`/`report.md`, `tracks.json`, Label-Studio-Schema `config.xml`.
- Aus dem Entwurf `docs/entwuerfe/t3b-struktur.md` **nicht umgesetzt**: `interlaced`, `field_order` und `typical_player_height_px` im Profil, `stages` in `run.json`.

## 5. Wo was liegt

```
data\library\                       Bibliothek (Standard von --library), nie im Git
  spiel-001\
    match.json
    clip1\  clip.mp4, clip.json, testset\ (coco.json, images\), runs\run-001\ (run.json, t3-ergebnis\)
    clip2\  clip.mp4, clip.json, testset\ (coco.json, images\)     (ohne runs\)
    clip3\  wie clip2
data\clips\, data\testset\, data\ergebnis\t3\     alte Ordner (T1 bis T3), bleiben unverändert
```

- `src/matchstats/`: Code nach Schichten (Abschnitt 1). Neu in T3b: `domain/library.py`, `application/library.py`, `infrastructure/file_library.py`, `infrastructure/clip_table.py`.
- `tests/`: `test_file_library.py` (Bibliothek, Import mit Fake-Video, Läufe, Schema-Versionen), `test_library_domain.py` (Profilregeln), `test_library_cli.py` (Befehle, Messung je Halbzeit), `test_settings_layering.py` (Schichtung), `test_library_real.py` (Abnahme AK 3 am echten Spiel; nur mit `MATCHSTATS_SLOW=1`, sonst übersprungen, Laufzeit ca. 8 min). Dazu die älteren Tests und `test_architecture.py`.
- `tools/migrate_t3b.py`: einmalige Migration (Abschnitt 2).
- `docs/entscheidungen/`: 0001 Schichten, 0002 Agententeam, 0003 Testset und Label Studio, 0004 Detektor und Kacheln, 0005 Bibliothek (Spiel/Clip/Lauf).
- `README.md`, `CLAUDE.md`, `pyproject.toml`, `.gitignore` (`data/` und `ergebnis/` stehen drin).

## 6. Noch nicht umgesetzt oder unklar

- **Läufe:** Kein CLI-Befehl legt einen Lauf an. `run-001` entstand nur durch die Migration. `evaluate --game` schreibt in `--out`, nicht in den Lauf.
- **Profil-Parameter:** Die Überschreibungen aus `clip.json` (`settings`) wirken im Ablauf nicht. Der Import übergibt leere Überschreibungen; Messung und `run` lesen sie nicht. Getestet ist nur `load_settings` selbst.
- **`sample-frames`:** kennt keine Bibliothek (kein `--game`/`--clip`). Die Spezifikation T3b (AK 3) nennt den Befehl im Zusammenhang mit der neuen Struktur. **Abweichung, offen.** Wie das Testset eines neuen Clips im CLI entsteht, ist **unklar**.
- **`run`** (Pipeline) nutzt die Bibliothek noch nicht; das kommt mit T4.
- **Bewusst verschoben:** Stufen-Cache (T4), Verweis statt Kopie (`--link`), Deinterlacen und Schneiden beim Import, Oberfläche, Datenbank.
- **Messung:** eine Perspektive, ein Spiel (Testset), Score-Schwelle fest 0,3.
- Tracking, Teamzuordnung, Ausgabevideo und Bericht (T4 bis T7) sind geplant, nicht vorhanden.

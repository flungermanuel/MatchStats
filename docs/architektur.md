# matchstats: Systemkarte

Stand: 2026-11-16, nach T2 (Code fertig, beschriftetes Testset noch nicht vorhanden). Was hier nicht als *(geplant)* markiert ist, existiert im Repo. Was ich im Repo nicht finden konnte, steht als **unklar**.

## 1. Schichten und Abhängigkeitsrichtung

Abhängigkeiten zeigen nur nach innen: `cli` -> `infrastructure` -> `application` -> `domain`. Ein Test (`tests/test_architecture.py`) prüft das automatisch.

| Schicht | Ordner in `src/matchstats/` | Inhalt heute | darf importieren |
|---|---|---|---|
| domain | `domain/` | `Settings`, `RunResult`, `SampledFrame` (Bildauswahl), `LabeledBox`/`LabeledImage` (Testset). Reine Regeln und Datentypen, keine Dateizugriffe | nur domain |
| application | `application/` | `run_pipeline` (Ablauf). Noch keine Schnittstellen (Ports) | domain, application |
| infrastructure | `infrastructure/` | Konfiguration laden, Ergebnis speichern, Bilder aus Videos ziehen, Testset lesen | domain, application |
| cli | `cli.py`, `__main__.py` | Argumente lesen, Schichten verdrahten | alles |

Begriffe: Ein **Port** ist eine Schnittstelle, also eine Festlegung, was ein Baustein können muss (z. B. "ein Detektor liefert Personenboxen"). Die Pipeline kennt nur den Port, die konkrete Umsetzung (YOLO, RF-DETR) liegt in `infrastructure/`. Das ist noch *(geplant, T3)*.

## 2. Bausteine heute

| Baustein | Datei | Eingabe | Ausgabe |
|---|---|---|---|
| CLI `matchstats run` | `cli.py` | Videopfad, `--out <Ordner>`, optional `--config <toml>` | Meldung `Fertig: <Pfad>`. Exit 0; Exit 2, wenn das Video fehlt |
| CLI `matchstats sample-frames` | `cli.py` | 1 bis n Videos, `--out <Ordner>`, optional `--count` und `--config` | PNG-Bilder und `manifest.json` im Ausgabeordner. Exit 2 bei fehlendem Video oder Fehler beim Ziehen |
| Settings | `domain/settings.py` | Werte aus der Konfiguration | `detect_every` (Standard 5), `frames_per_clip` (Standard 20) |
| Konfiguration laden | `infrastructure/config_loader.py`, `default.toml` | `default.toml` im Paket, optional eigene TOML | `Settings`. Eigene Werte überschreiben Standardwerte |
| Auswahlregeln | `domain/sampling.py` | Dauer, Anzahl, Bildrate | Zeitpunkte in Abschnittsmitten, Bildnummer = round(Zeit x Bildrate) |
| Bilder ziehen | `infrastructure/frame_sampler.py` | Clip, Ausgabeordner, Anzahl | Bilder + Manifest. Nutzt `ffprobe` (Dauer, Bildrate) und `ffmpeg` (Einzelbilder) |
| Testset-Typen | `domain/testset.py` | - | Die vier Klassen, Box (Pixel, Ecke links oben), Bild mit Boxen |
| Testset-Loader | `infrastructure/testset_loader.py` | `coco.json` (Pfad) | Liste von `LabeledImage`. Jede Formatverletzung wird als Fehler gemeldet, nie still übergangen |
| Pipeline | `application/pipeline.py` | Videoname, `Settings` | `RunResult` mit leerer Spurliste. Das Video wird **nicht** geöffnet |
| Speichern | `infrastructure/result_store.py` | `RunResult`, Ausgabeordner | `tracks.json` im Ausgabeordner |
| Beschriftungswerkzeug (extern) | `tools/start_labelstudio.ps1`, `docs/labelstudio/config.xml` | Bilder aus `data/testset/images` | Beschriftung als Export (COCO). Kein eigener Code, nur Startskript und Schema |

`python -m matchstats ...` startet dasselbe wie das Kommando (`__main__.py`).

## 3. Datenfluss

**Testset-Ast (T2, heute):**
```
data\clips\clip1.mp4, clip2.mp4, clip3.mp4   (je 60 s, 1080p25)
   |
matchstats sample-frames   (cli -> frame_sampler -> ffprobe/ffmpeg, Zeitpunkte aus domain/sampling)
   |
data\testset\images\clip<N>_f<NNNNN>.png  +  manifest.json   (je 20 Bilder pro Clip)
   |
Beschriften in Label Studio (http://127.0.0.1:8080, Schema docs\labelstudio\config.xml)
   |
Export als COCO  -->  data\testset\coco.json        (manueller Schritt, noch nicht erfolgt)
   |
load_testset(coco.json)  -> Liste von LabeledImage
   |
tests\test_testset_real.py prüft das Ergebnis (heute übersprungen, weil coco.json fehlt)
```
Das Testset ist der Maßstab für spätere Messungen (T3 ff.). Es fließt heute in keine Pipeline-Stufe ein.

**Pipeline-Ast (T1, unverändert):**
```
clip.mp4  (nur geprüft: existiert die Datei?)
   |
cli.py  -->  load_settings(default.toml [+ --config])  -->  Settings
   |
run_pipeline(Dateiname, Settings)        keine Stufen, leeres Ergebnis
   |
save_result  -->  <out>/tracks.json
```

**Geplant (laut Spezifikation, Details offen):**
```
Quelle (.MTS 1080i25) --T0, manuell mit ffmpeg/yadif--> 3 Clips, progressiv 1080p25
  -> T2 Testset: 60 Bilder mit Boxen und Klassen (Team A/B, Torhüter, Schiedsrichter)   [Code fertig]
  -> T3 Erkennung: Detektor hinter Port, je Gesamtbild oder Kacheln, nur jedes N-te Bild   *(geplant)*
  -> T4 Tracking: konstante IDs, Lücken werden überbrückt  -> Spuren                       *(geplant)*
  -> T5 Teamzuordnung: Klasse je Spieler                                                   *(geplant)*
  -> T6 Ausgabe: annotiertes Video + Spurdatei (mit Sichtbarkeit und Unsicherheit)         *(geplant)*
  -> T7 Bericht: Kennzahlen, Laufzeiten, Beispielbilder                                    *(geplant)*
```
Regel: Jede Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden aus den gespeicherten Spuren berechnet, nicht aus dem Video.

## 4. Dateiformate

**Vorhanden:**
- `manifest.json` (in `data\testset\images\`): JSON-Liste, je Bild ein Eintrag mit `clip` (Dateiname des Videos), `time_s` (Soll-Zeitpunkt in Sekunden, nicht die gemessene Zeitmarke), `frame_number` (Bildnummer ab 0) und `file_name`. Ein erneutes Ziehen für einen Clip ersetzt nur dessen Einträge.
- Testbilder: PNG, Name `clip<N>_f<NNNNN>.png` (Zahl = Bildnummer im Clip), 1920 x 1080.
- Testset-Beschriftung `data\testset\coco.json`: **COCO-JSON**, Export aus Label Studio (laut Auftraggeber bestätigt, 2026-11-16). Enthält `images` (id, file_name, width, height), `annotations` (id, image_id, category_id, bbox), `categories` (id, name). Vier Klassen: `team_a`, `team_b`, `goalkeeper`, `referee`. `bbox` = `[x, y, Breite, Höhe]` in Pixeln, Ursprung links oben. Label Studio darf ein Präfix vor den Dateinamen setzen; der Lader ignoriert es.
- Konfiguration: TOML (`infrastructure/default.toml`, optional eigene Datei per `--config`). Schlüssel `detect_every`, `frames_per_clip`.
- Label-Studio-Schema: `docs/labelstudio/config.xml` (Label-Studio-Format, XML).
- `tracks.json` (im Ausgabeordner von `run --out`): JSON, UTF-8, Einrückung 2. Schlüssel: `source` (nur Dateiname des Videos), `config` (die Einstellungen; im Code `settings`, beim Speichern umbenannt), `tracks` (heute leere Liste), `schema_version` (1). Die Version wird erhöht, sobald sich das Format ändert.

**Geplant oder unklar:**
- Spurdatei (T6): Spezifikation sagt "Datei mit allen Spuren". Dass `tracks.json` sie aufnimmt, ist die Absicht des Codes, aber Felder für Sichtbarkeit und Unsicherheit gibt es noch nicht.
- Annotiertes Video (T6): Format **unklar**.
- Bericht (T7): Format **unklar**.
- Detektor-Ausgabe (T3): noch nicht festgelegt, **unklar**.
- Label-Studio-Export: Präfix vor Dateinamen und Pixelwerte sind im Code angenommen, aber noch **nicht an einer echten Exportdatei geprüft** (unklar, bis `coco.json` existiert).
- Die Spezifikation nennt COCO-JSON und Label Studio noch als Vorschlag. Die Anpassung der Spezifikation liegt beim Auftraggeber (nicht von mir geändert).

## 5. Wo was liegt

- `src/matchstats/`: Code, nach Schichten geordnet (Abschnitt 1).
- `tests/`: `test_architecture.py` (Schichtenregel), `test_cli.py`, `test_config.py`, `test_sampling.py` und `test_frame_sampler.py` (Bildauswahl und Ziehen), `test_testset_loader.py` (Format mit synthetischen Daten), `test_testset_real.py` (echtes Testset, übersprungen ohne `data\testset\coco.json`), `conftest.py`. Ausführen mit `pytest`.
- `tools/start_labelstudio.ps1`: startet Label Studio lokal auf `127.0.0.1:8080`. Daten nach `data\labelstudio\`, Nutzungsdaten aus. Kein Python-Code. Wie `.venv-labelstudio\` eingerichtet wird, steht nicht im Repo (**unklar**, im README fehlt der Schritt).
- `.venv-labelstudio\`: eigene Python-Umgebung für Label Studio, getrennt von `.venv\` (Projekt). In `.gitignore`.
- `docs/`: `projektbrief.md`, `woche1-spezifikation.md`, `architektur.md` (diese Karte), `entscheidungen/` (0001 Schichtenarchitektur, 0002 Agententeam, 0003 Testset und Label Studio), `labelstudio/config.xml` (Beschriftungsschema), `Prototyp/` (Screenshots).
- `data/` (nie im Git, per `.gitignore` geprüft): `clips\` (3 Clips), `testset\images\` (Bilder und `manifest.json`), `testset\coco.json` (fehlt noch), `labelstudio\` (Datenbank und Uploads von Label Studio).
- `ergebnis/` (Beispiel für `--out`): in `.gitignore`.
- `CLAUDE.md` (Arbeitsregeln), `README.md` (Einrichtung, Befehle, Testset-Format), `pyproject.toml` (Paket und Werkzeuge), `.gitignore`.
- `.claude/`: Einrichtung für Claude Code (Subagenten, Skills, Commit-Hook).

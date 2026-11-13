# matchstats: Systemkarte

Stand: 2026-11-13, nach T0 und T1. Was hier nicht als *(geplant)* markiert ist, existiert im Repo. Was ich im Repo nicht finden konnte, steht als **unklar**.

## 1. Schichten und Abhängigkeitsrichtung

Abhängigkeiten zeigen nur nach innen: `cli` -> `infrastructure` -> `application` -> `domain`. Ein Test (`tests/test_architecture.py`) prüft das automatisch.

| Schicht | Ordner in `src/matchstats/` | Inhalt heute | darf importieren |
|---|---|---|---|
| domain | `domain/` | `Settings`, `RunResult` (reine Datentypen) | nur domain |
| application | `application/` | `run_pipeline` (Ablauf). Noch keine Schnittstellen (Ports) | domain, application |
| infrastructure | `infrastructure/` | Konfiguration laden, Ergebnis speichern | domain, application |
| cli | `cli.py`, `__main__.py` | Argumente lesen, Schichten verdrahten | alles |

Begriffe: Ein **Port** ist eine Schnittstelle, also eine Festlegung, was ein Baustein können muss (z. B. "ein Detektor liefert Personenboxen"). Die Pipeline kennt nur den Port, die konkrete Umsetzung (YOLO, RF-DETR) liegt in `infrastructure/`. Das ist noch *(geplant, T3)*.

## 2. Bausteine heute

| Baustein | Datei | Eingabe | Ausgabe |
|---|---|---|---|
| CLI `matchstats run` | `cli.py` | Videopfad, `--out <Ordner>`, optional `--config <toml>` | Meldung `Fertig: <Pfad>`. Exit 0; Exit 2, wenn das Video fehlt |
| Settings | `domain/settings.py` | Werte aus der Konfiguration | Datentyp mit `detect_every` (Standard 5, mindestens 1) |
| Konfiguration laden | `infrastructure/config_loader.py`, `default.toml` | `default.toml` im Paket, optional eigene TOML | `Settings`. Eigene Werte überschreiben gleichnamige Standardwerte |
| Pipeline | `application/pipeline.py` | Videoname, `Settings` | `RunResult` mit leerer Spurliste. Das Video wird **nicht** geöffnet |
| Ergebnis-Datentyp | `domain/result.py` | - | Quelle, Einstellungen, `tracks` (leer), `schema_version` (1) |
| Speichern | `infrastructure/result_store.py` | `RunResult`, Ausgabeordner | `tracks.json` im Ausgabeordner |

`python -m matchstats ...` startet dasselbe wie das Kommando (`__main__.py`).

## 3. Datenfluss

**Heute (T1):**
```
clip.mp4  (nur geprüft: existiert die Datei?)
   |
cli.py  -->  load_settings(default.toml [+ --config])  -->  Settings
   |
run_pipeline(Dateiname, Settings)        keine Stufen, leeres Ergebnis
   |
save_result  -->  <out>/tracks.json
```

**Geplant (laut Spezifikation v1.1, Details noch offen):**
```
Quelle (.MTS 1080i25) --T0, manuell mit ffmpeg/yadif--> 3 Clips, progressiv 1080p25
  -> T2 Testset (manuell): 60 Bilder mit Boxen und Klassen (Team A/B, Torhüter, Schiedsrichter)
  -> T3 Erkennung: Detektor hinter Port, je Gesamtbild oder Kacheln, nur jedes N-te Bild
  -> T4 Tracking: konstante IDs, Lücken werden überbrückt  -> Spuren
  -> T5 Teamzuordnung: Klasse je Spieler
  -> T6 Ausgabe: annotiertes Video + Spurdatei (mit Sichtbarkeit und Unsicherheit)
  -> T7 Bericht: Kennzahlen, Laufzeiten, Beispielbilder
```
Regel: Jede Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden aus den gespeicherten Spuren berechnet, nicht aus dem Video.

## 4. Dateiformate

**Vorhanden:**
- `tracks.json` (im Ausgabeordner von `--out`): JSON, UTF-8, Einrückung 2. Schlüssel: `source` (nur Dateiname des Videos), `config` (die Einstellungen; im Code heißen sie intern `settings`, beim Speichern wird umbenannt), `tracks` (heute leere Liste), `schema_version` (1). Die Version wird erhöht, sobald sich das Format ändert.
- Konfiguration: TOML (`infrastructure/default.toml`, optional eigene Datei per `--config`).

**Geplant oder unklar:**
- Testset-Format (T2): Vorschlag COCO-JSON und Label Studio. In der Spezifikation noch **nicht bestätigt**.
- Spurdatei (T6): Spezifikation sagt "Datei mit allen Spuren". Dass `tracks.json` sie aufnimmt, ist die Absicht des Codes, aber Felder für Sichtbarkeit und Unsicherheit gibt es noch nicht (kein Spur- oder Messtyp in `domain/`).
- Annotiertes Video (T6): Format **unklar**.
- Bericht (T7): Format **unklar**.
- Detektor-Ausgabe (T3): noch nicht festgelegt, **unklar**.

## 5. Wo was liegt

- `src/matchstats/`: Code, nach Schichten geordnet (Abschnitt 1).
- `tests/`: `test_architecture.py` (Schichtenregel), `test_cli.py`, `test_config.py`. Ausführen mit `pytest`.
- `docs/`: `projektbrief.md` (Ziel, Architektur), `woche1-spezifikation.md` (Aufgaben T0 bis T7), `architektur.md` (diese Karte), `entscheidungen/` (0001 Schichtenarchitektur, 0002 Agententeam), `Prototyp/` (Screenshots).
- `.claude/`: Einrichtung für Claude Code. `agents/` (7 Subagenten: architect, backend-engineer, frontend-engineer, test-engineer, code-reviewer, product-owner, doc-keeper), `skills/` (aufgabe-start, aufgabe-abschluss), `hooks/pre_commit_check.py`, `settings.json`.
- `CLAUDE.md` (Arbeitsregeln), `README.md`, `pyproject.toml` (Paket und Werkzeuge), `.gitignore`.
- `data/`: Rohvideos, Clips, Bilder und Ergebnisse. Durch `.gitignore` von Git ausgeschlossen (per `git check-ignore` geprüft).
- `ergebnis/` (Beispiel für `--out`): ebenfalls in `.gitignore`. Der Ausgabeordner ist frei wählbar, nur `ergebnis/` ist ausgeschlossen.

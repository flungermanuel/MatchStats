# matchstats

Taktische Auswertung aus eigenen Videoaufnahmen von Ligaspielen: Positionsdaten, Heatmaps,
Formation, Kompaktheit. Leitprinzip: **Daten -> Erkenntnisse -> Darstellung.**

Stand: Woche 1, Aufgabe T3 (Erkennung). Der Befehl `matchstats run` erzeugt bisher nur ein
leeres, gültiges Ergebnis. `matchstats sample-frames` zieht die Testbilder (siehe "Testset"),
`matchstats evaluate` misst die Detektoren (siehe "Erkennung messen"). Tracking und
Teamzuordnung kommen in T4 und T5.

## Voraussetzungen
- Windows 11, Python 3.12 oder neuer (getestet mit 3.13), Git
- ffmpeg (inkl. ffprobe): `winget install Gyan.FFmpeg`
- Keine NVIDIA-GPU nötig, alles läuft auf der CPU.

## Einrichten (PowerShell)
```powershell
git clone <repo-url> matchstats
cd matchstats
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Nur für das Beschriften (T2):** Label Studio (Apache 2.0) läuft in einer eigenen Umgebung, weil es
viele Bibliotheken mitbringt:
```powershell
py -3.13 -m venv .venv-labelstudio
.venv-labelstudio\Scripts\python.exe -m pip install label-studio
```

## Benutzen
```powershell
matchstats run clip.mp4 --out ergebnis/
```
Ergebnis: `ergebnis/tracks.json` (Format siehe `src/matchstats/domain/result.py`).
Eigene Parameter: `--config meine.toml` (Standardwerte: `src/matchstats/infrastructure/default.toml`).

## Testset (T2)
Das Testset besteht aus 60 von Hand beschrifteten Bildern: 20 pro Clip, gleichmäßig gezogen
(jeweils die Mitte von 20 gleich langen Abschnitten, nicht von Hand ausgewählt).

1. Bilder ziehen (alle liegen unter `data/`, nicht im Git):
   ```powershell
   matchstats sample-frames data\clips\clip1.mp4 data\clips\clip2.mp4 data\clips\clip3.mp4 --out data\testset\images
   ```
   Ergebnis: `data\testset\images\clip1_f00038.png` usw. (Zahl = Bildnummer im Clip) und
   `manifest.json` (Clip, Zeitpunkt, Bildnummer, Dateiname).
2. Beschriften in Label Studio (Start: `.\tools\start_labelstudio.ps1`, dann
   http://localhost:8080). Schema: [docs/labelstudio/config.xml](docs/labelstudio/config.xml).
3. Export als **COCO** nach `data\testset\coco.json`.

**Festes Format (COCO-JSON, Pixelwerte):**
- `images`: `id`, `file_name`, `width` = 1920, `height` = 1080. Der Dateiname muss auf
  `clip<N>_f<5 Ziffern>.png` enden (Label Studio setzt davor ein Präfix, das beim Laden entfernt wird).
- `annotations`: `id`, `image_id`, `category_id`, `bbox` = `[x, y, Breite, Höhe]` in Pixeln, Ursprung links oben.
  Die Box darf höchstens 1 Pixel über den Bildrand hinausragen (Rundung beim Export).
- `categories`: `id`, `name`. Erlaubte Namen (Zuordnung über den Namen, nicht über die ID):
  `team_a`, `team_b`, `goalkeeper`, `referee`.
- Alle Spieler im Bild bekommen eine Box. Bilder ohne Person sind nur in Ausnahmefällen erlaubt.

Das Format prüft `tests/test_testset_loader.py` (synthetische Daten). `tests/test_testset_real.py`
prüft das echte Testset (60 Bilder, je 20 pro Clip, alle vier Klassen) und wird übersprungen,
solange `data\testset\coco.json` fehlt. Lader: `matchstats.infrastructure.testset_loader.load_testset`.

## Erkennung messen (T3)
Detektoren sind optionale Zusatzpakete (torch als CPU-Version):
```powershell
pip install -e ".[detect]" --extra-index-url https://download.pytorch.org/whl/cpu   # RF-DETR (Apache 2.0)
pip install -e ".[yolo]"                                                           # YOLO (AGPL-3.0), optional
matchstats evaluate --out data\ergebnis\t3                                          # alle Varianten
matchstats evaluate --detectors rfdetr --out data\ergebnis\t3                       # nur RF-DETR
```
Gemessen wird jeder Detektor als Ganzbild und als Kacheln auf den 60 Testbildern. Ergebnis:
`report.md` (Tabelle), `report.json` und Beispielbilder in `overlays\` (grün = getroffen,
gelb = verpasst, rot = Erkennung). Die Gewichte werden beim ersten Lauf heruntergeladen.
Parameter (Modellgröße, Score, Kacheln) stehen in `src\matchstats\infrastructure\default.toml`.

## Bibliothek: Spiel, Clip, Lauf (T3b)
Videos werden als Spiel → Clip → Lauf unter `data\library\` verwaltet (nie im Git):
```powershell
matchstats match add spiel-001 --name "Ligaspiel 1" --date 2026-11-15
matchstats clip import data\clips\clip1.mp4 --game spiel-001 --clip clip1 --half 1 --angle tribuene_hoch --camera-motion schwenkt_und_zoomt
matchstats clip list --game spiel-001
matchstats evaluate --game spiel-001 --half 1 --out data\ergebnis\spiel-001-h1   # ein Bericht je Halbzeit
```
Der Import kopiert das Video (Original bleibt unverändert). Gültige Profilwerte stehen in
`src\matchstats\domain\library.py`. `Match.name` und Notizen enthalten keine Spielernamen.
Profil-Überschreibungen (`settings` in `clip.json`) gelten für neue Läufe von `matchstats track`.
Die vorhandenen T3-Daten wurden einmalig mit `python tools\migrate_t3b.py` übernommen.

## Tracking (T4)
```powershell
# [track]: scipy + OpenCV (Tracking, Video); [detect]: RF-DETR (Erkennung), siehe oben
pip install -e ".[track,detect]" --extra-index-url https://download.pytorch.org/whl/cpu
matchstats track --game spiel-001 --clip clip1 [--variant whole|tiles] [--no-render]
matchstats track --game spiel-001 --clip clip1 --run run-001   # Erkennung wiederverwenden
```
Erkennt Personen auf jedem N-ten Bild und verbindet sie zu Spuren (ohne Kamerabewegung, ohne
Teamzuordnung). Ohne `--run` entsteht ein neuer Lauf; mit `--run` bleiben dessen Parameter
gültig und `detections.json` wird wiederverwendet, wenn die Erkennungs-Parameter gleich sind.
Im Lauf-Ordner: `detections.json`, `tracks.json`, `summary.json` (Kennzahlen, Laufzeiten) und
`render/tracks.mp4` (halbe Geschwindigkeit) plus `render/sheet_*.png` (alle 2 s, volle Auflösung).

## Entwickeln
```powershell
pytest                       # Tests
ruff check . ; ruff format . # Linting und Formatierung
```

## Aufbau
```
src/matchstats/
├─ domain/          Datentypen und Regeln (importiert nichts aus anderen Schichten)
├─ application/     Ablauf der Pipeline, Schnittstellen (z. B. Detektor)
├─ infrastructure/  Dateien, Video, Modelle, konkrete Detektoren, Konfiguration
└─ cli.py           Kommandozeile, verdrahtet die Schichten
tests/              Tests (inkl. Schichtentest `test_architecture.py`)
docs/               Projektbrief, Wochenspezifikation, Entscheidungsnotizen (`docs/entscheidungen/`)
data/               Rohvideos, Clips, Bilder, Ergebnisse: lokal, nie im Git
```
Abhängigkeiten zeigen nur nach innen: `cli -> infrastructure -> application -> domain`.
Begründung: [docs/entscheidungen/0001-schichtenarchitektur.md](docs/entscheidungen/0001-schichtenarchitektur.md).

## Daten und Datenschutz
Rohvideos, Clips, Bilder und Ergebnisse liegen in `data/` und werden nie committet
(siehe `.gitignore`). Keine Spielernamen im Code, in Tests oder in Commits.

Arbeitsregeln für Claude Code: [CLAUDE.md](CLAUDE.md).

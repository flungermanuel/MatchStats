# matchstats

Taktische Auswertung aus eigenen Videoaufnahmen von Ligaspielen: Positionsdaten, Heatmaps,
Formation, Kompaktheit. Leitprinzip: **Daten -> Erkenntnisse -> Darstellung.**

Stand: Woche 1, Aufgabe T1 (Projektgerüst). Der Befehl `matchstats run` erzeugt bisher nur ein
leeres, gültiges Ergebnis. Erkennen, Tracken und Teamzuordnung kommen in T3 bis T5.

## Voraussetzungen
- Windows 11, Python 3.12 oder neuer (getestet mit 3.13), Git
- ffmpeg (ab T3 nötig): `winget install Gyan.FFmpeg`
- Keine NVIDIA-GPU nötig, alles läuft auf der CPU.

## Einrichten (PowerShell)
```powershell
git clone <repo-url> matchstats
cd matchstats
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Benutzen
```powershell
matchstats run clip.mp4 --out ergebnis/
```
Ergebnis: `ergebnis/tracks.json` (Format siehe `src/matchstats/domain/result.py`).
Eigene Parameter: `--config meine.toml` (Standardwerte: `src/matchstats/infrastructure/default.toml`).

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

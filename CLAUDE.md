# matchstats: Arbeitsregeln für Claude Code

## Projekt
matchstats erzeugt aus eigenen Videoaufnahmen von Ligaspielen taktische Auswertungen (Positionsdaten, Heatmaps, Formation, Kompaktheit). Leitprinzip: Daten -> Erkenntnisse -> Darstellung. Bildverarbeitung (Erkennen, Tracken, Kalibrieren) machen spezialisierte Modelle; Agenten orchestrieren, prüfen und interpretieren und erkennen keine Spieler pro Bild.

Maßgebliche Dokumente (vor jeder Aufgabe die passende lesen):
- `docs/projektbrief.md`: Ziel, Architektur, Prinzipien, Roadmap.
- `docs/woche1-spezifikation.md`: aktuelle Aufgaben T0 bis T7 mit Abnahmekriterien (AK) und Messregeln.
Bei Widerspruch zwischen Code und Spezifikation gilt die Spezifikation. Ändere sie nicht stillschweigend: Schlage die Änderung vor und warte auf mein Ja.

## Zusammenarbeit
- Ich bin Informatikstudent (5. Semester), kein sicherer Programmierer. Ziel des Projekts ist auch, sauberes Vibe Coding zu lernen: Ich führe Regie, du implementierst, Tests sichern die Qualität.
- Antworte auf Deutsch, kurz und verständlich. Bezeichner im Code auf Englisch, Kommentare und Doku auf Deutsch.
- Erkläre vor dem Commit in einfachen Worten, was sich geändert hat und warum. Erkläre neue Begriffe oder Bibliotheken beim ersten Auftreten in ein, zwei Sätzen.
- Wenn etwas unklar ist, frage nach, statt zu raten.

## Ablauf pro Aufgabe
1. Aufgabe und Abnahmekriterium aus der Spezifikation in eigenen Worten zusammenfassen, Rückfragen stellen.
2. Plan vorschlagen und auf meine Bestätigung warten.
3. Zuerst den Test schreiben (er bildet das Abnahmekriterium ab), dann die Umsetzung.
4. Ergebnisse an echten Bildern zeigen (Ausgabebilder anlegen), nicht nur an Zahlen.
5. Ein Commit pro Aufgabe mit klarer Message. Keine Arbeit über die aktuelle Aufgabe hinaus.
6. Am Ende: kurze Entscheidungsnotiz in `docs/entscheidungen/` (Was, Warum, Alternativen), falls eine Architekturentscheidung gefallen ist.

## Modellwahl (Kontingent schonen, Claude Pro)
Standard ist **Sonnet 5.5**. Du kannst das Modell nicht selbst wechseln: Sag mir rechtzeitig und konkret Bescheid ("Wechsle jetzt mit /model auf Opus, weil ...") und sag auch, wann ich zurückwechseln kann.
- **Opus empfehlen**, wenn: eine Architekturentscheidung ansteht, die später schwer zu ändern ist (z. B. Schnittstelle des Detektors, Format der Spurdatei, Pipeline-Aufbau); ein Fehler nach zwei erfolglosen Versuchen nicht gelöst ist; eine Änderung viele Dateien (grob mehr als 5) gleichzeitig betrifft. Danach zurück auf Sonnet.
- **Haiku empfehlen**, wenn: rein mechanische Arbeit anfällt (Umbenennen, Log-Zeilen, Boilerplate, Formatierung, einfache Erklärungen).
- **Nie Fable verwenden** (läuft auf Pro nur über kostenpflichtige Credits).
- Weise mich darauf hin, wenn eine Sitzung lang wird (viele Dateien gelesen, viel Hin und Her): Dann ist `/clear` oder eine neue Sitzung für die nächste Aufgabe günstiger, und `/usage` zeigt, was das Kontingent verbraucht.
- Lies nur die Dateien, die du für die Aufgabe brauchst. Keine ganzen Verzeichnisse durchsuchen, keine großen Ausgaben (Videos, lange Logs) in die Sitzung kopieren.

## Umgebung
- Windows 11, Intel Core Ultra 7 155H, 16 GB RAM, **keine NVIDIA-GPU**: alles läuft auf der CPU (OpenVINO als Option). Kein CUDA voraussetzen, keine GPU mieten.
- Python, getrennte virtuelle Umgebung. Pfade und Befehle müssen unter Windows (PowerShell) funktionieren.
- ffmpeg ist installiert.
- Video immer **Bild für Bild** lesen, nie komplett in den Speicher laden.
- Erkennung läuft nur auf jedem N-ten Bild (Parameter `detect_every`, Start 5); das Tracking überbrückt die Lücken.
- Python 3.13 (mindestens 3.12), virtuelle Umgebung in `.venv/`.

### Befehle (PowerShell, im Projektordner)
```
py -3.13 -m venv .venv                  # einmalig: Umgebung anlegen
.venv\Scripts\Activate.ps1              # Umgebung aktivieren
pip install -e ".[dev]"                 # einmalig: Projekt und Entwicklungswerkzeuge installieren
pytest                                  # Tests
ruff check . ; ruff format .            # Linting und Formatierung
matchstats run clip.mp4 --out ergebnis/ # Verarbeitung starten
```
Vor jedem Commit müssen `pytest` und `ruff check .` grün sein.

## Systemarchitektur (verbindlich)
Das Projekt ist in Schichten gebaut, damit es sich leicht ausbauen lässt (später Weboberfläche, Dienst, Warteschlange, Agenten). Abhängigkeiten zeigen nur nach innen:

```
cli  ->  infrastructure  ->  application  ->  domain
```
| Schicht | Ordner in `src/matchstats/` | Aufgabe | Darf importieren |
|---|---|---|---|
| domain | `domain/` | Reine Datentypen und Regeln (Settings, Ergebnis, später Spur, Messung) | nur domain |
| application | `application/` | Ablauf der Pipeline, Schnittstellen (Ports) wie `Detector` | domain, application |
| infrastructure | `infrastructure/` | Außenwelt: Dateien, Video lesen, Modelle, konkrete Detektoren, Konfig laden | domain, application |
| cli | `cli.py` | Einstiegspunkt, verdrahtet die Schichten (später ersetzbar durch API/Web) | alles |

Regeln:
- Neue Funktion zuerst der richtigen Schicht zuordnen. Im Zweifel nachfragen, nicht mischen.
- Schnittstellen (Ports) liegen in `application/`, ihre Implementierungen in `infrastructure/`. Die Pipeline kennt nur die Schnittstelle, nie YOLO, RF-DETR, ffmpeg oder OpenCV.
- Jede Pipeline-Stufe ist ein eigenes Modul mit klarer Ein- und Ausgabe (Datentypen aus `domain/`) und speichert ihr Ergebnis über die Infrastruktur.
- Keine Logik in `cli.py`: nur Argumente lesen, Schichten verdrahten, Ergebnis melden.
- Keine zirkulären Imports, keine Imports "nach außen". `tests/test_architecture.py` prüft das automatisch; der Test darf nicht abgeschwächt werden.
- Importe zwischen Schichten immer absolut (`from matchstats.domain...`).
- Neue Schicht oder neues Top-Level-Paket nur nach Rücksprache mit mir, mit Eintrag in `docs/entscheidungen/`.

## Architekturregeln
- Der Detektor steht hinter einer austauschbaren Schnittstelle (YOLO ist AGPL-3.0, RF-DETR ist Apache 2.0). Kein Detektor-spezifischer Code außerhalb seiner Implementierung (`infrastructure/`); der Schichtentest prüft, dass `ultralytics` und `rfdetr` nur dort importiert werden.
- Jede Pipeline-Stufe speichert ihr Zwischenergebnis auf Platte. Kennzahlen werden später aus gespeicherten Spuren berechnet, nicht aus dem Video.
- Jede Messung hat Felder für Sichtbarkeit ("im Bild?") und Unsicherheit. Unbekannt ist nicht null: fehlende Werte werden als fehlend gespeichert, nicht als 0.
- Heatmaps und Grafiken werden deterministisch aus Daten gerendert.
- Parameter (z. B. `detect_every`, Schwellwerte, Modellname) kommen aus einer Konfiguration, nicht fest im Code.
- Einfach halten: keine zusätzlichen Bibliotheken oder Abstraktionen, die die aktuelle Aufgabe nicht braucht. Bei neuen Abhängigkeiten kurz begründen und Lizenz nennen.

## Messen und Testen
- Messregeln stehen in der Spezifikation (IoU 0,5, Recall/Precision, nah/fern, ID-Wechsel). Nicht ändern, ohne zu fragen.
- Tests müssen schnell laufen und ohne die großen Videos auskommen (kleine Testdaten verwenden).
- Gemessene Werte nie schönen oder runden, ohne es zu sagen. Wenn ein Ergebnis schlecht ist, zeige es und erkläre mögliche Ursachen.

## Daten und Datenschutz
- Rohvideos, Clips, Bilder und Ergebnisse liegen in `data/` und **nie im Git** (.gitignore prüfen, bevor etwas committet wird).
- Keine Spielernamen, keine Rohvideos oder Bilder von Personen in Code, Tests, Commits oder externen Diensten.
- Keine Daten an externe Dienste schicken, ohne vorher zu fragen.

## Nicht tun
- Nicht über die aktuelle Aufgabe hinaus arbeiten (keine vorgezogenen Features aus späteren Wochen).
- Keine Dateien außerhalb des Projektordners ändern. Nichts löschen, ohne zu fragen.
- Kein `git push`, kein Force-Push, keine History-Änderungen ohne meine ausdrückliche Anweisung.
- Keine `Co-Authored-By`-Zeilen und keine Claude-Hinweise in Commit-Messages oder Pull-Requests. Der Autor bin allein ich.
- Keine Tests abschwächen oder auskommentieren, damit sie grün werden. Wenn ein Test falsch erscheint, sag es mir.

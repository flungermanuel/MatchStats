# 0010: Teams je Spur, Abstimmung und Stufen-Cache (T5b1)

Datum: 2026-11-25. Spezifikation v1.6 (T5). Noch nicht an `matchstats track` angebunden (T5b2).

## Was
- **Stufe `team_stage`** (`application/team_stage.py`): Aus `tracks.json` (als `RunResult`) und dem Video entsteht `teams.json` (Version 1) im Lauf-Ordner. Die Stufe kennt nur Ports (`FrameSource`, `TeamClassifier`, `TeamsStore`).
- **Abstimmung je Spur** über höchstens `team_samples_per_track` (8) gesehene Punkte (`visible: true`), gleichmäßig über die Spur gewählt, erster und letzter Punkt inklusive.
- **Ein `classify`-Aufruf je Clip** über alle Stichproben aller Spuren, weil der Klassifikator über die ganze Menge gruppiert. Das Video wird einmal gelesen; je Stichprobe wird nur ein **Ausschnitt als Kopie** um die Box gehalten (nicht das 1080p-Bild).
- **Bildschrittweite per gcd:** Gelesen werden nur Bilder, deren Nummer ein Vielfaches des größten gemeinsamen Teilers aller gewünschten Bildnummern ist (bei `detect_every` 5 also jedes 5. Bild); nach dem letzten gewünschten Bild wird abgebrochen.
- **Mehrheit mit Mindeststimmen:** Die häufigste bekannte Klasse gewinnt. "Unbekannt" wird gezählt (`votes`), stimmt aber nicht mit. Weniger als `team_min_votes` (3) bekannte Stimmen: `label` ist `null`, nicht eine Zufallsklasse.
- **Unsicherheit** = 1 minus Anteil der Siegerklasse an den bekannten Stimmen (3:1 gibt 0,25; 4:0 gibt 0; `null` ohne bekannte Stimme).
- **Gleichstand** entscheidet die Reihenfolge von `CLASSES` (`team_a`, `team_b`, `goalkeeper`, `referee`), also deterministisch.
- **Cache-Schlüssel:** alle `team_*`-Parameter plus Klassifikatorname (`stage_params`), Videoidentität (Dateiname, Bildanzahl) und **Spur-Fingerabdruck** (sha256 über id, frame, x, y, w, h und `visible`, auf 2 Stellen gerundet, unabhängig von der Spurreihenfolge). Passt alles, wird weder das Video gelesen noch klassifiziert.
- **Eigener Port `TeamsStore`** (`load_teams`/`save_teams`); `FileStageStore` setzt ihn um (`teams.json`; abgeschnitten = `None`, falsche Version = `ValueError`).
- Kennzahlen als reine Funktionen in `domain/teams.py`: `class_change_share` (Anteil Spuren mit Klasse, die mindestens eine bekannte Stimme für eine andere Klasse haben) und `null_track_count`.

## Warum
- Eine Klasse je Spur statt je Box: Einzelne Fehlklassifikationen kippen eine Spur nicht, und spätere Kennzahlen brauchen eine Klasse je Spieler.
- Ein Aufruf je Clip: "Team A" hat keine feste Farbe (siehe 0009); die Gruppierung braucht viele Boxen gemeinsam.
- Ausschnitte als Kopien: Tausende Ganzbilder im Speicher wären zu viel, und eine View würde das Ganzbild halten. Der Ausschnitt-Ursprung ist gerade, damit die Vorhersage mit der auf dem Ganzbild übereinstimmt (`test_team_crop.py`).
- `null` statt Raten: Unbekannt ist nie 0 und nie eine Zufallsklasse.
- Fingerabdruck im Cache: `teams.json` hängt von den Spuren ab; ändert sich eine Spur, wäre die Datei sonst veraltet.
- Eigener Port: `StageStore` bleibt unverändert, die Teamstufe zieht keine Kamera- und Erkennungsmethoden mit.

## Alternativen
- **Ganzbilder im Speicher halten:** verworfen, Speicherbedarf.
- **Teams in `tracks.json` schreiben:** verworfen, bräuchte einen Versionssprung bei `tracks.json` und koppelt die schnelle Spurbildung (läuft immer neu) an eine teure Stufe.
- **`StageStore` um `load_teams`/`save_teams` erweitern:** verworfen, jede Fake-Umsetzung in Tests müsste sie mitführen; ein eigener kleiner Port ist einfacher.
- **Gewichtete Abstimmung** (nach Boxgröße oder Sicherheit): nicht jetzt, keine Messung zeigt, dass einfache Mehrheit nicht reicht.
- **Stufenkette verallgemeinern:** verworfen (Bremse laut Systemkarte); jede Stufe hat ihren eigenen Cache, geteilt wird nur die Prüfung `_is_reusable`.

## Messung (Handlauf clip1, run-005, nicht an `track` angebunden)
| Wert | Ergebnis |
|---|---|
| Spuren | 73 |
| team_a / team_b | 24 / 49 |
| Torwart / Schiedsrichter | 0 / 0 |
| label `null` | 0 |
| Anteil Spuren mit wechselnder Klasse | **45,2 %** |
| Stichproben | 573 |
| Laufzeit der Stufe | 14,6 s |
| Laufzeit bei Cache-Treffer | 0,38 s |

Befund und Grenzen:
- **45,2 % wechselnde Klasse** ist hoch. Die Schwelle von 30 % (Stopp-Grund für T5b2) ist geraten. Ob die Schwelle oder das Verfahren der Maßstab ist, ist **offen**; vor T5b2 werden Beispiele angesehen.
- Torwart und Schiedsrichter kommen nicht vor (passt zu 0009: über Farbe nicht getrennt); Thema von T5c.
- **Messrisiko:** Die Gruppierung läuft jetzt über die Stichproben je Spur (höchstens 8 je Spur) statt über alle Boxen je Bild wie in T5a. Dadurch ändert sich das Gewicht von `team_outlier_max_share` (Gruppenanteile beziehen sich auf andere Mengen). Die Zahlen sind mit T5a nicht direkt vergleichbar.
- Ein Clip, ein Lauf, keine Wahrheit je Spur: Es gibt keine Trefferquote, nur die Konsistenz der Abstimmung. Parameter sind geraten.

## Offene Nachbesserungen aus dem Review
- `team_stage` importiert das private `_is_reusable` aus `tracking_stages.py`; es sollte öffentlich werden oder über ein Protocol laufen.
- Fehlen Stichproben, weil das Video zu kurz ist, werden sie still verschluckt; eine Warnung fehlt.
- `load_teams` prüft die Struktur von `votes` nicht.
- Tests fehlen für eine leere Spurliste und für eine Stichprobe nur auf Bild 0.

## Nummerierung
Die Ursachenklärung der dritten Farbgruppe sowie Torwart und Schiedsrichter (T5c) bekommt die Nummer **0011** (im Backlog bisher als 0010 geführt).

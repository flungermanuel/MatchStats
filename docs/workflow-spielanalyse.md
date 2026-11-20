# Workflow: Spielanalyse (Anwendersicht, Zielbild)

Stand: 2026-11-20. Das ist ein **Entwurf** aus dem Projektbrief, keine Spezifikation. Er beschreibt, wie ein Anwender (Trainer oder Analyst eines Vereins) ein Spiel von der Aufnahme bis zum Briefing durchläuft. Die Systemarchitektur in `docs/architektur.md` (Teil A) ist daraus abgeleitet. Woche-1-Spezifikation und Brief ändert dieses Dokument nicht.

## Rolle und Ziel
- **Anwender:** Trainer oder Analyst. Hat ein Video vom eigenen Spiel (Hochstativ, taktische Ansicht), will in der Halbzeit oder danach wissen: Wie stand die Mannschaft (Formation, Kompaktheit, Abstände), wo wurde gelaufen (Heatmaps), wo gab es Auffälligkeiten (Umschaltmomente).
- **Nebenrolle Liga:** will Statistiken und Grafiken als Bilddatei.
- **Ergebnis für den Anwender:** Ein Spiel mit Kennzahlen, Heatmaps, Minimap-Video und einem kurzen Bericht, dazu der Hinweis, **wie verlässlich** die Zahlen sind (Abdeckung, Kalibriergüte).

## Der klassische Ablauf (Happy Path)

| # | Schritt des Anwenders | Was das System tut | Ergebnis (gespeichert) | Stand |
|---|---|---|---|---|
| 1 | **Spiel anlegen**: Name, Datum, Mannschaften, **eigene Mannschaft wählen** | Spiel in der Bibliothek anlegen | `match.json` | vorhanden (CLI `match add`), Mannschaften fehlen |
| 2 | **Video importieren**, Halbzeit angeben, Aufnahme-Profil wählen (Perspektive, Kamera fest oder schwenkt) | Original kopieren, fps/Auflösung lesen, bei Zeilensprung deinterlacen | `clip.mp4`, `clip.json` | vorhanden (CLI `clip import`); Deinterlacen noch manuell (T0) |
| 3 | **Aufnahme prüfen** | Abschnitte erkennen, in denen Tracking nichts taugt (Zoom auf Jubeltraube, Schnitt, Pause) und ausschließen; Kamerabewegung schätzen | `segments.json`, `camera.json` | geplant (T4b nur bei Bedarf) |
| 4 | **Feld kalibrieren**: wenige Schlüsselbilder, vier bis sechs Feldpunkte anklicken | Bild-zu-Feld-Abbildung rechnen, über den Abschnitt fortführen, Drift prüfen | `calibration.json` (mit Güte je Bild) | geplant (Woche 2) |
| 5 | **Verarbeitung starten** ("Analyse läuft", Fortschritt sichtbar) | Pipeline: Erkennen, Tracken, Spielfeldfilter, Teams zuordnen, in Feldkoordinaten umrechnen | `detections.json`, `tracks.json`, `teams.json`, `pitch_tracks.json` | Erkennen und Tracken vorhanden (T4), Rest geplant (T5, Woche 2) |
| 6 | **Qualität prüfen**: Qualitätsbericht lesen, Stichproben im Viewer ansehen | Abdeckung ("im Bild?"), Anteil gesehen/überbrückt, Kalibriergüte, Auffälligkeiten melden | `quality.json` | geplant |
| 7 | **Korrigieren (nur bei Bedarf)**: Team einer Spur ändern, Torhüter/Schiedsrichter markieren, Spuren zusammenführen, Ordner/Bank entfernen | Korrekturen als eigene Datei speichern, **Rohdaten bleiben unverändert** | `corrections.json` | geplant |
| 8 | **Kennzahlen ansehen**: Heatmaps, Formation, Kompaktheit, Linienabstände, Tempo | Kennzahlen aus gespeicherten Spuren berechnen (kein neuer Bildlauf) | `metrics.json`, Heatmap-Bilder | geplant (nach Woche 2) |
| 9 | **Viewer**: Video mit Minimap, Zeitleiste, Szenen anspringen | Daten und Video zusammen ausliefern | (Oberfläche) | geplant (Woche 3 bis 4) |
| 10 | **Bericht und Export**: Halbzeit-Briefing, Heatmap als Bilddatei, Kennzahlen als Tabelle | Bericht deterministisch aus Daten bauen; Text nur mit Faktenprüfung und Freigabe | `report.md`/PDF, PNG | geplant |
| 11 | **Spiele vergleichen** (später) | Kennzahlen mehrerer Spiele nebeneinander | Vergleichsansicht | geplant (danach) |

## Varianten und Fehlerfälle
- **Schlechte Aufnahme:** Schritt 3 meldet "Abschnitt unbrauchbar". Der Anwender sieht, welcher Anteil des Spiels auswertbar ist; Kennzahlen werden mit dieser Abdeckung gerechnet und ausgewiesen.
- **Kalibrierung driftet** (Kamera schwenkt stark): Das System meldet die Stelle; der Anwender setzt ein weiteres Schlüsselbild und es wird nur ab dort neu gerechnet.
- **Neuer Parameter oder neues Modell:** Neuer **Lauf** auf demselben Clip. Der alte Lauf bleibt, Läufe sind vergleichbar. Nur betroffene Stufen rechnen neu (Stufen-Cache).
- **Neue Kennzahl:** Rechnet nur die Kennzahl-Stufe aus vorhandenen Spuren neu, **kein** neuer Bildlauf.
- **Abbruch mitten im Lauf:** Der Lauf ist als "unvollständig" erkennbar; Wiederaufnahme ab der letzten fertigen Stufe.
- **Mehrere Clips pro Halbzeit:** Ein Spiel besteht aus mehreren Clips; Kennzahlen gelten je Clip, Halbzeit und Spiel (Zusammenfassung über Clips).

## Was der Anwender nie tun muss
Videos von Hand schneiden (nach Zielbild macht der Import das), Parameter von Hand setzen (Profil und Standardwerte reichen), Rechenstufen einzeln starten (außer Entwickler-CLI).

## Entschieden und offen
1. **Entschieden (2026-11-20):** Der Anwender wählt **seine Mannschaft** im Spiel aus und bekommt Kennzahlen, Heatmaps und Briefing aus deren Sicht (Gegner als Vergleich). Folge: `match.json` bekommt Mannschaften und die eigene Seite; Teamzuordnung (T5) liefert "Team A/B", der Anwender ordnet "meine Mannschaft" zu.
Noch offen:
2. Reichen vier Feldpunkte je Schlüsselbild, oder soll das Werkzeug Linien erkennen? (Brief: manuell plus automatische Fortführung.)
3. Korrekturen (Schritt 7) in Woche 3 bis 4 oder später? Ohne sie ist jede Fehlzuordnung dauerhaft in den Kennzahlen.

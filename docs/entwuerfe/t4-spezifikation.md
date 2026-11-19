# T4 Tracking: Spezifikation (Entwurf zur Freigabe)

Stand: 18.11.2026. Entwurf; die verbindliche Wochenspezifikation (`docs/woche1-spezifikation.md`) ändert sich nur
nach deinem Ja (siehe Abschnitt 9). Vorgaben aus der Besprechung: Kamera schwenkt und zoomt, nicht
immer sind alle Spieler im Bild; Rechenzeit in der Entwicklung minimal halten; 6 bis 8 Spieler von Hand zählen.

**Voraussetzung:** T3b (Spiel-/Clip-/Lauf-Struktur) ist umgesetzt. Alle Dateien dieses Entwurfs (`detections.json`, `camera.json`, `tracks.json`) liegen im Ordner eines Laufs (`runs/<run_id>/`), Parameter kommen aus Standard, Profil und Aufruf.

## 0. Beschlüsse (18.11.2026, nach Architektur-Prüfung; gehen den Abschnitten unten vor)
- Wochenspezifikation auf **v1.4** gehoben (Abschnitt 9 umgesetzt).
- **Kamerabewegung nicht in T4**: Stufe 2, `camera.json`, Port `CameraMotionEstimator` und Regeln 7/8 entfallen vorerst. Sie kommen als T4b nur, wenn die Handzählung ohne Ausgleich deutlich schlecht ist. Regel 7 gilt in T4 in der Form "ohne Kamerawissen" (keine Verschiebung der Vorhersage).
- **Detektor in der Entwicklung: RF-DETR Ganzbild.** Variantenschalter `--variant whole|tiles` existiert, Kacheln laufen später (z. B. für T7).
- **Schwellen:** `detect_min_score` (0,1) filtert beim Speichern von `detections.json` (Parameter der Erkennungsstufe); `track_high_score` (0,5) eröffnet neue Spuren und trennt hoch/niedrig; `track_new_score` entfällt. `track_low_score` entfällt ebenfalls (= `detect_min_score`).
- **Ein Befehl** `matchstats track --game <id> --clip <id> [--variant] [--run <id>]` statt `detect`/`camera`/`track`/`render`. Stufen-Cache: Eine Stufe wird nur übersprungen, wenn ihre Datei existiert **und** ihre Stufen-Parameter (Detektor, Variante, Modell, `detect_every`, `detect_min_score`) übereinstimmen. Schreiben über Temp-Datei plus Umbenennen. Das Tracking läuft immer neu (Sekunden).
- **Schichten:** Datentypen in `domain/`; Port `Tracker` und Implementierung `ByteTrackLikeTracker` (reine Rechnung, numpy/scipy) in `application/`; Port `FrameSource` (Video bildweise lesen) in `application/`, OpenCV-Umsetzung in `infrastructure/`; Stufenablauf in `application/`, nicht in `cli.py`.
- **Dateiformate:** eigene `schema_version` je Datei. `tracks.json` wird Version 2 (Version 1 wird mit klarer Meldung abgelehnt). `run.json` erhält Versionen von Detektor und Bibliotheken.
- **Darstellung:** nur als Zählhilfe (Box + ID, Kontaktbögen); T6 erweitert dasselbe Modul.
- **Hilfszahlen:** Spuren pro Minute, mittlere Spurlänge, Anteil `visible`.
- Neue Abhängigkeiten als Extra `track`: `scipy` (BSD), `opencv-python` (Apache 2.0).

## 1. Ziel und Abnahmekriterium
Aus den Erkennungen (jedes N-te Bild) entstehen **Spuren mit konstanter ID** für jedes Bild des Clips.
- **AK (aus der Wochenspezifikation):** Auf einem Clip werden ID-Wechsel pro Minute von Hand gezählt und im Bericht notiert, mit Methode.
- **AK (zusätzlich, automatisch geprüft):** Tests mit künstlichen Daten belegen die Regeln aus Abschnitt 5; Spuren werden als Datei gespeichert und wieder gelesen (Schema-Test).

## 2. Bausteine und Datenfluss
```
Video ──► Stufe 1: Erkennung ──► detections.json   (jedes N-te Bild, alle Scores >= 0,1)
Video ──► Stufe 2: Kamerabewegung ► camera.json     (je Erkennungsbild eine 2x3-Transformation)
detections.json + camera.json ──► Stufe 3: Tracking ──► tracks.json (alle Bilder, mit ID)
tracks.json + Video ──► Stufe 4: Darstellung ──► tracks.mp4 + Kontaktbogen-Bilder
```
Jede Stufe speichert ihr Ergebnis; **Stufe 3 liest nur Dateien** und läuft deshalb in Sekunden. Das ist die Antwort auf
"Rechenzeit minimal": Erkennung (teuer) und Kamerabewegung (mittel) laufen **einmal** pro Clip und Variante, das Tracker-Tuning
beliebig oft darauf.

| Schicht | Neu |
|---|---|
| `domain/` | `Track`/`TrackPoint` (Spur, Position je Bild, `visible`, `score`), `CameraMotion` (2x3-Matrix), Kalman-Box-Zustand und Zuordnungsregeln als reine Funktionen |
| `application/` | Port `Tracker` (`update(frame_index, detections, camera) -> list[TrackPoint]`); Port `CameraMotionEstimator`; Stufen-Ablauf in `pipeline.py` |
| `infrastructure/` | `ByteTrackLikeTracker`; `CameraMotionEstimatorCv` (OpenCV); Lesen/Schreiben von `detections.json`, `camera.json`, `tracks.json`; Video-Zeichnen und Kontaktbogen |
| `cli.py` | Befehle `detect`, `camera`, `track`, `render` (jeder einzeln wiederholbar) und `run` als Kette |

## 3. Entwurfsentscheidungen
1. **Eigener ByteTrack-ähnlicher Tracker** (numpy + scipy für die Zuordnung). Gründe: Ultralytics/boxmot sind AGPL; `supervision` (MIT) zieht viele Abhängigkeiten nach und ist für Erkennung auf jedem Bild gebaut. numpy und scipy (BSD) sind bereits installiert; scipy kommt als eigener Extra `track` in die `pyproject.toml`.
2. **Kamerabewegung schätzen und herausrechnen.** Bei Schwenk und Zoom verschieben sich alle Boxen zwischen zwei Erkennungen (0,2 s) gemeinsam; ohne Ausgleich würde die Zuordnung per Überlappung bei jedem Schwenk reißen. Schätzung mit OpenCV (Lizenz Apache 2.0, bereits installiert, da von rfdetr/supervision gebracht): Merkmale auf einem verkleinerten Graubild verfolgen (Lucas-Kanade), Ähnlichkeitstransformation (Verschiebung, Drehung, Zoom) mit RANSAC; Spieler selbst werden als bewegte Punkte ausgeblendet (RANSAC verwirft sie). Der Spielfeldrasen ist arm an Merkmalen: Linien, Tribüne und Werbebande liefern sie. **Ungeprüft**, ob das auf den Clips zuverlässig ist; deshalb Variante A (ohne Ausgleich) und B (mit Ausgleich) im Vergleich (Abschnitt 6).
3. **Tracker arbeitet nur auf Erkennungsbildern**; in den Zwischenbildern wird die Box vorhergesagt (`visible = false`) und mit der Kamerabewegung des jeweiligen Bildes korrigiert. Die Kamerabewegung wird für **jedes** Bild geschätzt (nicht nur für Erkennungsbilder), damit auch die Vorhersage dazwischen stimmt; Verschieben der Vorhersage geht nur über die Kette der Zwischenbilder.
4. **Aufbewahrungsdauer verlorener Spuren in Sekunden** (Konfiguration `track_max_lost_seconds`), intern in Erkennungsschritte umgerechnet.
5. **Klassenunabhängig:** Der Tracker verfolgt "Person"; Team/Torhüter/Schiedsrichter kommen in T5.
6. **Stufen und Dateien sind austauschbar:** Die Messung (T3) und die Pipeline benutzen denselben Detektor-Port; der Detektor wird für die Pipeline ebenfalls als Stufe 1 verwendet, sein Ergebnis liegt in `detections.json`.

## 4. Dateiformate (Schema-Version erhöhen, wenn sich etwas ändert)
- `detections.json`: `{schema_version, source, detector, fps, frames: [{frame: int, detections: [{x, y, w, h, score}]}]}`. Alle Erkennungen ab `track_low_score` (Start 0,1); der Tracker filtert selbst.
- `camera.json`: `{schema_version, fps, frame_size, frames: [{frame: int, matrix: [[a,b,tx],[c,d,ty]] | null, quality: float}]}`. Matrix beschreibt die Bewegung von Bild i-1 nach Bild i; **`null` = Schätzung fehlgeschlagen** (nicht 0 und nicht Einheitsmatrix, fehlend bleibt fehlend).
- `tracks.json` (Erweiterung von `RunResult.tracks`): je Spur `{id, points: [{frame, x, y, w, h, visible, score|null, uncertainty|null}]}`. `visible = true` heißt von einem Detektor gesehen, `false` heißt vorhergesagt. `uncertainty` bleibt in T4 `null` (Platzhalter für T6).

## 5. Regeln für den Tracker (jede Regel bekommt einen Test, Namen als Anforderung lesbar)
1. Eine Person, die sich gleichmäßig bewegt und in jedem N-ten Bild erkannt wird, behält ihre ID über 60 s.
2. Fehlt eine Erkennung kurz (weniger als `track_max_lost_seconds`), bleibt die ID erhalten.
3. Fehlt sie länger, wird die Spur beendet; tauchen dort wieder Erkennungen auf, gibt es eine **neue** ID (kein Wiedererkennen nach Aussehen).
4. Zwei Personen, die sich kreuzen, behalten ihre IDs, wenn ihre Bewegung vorher gleichmäßig war (Bewegungsmodell, kein Aussehen); bei sehr starker Überdeckung sind Wechsel erlaubt und werden gezählt.
5. Eine Erkennung mit niedrigem Score (zwischen `track_low_score` und `track_high_score`) verlängert eine bestehende Spur, **eröffnet aber keine neue** (ByteTrack-Regel).
6. Eine neue Spur gilt erst nach `track_min_hits` Erkennungen als bestätigt und erscheint erst dann in `tracks.json`; einzelne Fehlerkennungen erzeugen so keine IDs.
7. **Kamera schwenkt:** Verschieben sich alle Boxen gemeinsam um (dx, dy), bleibt jede ID erhalten, sofern die Kamerabewegung bekannt ist. Mit unbekannter Kamerabewegung (`null`) wird die Vorhersage nicht verschoben und die Zuordnung toleranter (größere Suchzone).
8. **Zoom:** Eine Skalierung aller Boxen um Faktor s ändert die ID nicht, wenn die Kamerabewegung bekannt ist.
9. **Spieler verlässt das Bild:** Verschwindet eine Spur am Bildrand, wird sie früher beendet (Randbereich); sie wartet nicht die volle Aufbewahrungsdauer, weil sie nicht mehr zurückkommt. Kommt dort später jemand ins Bild, bekommt er eine neue ID.
10. IDs werden nie wiederverwendet; sie steigen innerhalb eines Laufs ohne Lücken-Garantie.
11. Gleiche Eingabe ergibt gleiche Ausgabe (deterministisch).

## 6. Messung (Basislinie)
- **Eingabe-Varianten:** RF-DETR Ganzbild und RF-DETR Kacheln (T3-Ergebnis: 0,51 s und 3,99 s je Bild, rechnerisch ca. 2,5 und 20 min je Clip; am Clip nicht gemessen). **Clip: clip1** (Vorschlag).
- **Tracker-Varianten:** A ohne Kamerabewegung, B mit Kamerabewegung.
- **Automatische Hilfszahlen** (im Bericht deutlich als Hinweis gekennzeichnet, keine Kennzahl der Spezifikation): Spuren pro Minute, mittlere Spurlänge in Sekunden, Anteil `visible`, Anteil Bilder mit `camera = null`.
- **Handzählung** (die Kennzahl der Spezifikation) nur auf der besseren der Kombinationen, nach dieser Methode:
  1. Das Programm erzeugt ein annotiertes Video (halbe Geschwindigkeit) und Kontaktbogen-Bilder (alle 2 s, mit ID).
  2. Du wählst vorab **6 bis 8 Spieler** (nah und fern gemischt, auf mehrere Abschnitte des Clips verteilt) und notierst sie mit Startzeit und Bildposition (`docs/..../zaehlung.md`, ohne Namen, nur "Spieler 1 = linker Außenverteidiger").
  3. Du verfolgst jeden dieser Spieler, solange er im Bild ist, und notierst jeden **ID-Wechsel** (Zeit, alte ID, neue ID) und jeden **Tausch** (zwei Spieler tauschen IDs).
  4. **Wiedereintritte zählen nicht als Wechsel:** Verlässt ein Spieler das Bild (Schwenk, Zoom) und kommt mit anderer ID zurück, wird das getrennt als "neue ID nach Wiedereintritt" gezählt und im Bericht genannt (Begründung: Wiedererkennung nach Aussehen ist in Woche 1 ausgeschlossen).
  5. Ergebnis: Wechsel pro Spieler-Minute = Wechsel / (Summe der Beobachtungszeit der gezählten Spieler in Minuten), dazu die Einzelzahlen. Die Summe der Beobachtungszeit steht im Bericht, nicht nur der Quotient.
- Keine MOTA/IDF1: dafür fehlt eine beschriftete Spurreferenz. Der Bericht sagt das offen.
- Zählung von nur 6 bis 8 Spielern ist eine Stichprobe; Aussage "Spieler pro Minute", nicht "alle Spieler".

## 7. Konfiguration (alle in `default.toml`, nichts fest im Code)
`detect_every` (besteht), `track_low_score` = 0,1, `track_high_score` = 0,5 (Start; **kein Vorschlag aus den Daten**, wird an `detections.json` geprüft), `track_new_score` = 0,5, `track_match_iou` = 0,3, `track_max_lost_seconds` = 1,5, `track_min_hits` = 2, `track_edge_margin_px` = 40, `camera_downscale` = 0,25. Ob die Kamerabewegung geschätzt wird, kommt **aus dem Aufnahme-Profil des Clips** (`camera_motion`, siehe `t3b-struktur.md`): `fest` = aus, `schwenkt`/`schwenkt_und_zoomt` = an. Für den Vergleich A/B kann ein Lauf das per Aufruf-Argument überschreiben.
Die Werte sind Ausgangswerte, keine Entscheidungen. Änderungen am Wert werden im Bericht genannt, wenn sie die Zahlen beeinflussen.

## 8. Reihenfolge (jede Teilstufe einzeln testbar und einzeln committbar nach T4-Abschluss)
1. Test-Gerüst mit künstlichen Daten (Regeln 1 bis 11), Datentypen in `domain/`. **Kein Video, keine Erkennung nötig.**
2. Tracker (`ByteTrackLikeTracker`) bis die Regeln 1 bis 6 und 9 bis 11 grün sind.
3. Kamerabewegung (Test mit künstlich verschobenem/gezoomtem Bild) und Regeln 7 und 8.
4. Dateien (`detections.json`, `camera.json`, `tracks.json`) mit Schema-Tests, Befehle `detect`, `camera`, `track`.
5. Darstellung (Video, Kontaktbogen), **sichtbares Ergebnis** (Bild/Video) für dich.
6. Läufe auf clip1 (Erkennung ggf. im Hintergrund), Hilfszahlen, Methode für die Handzählung bereitstellen.
7. Du zählst; ich trage das Ergebnis in die Notiz und den Bericht-Entwurf ein.

## 9. Vorschlag zur Änderung der Wochenspezifikation (nur mit deinem Ja, dann v1.3)
- T4: Abschnitt "Kamera" ergänzen: Der Tracker nutzt eine geschätzte Kamerabewegung (Variante mit/ohne im Vergleich).
- Messregel "ID-Wechsel (T4)": ergänzen, dass Wiedereintritte nach Verlassen des Bildes **nicht als Wechsel zählen**, aber getrennt berichtet werden; Zählung an 6 bis 8 Spielern, Beobachtungszeit im Bericht.
- T4 auf "ca. 3 bis 4 h" statt "1 bis 2 h" (Kamerabewegung ist neu hinzugekommen).

## 10. Risiken, offen (ungeprüft)
- Kamerabewegung auf Rasen: wenig Merkmale, schnelle Schwenks, Bewegungsunschärfe. Dann fällt Variante B auf `null` zurück, und die Zuordnung ist toleranter.
- Stärkere Zooms ändern die Boxhöhe; die Überlappung als Zuordnung ist dann empfindlicher.
- Rechenzeit der Kamerabewegung auf 1500 Bildern ist unbekannt (Schätzung: 1 bis 3 min auf verkleinerten Bildern, nicht gemessen).
- Zuschauer, Ordner, Bank erhalten auch Spuren und verfälschen die Hilfszahlen (nicht die Handzählung der 6 bis 8 Spieler). Spielfeldfilter erst in Woche 2.
- Deinterlacing ist erfolgt (T0); Interlacing-Artefakte sollten die Merkmalsverfolgung nicht stören; nicht geprüft.

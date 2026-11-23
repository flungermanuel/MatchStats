# Woche 1: Von Video zu annotiertem Video (Spezifikation v1.5, 23.11.2026)
 
Projekt: matchstats. Stand: v1.1 ersetzt v1. Änderungen gegenüber v0 und v1 stehen am Ende.
 
## Ziel
Ein 60-Sekunden-Ausschnitt in taktischer Ansicht wird verarbeitet. Ergebnis: ein Video, in dem alle Spieler mit Box, konstanter ID und Teamfarbe eingezeichnet sind, dazu ein Bericht mit gemessenen Zahlen und eine begründete Entscheidung (Detektor, Kacheln ja/nein).
 
## Rahmen
- **Zeitbudget:** ca. 8 Stunden pro Woche. "Woche 1" ist eine Arbeitseinheit (geschätzt 12 bis 18 Stunden), also etwa 2 bis 3 Kalenderwochen.
- **Hardware:** Windows-Laptop, Intel Core Ultra 7 155H, 16 GB RAM, integrierte Intel-Arc-Grafik, keine NVIDIA-GPU. Alles läuft lokal auf der CPU (OpenVINO als Option). Es wird nichts gemietet. Kostenlose GPU-Zeit (Colab/Kaggle) ist nur Notnagel.
- **Material (ffprobe, 12.11.2026):** Eine Quelldatei im Format .MTS (AVCHD), 12 Minuten, H.264, **1920x1080, 25 Bilder pro Sekunde, interlaced (Oberfeld zuerst, "tt")**. Das ist Full HD, nicht 4K (der Brief ging von 4K aus). Weit entfernte Spieler sind dadurch voraussichtlich noch kleiner; der Kachelvergleich wird wichtiger.
- **Konsequenzen für das Design:**
  - Interlaced Material wird beim Schneiden mit `yadif` deinterlaced (Modus 0, damit es bei 25 Bildern pro Sekunde bleibt).
  - Video wird Bild für Bild gelesen, nie komplett in den Speicher geladen (16 GB RAM).
  - Erkennung läuft nur auf jedem N-ten Bild (Start: N = 5, entspricht 5 Erkennungen pro Sekunde), das Tracking überbrückt die Lücken. N ist ein Parameter.
  - Der Kachelvergleich (T3) läuft nur auf den 60 beschrifteten Bildern, nicht auf ganzen Clips.
  - Nur ein Clip bekommt den vollen Lauf (T4 bis T6); die anderen zwei werden in Woche 1 nur für die Testbilder gebraucht.
  - Kleine Modellvarianten reichen für die Basislinie.
- **Lernziel:** sauber vibecoden. Jede Aufgabe: Spezifikation, Test zuerst, Umsetzung, Diff-Review, Commit, kurze Entscheidungsnotiz. Der Entwickler liest die Tests selbst und lässt sich die Änderungen in einfachen Worten erklären, bevor er committet.
## Nicht-Ziele (kommt später)
Kalibrierung und Minimap (Woche 2), Heatmaps, Weboberfläche, Warteschlange, Agenten, Ball, Statistiken, Erkennung von Zoom-Abschnitten.
 
## Eingaben (von Hand vorzubereiten, siehe T0)
- Eine Quelldatei (.MTS, 12 min, 1080i25) aus einem Spiel. Daraus 3 Clips à 60 Sekunden aus verschiedenen Spielphasen (z. B. bei Minute 1, 5 und 9), ohne Torjubel-Zoom.
- **Einschränkung:** Alle Clips stammen aus demselben Spiel und derselben Perspektive. Die Basislinie sagt deshalb weniger über andere Perspektiven aus. Das Testset wird erweitert, sobald Material aus weiteren Spielen vorliegt (Ziel laut Brief: 3 bis 5 Spiele).
- Optional später ein Clip mit Torjubel-Zoom.
- Rohvideos liegen nur lokal, nicht im Git, und werden nicht öffentlich geteilt.
## Messregeln (einmal festgelegt, gelten für den ganzen Bericht)
- **Treffer (T3):** Eine Erkennung zählt als Treffer, wenn ihre Box mit einer beschrifteten Box eine Überlappung (IoU) von mindestens 0,5 hat. Jede beschriftete Box kann nur einmal getroffen werden.
- **Recall** = getroffene beschriftete Boxen / alle beschrifteten Boxen. **Precision** = Treffer / alle Erkennungen.
- **Nah/fern:** Recall wird zusätzlich getrennt berichtet nach Boxhöhe in Pixeln (Grenze wird nach Sichtung der Daten festgelegt und im Bericht genannt), weil dort die Kachelfrage entschieden wird.
- **Auswahl der Testbilder (T2):** 20 Bilder pro Clip, gleichmäßig über die 60 Sekunden gezogen (nicht von Hand ausgesucht), damit die Basislinie nicht geschönt ist.
- **ID-Wechsel (T4):** Gemessen werden **Kandidaten** für ID-Wechsel, automatisch aus den Spuren (kein Handzählen). Kandidat: eine Spur endet mitten im Bild (nicht am Bildrand, nicht am Clip-Ende), und höchstens `switch_max_gap_seconds` (Standard 1,0 s) später beginnt höchstens `switch_max_distance_heights` (Standard 1,0) Boxhöhen entfernt eine neue; jede Spur wird höchstens einmal zugeordnet (nächste zuerst). Ergebnis = Kandidaten pro Spur-Minute (Summe aller Spurlängen in Minuten), die Summe der Spurzeit steht im Bericht. Das ist ein **Indikator, keine Zählung**: Kamerabewegung, Gedränge und Zuschauer erzeugen falsche Kandidaten, Lücken über der Schwelle fallen durch. Zur Einordnung wird eine Stichprobe von mindestens 8 Kandidaten (gleichmäßig gewählt, nicht ausgesucht) an den Vergleichsbildern geprüft und der Anteil echter Wechsel berichtet. Wiedererkennung nach Aussehen ist in Woche 1 ausgeschlossen.
- **Teamzuordnung (T5):** Anteil der Spieler (Feldspieler mit Team A/B, Torhüter, Schiedsrichter als eigene Klassen), deren Klasse auf den 60 Bildern stimmt.
- **Laufzeit:** Zeit pro Bild und Gesamtzeit je Variante werden in T3/T6 mitgemessen.
- Keine Zielwerte in Woche 1, nur Basislinie.
## Aufgaben mit Abnahmekriterien
 
### T0 Vorbereitung (Entwickler, ca. 1 bis 2 h)
- ffmpeg installieren (Windows z. B. `winget install Gyan.FFmpeg`).
- 3 Clips à 60 s aus der .MTS-Datei schneiden, deinterlaced, ohne Ton, z. B.:
  `ffmpeg -ss 00:01:00 -t 60 -i quelle.MTS -an -vf yadif=0 -c:v libx264 -crf 18 clip1.mp4`
  (Startzeiten für clip2/clip3 z. B. 00:05:00 und 00:09:00; vorher kurz ansehen, dass dort kein Torjubel-Zoom ist.)
- Beschriftungswerkzeug: Label Studio (lokal per pip, eigene Umgebung; Alternative CVAT braucht Docker). Format: COCO-JSON. Beides am 16.11.2026 festgelegt, siehe `docs/entscheidungen/0003-testset-label-studio.md`.
- AK: 3 Clips liegen in einem lokalen Ordner als progressive 1080p25-Dateien (per ffprobe geprüft, `field_order=progressive`); das Beschriftungswerkzeug ist gewählt.
### T1 Projektgerüst (ca. 1 bis 2 h)
- Git-Repository "matchstats" mit README, CLAUDE.md (Arbeitsregeln für den Agenten), Ordnern für Quellcode, Tests, Daten (nicht im Git, per .gitignore), Doku/Entscheidungen (`docs/`).
- CLAUDE.md enthält mindestens: Arbeitsregeln aus dem Brief (erst Test, kleine Schritte, ein Commit pro Aufgabe), Windows/CPU-Umgebung, Video nur Bild für Bild lesen, Rohvideos nie ins Git, keine Spielernamen, Detektor hinter Schnittstelle.
- Ein Befehl startet die Verarbeitung: `matchstats run clip.mp4 --out ergebnis/` (in T1 darf er nur ein leeres, valides Ergebnis erzeugen).
- AK: Frischer Klon plus die im README beschriebenen Einrichtungsschritte ergibt eine laufende Umgebung; der Testbefehl läuft grün.
### T2 Testset (ca. 3 bis 4 h, größter manueller Brocken)
- Pro Clip 20 Bilder (gleichmäßig gezogen, siehe Messregeln), alle Feldspieler, Torhüter und Schiedsrichter mit Boxen markiert, jeweils mit Klasse (Team A, Team B, Torhüter, Schiedsrichter).
- Vorbeschriften durch den Detektor und anschließendes Korrigieren ist erlaubt, aber jede Box wird wirklich geprüft. Der Bericht nennt, dass vorbeschriftet wurde.
- Festes Dateiformat (COCO-JSON, Export aus Label Studio, vier Klassen), dokumentiert im README.
- AK: 60 beschriftete Bilder liegen vor; ein Test prüft das Format.
### T3 Erkennung (ca. 2 bis 3 h plus Rechenzeit)
- Personen-Detektor hinter einer austauschbaren Schnittstelle. Zu testen: YOLO (schneller Start, AGPL-3.0) und RF-DETR (Apache 2.0), jeweils kleine Modellgröße.
- Pro Detektor zwei Varianten: ganzes Bild verkleinert vs. Bild in Kacheln (mit Überlappung, doppelte Erkennungen an Kachelrändern werden zusammengeführt).
- AK: Recall und Precision (gesamt und nah/fern) aller Kombinationen auf den 60 Testbildern sowie Zeit pro Bild stehen im Bericht.
### T3b Spiel-/Clip-/Lauf-Struktur (ca. 3 bis 4 h)
- Videos werden als **Spiel → Clip → Lauf** unter `data/library/` verwaltet (`match.json`, `clip.json`, `runs/<run_id>/run.json`, Testset je Clip in `testset/`). Jede Datei trägt eine `schema_version`; Pfade sind relativ zum Bibliotheksordner.
- Jeder Clip hat eine **Halbzeit** (`half`: 1, 2 oder `null`) und ein **Aufnahme-Profil** (`angle`, `camera_motion`, `notes`; unbekannt = `null`). Das Profil ist reine Daten und kann Parameter überschreiben.
- Parameter-Schichtung: Standard (`default.toml`) → Profil-Überschreibungen (`clip.json`) → Aufruf-Argumente. Das Ergebnis steht in `run.json`. Unbekannte Schlüssel werden mit klarer Meldung abgelehnt.
- Auswertung je **Spiel und Halbzeit**: `matchstats evaluate --game <id> --half <n>` fasst alle Clips einer Halbzeit zu einem Bericht zusammen; die nah/fern-Grenze (Median der Boxhöhen) wird je Bericht bestimmt. Die bisherigen Aufrufe (`run --out`, `evaluate --testset/--images`) bleiben gültig.
- Import kopiert das Video (Original bleibt unverändert) und trägt fps, Auflösung und Länge per ffprobe ein. Neue Befehle: `match add`, `clip import`, `clip list`.
- Migration der vorhandenen Daten (clip1 bis 3, Testset, T3-Ergebnisse) per einmaligem Skript in `tools/`; alte Ordner bleiben bestehen.
- Bewusst nicht in T3b: Stufen-Cache (kommt mit T4), Verweis statt Kopie (`--link`), Deinterlacen/Schneiden beim Import, Oberfläche, Datenbank.
- AK 1: Ein Test legt ein Spiel und zwei Clips mit verschiedenen Profilen an, importiert (Fake-)Videos und findet sie wieder; ein zweiter Lauf desselben Clips überschreibt den ersten nicht.
- AK 2: Profil-Werte überschreiben Standardwerte, Aufruf-Argumente überschreiben Profil-Werte (Test mit zwei Profilen).
- AK 3: Nach der Migration liefert `matchstats evaluate --game spiel-001 --half <n>` (alle drei Clips stammen aus derselben Halbzeit) je Variante dieselben Recall- und Precision-Werte (gesamt und nah/fern) wie `data/ergebnis/t3/report.json`. Laufzeiten sind vom Vergleich ausgenommen.
- AK 4: `pytest` und `ruff check .` grün; Schichtentest unverändert.
### T4 Tracking (ca. 3 bis 4 h)
- Konstante IDs über die Zeit (ByteTrack-ähnlicher Ansatz), Erkennung nur auf jedem N-ten Bild, Lücken werden vom Tracker überbrückt.
- Stufen mit gespeicherten Zwischenergebnissen im Lauf-Ordner (`detections.json`, `tracks.json`); das Tracking liest nur Dateien und kann ohne neue Erkennung wiederholt werden. Detektor in der Entwicklung: RF-DETR Ganzbild.
- Kamerabewegung (Schwenk/Zoom herausrechnen) ist **nicht** Teil von T4; sie folgt als eigener Schritt T4b nur, wenn die Kandidaten-Rate und die Stichprobe der Vergleichsbilder ohne Ausgleich deutlich schlecht ausfallen. Grundlage: `docs/entwuerfe/t4-spezifikation.md`.
- AK: Auf einem Clip werden Kandidaten für ID-Wechsel pro Spur-Minute automatisch berechnet (`id_switch_candidates.json`, `summary.json`), mit Vergleichsbildern je Kandidat (`render/switches/`) stichprobenartig geprüft (Methode siehe Messregeln) und im Bericht notiert.
### T5 Teamzuordnung (ca. 1 bis 2 h)
- Zuordnung über Trikotfarben, Torhüter und Schiedsrichter getrennt behandelt (z. B. als Ausreißer).
- AK: Anteil richtig zugeordneter Spieler auf den 60 beschrifteten Bildern steht im Bericht.
### T6 Ausgabe (ca. 1 bis 2 h)
- Annotiertes Video plus Datei mit allen Spuren. Pro Messung Felder für Sichtbarkeit ("im Bild?") und Unsicherheit; in Woche 1 einfach befüllt (Sichtbarkeit aus Erkennung/Tracker, Unsicherheit als Platzhalter).
- Der Volllauf auf dem Hauptclip darf über Nacht laufen.
- AK: Ein Schema-Test prüft die Datei; die Felder sind vorhanden.
### T7 Bericht und Entscheidung (ca. 1 bis 2 h)
- Kurzer Bericht mit den Kennzahlen aus T3 bis T5, Laufzeiten und 6 Beispielbildern (gute und schlechte).
- Entscheidungsnotiz: Welcher Detektor, Kacheln ja oder nein, welches N, warum (inklusive Lizenz-Überlegung).
- AK: Bericht liegt vor, Entscheidung begründet.
## Reihenfolge
T0 → T1 → T2 → T3 → T3b → T4 → T5 → T6 → T7. T2 und T1 können sich überschneiden, T3 braucht T2, T4 baut auf der Struktur aus T3b auf.
 
## Definition of Done
Alles im Git, Tests grün, Bericht erstellt, alle Änderungen vom Entwickler selbst gelesen (Diff-Review), Entscheidungsnotiz geschrieben, Entscheidung und Lernpunkte kurz im Projekt festgehalten.
 
## Arbeitsweise pro Aufgabe (mit Claude Code)
1. Aufgabe und Abnahmekriterium vorlesen lassen, Plan bestätigen.
2. Zuerst den Test schreiben lassen, dann die Umsetzung.
3. Ergebnisse an Bildern prüfen (Ausgabebilder ansehen), nicht nur an Zahlen.
4. Änderungen in einfachen Worten erklären lassen und Tests selbst lesen.
5. Ein Commit pro Aufgabe, neue Sitzung pro Aufgabe.
## Risiken
- Full HD statt 4K: weit entfernte Spieler sind sehr klein; Detektion kann schlecht ausfallen (deshalb der Kachel-Vergleich, evtl. zusätzlich Hochskalieren der Kacheln).
- Interlaced-Material: Ohne Deinterlacing entstehen Kammartefakte an bewegten Spielern; T0 verlangt progressive Clips.
- Nur ein Spiel und eine Perspektive im Testset: Ergebnisse sind nicht allgemeingültig.
- Gleiche Trikotfarben bei Torhütern/Schiedsrichtern.
- Rechenzeit auf der CPU: Gegenmittel sind jedes N-te Bild, kleine Modelle, ein Hauptclip, Läufe über Nacht. Falls das nicht reicht, kostenlose GPU-Zeit (Colab/Kaggle) als Notnagel.
- Vorbeschriftung kann die Messung zugunsten des Detektors verzerren; deshalb jede Box prüfen.
- Basislinie des Trackings ist grob (Kandidaten-Rate auf einem Clip, stichprobenartig geprüft); für den Prüfstand in Woche 5 braucht es später beschriftete Spuren.
- Nutzungsrechte: Absprache mit dem Chef ist nur mündlich. Für Woche 1 unkritisch (alles lokal), muss aber schriftlich stehen, bevor Ergebnisse gezeigt oder weitergegeben werden.
## Offene Punkte
- Weiteres Material: Am Sonntag (15.11.2026) wird ein weiteres Spiel gefilmt. Danach Testset, Brief und Beschreibung anpassen (Auflösung, Perspektive).
- Grenze für nah/fern in Boxhöhe nach Sichtung der Daten festlegen.
## Änderungen
**v1.5 gegenüber v1.4 (23.11.2026):** T4: Handzählung ersetzt durch automatische Kandidaten für ID-Wechsel pro Spur-Minute mit Stichprobenprüfung an Vergleichsbildern (Indikator, keine Zählung). Messregel ID-Wechsel und AK angepasst; Wiedereintritte werden nicht mehr getrennt gezählt, sondern per Bildrand-Regel ausgeschlossen. Grundlage: `docs/entscheidungen/0007-id-wechsel-kandidaten.md`.

**v1.4 gegenüber v1.3 (18.11.2026):** T4 präzisiert (Stufen mit Dateien, RF-DETR Ganzbild in der Entwicklung, Kamerabewegung als möglicher Folgeschritt T4b), Zeitrahmen T4 auf 3 bis 4 h. Messregel ID-Wechsel ergänzt: Stichprobe 6 bis 8 Spieler, Wechsel pro Spieler-Minute mit Beobachtungszeit, Wiedereintritte getrennt gezählt und nicht als Wechsel. Grundlage: `docs/entwuerfe/t4-spezifikation.md` nach Architektur-Prüfung.

**v1.3 gegenüber v1.2 (18.11.2026):** Neue Aufgabe T3b (Spiel-/Clip-/Lauf-Struktur mit Aufnahme-Profil, Halbzeit und Parameter-Schichtung, Bericht je Spiel und Halbzeit) zwischen T3 und T4, Reihenfolge angepasst. Die Struktur unterstützt mehrere Spiele und Profile; die Basislinie ist weiterhin nur auf einem Spiel und einer Perspektive gemessen. Messregeln und Nicht-Ziele unverändert. Grundlage: `docs/entwuerfe/t3b-struktur.md`, gekürzt nach Architektur-Prüfung.

**v1.2 gegenüber v1.1 (16.11.2026):** Beschriftungswerkzeug (Label Studio) und Format (COCO-JSON) von Vorschlag auf festgelegt gesetzt (T0, T2), entsprechender offener Punkt entfernt. Inhaltlich keine weitere Änderung.

**v1.1 gegenüber v1:** Material festgestellt (.MTS, 1920x1080, 25 fps, interlaced, 12 min), kein 4K. Deinterlacing mit ffmpeg-Befehl in T0 und als AK, alle Clips aus einem Spiel als Einschränkung, Risiken und offene Punkte entsprechend ergänzt. Projekt- und Befehlsname ist jetzt matchstats (statt footy), Beschriftungswerkzeug Label Studio vorgeschlagen.
 
**v1 gegenüber v0:**
- Zeitbudget (8 h/Woche) und Hardware (CPU, nichts mieten) als Rahmen aufgenommen, Designfolgen abgeleitet (jedes N-te Bild, Kachelvergleich nur auf Testbildern, ein Hauptclip).
- Neue Aufgabe T0 (Clips schneiden, Werkzeug wählen).
- Messregeln ergänzt: IoU 0,5, Recall/Precision nah/fern, Bildauswahl gleichmäßig, Definition ID-Wechsel, Laufzeitmessung.
- T2: Klassen pro Box, Vorbeschriften erlaubt aber mit Prüfpflicht.
- T3: beide Detektoren (YOLO und RF-DETR) je mit zwei Varianten.
- Arbeitsweise: Änderungen in einfachen Worten erklären lassen und Tests selbst lesen.
- Risiken und offene Punkte aktualisiert, Zeitschätzungen pro Aufgabe ergänzt.
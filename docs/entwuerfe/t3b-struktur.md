# T3b Spiel-/Clip-/Lauf-Struktur: Spezifikation (Entwurf zur Freigabe)

Stand: 18.11.2026. Entwurf; die verbindliche Wochenspezifikation ändert sich nur nach deinem Ja (Abschnitt 9).
Anlass: Es sollen später verschiedene Spiele mit verschiedenen Winkeln, Zoomstufen und Kameraverhalten verarbeitet werden.
T3b legt dafür die **Grundkonstruktion** an, bevor T4 darauf aufbaut. Keine Oberfläche, kein Upload-Dialog, keine
Warteschlange (bleibt "später").

## 1. Ziel und Abnahmekriterium
Videos werden nicht mehr als lose Dateipfade behandelt, sondern als **Spiel → Clip → Lauf** verwaltet. Jeder Clip hat ein
**Aufnahme-Profil** (Winkel, Kameraverhalten, Zoom), das die Verarbeitung steuert. Ergebnisse jedes Laufs liegen in einem
eigenen Ordner zusammen mit den verwendeten Parametern.
- **AK 1:** Ein Test legt ein Spiel und zwei Clips mit verschiedenen Profilen an, importiert (Fake-)Videos und findet sie
  wieder; ein zweiter Lauf desselben Clips mit anderen Parametern überschreibt den ersten nicht.
- **AK 2:** Das Profil steuert Parameter: Standardwerte gelten, Profil-Werte überschreiben sie (Test mit zwei Profilen).
- **AK 3:** Die vorhandenen Daten (clip1 bis 3, Testset, T3-Ergebnisse) liegen in der neuen Struktur; `matchstats evaluate`
  und `matchstats sample-frames` arbeiten damit und liefern dieselben Zahlen wie vor dem Umzug (Vergleich mit
  `data/ergebnis/t3/report.json`, Recall und Precision je Variante unverändert).
- **AK 4:** `pytest` und `ruff check .` grün; Schichtentest unverändert.

## 2. Bausteine
```
data/library/
  <spiel_id>/                       z. B. spiel-001
    match.json                      Name (ohne Personen), Datum, Notiz
    <clip_id>/                      z. B. clip1
      clip.mp4                      das Video (oder Verweis, siehe 3.4)
      clip.json                     Aufnahme-Profil + Metadaten (fps, Auflösung, Länge), Version
      testset/                      Bilder + coco.json dieses Clips
      runs/<run_id>/                run_id = Zeitstempel oder fortlaufend
        run.json                    verwendete Parameter (Standard + Profil + Eingabe), Stufenstatus
        detections.json …           Ergebnisse je Stufe (ab T3/T4)
```
Ordner `data/` bleibt komplett im `.gitignore`.

| Schicht | Neu |
|---|---|
| `domain/` | `Match`, `Clip`, `RecordingProfile`, `RunInfo` (reine Datentypen, Prüfregeln); `merge_settings(defaults, profile_overrides)` |
| `application/` | Port `Library` (Spiele anlegen, Clips importieren, Läufe anlegen und finden); Port `VideoInspector` (liest fps, Auflösung, Länge, Halbbild-Reihenfolge) |
| `infrastructure/` | `FileLibrary` (Ordnerstruktur oben, JSON lesen/schreiben); `FfprobeInspector`; Importfunktion (Prüfen, optional Deinterlacen/Schneiden mit ffmpeg) |
| `cli.py` | Befehle `match add`, `clip import`, `clip list`, `run`, Anpassung `evaluate`/`sample-frames` auf Clip-Bezug |

## 3. Entwurfsentscheidungen
1. **Profil = Daten, keine Programmlogik.** Stufen lesen Parameter (z. B. "Kamera bewegt sich: ja"), nie "das Spiel" oder "den Winkel".
2. **Profil-Felder (Start):**
   - `angle` (Text aus Liste: `tribuene_hoch`, `seitenlinie`, `ecke`, `hinter_tor`, `sonstige`), `camera_motion` (`fest`, `schwenkt`, `schwenkt_und_zoomt`),
   - `typical_player_height_px` (optional, Schätzwert für Kachelgröße und Nah/Fern, nicht Pflicht),
   - `interlaced` (ja/nein/unbekannt), `notes` (Freitext).
   Unbekannt bleibt als `null` gespeichert, nicht als geratener Standardwert.
3. **Parameter-Schichtung:** Standard (`default.toml`) → Profil-Überschreibungen (`clip.json: settings`) → Aufruf-Argumente. Das Ergebnis wird im `run.json` des Laufs gespeichert, damit jede Zahl nachvollziehbar bleibt.
4. **Video-Ablage:** Import **kopiert** das Video in den Clip-Ordner (Original bleibt unangetastet); `--link` speichert nur den Pfad, falls der Platz knapp ist. Der Import führt `ffprobe` aus und trägt fps/Auflösung/Länge/Halbbilder in `clip.json` ein.
5. **Stufen-Cache (Vorbereitung für T4):** Jede Stufe schreibt neben ihr Ergebnis einen Fingerabdruck (Eingabedatei + relevante Parameter). Stimmt er beim nächsten Lauf, wird die Stufe übersprungen. In T3b nur die Mechanik und ein Test; echte Stufen nutzen sie ab T4.
6. **Testset pro Clip:** `testset/` im Clip-Ordner. `matchstats evaluate` bekommt `--clip <id>` oder `--game <id>` (mehrere Clips zusammen); der Bericht nennt das Profil und trennt die Zahlen nach Profil, wenn mehrere dabei sind.
7. **Kein Mehrbenutzerbetrieb, keine Datenbank:** Dateien reichen. Die Struktur ist so gewählt, dass eine spätere Weboberfläche dieselben Ports nutzt (`Library`), ohne die Pipeline zu ändern.
8. **Datenschutz:** `Match.name` und `notes` dürfen keine Spielernamen enthalten (steht in der README); die Struktur liegt nie im Git.

## 4. Dateiformate (Schema-Version in jeder Datei)
- `match.json`: `{schema_version, id, name, date|null, notes}`
- `clip.json`: `{schema_version, id, source_file, fps, width, height, duration_s, field_order|null, profile: {angle|null, camera_motion|null, typical_player_height_px|null, interlaced|null, notes}, settings: {…Überschreibungen…}}`
- `run.json`: `{schema_version, id, created, clip_id, settings: {…aufgelöst…}, stages: {<stufe>: {status, fingerprint, file}}}`

## 5. Regeln (jede bekommt einen Test, Namen als Anforderung lesbar)
1. Ein Spiel kann angelegt werden; eine doppelte ID wird abgelehnt.
2. Ein Clip kann in ein Spiel importiert werden; unbekanntes Spiel, fehlende Datei und Nicht-Video werden mit klarer Meldung abgelehnt.
3. Der Import trägt fps, Auflösung und Länge aus `ffprobe` ein (Test mit kurzem künstlichem Video wie in `tests/conftest.py`).
4. Ein ungültiges Profil (unbekannter Winkel, negativer Wert) wird abgelehnt; `null` ist erlaubt.
5. Profil-Überschreibungen schlagen Standardwerte; Aufruf-Argumente schlagen Profil; ein ungültiger Wert nach dem Zusammenführen wird abgelehnt (`Settings` prüft wie bisher).
6. Ein neuer Lauf desselben Clips erzeugt einen eigenen Ordner; bestehende Läufe bleiben unverändert.
7. `run.json` enthält die aufgelösten Parameter (Standard + Profil + Aufruf).
8. Gleicher Fingerabdruck ⇒ Stufe wird übersprungen; geänderter Parameter oder Eingabe ⇒ Stufe läuft neu.
9. Der Import ändert das Original nicht (Hash vorher und nachher).
10. Lesen alter oder fremder Schema-Versionen: klare Fehlermeldung, kein Raten.
11. Pfade in den JSON-Dateien sind relativ zum Bibliotheksordner (portabel, Windows und später andere Rechner).

## 6. Migration der vorhandenen Daten (Teil der Aufgabe)
- Einmaliges Skript/Befehl `matchstats library migrate`: legt `spiel-001` an, importiert `clip1` bis `clip3` (Kopie), setzt das Profil
  (**von dir bestätigen**: Winkel, `schwenkt_und_zoomt`, interlaced `ja` wegen Quelle, bereits deinterlaced), verschiebt das Testset
  je Clip in `testset/`, teilt `coco.json` pro Clip (60 Bilder → 3 × 20), kopiert T3-Ergebnisse nach `runs/…`.
- Die alten Ordner bleiben bis zu deinem Ja unverändert bestehen (nichts löschen ohne Frage). Der Test vergleicht die Zahlen mit `report.json`.

## 7. Reihenfolge
1. Datentypen und Tests (Regeln 1 bis 11, ohne Video).
2. `FileLibrary` und `FfprobeInspector`, Import mit Fake-Video.
3. Parameter-Schichtung (Regeln 5 bis 7), Stufen-Cache (Regel 8).
4. CLI (`match add`, `clip import`, `clip list`), `evaluate`/`sample-frames` auf Clip-Bezug.
5. Migration mit Zahlenvergleich, sichtbares Ergebnis: `matchstats clip list` als Tabelle.
6. Systemkarte, README, Entscheidungsnotiz `0005`.

## 8. Bewusst nicht in T3b
Oberfläche, Upload-Dialog, Warteschlange, Datenbank, automatische Winkel-Erkennung, Kalibrierung (Woche 2), Cloud/Mehrbenutzer.

## 9. Vorschlag zur Änderung der Wochenspezifikation (nur mit deinem Ja, dann v1.3 zusammen mit T4)
- Neue Aufgabe **T3b** zwischen T3 und T4 (ca. 3 bis 4 h), mit den AK aus Abschnitt 1.
- Rahmen/Einschränkung: Hinweis, dass die Struktur mehrere Spiele und Profile unterstützt, die Basislinie aber weiterhin nur auf einem Spiel und einer Perspektive gemessen ist.
- Nicht-Ziele unverändert (Oberfläche, Warteschlange); die Struktur bereitet sie nur vor.

## 10. Risiken, offen
- Zu viel Struktur für zu wenig Material: Wir haben bisher **ein** Spiel. Profil-Felder können falsch gewählt sein; deshalb nur wenige, mit `null` als Normalfall, und `schema_version`.
- Migration der Testset-Dateien (Labelstudio-Dateinamen, 60 Bilder in 3 Gruppen) ist fehleranfällig; deshalb der Zahlenvergleich als AK.
- Der Fingerabdruck-Cache ist neu und kann veraltete Ergebnisse liefern, wenn ein relevanter Parameter vergessen wird; Test und klare Liste der Parameter je Stufe nötig.
- Ob `--link` (nur Pfad) nötig ist, ist offen; kann in T3b entfallen, wenn Plattenplatz kein Problem ist.

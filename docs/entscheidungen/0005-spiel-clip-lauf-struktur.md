# 0005: Spiel-/Clip-/Lauf-Struktur (T3b): Dateien statt Datenbank, Halbzeit als Feld, Profil als Daten

Datum: 2026-11-18

## Was
- Videos werden unter `data\library\` als Spiel → Clip → Lauf abgelegt, jeweils als Ordner mit einer JSON-Datei (`match.json`, `clip.json`, `run.json`). Jede Datei trägt `schema_version` (1), Pfade sind relativ.
- Der Import kopiert das Video; das Original bleibt unverändert. fps, Auflösung und Länge liest ffprobe.
- Die Halbzeit ist ein Feld des Clips (1, 2 oder `null`), keine Ordnerebene. `matchstats evaluate --game <id> --half <n>` fasst alle Clips dieser Halbzeit mit Testset in einem Bericht zusammen, mit einer gemeinsamen nah/fern-Grenze.
- Das Aufnahme-Profil (Blickwinkel, Kameraverhalten, Notiz) ist reine Daten. Unbekannte Werte bleiben `null`.
- Parameter-Schichtung: `load_settings` legt Standard, eigene Datei, Profil-Überschreibungen und Aufruf-Argumente in dieser Reihenfolge übereinander; unbekannte Schlüssel werden abgelehnt.
- Die bisherigen Aufrufe (`run --out`, `evaluate --testset/--images`) bleiben gültig.
- Die T3-Daten werden durch ein einmaliges Skript (`tools/migrate_t3b.py`) übernommen, nicht durch einen CLI-Befehl.

## Warum
- **Dateien statt Datenbank:** Ein Nutzer, lokal, kein Mehrbenutzerbetrieb. Dateien lassen sich im Explorer prüfen. Der Entwurf (`docs/entwuerfe/t3b-struktur.md`, Abschnitt 3.7) sagt: "Dateien reichen". Eine spätere Weboberfläche kann denselben Port `Library` nutzen.
- **Halbzeit als Feld:** Ein Bericht je Halbzeit ist gewünscht. Die Halbzeit ist aber eine Eigenschaft des Clips. Ein Feld lässt sich korrigieren, ohne Ordner umzubenennen, und ein unbekannter Wert bleibt `null`, statt geraten zu werden.
- **Profil als Daten:** Stufen lesen Parameter (z. B. "Kamera schwenkt"), statt Sonderfälle nach Blickwinkel zu machen (Entwurf, Entscheidung 1).
- **Schichtung über das bestehende `load_settings`:** Die Reihenfolge steht an einer Stelle und ist getestet. Die Funktion wurde um zwei Schichten erweitert, nicht ersetzt.
- **Migration als Skript:** Der Vorgang läuft einmal. Ein CLI-Befehl müsste dauerhaft gepflegt werden und ist für einen einmaligen Umzug zu viel.
- **Langsamer Abnahmetest hinter `MATCHSTATS_SLOW=1`:** Der Test (AK 3) lässt die echten Detektoren über 60 Bilder laufen, ca. 8 Minuten. Alle übrigen Tests laufen schnell und ohne Modelle.

## Alternativen
- **Datenbank:** verworfen, siehe oben.
- **Ordnerebene Spiel → Halbzeit → Clip:** hätte den Bericht je Halbzeit ebenfalls erlaubt. Ein falsch einsortierter Clip würde aber das Verschieben von Ordnern verlangen. Verworfen.
- **Profil als Programmlogik** (eigener Code je Blickwinkel): verworfen (Entwurf, Entscheidung 1).
- **Zweite Funktion neben `load_settings`** für die Schichtung: verworfen, damit die Reihenfolge nicht an zwei Stellen steht.
- **Migration als Befehl `matchstats library migrate`** (Entwurf, Abschnitt 6): verworfen, siehe oben.
- **Verweis statt Kopie (`--link`):** verschoben. Plattenplatz war bisher kein Problem; der Entwurf lässt die Frage offen.
- **Stufen-Cache mit Fingerabdruck:** verschoben auf T4, wenn die ersten echten Stufen existieren (Entwurf, Abschnitt 3.5).
- **Deinterlacen und Schneiden beim Import:** nicht in T3b. Die Clips sind in T0 manuell mit ffmpeg vorbereitet worden.

## Offen
- Kein CLI-Befehl legt einen Lauf an. `run-001` entstand nur durch die Migration. `evaluate --game` schreibt in `--out`, nicht in den Lauf.
- Die Profil-Überschreibungen aus `clip.json` (`settings`) wirken im Ablauf noch nicht.
- `sample-frames` ist nicht an die Bibliothek angebunden. Die Spezifikation T3b (AK 3) nennt den Befehl; das ist eine Abweichung und liegt beim Lead.
- Die Entwurfsfelder `interlaced`, `field_order`, `typical_player_height_px` und `stages` sind nicht umgesetzt.
- Die Migration ist nicht wiederholbar, ohne `spiel-001` von Hand zu löschen.

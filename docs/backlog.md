# Backlog (gepflegt vom Planer)

Stand: 2026-11-25. Grundlage: `docs/woche1-spezifikation.md` v1.6, Git-Stand b803a8a (T5a fertig, T5b1 umgesetzt, Commit folgt). Reihenfolge der Spezifikation: ... T4b -> **T5** -> T6 -> T7.

## Nächste Aufgabe

**T5b2 Anbindung an `matchstats track`: summary.json v4, Render in Teamfarbe**

- **Status:** wartet auf Klärung (siehe Stopp-Grund unten). T5b1 ist umgesetzt (Stufe `team_stage`, `teams.json` Version 1, Stufen-Cache; Details in `docs/entscheidungen/0010-teams-je-spur-t5b1.md`).
- **Stopp-Grund vor T5b2 (ausgelöst):** Der Handlauf von T5b1 auf clip1 (run-005) ergab **45,2 % Spuren mit wechselnder Klasse** (73 Spuren, 573 Stichproben). Die Schwelle für den Stopp (grob 30 %) ist geraten. Bevor T5b2 beginnt, zeigt der Lead Beispiele, bzw. der Planer klärt, ob die Schwelle oder das Verfahren der Maßstab ist (z. B. Gruppierung über die Stichproben je Spur statt je Bild wie in T5a, Gewicht von `team_outlier_max_share`).
- **Inhalt:** Siehe Punkt 1 unter "Danach" (`track` ruft nach `track_stage` die `team_stage`, `stage_seconds` erhält `teams`, `summary.json` Version 4 mit `team_counts`, `team_null_count`, `track_class_change_share`, `teams_reused`; `render_tracks` mit optionalem `TeamsDoc`, Boxfarbe je Klasse).

## Offene Nachbesserungen aus dem Review von T5b1

- `team_stage` importiert das private `_is_reusable` aus `tracking_stages.py`; es sollte öffentlich werden oder über ein Protocol laufen.
- Fehlende Stichproben bei zu kurzem Video werden still verschluckt; eine Warnung ergänzen.
- `load_teams` prüft die Struktur von `votes` nicht.
- Tests fehlen für eine leere Spurliste und für eine Stichprobe nur auf Bild 0.

## Rückfragen

Keine offen. (Frage 1 "meine Mannschaft" ist beantwortet, siehe unten.) Keine neue Feature-Frage: T5b entspricht der Systemkarte (Stufe 4) und dem beschlossenen T5.

## Entscheidungen des Auftraggebers

- 2026-11-25, Frage 1 "Wie wird 'meine Mannschaft' festgehalten?": **Option A, erst nicht festhalten.** T5 liefert nur "Team A/B" je Spur; `match.json` Version 2 (`teams`, `own_team`) kommt, wenn Kennzahlen aus Sicht einer Mannschaft gebraucht werden.
- 2026-11-25, Stopp-Grund T5a (Trefferquote schlecht, ausgewertet): Auftraggeber entschied **"als Basislinie committen"**. Offene Verbesserung (Torwart/Schiedsrichter, dritte Farbgruppe) als Punkt in T5b oder später.

## Danach

1. **T5b2 Teams im Lauf und Spuren in Teamfarbe (Sonnet):** `matchstats track` ruft nach `track_stage` die `team_stage` auf (`ColorTeamClassifier`, gleiche Videoquelle). `stage_seconds` erhält `teams`; `summary.json` wird Version 4 mit `team_counts`, `team_null_count`, `track_class_change_share`, `teams_reused`. `render_tracks` bekommt optional ein `TeamsDoc`: Boxfarbe je Klasse (team_a blau, team_b rot, Torwart gelb, Schiedsrichter grau, `null` weiß; BGR-Konstanten; dünne Linie bei `null` oder Unsicherheit über 0,5), ID bleibt als Beschriftung; Kontaktbögen ebenso; ohne `TeamsDoc` unverändert (bisherige Tests grün). Dateien: `tracking_job.py`, `track_render.py`, `track_summary.py`, evtl. `cli.py` (Schalter `--no-teams`), Tests. AK: Lauf auf clip1 mit wiederverwendeten Erkennungen liefert `teams.json` und Video in Teamfarbe; `summary.json` nennt den Anteil Spuren mit wechselnder Klasse; 6 Kontaktbogen-Bilder (gute und schlechte) angesehen und notiert; zweiter Aufruf nutzt den Cache (`teams_reused` true); `pytest` und `ruff check .` grün. Stopp, falls der Anteil Spuren mit wechselnder Klasse sehr hoch ist (grob über 30 %, Schwelle geraten): Beispiele zeigen.
2. **T5c Ursache der dritten Farbgruppe, Torwart und Schiedsrichter (eigener Punkt aus T5a; Sonnet):** Erst klären, dann ändern. Schritt 1: je Clip die Boxen der dritten Gruppe als Kontaktbogen zeigen (Zuschauer/Ordner im Hintergrund? Schatten? Gegner mit zwei Trikots? falsche Beschriftung?) und das Ergebnis in `docs/entscheidungen/0011-...` festhalten. Schritt 2 nur bei klarer Ursache: kleine Änderung (z. B. Boxen außerhalb des Spielfeldes verwerfen, Torwart/Schiedsrichter über Abstand zu beiden Teams statt nur Gruppengröße) und Wiedermessung mit `evaluate-teams` gegen die Basislinie aus 0009 (gesamt 66,1 %, Torwart 10,5 %, Schiedsrichter 0 %). Ein Embedding-Modell wäre eine neue Abhängigkeit mit Lizenzfolgen: dann Rückfrage. Reihenfolge: nach T5b2, vor T6, weil T6 die Klassen ausgibt; auf die Ursache begrenzt (ca. 1 bis 2 h).
3. **T6 Ausgabe:** Annotiertes Video (Box, konstante ID, Teamfarbe aus T5b2) plus Datei mit allen Spuren, Felder Sichtbarkeit und Unsicherheit (Unsicherheit aus `teams.json` statt Platzhalter, sofern T5b2 sie liefert), Schema-Test. Dabei alten Befehl `matchstats run` auf den neuen Ablauf umstellen (Entwurf Punkt 6; Löschen nur auf ausdrückliche Anweisung). Volllauf auf clip1 darf über Nacht laufen.
4. **T7 Bericht und Entscheidung:** Kennzahlen T3 bis T5, Laufzeiten, 6 Beispielbilder, Entscheidungsnotiz (Detektor, Kacheln, N, Lizenz). Danach ist Woche 1 laut Spezifikation zu Ende; Planer meldet `fertig` und schlägt vor, `product-owner` oder Auftraggeber über Woche 2 entscheiden zu lassen.

## Erledigt

- T0 Vorbereitung: 3 Clips geschnitten, Label Studio und COCO festgelegt (Details im Spezifikationsstand; kein eigener Commit-Hash ermittelt).
- T1 `d3fce46`: Projektgerüst mit Schichtenarchitektur, CLI und Tests.
- T2 `d6fb7df`: Testset (Bilder ziehen, Label-Studio-Beschriftung, COCO-Lader) mit Tests und Doku.
- T3 `d341ff5`: Personen-Detektor hinter Port (RF-DETR, YOLO), Kachel-Variante, Messung mit Recall/Precision nah/fern.
- T3b `3fb9509`: Spiel-/Clip-/Lauf-Struktur mit Aufnahme-Profil, Halbzeit und Parameter-Schichtung.
- T4 `38f5ba3`, `f590e85`: Tracking in Stufen mit Stufen-Cache; ID-Wechsel-Kandidaten automatisch (Spezifikation v1.5).
- T4b `5871ee5`: Kamerabewegung schätzen und im Tracker ausgleichen (Spezifikation v1.6).
- T5a b803a8a: Teamzuordnung per Trikotfarbe auf beschrifteten Boxen, Befehl `evaluate-teams`. Basislinie Halbzeit 1: gesamt 66,1 % (nah 73,1 %, fern 59,2 %), team_a 84,4 %, team_b 66,9 %, Torwart 10,5 %, Schiedsrichter 0 %, 75 unbekannt; optimistisch (Zuordnung je Clip anhand der Wahrheit). Entscheidung `docs/entscheidungen/0009-teamzuordnung-t5a.md`.
- T5b1 (folgt): Teams je Spur: Abstimmung über höchstens 8 gesehene Punkte, `teams.json` Version 1, Stufen-Cache, noch nicht an `track` angebunden. Handlauf clip1 (run-005): 73 Spuren, team_a 24, team_b 49, Torwart 0, Schiedsrichter 0, `null` 0; Anteil Spuren mit wechselnder Klasse 45,2 % (Stopp-Grund für T5b2 ausgelöst); 573 Stichproben, 14,6 s, Cache-Treffer 0,38 s. Entscheidung `docs/entscheidungen/0010-teams-je-spur-t5b1.md`.

## Stopp-Gründe

- T5a (erledigt, Auftraggeber entschied "als Basislinie committen"): Trefferquote deutlich schlecht (z. B. Torhüter oder Schiedsrichter kaum von einem Team trennbar, weil gleiche Trikotfarbe): anhalten, Beispielbilder zeigen, Auftraggeber entscheidet (andere Merkmale, Handkorrektur, Ergebnis als Basislinie akzeptieren). Spezifikation verlangt in Woche 1 keine Zielwerte, aber das Ergebnis muss bewertet werden.
- Beschriftete Klassen im Testset passen nicht zur Erwartung (z. B. fehlende Torhüter/Schiedsrichter-Boxen): Spezifikation T2 verlangt alle vier Klassen; Abweichung melden.
- Test oder `ruff` bleibt nach zwei Versuchen rot (Modellwechsel auf Opus empfehlen).
- Aufgabe würde Spezifikation oder Messregeln ändern oder ein neues Top-Level-Paket brauchen: Rückfrage statt Umsetzung.

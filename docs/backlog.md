# Backlog (gepflegt vom Planer)

Stand: 2026-11-25. Grundlage: `docs/woche1-spezifikation.md` v1.6, Git-Stand 5fe1565 plus T5c1 (Commit folgt; T5a, T5b1 fertig, T5c1 umgesetzt, T5c2 als Nächstes, T5b2 zurückgestellt). Reihenfolge der Spezifikation: ... T4b -> **T5** -> T6 -> T7.

## Nächste Aufgabe

> Hinweis an den Planer: Diese Planung (T5c2, T5c3, Stopp-Grund T5b2) wurde vom Lead vorgenommen, nicht vom Planer. Beim nächsten Aufruf prüfen und ggf. anpassen.

**T5c2 Gruppierung der Teams verbessern (Sonnet)**

- **Status:** bereit (Ursache zuerst, dann Umsetzung).
- **Hintergrund (Messung T5c1, `docs/entscheidungen/0011-teamzuordnung-t5c1.md`):** Die Mindesthöhe senkte die Wechselrate auf clip1 (45,2 % -> 20,3 %), aber ein Kontaktbogen von 10 Spuren zeigt: Spieler in dunkel/grünem UND weiß/lila Trikot stehen beide bei team_a; team_b besteht größtenteils aus Nicht-Spielern. Die Gruppierung (k-means über alle Stichproben aller Spuren) trennt die Mannschaften nicht. Die gesenkte Wechselrate ist kein Nachweis besserer Zuordnung.
- **Ziel:** Ursache klären, dann die Gruppierung so ändern, dass beide Mannschaften getrennt werden. Zu prüfen, in dieser Reihenfolge:
  1. **Ursache:** warum fallen die Trikotfarben zusammen (Farbraum, Gewicht, Nicht-Spieler als große Gruppe)? Kurz belegen, bevor Code geändert wird.
  2. **Gruppierung je Spur-Medianfarbe statt je Stichprobe:** erst je Spur die Medianfarbe bilden, k-means nur über Spuren (eine Stimme je Spur statt bis zu 8 je Spur).
  3. **Gewicht großer Boxen:** große Boxen zählen mehr beim Gruppieren (Gewicht nach Höhe), Mindesthöhe `team_vote_min_box_height` bleibt Schalter.
- **AK (Maßstab: Mannschaften getrennt UND Wechselrate; eine niedrigere Wechselrate allein zählt nicht):**
  1. Testset (`evaluate-teams`): Tabelle gegen Basislinie T5a (gesamt 66,1 %, team_a 84,4 %, team_b 66,9 %) und gegen T5c1 (71,6 % bei 61,4 % Abdeckung), mit Abdeckung.
  2. clip1: Wechselrate, Spuren je Klasse, `null`-Spuren und **Kontaktbogen-Stichprobe von mindestens 20 Spuren** mit Urteil je Spur: stabil richtig / stabil falsch / Nicht-Spieler / wechselnd. Mannschaften gelten als getrennt, wenn Spieler beider Trikotfarben auf verschiedene Klassen fallen.
  3. Verschlechtert sich Testset-Genauigkeit oder die Stichprobe (mehr stabil falsch): nicht übernehmen, Stopp (siehe Stopp-Gründe).
  4. `pytest` und `ruff check .` grün; Tests für die neue Gruppierung.
- **Schichten/Dateien:** `infrastructure/color_team_classifier.py`, ggf. `application/team_stage.py`, `domain/teams.py`, Parameter-Schichtung, Tests. Keine Änderung am Tracker.
- **Sichtbares Ergebnis:** Abschnitt T5c2 in `docs/entscheidungen/` (neue Notiz oder Fortsetzung von 0011, Planer entscheidet), Kontaktbögen unter `data/ergebnis/`.
- **Modell:** Sonnet; bei nicht klärbarer Ursache Opus empfehlen.

**Folgeteil:**

- **T5c3 Merkmalsvarianten (Sonnet):** Varianten einzeln messen, nicht gebündelt, auf dem T5c2-Stand als Vergleichsbasis (Basislinie T5a bleibt Referenz): (a) Lab statt RGB für Medianfarbe/Clustering, (b) zentraler Oberkörper (`team_upper_body_fraction` 0.35; in der T5b1-Diagnose einzeln -9 Punkte Wechselrate), (c) Rasenpixel in Lab/HSV vor der Medianbildung verwerfen. Messung wie T5c2 (Testset UND clip1 mit Stichprobe). Behalten wird nur, was beide Messungen verbessert; Schalter per Parameter. Danach Ausreißerlogik (Torwart/Schiedsrichter) prüfen, sonst offener Punkt; Entscheidungsnotiz vervollständigen, neue Basislinie festschreiben.

## Offene Nachbesserungen aus dem Review von T5b1

- `team_stage` importiert das private `_is_reusable` aus `tracking_stages.py`; es sollte öffentlich werden oder über ein Protocol laufen.
- Fehlende Stichproben bei zu kurzem Video werden still verschluckt; eine Warnung ergänzen.
- `load_teams` prüft die Struktur von `votes` nicht.
- Tests fehlen für eine leere Spurliste und für eine Stichprobe nur auf Bild 0.

## Rückfragen

Keine blockierende Frage offen. (Frage 1 "meine Mannschaft" ist beantwortet, siehe unten.)

- **Zurückgestellt, nicht blockierend (Lizenz): Embedding-Modell für Teamzuordnung.** Würde eine neue Abhängigkeit (Modellgewichte, Lizenz prüfen) bringen. Wird erst gefragt, wenn T5c2/T5c3 zeigen, dass Farbmerkmale nicht reichen. Optionen dann: (A) bei Farbmerkmalen bleiben, (B) kleines frei lizenziertes Embedding-Modell (nur Apache/MIT), (C) Handkorrektur je Spur. Empfehlung dann: A, solange Genauigkeit auf großen Boxen gut ist.

## Entscheidungen des Auftraggebers

- 2026-11-25, Frage 1 "Wie wird 'meine Mannschaft' festgehalten?": **Option A, erst nicht festhalten.** T5 liefert nur "Team A/B" je Spur; `match.json` Version 2 (`teams`, `own_team`) kommt, wenn Kennzahlen aus Sicht einer Mannschaft gebraucht werden.
- 2026-11-25, Stopp-Grund T5a (Trefferquote schlecht, ausgewertet): Auftraggeber entschied **"als Basislinie committen"**. Offene Verbesserung (Torwart/Schiedsrichter, dritte Farbgruppe) als Punkt in T5b oder später.

- 2026-11-25, Stopp-Grund T5b1 (45,2 % Spuren mit wechselnder Klasse): Auftraggeber wählte **"erst Ursache klären"**. Diagnose liegt vor; daraus T5c1 bis T5c3, T5b2 danach.
- 2026-11-25, T5c1 (Mindesthöhe senkt Wechselrate, aber Mannschaften fallen zusammen): Auftraggeber entschied **"Filter committen, Standard 0"**. Weiter mit T5c2 (Gruppierung).

## Danach

1. **T5b2 Teams im Lauf und Spuren in Teamfarbe (Sonnet):** `matchstats track` ruft nach `track_stage` die `team_stage` auf (`ColorTeamClassifier`, gleiche Videoquelle). `stage_seconds` erhält `teams`; `summary.json` wird Version 4 mit `team_counts`, `team_null_count`, `track_class_change_share`, `teams_reused`. `render_tracks` bekommt optional ein `TeamsDoc`: Boxfarbe je Klasse (team_a blau, team_b rot, Torwart gelb, Schiedsrichter grau, `null` weiß; BGR-Konstanten; dünne Linie bei `null` oder Unsicherheit über 0,5), ID bleibt als Beschriftung; Kontaktbögen ebenso; ohne `TeamsDoc` unverändert (bisherige Tests grün). Dateien: `tracking_job.py`, `track_render.py`, `track_summary.py`, evtl. `cli.py` (Schalter `--no-teams`), Tests. AK: Lauf auf clip1 mit wiederverwendeten Erkennungen liefert `teams.json` und Video in Teamfarbe; `summary.json` nennt den Anteil Spuren mit wechselnder Klasse; 6 Kontaktbogen-Bilder (gute und schlechte) angesehen und notiert; zweiter Aufruf nutzt den Cache (`teams_reused` true); `pytest` und `ruff check .` grün. Stopp, falls die Mannschaften nicht getrennt sind oder die Wechselrate sehr hoch ist (siehe Stopp-Gründe, Schwelle 30 % geraten): Beispiele zeigen.
2. **T5c2 und T5c3** siehe "Nächste Aufgabe". Vor T5b2 abzuschließen; danach wird der Stopp-Grund von T5b2 mit den neuen Zahlen neu bewertet. Maßstab: Mannschaften getrennt (Kontaktbogen-Stichprobe) UND Wechselrate, nicht die Wechselrate allein (die Schwelle 30 % war geraten und ist kein Maßstab für sich).
2a. **Tracker-ID-Wechsel zwischen ähnlichen Personen (eigener Punkt, Sonnet/Opus):** z. B. weißer Spieler und oranger Schiedsrichter-Assistent in drei Spuren verwechselt. Gehört zur Tracking-Stufe (T4-Nachfolger), nicht zur Teamzuordnung. Messung über die ID-Wechsel-Kandidaten aus T4. Einordnung durch den Planer: vor T5b2 neu bewerten, weil Nicht-Spieler und ID-Wechsel die Teamzahlen verfälschen (Befund T5c1: team_b besteht auf clip1 größtenteils aus Nicht-Spielern); sonst nach T5b2, vor oder nach T6.
2b. **Nicht-Spieler per Spielfeld-Filter (eigener Punkt, Sonnet):** Ordner, Fotografen, Zuschauer werden als Spieler verfolgt. Boxfuß außerhalb des Spielfeldes verwerfen (Rasenmaske oder Spielfeldpolygon je Clip). Neues Verhalten (Spuren verschwinden), daher bei Umsetzung kurz mit der Messregel Recall im Testset absichern; wirkt auch auf T5c-Zahlen (neu messen). Vor T5b2 neu bewerten: Nicht-Spieler verfälschen die Teamzahlen (Befund T5c1); ggf. vor T5c2 oder T5b2 vorziehen.
2c. **Embedding-Modell (Lizenz-Rückfrage, siehe Rückfragen):** nur nach T5c3 (T5c2 zuerst), falls Farbmerkmale nicht reichen.
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
- T5b1 5fe1565: Teams je Spur: Abstimmung über höchstens 8 gesehene Punkte, `teams.json` Version 1, Stufen-Cache, noch nicht an `track` angebunden. Handlauf clip1 (run-005): 73 Spuren, team_a 24, team_b 49, Torwart 0, Schiedsrichter 0, `null` 0; Anteil Spuren mit wechselnder Klasse 45,2 % (Stopp-Grund für T5b2 ausgelöst); 573 Stichproben, 14,6 s, Cache-Treffer 0,38 s. Entscheidung `docs/entscheidungen/0010-teams-je-spur-t5b1.md`.
- T5c1 (Commit folgt): Abstimmungs-Mindesthöhe `team_vote_min_box_height`, Filter vor Stichprobe, Standard 0 (aus, Entscheidung des Auftraggebers 2026-11-25; geprüfter Wert 48 px). Messung (Backend-Engineer): Testset H1 nur Boxen ab 48 px: gesamt 71,6 % (Basis 66,1 %), team_a 81,7 % (84,4 %), team_b 79,1 % (66,9 %), Abdeckung 61,4 % (830 von 1352). clip1: Wechselrate 45,2 % -> 20,3 %, `null`-Spuren 0 -> 4, team_a/team_b 24/49 -> 52/17. **Kein Nachweis besserer Zuordnung:** Kontaktbogen 10 von 73 Spuren (3 stabil richtig, 3 stabil falsch = Nicht-Spieler, 4 wechselnd); beide Trikotfarben fallen bei team_a zusammen. Entscheidung `docs/entscheidungen/0011-teamzuordnung-t5c1.md`.

## Stopp-Gründe

- T5c2/T5c3: Wechselrate sinkt, aber Testset-Genauigkeit auf bewerteten Boxen fällt unter 66,1 % oder die Kontaktbogen-Stichprobe zeigt mehr stabil falsche Spuren (Gefahr: Schein-Verbesserung): nicht übernehmen, Zahlen zeigen, Auftraggeber entscheidet.
- T5c2/T5c3: Mannschaften nach Kontaktbogen-Stichprobe weiterhin nicht getrennt (Spieler beider Trikotfarben in derselben Klasse): nicht als Verbesserung werten, Zahlen und Beispiele zeigen, Auftraggeber entscheidet.
- T5b2 (angepasst): Stopp nicht allein bei hoher Wechselrate (Schwelle 30 % war geraten), sondern wenn die Mannschaften nicht getrennt sind (Stichprobe) ODER die Wechselrate hoch ist; eine niedrige Wechselrate bei zusammengefallenen Mannschaften zählt nicht als bestanden.
- T5c: Abdeckung (Anteil Spuren/Boxen mit Klasse != `null`) fällt unter etwa 60 %: melden, weil dann T6 zu wenig Teamfarben hat (Schwelle geraten).

- T5a (erledigt, Auftraggeber entschied "als Basislinie committen"): Trefferquote deutlich schlecht (z. B. Torhüter oder Schiedsrichter kaum von einem Team trennbar, weil gleiche Trikotfarbe): anhalten, Beispielbilder zeigen, Auftraggeber entscheidet (andere Merkmale, Handkorrektur, Ergebnis als Basislinie akzeptieren). Spezifikation verlangt in Woche 1 keine Zielwerte, aber das Ergebnis muss bewertet werden.
- Beschriftete Klassen im Testset passen nicht zur Erwartung (z. B. fehlende Torhüter/Schiedsrichter-Boxen): Spezifikation T2 verlangt alle vier Klassen; Abweichung melden.
- Test oder `ruff` bleibt nach zwei Versuchen rot (Modellwechsel auf Opus empfehlen).
- Aufgabe würde Spezifikation oder Messregeln ändern oder ein neues Top-Level-Paket brauchen: Rückfrage statt Umsetzung.

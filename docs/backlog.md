# Backlog (gepflegt vom Planer)

Stand: 2026-11-25. Grundlage: `docs/woche1-spezifikation.md` v1.6, Git-Stand 5871ee5 (T4b fertig). Reihenfolge der Spezifikation: ... T4b -> **T5** -> T6 -> T7.

## Nächste Aufgabe

**T5b Teamzuordnung auf Spuren**

- **Status:** bereit
- **Modell:** Sonnet; bei mehr als 5 Dateien Opus empfehlen.
- **Ziel:** Je Spur eine Klasse (`team_a`, `team_b`, `goalkeeper`, `referee`) per Mehrheitsentscheid über mehrere Bilder (Stufe 4 der Systemkarte), `teams.json` im Lauf-Ordner mit `schema_version`, Unsicherheit je Spur, Stufen-Cache analog Erkennung/Kamera; Spuren-Render in Teamfarbe. Baut auf dem `TeamClassifier` aus T5a auf.
- **AK:** `teams.json` für clip1 vorhanden, Schema-Test, Anteil Spuren mit wechselnder Klasse im Bericht.
- **Offener Verbesserungspunkt aus T5a (in T5b oder später, Planer/Lead entscheidet beim Zuschnitt):** Torwart (10,5 %) und Schiedsrichter (0 %) werden kaum erkannt; in allen Clips gibt es eine dritte große Farbgruppe (87 bis 133 Boxen), Ursache offen. Erst Ursache an Beispielbildern klären, dann Verfahren ändern. Basislinie und Zahlen: `docs/entscheidungen/0009-teamzuordnung-t5a.md`.
- **Annahmen:** Frage 1 ist beantwortet (Option A): kein `match.json` Version 2 in T5; nur "Team A/B" je Spur.

## Rückfragen

Keine offen. (Frage 1 "meine Mannschaft" ist beantwortet, siehe unten.)

## Entscheidungen des Auftraggebers

- 2026-11-25, Frage 1 "Wie wird 'meine Mannschaft' festgehalten?": **Option A, erst nicht festhalten.** T5 liefert nur "Team A/B" je Spur; `match.json` Version 2 (`teams`, `own_team`) kommt, wenn Kennzahlen aus Sicht einer Mannschaft gebraucht werden.
- 2026-11-25, Stopp-Grund T5a (Trefferquote schlecht, ausgewertet): Auftraggeber entschied **"als Basislinie committen"**. Offene Verbesserung (Torwart/Schiedsrichter, dritte Farbgruppe) als Punkt in T5b oder später.

## Danach

1. **T6 Ausgabe:** Annotiertes Video (Box, konstante ID, Teamfarbe) plus Datei mit allen Spuren, Felder Sichtbarkeit und Unsicherheit, Schema-Test. Dabei alten Befehl `matchstats run` auf den neuen Ablauf umstellen (Entwurf Punkt 6; Löschen nur auf ausdrückliche Anweisung). Volllauf auf clip1 darf über Nacht laufen.
2. **T7 Bericht und Entscheidung:** Kennzahlen T3 bis T5, Laufzeiten, 6 Beispielbilder, Entscheidungsnotiz (Detektor, Kacheln, N, Lizenz). Danach ist Woche 1 laut Spezifikation zu Ende; Planer meldet `fertig` und schlägt vor, `product-owner` oder Auftraggeber über Woche 2 entscheiden zu lassen.

## Erledigt

- T0 Vorbereitung: 3 Clips geschnitten, Label Studio und COCO festgelegt (Details im Spezifikationsstand; kein eigener Commit-Hash ermittelt).
- T1 `d3fce46`: Projektgerüst mit Schichtenarchitektur, CLI und Tests.
- T2 `d6fb7df`: Testset (Bilder ziehen, Label-Studio-Beschriftung, COCO-Lader) mit Tests und Doku.
- T3 `d341ff5`: Personen-Detektor hinter Port (RF-DETR, YOLO), Kachel-Variante, Messung mit Recall/Precision nah/fern.
- T3b `3fb9509`: Spiel-/Clip-/Lauf-Struktur mit Aufnahme-Profil, Halbzeit und Parameter-Schichtung.
- T4 `38f5ba3`, `f590e85`: Tracking in Stufen mit Stufen-Cache; ID-Wechsel-Kandidaten automatisch (Spezifikation v1.5).
- T4b `5871ee5`: Kamerabewegung schätzen und im Tracker ausgleichen (Spezifikation v1.6).
- T5a (folgt): Teamzuordnung per Trikotfarbe auf beschrifteten Boxen, Befehl `evaluate-teams`. Basislinie Halbzeit 1: gesamt 66,1 % (nah 73,1 %, fern 59,2 %), team_a 84,4 %, team_b 66,9 %, Torwart 10,5 %, Schiedsrichter 0 %, 75 unbekannt; optimistisch (Zuordnung je Clip anhand der Wahrheit). Entscheidung `docs/entscheidungen/0009-teamzuordnung-t5a.md`.

## Stopp-Gründe

- T5a (erledigt, Auftraggeber entschied "als Basislinie committen"): Trefferquote deutlich schlecht (z. B. Torhüter oder Schiedsrichter kaum von einem Team trennbar, weil gleiche Trikotfarbe): anhalten, Beispielbilder zeigen, Auftraggeber entscheidet (andere Merkmale, Handkorrektur, Ergebnis als Basislinie akzeptieren). Spezifikation verlangt in Woche 1 keine Zielwerte, aber das Ergebnis muss bewertet werden.
- Beschriftete Klassen im Testset passen nicht zur Erwartung (z. B. fehlende Torhüter/Schiedsrichter-Boxen): Spezifikation T2 verlangt alle vier Klassen; Abweichung melden.
- Test oder `ruff` bleibt nach zwei Versuchen rot (Modellwechsel auf Opus empfehlen).
- Aufgabe würde Spezifikation oder Messregeln ändern oder ein neues Top-Level-Paket brauchen: Rückfrage statt Umsetzung.

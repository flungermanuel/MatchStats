# 0011: Abstimmungs-Mindesthöhe `team_vote_min_box_height` (T5c1)

Datum: 2026-11-25. Spezifikation v1.6 (T5). Baut auf 0009 (T5a) und 0010 (T5b1) auf. Noch nicht an `matchstats track` angebunden (T5b2).

## Was
- Neuer Parameter **`team_vote_min_box_height`** (Pixel, Standard **0 = aus**). Nur Boxen mit Höhe >= diesem Wert stimmen in der Abstimmung einer Spur mit.
- **Reihenfolge der Auswahl:** zuerst Filter (gesehen und Höhe >= Mindesthöhe), danach die gleichmäßige Stichprobe von höchstens `team_samples_per_track` (8) Punkten aus den *geeigneten* Punkten (erster und letzter geeigneter Punkt inklusive). Nicht: erst 8 Punkte ziehen und dann filtern.
- Die Spur bleibt bestehen. Bleiben weniger als `team_min_votes` (3) bekannte Stimmen übrig, ist `label` `null`.
- Der Parameter ist ein `team_*`-Parameter und damit automatisch Teil von `stage_params` und des Cache-Schlüssels von `teams.json`. Er steht auch im Lauf-Ordner (`teams.json`, `stage_params`).
- Code: `select_sample_points(track, count, min_height)` in `domain/teams.py`, Aufruf in `application/team_stage.py`, Wert in `domain/settings.py` (negativ wird abgelehnt) und `infrastructure/default.toml`.

## Warum
- Die Diagnose zu T5b1 zeigte: Die Wechselrate hängt stark an der Boxhöhe (klein 70,8 %, groß 8 %). Kleine Boxen haben wenige Trikotpixel, viel Rasenanteil und Bewegungsunschärfe.
- Filter vor Stichprobe, damit kleine Boxen nicht einen Teil der 8 Stichprobenplätze verbrauchen.

## Alternativen
- **Erst ziehen, dann filtern:** verworfen, die Stimmenzahl hinge vom Zufall der Verteilung ab.
- **Gewichten nach Boxhöhe statt Filter:** nicht jetzt (siehe T5c2).
- **Parameter-Variation allein** (cluster_count 2, upper_body_fraction 0.35, min_box_height 40): in der Diagnose T5b1 half wenig (Wechselrate 32,9 %, 36,1 %, 40,8 %).
- **Standard 48 px:** Der Auftraggeber entschied dagegen (siehe unten). 48 px war der geprüfte Wert, die Mitte der Spanne 45 bis 50 (geraten).

## Messung
Quelle: Messbericht des Backend-Engineers, hier wiedergegeben, nicht neu gemessen. Mindesthöhe 48 px.

**Testset Halbzeit 1** (nur beschriftete Boxen ab 48 px ausgewertet; die Klassifikation lief mit allen Boxen, nur die Auswertung ist gefiltert):

| Wert | Basis T5a | T5c1 (48 px) |
|---|---|---|
| Genauigkeit gesamt | 66,1 % | 71,6 % |
| team_a | 84,4 % | 81,7 % |
| team_b | 66,9 % | 79,1 % |
| Abdeckung (bewertete Boxen) | 100 % | 61,4 % (830 von 1352) |

Die Basis ist auf allen Boxen, T5c1 nur auf den großen: nicht gleiche Menge, der Vergleich ist daher nur bedingt fair.

**clip1 (run-005, 73 Spuren):**

| Wert | T5b1 | T5c1 (48 px) |
|---|---|---|
| Wechselrate (Spuren mit wechselnder Klasse) | 45,2 % | 20,3 % |
| Spuren mit `null` | 0 | 4 |
| Spuren team_a / team_b | 24 / 49 | 52 / 17 |
| Spuren mit reiner Stimme 8:0 | 35 | 50 |

Wechsel nach Höhenklasse (Spurmittel):

| Höhe | T5b1 | T5c1 (48 px) |
|---|---|---|
| < 48 px | 11 von 15 | 0 von 11 (4 `null`) |
| 48 bis 70 px | 18 von 31 | 8 von 31 |
| >= 70 px | 4 von 27 | 6 von 27 |

**Kontaktbogen, 10 Spuren** (`data/ergebnis/t5c1_diagnose/kontakt.png`, `kontakt2.png`, nicht im Git): 3 stabil richtig (Spieler), 3 stabil falsch (Nicht-Spieler wie Ordner, Fotograf, Person am Rand), 4 wechselnd.

## Ehrliches Urteil
- **Die Wechselrate sinkt, ist aber kein Nachweis besserer Zuordnung.** Spieler in dunkel/grünem und in weiß/lila Trikot stehen beide bei team_a; team_b besteht größtenteils aus Nicht-Spielern. Die Gruppierung über die Stichproben aller Spuren trennt auf clip1 die Mannschaften nicht.
- Die gesunkene Wechselrate erklärt sich damit zum Teil durch Zusammenfallen der Gruppen (wer überall team_a ist, wechselt nie) und dadurch, dass kleine Spuren wegfallen (`null`). Das ist genau die im Backlog befürchtete Schein-Verbesserung.
- Beobachtet an **nur 10 von 73 Spuren**; keine Wahrheit je Spur. Anteile sind Indizien.
- Auf dem Testset steigt die Genauigkeit auf den bewerteten Boxen (71,6 % >= 66,1 %), aber nur bei 61,4 % Abdeckung; team_a fällt leicht. Der Wert 61,4 % liegt knapp über der geratenen Stopp-Schwelle von etwa 60 %.
- Parameterwerte sind geraten.

## Entscheidung des Auftraggebers (2026-11-25)
**Filter committen, Standard 0 (aus).** Die Möglichkeit steht bereit; ob und mit welchem Wert sie eingeschaltet wird, hängt am Ergebnis von T5c2 (Gruppierung). Ursachenklärung geht weiter (T5c2).

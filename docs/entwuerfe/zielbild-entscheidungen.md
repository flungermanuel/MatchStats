# Entscheidungsvorschläge zum Zielbild (Entwurf, wartet auf dein Ja je Punkt)

Stand: 2026-11-20. Grundlage: `docs/architektur.md` Teil A, Abschnitt A5. Nichts hier ist beschlossen oder umgesetzt. Wird ein Punkt bestätigt, wird daraus eine Notiz `docs/entscheidungen/000N-...md` und (falls nötig) eine Änderung der Spezifikation, die du vorher freigibst.

## 1. Mannschaften und eigene Seite im Spiel
- **Entschieden (von dir):** Anwender wählt seine Mannschaft, Feedback aus deren Sicht.
- **Vorschlag:** `match.json` Version 2 mit `teams: [{id: "a", name}, {id: "b", name}]` und `own_team: "a"` (oder `null`). Namen sind Vereinsnamen, keine Spielernamen. T5 ordnet Spuren "Team A/B" nach Trikotfarbe zu; die Zuordnung zu "meine Mannschaft" macht der Anwender einmal je Spiel (Halbzeitwechsel: Seite wechselt, Team bleibt).
- **Alternative:** Nur ein Feld `own_team_color` im Clip-Profil. Einfacher, aber Gegner und Seitenwechsel schlecht abbildbar.
- **Zeitpunkt:** mit T5, nicht vorher (Bremse).
- **Folge:** Migration `schema_version` 1 -> 2 braucht eine klare Meldung bei alten Dateien (Regel aus CLAUDE.md).

## 2. Korrekturen als eigene Datei
- **Vorschlag:** `corrections.json` je Lauf. Einträge: Team einer Spur ändern, Spuren zusammenführen, Spur entfernen (Ordner/Bank), Rolle (Torhüter, Schiedsrichter). Rohdateien bleiben unverändert; Kennzahlen lesen Rohdaten plus Korrekturen.
- **Alternative:** Rohdaten überschreiben. Einfacher, aber nicht nachvollziehbar und nicht wiederholbar.
- **Zeitpunkt:** erst mit dem Viewer (Woche 3 bis 4). Bis dahin nur das Prinzip festhalten.

## 3. Aufnahmeprüfung (Abschnitte ausschließen)
- **Lücke:** Brief verlangt, Zoom auf Jubel erkennen und ausschließen. In keiner Aufgabe verplant; T4b deckt nur Kamerabewegung ab.
- **Vorschlag:** Eine eigene Aufgabe nach T7, Stufe `segments.json` (Zeitbereiche mit Grund, z. B. "zoom", "kein Spielfeld"). Erste Version regelbasiert (Spielfeldanteil im Bild, Boxgrößen-Sprung), keine neue Modellabhängigkeit.
- **Offen:** Ob zuerst gemessen werden soll, wie viel Material betroffen ist (an clip1 bis clip3 nicht geprüft).

## 4. Spielfeldfilter
- Bleibt in Woche 2, weil er die Kalibrierung braucht. Keine Zwischenlösung vorschlagen, bis die Handzählung zeigt, ob Ordner/Bank stören (sie stören die Handzählung der Spieler nicht, nur die Hilfszahlen).

## 5. Tracker in `application/`
- **Vorschlag:** So lassen, solange es einen Tracker gibt, und in der Notiz 0006 ausdrücklich als Ausnahme begründen (reine Rechenlogik ohne Außenwelt, gehört fachlich zur Anwendung). CLAUDE.md verlangt Implementierungen in `infrastructure/`; die Regel gilt dort für Dinge mit Außenwelt oder Bibliotheken. Alternative: verschieben (viele Importe, wenig Gewinn).
- **Das ändert eine Arbeitsregel**, deshalb nur mit deinem Ja.

## 6. Alter Befehl `matchstats run`
- **Vorschlag:** Bei T6 (Ausgabe) auf den neuen Ablauf umstellen oder entfernen, nicht vorher. Bis dahin steht er als "leer" in der Systemkarte.
- **Entfernen** wäre ein Löschen: nur auf deine ausdrückliche Anweisung.

## Empfohlene Reihenfolge
1 mit T5, 5 jetzt als Satz in Notiz 0006 (nach deinem Ja), 6 mit T6, 2 vor Woche 3, 3 nach T7, 4 in Woche 2.

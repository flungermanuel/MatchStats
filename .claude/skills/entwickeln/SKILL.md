---
name: entwickeln
description: Automatische Entwicklungsschleife. Der planner wählt die nächste Aufgabe, die Agenten setzen sie um, der Lead committet und plant weiter. Gefragt wird der Entwickler nur bei Feature-Rückfragen.
disable-model-invocation: true
---

Auftrag: $ARGUMENTS
(Leer = die nächste Aufgabe aus dem Backlog. Sonst Anzahl der Aufgaben, z. B. `3`, oder eine Kennung wie `T4c`, oder `bis Ende T4`.)

Du bist der Lead. Subagents können keine Subagents starten, deshalb steuerst **du** die Schleife und rufst die Agenten nacheinander auf. Der Entwickler hat mit diesem Aufruf die Aufgaben der Schleife freigegeben, **einschließlich der Commits** (ein Commit pro Aufgabe, kein Push). Alle Regeln aus `CLAUDE.md` gelten weiter.

## Schleife (pro Aufgabe)

1. **Planen.** Rufe `planner` auf. Lies `STATUS`.
   - `fertig`: Schleife beenden, Zusammenfassung zeigen.
   - `wartet-auf-antwort`: weiter bei Schritt 2.
   - `bereit`: weiter bei Schritt 3.
2. **Feature-Rückfragen.** Stelle die Fragen des Planers gebündelt mit `AskUserQuestion` (max. 4 pro Aufruf, Empfehlung als erste Option). Trage die Antworten durch erneuten Aufruf des `planner` ins Backlog ein (Abschnitt Entscheidungen) und gehe zurück zu Schritt 1. Stelle keine technischen Fragen, die du oder der Planer selbst begründen können.
3. **Plan prüfen.** Rufe `architect` mit dem Plan der Aufgabe auf. Bei "Bedenken": einarbeiten. Bei "Blocker" oder Widerspruch zur Spezifikation: das ist eine Feature-Rückfrage, stelle sie dem Entwickler. Du änderst die Spezifikation nie selbst.
4. **Test zuerst.** Rufe `test-engineer` mit dem AK auf. Der Test muss zunächst aus dem richtigen Grund rot sein.
5. **Umsetzen.** Rufe `backend-engineer` (bei Oberfläche `frontend-engineer`, falls aktiv) mit Plan und Test auf. Nur diese Aufgabe, nichts vorziehen.
6. **Prüfen** wie `/aufgabe-abschluss` Schritte 1 bis 7: `code-reviewer`, Blocker beheben (max. 2 Runden), `pytest` und `ruff check .`, sichtbares Ergebnis erzeugen, `doc-keeper` (Systemkarte und Erklärung), Entscheidungsnotiz falls nötig, `git status` (nichts aus `data/`).
7. **Committen.** Nur bei grünen Tests und Ruff. Commit-Message auf Deutsch im Stil der bisherigen Commits, ohne Co-Authored-By-Zeile und ohne Claude-Hinweis. Kein Push. Der Hook blockiert bei Rot ohnehin.
8. **Backlog nachführen.** Rufe `planner` auf, der die Aufgabe unter "Erledigt" einträgt (mit Commit-Hash) und die nächste bestimmt. Weiter bei Schritt 1, bis der Auftrag erfüllt ist.

## Anhalten und den Entwickler holen

Halte die Schleife an (kein Weitermachen auf Verdacht) und melde dich, wenn:
- eine Feature-Rückfrage offen ist (Schritt 2, das ist der Normalfall),
- Tests oder Ruff nach zwei Reparaturrunden rot bleiben oder derselbe Fehler zweimal erfolglos behoben wurde,
- das sichtbare Ergebnis schlecht ist oder die Messwerte das AK verfehlen (zeigen, Ursachen nennen, nichts schönen),
- die Spezifikation fehlt, unklar ist oder widerspricht,
- ein Modellwechsel nötig ist (CLAUDE.md, Modellwahl): sage konkret "Wechsle jetzt mit /model auf Opus, weil ..." und wann zurück. Du kannst das Modell nicht selbst wechseln,
- die Sitzung lang wird: nach jeder abgeschlossenen Aufgabe kurz `/clear` empfehlen. Das Backlog hält den Stand, die Schleife lässt sich mit `/entwickeln` nahtlos fortsetzen,
- etwas Unumkehrbares oder Externes nötig wäre (Push, Löschen, Daten an Dienste, neue Abhängigkeit mit unklarer Lizenz).

## Nach jeder Aufgabe an den Entwickler (kurz)

Die Erklärung aus CLAUDE.md (vier Punkte, max. 10 Zeilen), Pfad zum sichtbaren Ergebnis, Commit-Hash, offen Gesagtes (nicht getestet, geraten, schwach). Dann sofort die nächste Aufgabe, ohne Rückfrage, solange kein Anhaltegrund vorliegt.

## Kontingent

Nur die Agenten aufrufen, die die Aufgabe braucht (z. B. kein `architect` bei reiner Doku-Aufgabe). Dateien nur gezielt lesen. Ohne Zahl im Auftrag höchstens 3 Aufgaben pro Aufruf, dann Zwischenstand und Frage, ob weitergemacht werden soll.

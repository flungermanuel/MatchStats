---
name: aufgabe-abschluss
description: Schließt eine Aufgabe ab. Review, Tests, Ruff, Systemkarte, Erklärung, Entscheidungsnotiz und Commit-Vorschlag.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Ablauf (du bist der Lead):
1. Rufe `code-reviewer` für den aktuellen Diff auf. Arbeite Blocker ein (über `backend-engineer` oder selbst) und zeige dem Entwickler offene "sollte"-Punkte.
2. Führe `pytest` und `ruff check .` aus (`ruff format .` nur, wenn nötig). Bei Rot: nicht committen, Ursache zeigen.
3. Erzeuge ein sichtbares Ergebnis, das der Entwickler selbst beurteilen kann (Bild, Video, Tabelle), und nenne den Pfad. Schlechte Ergebnisse zeigen und Ursachen erklären, nichts schönen.
4. Rufe `doc-keeper` auf: `docs/architektur.md` aktualisieren und die Erklärung (max. 10 Zeilen, vier Punkte) liefern. Prüfe, ob sie zum echten Stand passt.
5. Falls eine Architekturentscheidung fiel: Notiz in `docs/entscheidungen/` (Was, Warum, Alternativen), Entwurf vom `architect` möglich.
6. Prüfe, dass nichts aus `data/` im Git landet (`git status`).
7. Sage offen, was nicht getestet, unsicher oder nur geraten ist.
8. Schlage Commit-Message vor (ein Commit pro Aufgabe, KEINE Co-Authored-By-Zeile, kein Claude-Hinweis) und committe erst nach dem Ja des Entwicklers. Kein Push.

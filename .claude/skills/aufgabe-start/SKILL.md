---
name: aufgabe-start
description: Startet eine Aufgabe (z. B. T2) nach dem festen Ablauf. Fasst Aufgabe und Abnahmekriterium zusammen, lässt den Plan vom architect prüfen und wartet auf Bestätigung.
disable-model-invocation: true
---

Aufgabe: $ARGUMENTS

Ablauf (du bist der Lead, Auftraggeber ist der Entwickler):
1. Lies in `docs/woche1-spezifikation.md` nur die genannte Aufgabe, ihr Abnahmekriterium (AK) und die Messregeln, die dafür gelten. Lies bei Bedarf `docs/projektbrief.md` und `docs/architektur.md`.
2. Fasse Aufgabe und AK in eigenen Worten zusammen (Deutsch, kurz). Stelle Rückfragen, statt zu raten. Nenne Widersprüche zwischen Code und Spezifikation, ändere die Spezifikation nicht.
3. Entwirf einen Plan: Schritte, betroffene Schichten und Dateien, welche Tests das AK abbilden, welches sichtbare Ergebnis (Bild, Video, Tabelle) entsteht.
4. Rufe den Subagent `architect` auf, um den Plan zu prüfen. Arbeite sein Urteil ein.
5. Prüfe die Modellwahl nach CLAUDE.md. Empfiehl Opus, wenn eine schwer umkehrbare Entscheidung ansteht oder mehr als 5 Dateien betroffen sind. Weise auf eine lange Sitzung hin (`/clear`).
6. Zeige den Plan und WARTE auf das Ja des Entwicklers. Schreibe vorher weder Tests noch Code.

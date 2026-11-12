# matchstats: Projektbeschreibung (Stand 12.11.2026)
 
## Kurzbeschreibung
matchstats erzeugt aus eigenen Videoaufnahmen von Ligaspielen automatisch taktische Auswertungen: Positionsdaten, Heatmaps pro Spieler und Team, Formation, Kompaktheit und weitere Kennzahlen zur Mannschaftsform. Das Projekt ist zugleich Lernfeld für Systemarchitektur, Multi-Agent-Systeme und sauberes Vibe Coding (der Entwickler führt Regie, Claude Code implementiert, Tests und Prüfstände sichern die Qualität) und soll ein vorzeigbares Portfolio-Stück werden. Ein späterer Verkauf ist Zukunftsmusik.
 
## Ausgangslage
- Eigene Aufnahmen von Ligaspielen, Hochstativ ca. 6 m, taktische Ansicht (alle Spieler möglichst die ganze Zeit im Bild), Perspektive wechselt von Spiel zu Spiel. Das bisher vorliegende Material ist Full HD (1920x1080, 25 fps, interlaced, .MTS), nicht 4K; ein weiteres Spiel wird am 15.11.2026 gefilmt.
- Es wird geschwenkt und gezoomt; bei Toren wird auf die Jubeltraube gezoomt. Diese Abschnitte sind für Tracking nicht brauchbar und müssen erkannt und ausgeschlossen werden.
- Entwickler: Informatikstudent (5. Semester), allein, ca. 8 Stunden pro Woche, Windows-Laptop ohne dedizierte GPU (Intel Core Ultra 7 155H, 16 GB RAM). Anfangs wird nichts gemietet, alles läuft lokal auf der CPU.
## Zielgruppen
- Trainer: taktische Auswertung, Halbzeit-Briefing, Szenen.
- Liga: Statistiken und Grafiken (z. B. Heatmaps als Bilddatei).
- Vereine: eigene Nutzung der Software (später, mehrere Mandanten).
- Nicht Ziel: Inhalte für Social Media.
## Leitprinzip
Daten → Erkenntnisse → Darstellung.
- Bildverarbeitung (Erkennen, Tracken, Kalibrieren) übernehmen spezialisierte Modelle.
- Agenten orchestrieren, prüfen und interpretieren; sie erkennen keine Spieler pro Bild.
- Jede Pipeline-Stufe speichert ihr Zwischenergebnis. Kennzahlen werden aus gespeicherten Spuren berechnet, nicht aus dem Video, neue Kennzahlen brauchen keinen neuen Bildverarbeitungslauf.
- Heatmaps und Grafiken werden deterministisch aus Daten gerendert; Text nur mit Faktenprüfung und Freigabe.
## Zielarchitektur (später)
Web-Oberfläche (Upload, Projektliste, Viewer mit Video, Minimap, Heatmap, Statistiken), API-Dienst mit Rollen (Liga, Verein, Trainer), Objektspeicher, Warteschlange und Worker mit den Stufen erkennen, tracken, Teams zuordnen, kalibrieren, projizieren, Kennzahlen. Analyse-Agenten: Qualitätsprüfer, Taktik-Analyst, Chefanalyst, Faktenprüfer, Frage-Agent.
 
## Kennzahlen (Ziel, ohne Ball)
Heatmaps pro Spieler und Team, Durchschnittspositionen (Formation), Kompaktheit (Fläche, Breite, Tiefe), Abstände zwischen den Mannschaftslinien, Teamschwerpunkt, Tempo von Umschaltmomenten, Pressing-Nähe, Laufwege und Sprints. Der Ball kommt erst später. Extra-Idee: Kamera-Coach (Anteil der Zeit, in der alle Feldspieler im Bild waren).
 
## Datenmodell-Prinzipien
- Jede Messung hat Felder für Sichtbarkeit und Unsicherheit (Kalibriergüte).
- Unbekannt ist nicht null: Kennzahlen werden mit Abdeckung gerechnet.
- Detektor austauschbar halten (Ultralytics YOLO: AGPL-3.0; Alternative RF-DETR: Apache 2.0).
- Kalibrierung: wenige manuelle Schlüsselbilder plus automatische Fortführung, Prüfung auf Drift.
## Roadmap
Die "Wochen" sind Arbeitseinheiten, bei 8 h pro Woche etwa das 2- bis 3-fache an Kalenderzeit.
- Woche 0 bis 1: Testset aus eigenen Spielen, Erkennen, Tracken, Teamzuordnung auf 60-Sekunden-Clips, Ergebnis ist ein annotiertes Video plus Bericht (siehe claude/woche1-spezifikation.md).
- Woche 2: Kalibrierwerkzeug und Minimap.
- Woche 3 bis 4: Dienst mit Upload, Warteschlange, Fortschritt, Viewer mit Heatmaps.
- Woche 5: Prüfstand für die Bildverarbeitung über ganze Spiele.
- Danach: Qualitätsprüfer, Analyse-Agenten, Mehrspiel-Vergleich, optional Bildexport. Vorher 2 bis 3 Gespräche mit Trainern/Liga, welche Auswertung sie am ehesten nutzen würden.
## Prüfstände (Evals)
- Bildverarbeitung: öffentliche Vergleichsdaten (SoccerNet-GSR, TV-Perspektive, nur eingeschränkt passend) plus eigenes, von Hand beschriftetes Testset aus 3 bis 5 eigenen Spielen.
- Agenten: Fragen mit deterministisch berechenbarer Antwort (Trefferquote), Faktenprüfer-Quote bei erfundenen Zahlen.
## Arbeitsregeln (Vibe Coding)
Erst Spezifikation mit Abnahmekriterien, dann Code. Tests/Prüfstände zuerst, der Agent macht sie grün. Kleine Schritte, ein Commit pro Aufgabe, Diffs selbst lesen und in einfachen Worten erklären lassen. Architekturentscheidungen als kurze Begründungen festhalten.
 
## Rechte, Datenschutz, Risiken
- Nutzungsrechte: Die Absprache mit dem Chef (Aufnahmen für das Projekt) ist bisher nur mündlich. Schriftlich festhalten: Verwendung für das Projekt, Zeigen von Ergebnissen im Portfolio, Weitergabe an Vereine/Liga. Keine Rohvideos und keine Spielernamen öffentlich.
- Datenschutz: Einwilligung der Spieler, besondere Vorsicht bei Jugendspielern.
- Videoqualität: Full HD, weit entfernte Spieler bleiben sehr klein; Test "ganzes Bild verkleinert vs. Kacheln".
- Rechenleistung: lokal nur CPU; Gegenmittel sind kleine Modelle, Erkennung nur auf jedem N-ten Bild, kurze Clips, Läufe über Nacht.
## Aktueller Stand
Brief v1.1 und Woche-1-Spezifikation v1.1 liegen vor. T0 ist weitgehend erledigt: 3 Clips à 60 s sind geschnitten (Prüfung per ffprobe noch zu bestätigen). Nächster Schritt: Beschriftungswerkzeug festlegen (Vorschlag Label Studio), dann T1 (Projektgerüst und CLAUDE.md) in Claude Code.
# Ideen und Kandidaten (keine Spezifikation, nichts davon ist beschlossen)

Stand: 18.11.2026. Diese Datei sammelt Vorschläge. Sie ändert weder den Brief noch die Wochenspezifikation.
Aufnahme in eine Aufgabe nur nach Ja des Entwicklers.

## Kennwerte-Kandidaten (aus gespeicherten Spuren, ohne Ball)

Gemeinsame Annahmen:
- Eingabe: `tracks.json` (Spur, Team, Sichtbarkeit) plus Kalibrierung (Meter auf dem Feld, **ab Woche 2**).
- Feldspieler = ohne Torhüter und Schiedsrichter (T5). Spielrichtung je Halbzeit bekannt (Seitenwechsel beachten).
- **Fehlende Spieler:** Ist ein benötigter Spieler nicht sichtbar, ist der Kennwert für diesen Zeitpunkt *unbekannt* (nicht 0, nicht "kleiner"). Jeder Kennwert nennt seine **Abdeckung** (Anteil der Zeitpunkte, an denen er berechenbar war).
- Rechenstufe auf Spuren, kein neuer Bildverarbeitungslauf. Gleiche Eingabe ergibt gleiches Ergebnis.
- Alle Zahlen am Ende mit Prüfung an Beispielbildern (Overlay), nicht nur als Zahlenreihe.
- Priorität: **A** = wenige Eingaben, robust; **B** = braucht saubere Gruppierung oder Rollen; **C** = empfindlich gegen Rauschen oder fehlenden Ball.

### Gruppe 1: Mannschaftsstruktur je Zeitpunkt
| Nr | Kennwert | Definition | Eingaben | Abdeckung nötig | Prio | Test mit künstlichen Daten |
|---|---|---|---|---|---|---|
| K1 | Teamschwerpunkt | Mittel der Feldspieler-Positionen (x, y) | alle sichtbaren Feldspieler | mind. 6 sichtbar (Schwelle konfigurierbar) | A | Spieler symmetrisch gesetzt ⇒ Schwerpunkt in der Mitte |
| K2 | Teamlänge (Tiefe) | max x minus min x der Feldspieler, entlang der Längsachse | alle Feldspieler | alle 10 Feldspieler sichtbar (sonst unbekannt) | A | zwei Spieler 40 m auseinander ⇒ 40 |
| K3 | Teambreite | max y minus min y | alle Feldspieler | alle 10 sichtbar | A | |
| K4 | Teamfläche | Fläche der konvexen Hülle | alle Feldspieler | alle 10 sichtbar | A | Rechteck 40 × 30 ⇒ 1200 m² |
| K5 | Kompaktheit | K4 geteilt durch K2 × K3 (Füllgrad) und Abstand der Spieler zum Schwerpunkt (Mittel) | wie K2 bis K4 | wie K4 | B | |
| K6 | Höhe der Abwehrlinie | mittlerer Abstand der hintersten 3 bis 4 Feldspieler zum eigenen Tor | Feldspieler, Spielrichtung | die 4 hintersten sichtbar | A | |
| K7 | Abseitslinie | Abstand des zweithintersten Spielers zum Tor (Torhüter eingeschlossen) | Feldspieler + Torhüter | beide Hintersten sichtbar | B | |
| K8 | Kettenabstände | Feldspieler in Spielrichtung in 3 bis 4 Gruppen einteilen (1D-Clustering), Abstand der Gruppenmittel | alle Feldspieler | alle 10 sichtbar | B | Aufstellung 4-4-2 künstlich ⇒ erwartete Abstände |
| K9 | Breite einer Kette | y-Abstand äußerer zu äußerem Spieler der Gruppe | K8 | Gruppe vollständig | B | |
| K10 | Abstand der Teams | Schwerpunkt A zu Schwerpunkt B; Lücke zwischen eigener Abwehrlinie und gegnerischer Sturmlinie | beide Teams | je Team K1 bzw. K6 verfügbar | A | |
| K11 | Überzahl in Zonen | Spielerzahl je Team pro Drittel und Halbraum (Zonen konfigurierbar) | alle Spieler beider Teams | Zone vollständig im Bild | B | |
| K12 | Raumkontrolle (Voronoi) | Fläche je Team, in der der nächste Spieler zu ihm gehört | alle Spieler beider Teams | alle 20 Feldspieler sichtbar | C | |

### Gruppe 2: Kennwerte je Spieler über Zeit
| Nr | Kennwert | Definition | Prio | Hinweis |
|---|---|---|---|---|
| K13 | Heatmap und Zonenanteile | Aufenthaltszeit pro Feldzelle (z. B. 2 × 2 m), Anteile je Drittel/Halbraum | A | Abdeckung = sichtbare Zeit; ID-Wechsel zersplittern die Spur |
| K14 | Durchschnittsposition (Formation) | Mittel der Position je Spieler oder Rolle über einen Zeitraum | B | Rollenzuordnung (z. B. RV, IV) ist ein eigenes Problem |
| K15 | Positionsstreuung | Standardabweichung (x, y) je Spieler | B | |
| K16 | Laufdistanz | Summe der Wege der geglätteten Spur | C | Rauschen vergrößert Wege; nur auf geglätteter Spur, Lücken nicht überbrücken |
| K17 | Tempo und Sprints | Geschwindigkeit je Zeitpunkt; Sprint = über Schwelle (z. B. 7 m/s) für mind. 1 s | C | empfindlich; Schwelle und Glättung offen |
| K18 | Pressing-Nähe (Stellvertreter) | Abstand zum nächsten Gegner, Anzahl Gegner im Umkreis von 5 m | B | echter Druck braucht den Ball (fehlt) |

### Gruppe 3: Zeitabschnitte
| Nr | Kennwert | Definition | Prio | Hinweis |
|---|---|---|---|---|
| K19 | Umschaltmomente (grob) | schnelle Änderung von K2 oder K1 (z. B. Teamlänge sinkt um X m in Y s) | C | Auslöser (Ballverlust) fehlt; Schwellen aus Daten festlegen |
| K20 | Kamera-Coach | Anteil der Zeit, in der alle 10 Feldspieler eines Teams im Bild waren | A | **schon ohne Kalibrierung möglich**, reine Zählung aus Spuren |
| K21 | Abdeckungsbericht | je Spieler und Kennwert: Anteil berechenbarer Zeitpunkte | A | Pflicht bei jeder Auswertung |

## Was ohne Ball nicht geht
Ballbesitz, Pässe, Torschüsse, "wer presst den Ballführenden", echte Umschaltauslöser. Ball kommt erst später laut Brief.

## Voraussetzungen und Grenzen (nicht geprüft)
- **Kalibrierfehler** unbekannt vor Woche 2; Abstände unter ca. 2 m bis dahin nicht deuten.
- **Fußpunkt** (Unterkante der Box) ist bei kleinen, fernen Spielern ungenau.
- **ID-Wechsel** (T4) beeinflussen K13 bis K17 direkt; Team-Kennwerte (K1 bis K12) sind weniger betroffen, solange das Team stimmt (T5).
- **Zoom und Torjubel-Abschnitte** müssen vorher ausgeschlossen werden (nicht gebaut).
- **Spielrichtung und Halbzeit** müssen erkannt oder angegeben werden.
- Alle Schwellen (6 Spieler, 7 m/s, 5 m, Zonen) sind **Startwerte aus Überlegung, nicht aus Daten**.

## Vorschlag zur Einordnung (nur Anregung)
1. K20 und K21 früh (Woche 1/2), weil sie ohne Kalibrierung gehen und den Wert der Abdeckung zeigen.
2. Nach der Kalibrierung zuerst K1 bis K4, K6, K10 und K13 (Priorität A): wenig Annahmen, gut prüfbar.
3. K8, K9, K11, K14 (B) erst, wenn Gruppierung und Rollen belegt funktionieren.
4. K16, K17, K19 (C) zuletzt und mit offenem Hinweis auf geringe Genauigkeit.
5. Vor dem Ausbau 2 bis 3 Gespräche mit Trainern (laut Brief): Welche dieser Kennwerte würden sie überhaupt nutzen? Das ist offen.

## Technik-Roadmap (Kandidaten, vom Entwickler als Richtung bestätigt, 18.11.2026)
Reihenfolge nach Wirkung, jeweils erst nach der Basislinie aus Woche 1. Ball ist **auf später verschoben**.
Für die Grundkonstruktion (T3b/T4) wird davon **nichts** gebaut; sie muss nur so aufgebaut sein, dass diese Punkte später durch Hinzufügen möglich sind.
1. Kalibrierung mit Linien-Erkennung per Netz (Woche 2), danach Spielfeldfilter.
2. Detektor feinabstimmen (Fine-Tuning) mit vorbeschrifteten Daten aus mehreren Spielen; Testset strikt getrennt halten.
3. Beschleunigung (OpenVINO/ONNX, Quantisierung), Kacheln gezielt.
4. Re-Identification im Tracking, falls die ID-Wechsel-Zahl aus T4 zu hoch ist.
5. Teamzuordnung mit Bildmerkmalen statt nur Farbe.
6. Offen, vor jeder Umsetzung zu prüfen: Lizenz, CPU-Tauglichkeit, Datenmenge, Datenschutz (z. B. Rückennummern-OCR nicht ohne Klärung).
7. Verschoben: Ball-Erkennung, Pose-Schätzung.

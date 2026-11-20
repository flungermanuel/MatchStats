# T4 Handzählung der ID-Wechsel (Vorlage, von Hand auszufüllen)

Lauf: `data\library\spiel-001\clip1\runs\run-003` (RF-DETR Ganzbild, `track_high_score` 0,4, `track_min_hits` 3, ohne Kamerabewegung).
Material: `render\tracks.mp4` (halbe Geschwindigkeit, Box + ID) und `render\sheet_*.png` (alle 2 s).
Keine Namen, nur Rollen ("Spieler 1 = linker Außenverteidiger, helles Trikot").
Praktische Schritt-für-Schritt-Anleitung: `docs/berichte/t4-zaehlung-anleitung.md`.

## Methode (Messregel ID-Wechsel, Spezifikation v1.4)
1. Vorab 6 bis 8 Spieler wählen: nah und fern gemischt, auf mehrere Abschnitte des Clips verteilt. **Vor** dem Ansehen der IDs festlegen, nicht die "schönen" Fälle aussuchen.
2. Jeden Spieler verfolgen, solange er im Bild ist. Jeden **ID-Wechsel** notieren (Zeit, alte ID, neue ID) und jeden **Tausch** (zwei Spieler tauschen IDs).
3. **Wiedereintritt** (Spieler verlässt das Bild durch Schwenk/Zoom und kommt mit neuer ID zurück) zählt **nicht** als Wechsel, wird aber getrennt notiert.
4. Beobachtungszeit je Spieler notieren (von wann bis wann im Bild, in Sekunden).
5. Ergebnis: Wechsel pro Spieler-Minute = Summe der Wechsel / (Summe der Beobachtungszeit in Minuten). Die Summe der Beobachtungszeit steht im Bericht, nicht nur der Quotient.

Hinweis: Das ist eine Stichprobe von 6 bis 8 Spielern. Aussage "Wechsel pro Spieler-Minute", nicht "alle Spieler". Keine MOTA/IDF1 (keine beschriftete Spurreferenz).

## Die gewählten Spieler
| Nr. | Beschreibung (Rolle, Trikot) | nah/fern | von (s) | bis (s) | Beobachtungszeit (s) |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 (optional) | | | | | |
| 8 (optional) | | | | | |

## ID-Wechsel und Tausch
| Spieler | Zeit (s) | alte ID | neue ID | Art (Wechsel / Tausch) |
|---|---|---|---|---|
| | | | | |

## Wiedereintritte (zählen nicht als Wechsel)
| Spieler | Austritt (s) | Rückkehr (s) | alte ID | neue ID |
|---|---|---|---|---|
| | | | | |

## Ergebnis
- Summe Beobachtungszeit: ___ s (= ___ min)
- ID-Wechsel (inkl. Tausch): ___
- Wechsel pro Spieler-Minute: ___
- Wiedereintritte mit neuer ID: ___

## Eindruck (frei)
Was fiel auf? Wo reißen Spuren (Kreuzungen, Verdeckung, ferne Spieler, Schwenk)? Fehlende Boxen bei fernen Spielern?

## Automatische Hilfszahlen (nur Hinweis, keine Kennzahl)
Aus `summary.json` von run-003: 226 Spuren in 60 s, mittlere Spurlänge 5,4 s, Anteil "gesehen" 19,8 %. Zuschauer, Ordner und Bank erzeugen ebenfalls Spuren und verfälschen diese Zahlen (Spielfeldfilter kommt erst in Woche 2). Die Erkennungszeit lag bei 557 s (Lauf 002: 370 s bei gleicher Erkennung; Ursache der Abweichung nicht geprüft, vermutlich andere Auslastung des Laptops).

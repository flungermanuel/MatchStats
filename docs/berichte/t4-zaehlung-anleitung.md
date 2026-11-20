# Anleitung: Handzählung der ID-Wechsel (T4)

Ziel: Du füllst `docs/berichte/t4-zaehlung.md` aus. Dauer geschätzt 1 bis 1,5 Stunden (nicht gemessen). Die Methode (Messregel ID-Wechsel) steht dort und wird hier nicht geändert. Diese Anleitung sagt nur, **wie** du praktisch vorgehst.

## Was du brauchst
Alles im Ordner `data\library\spiel-001\clip1\`:
| Datei | Wofür |
|---|---|
| `clip.mp4` | Das Video **ohne** Boxen und IDs. Hier wählst du die Spieler aus. |
| `runs\run-003\render\tracks.mp4` | Das Video mit Box + ID, halbe Geschwindigkeit (60 s Clip = 120 s Video). Zum genauen Nachsehen. |
| `runs\run-003\render\sheet_NNNNNN.png` | 30 Standbilder, eines alle 2 s. Zum schnellen Überblick. |
| `docs\berichte\t4-zaehlung.md` | Hier trägst du alles ein. |

Zeit aus dem Dateinamen: `NNNNNN` ist die Bildnummer, bei 25 Bildern pro Sekunde ist `sheet_000500` = 20,0 s (steht auch oben links im Bild). Gezeichnet wird auf jedem Bild; die Erkennung selbst läuft nur auf jedem 5. Bild, dazwischen werden die Boxen überbrückt (dünne Box = überbrückt, dicke Box = gesehen).

Ein Videoplayer mit Bildschritt hilft (zum Beispiel VLC; dort geht Bild für Bild mit der Taste `E`, Geschwindigkeit mit `[` und `]`).

## Schritt 1: Spieler wählen (vor dem Ansehen der IDs)
1. Öffne `clip.mp4` (ohne IDs) und schau den Clip einmal ganz an.
2. Wähle 6 bis 8 **Spieler** nach Rolle und Trikot. Gemischt nah und fern, und verteilt auf den Clip (einige am Anfang, einige in der Mitte, einige am Ende im Bild). Nicht die schönen Fälle aussuchen.
3. Trage sie in die Tabelle "Die gewählten Spieler" ein (Rolle, Trikot, nah/fern, von/bis in Sekunden, Beobachtungszeit). Namen gehören nicht hinein.
4. Erst jetzt `tracks.mp4` und die Kontaktbögen ansehen.

Zählen **nur Spieler** der beiden Mannschaften. Ordner, Fotografen, Zuschauer, Bank und Schiedsrichter-Assistenten haben im Lauf auch IDs (im Bild `sheet_000500` zum Beispiel unten am Bildrand), gehören aber nicht in die Stichprobe.

## Schritt 2: Pro Spieler verfolgen
1. Auf dem ersten Kontaktbogen, auf dem dein Spieler im Bild ist, die **ID** ablesen (Zahl über der Box).
2. Von Bogen zu Bogen (2 s Schritte) prüfen, ob derselbe Spieler dieselbe ID trägt.
3. Ändert sich die ID: in `tracks.mp4` an die Stelle springen und die Sekunde möglichst genau bestimmen (Bildschritt). Eintragen: Zeit, alte ID, neue ID.
4. Hat die Box eine Zeit lang gefehlt und kommt mit anderer ID zurück, ist das **auch ein Wechsel** (der Spieler war die ganze Zeit im Bild). Nur wenn der Spieler wirklich aus dem Bild geht (Schwenk, Zoom), ist es ein **Wiedereintritt** und kommt in die dritte Tabelle.
5. **Tausch**: Zwei Spieler tragen plötzlich die ID des jeweils anderen. Das ist ein Eintrag mit Art "Tausch" und zählt in der Summe wie ein Wechsel (so steht es im Ergebnisfeld "inkl. Tausch").
6. Hat ein Spieler dauerhaft **keine Box** (zu klein, verdeckt): kein ID-Wechsel. Notiere es im Feld "Eindruck" und gib die Zeit, in der er nicht erkannt war, nicht als Beobachtungszeit an, wenn du sie nicht trennen kannst. Sag im Bericht, wie du es gehandhabt hast.

## Schritt 3: Ergebnis rechnen
- Beobachtungszeit je Spieler = bis minus von (Sekunden), dann alle addieren.
- Wechsel pro Spieler-Minute = Summe der Wechsel / (Summe der Beobachtungszeit in Minuten).
- Beide Summen schreibst du hin, nicht nur den Quotienten.

## Schritt 4: Eindruck (frei, 3 bis 5 Sätze)
Wo reißen Spuren? Bei Kreuzungen, Verdeckung, fernen Spielern, Schwenk? Beispiel aus meiner Durchsicht von `sheet_000500`: Mehrere Spieler im Bild haben keine Box (zum Beispiel einige weit entfernte oder verdeckte). Das ist ein Erkennungsproblem, kein ID-Problem, gehört aber in den Eindruck.

## Was ich nicht geprüft habe
- Ich habe nur `sheet_000500` angesehen, nicht alle 30 Bögen und nicht `tracks.mp4`. Dass alle Bögen so gut lesbar sind wie dieser, ist **nicht geprüft**. Die ID-Ziffern sind bei fernen Spielern klein, aber lesbar.
- Ob `tracks.mp4` bei halber Geschwindigkeit für den Bildschritt reicht, kann ich nicht sagen; sag Bescheid, wenn du etwas Feineres brauchst (zum Beispiel einen Ausschnitt in voller Größe).

## Danach
Sag mir die ausgefüllte Datei. Dann: (a) Ergebnis in `docs/berichte/t4-zaehlung.md` und `docs/architektur.md` übernehmen, (b) bei gutem Ergebnis T4 abschließen (Review, Tests, Commit-Vorschlag), (c) bei deutlich schlechtem Ergebnis T4b (Kamerabewegung) als Vorschlag an dich. Die Entscheidung über die Standardwerte (0,3/3 oder 0,4/3) bleibt bei dir.

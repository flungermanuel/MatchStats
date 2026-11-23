# 0008: Kamerabewegung wird ausgeglichen (T4b kommt)

Datum: 2026-11-23. Spezifikation v1.6.

## Was
T4b wird umgesetzt: Die Kamerabewegung (Schwenk, Zoom) wird je Bild aus dem Video geschätzt, als eigene Stufe in `camera.json` gespeichert, und der Tracker verschiebt damit seine Vorhersage. Fehlgeschlagene Schätzungen werden als `null` gespeichert. Ob der Ausgleich läuft, kommt aus dem Aufnahme-Profil (`camera_motion`) und kann per Aufruf-Argument überschrieben werden.

## Warum
Prüfung auf run-003 (clip1, nur aus `tracks.json` und `id_switch_candidates.json`, kein Video). Kamerabewegung geschätzt als Median der Verschiebung aller gesehenen Boxen zwischen zwei Erkennungsbildern:
- 83 % der 59 Kandidaten liegen in einem Fenster mit starkem Schwenk (oberste 25 % der Schritte); bei zufälligen Fenstern gleicher Länge sind es 43 %. Sehr starker Schwenk (oberste 10 %): 61 % gegenüber 23 %.
- 33 der 59 Kandidaten treten gebündelt auf (3 bis 6 Spuren reißen im selben Bild ab).
- In den ruhigen Abschnitten (0 bis 5 s, 38 bis 60 s) gibt es keinen Kandidaten.
Bild: `data/ergebnis/t4b-pruefung/kamera_vs_kandidaten.png` (nicht im Git).

Die Stichprobe aus 0007 (6 von 8 Kandidaten wirken echt) widerspricht dem nicht: Sie sagt, dass ein Wechsel passiert ist, nicht warum.

## Alternativen
- T4b streichen und mit T5 weitermachen: verworfen, weil der Schwenk nach der Prüfung die Hauptursache der Kandidaten ist.
- Nur die Zuordnung toleranter machen (größere Suchzone) ohne Schätzung: einfacher, erhöht aber Verwechslungen im Gedränge.
- Kamerabewegung aus den Boxen selbst schätzen (wie in der Prüfung): kein Video nötig, vermischt aber Spieler- und Kamerabewegung und fällt aus, wenn Spuren abreißen.

## Nachtrag nach der Umsetzung
- **Schnittstelle:** Der Tracker bekommt einen `CameraPath` (domain). Ohne Ausgleich ist das `NO_CAMERA`, ein leerer Pfad, der nichts verschiebt; dadurch gibt es im Tracker keine Sonderfälle für "keine Kamera". Die Vorhersage verschiebt die letzte Box mit der Kamerabewegung und addiert dann die Spielergeschwindigkeit; die Geschwindigkeit enthält so keine Kamerabewegung.
- **Verkettung:** `CameraPath.transform` multipliziert die Matrizen der Bilder zwischen zwei Erkennungen. Fehlt ein Glied (`null`), ist das Ergebnis unbekannt, und die Box bleibt unverschoben (kein stilles Überspringen).
- **Schätzer:** Port `CameraMotionEstimator`, Implementierung mit OpenCV; er bekommt die Bilder von der vorhandenen Videoquelle und liest das Video nicht selbst. Ergebnis in `camera.json` mit Stufen-Cache.
- **An/aus:** Setting `camera_compensation`; die Voreinstellung kommt als Daten aus `[camera_motion_presets]` in `default.toml` (fest = aus, sonst an, auch bei unbekanntem Profil).
- **Versionen:** `camera.json` startet mit 1, `summary.json` geht auf 3 (neu: `camera_compensation`, `camera_null_share`). `run.json` und `tracks.json` unverändert.
- **Ergebnis clip1 (gleiche Erkennungen):** ohne Ausgleich 59 Kandidaten (2,90 pro Spur-Minute, identisch zu run-003), mit Ausgleich 6 (0,25 pro Spur-Minute); Spuren 226 -> 73, mittlere Spurlänge 5,4 s -> 19,7 s; Anteil `null` 0 %. Die Kandidaten erfassen nur Abrisse, keine Verwechslungen: In der Stichprobe ist bei 30 s eine Spur auf einen falschen Spieler gerutscht. Die Verbesserung ist deshalb ein Indiz, keine gemessene Fehlerrate.

## Grenzen
Die Prüfung ist ein Indiz auf einem Clip. Spieler- und Kamerabewegung sind darin vermischt (Konter: alle laufen in eine Richtung, die Kamera folgt). Das Zoom-Signal ist verrauscht. Ob die Bildschätzung auf Rasen mit wenig Merkmalen zuverlässig ist, ist ungeprüft.

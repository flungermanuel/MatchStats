# 0009: Teamzuordnung nach Trikotfarbe, Basislinie T5a

Datum: 2026-11-25. Spezifikation v1.6 (T5).

## Was
- **Port `TeamClassifier`** (`application/team_classifier.py`): Er arbeitet auf **Mengen pro Clip**, nicht auf einer einzelnen Box. Eingabe: Listen von Bildern und Boxen (Box i liegt in Bild i); Ausgabe: je Box eine `TeamPrediction` (Klasse, Sicherheit) oder `(None, None)` für unbekannt. Unbekannt ist nie 0 und nie eine zufällige Klasse.
- **Farbverfahren** (`infrastructure/color_team_classifier.py`): reines NumPy, kein scikit-learn, keine Zufallszahlen. Je Box wird der obere Teil der Box (Anteil `team_upper_body_fraction`) ausgeschnitten, Rasenpixel werden per HSV-Maske entfernt, die Medianfarbe der übrigen Pixel ist das Merkmal. Ein kleines k-Means (Startpunkte nach "weitester Abstand") gruppiert alle Merkmale eines Clips.
- **Zuordnung der Gruppen:** Die **zwei größten Gruppen sind team_a und team_b**. Weitere **große** Gruppen (Anteil über `team_outlier_max_share`) gehen zum **näheren Team** (z. B. hellere und dunklere Variante desselben Trikots). **Kleine** Gruppen sind Schiedsrichter (die größere) und Torwart (die kleinere); **Torwart und Schiedsrichter werden nur über die Größe der Gruppe unterschieden**, nicht über eine Farbe.
- **Messung** (`application/team_evaluation.py`, Befehl `matchstats evaluate-teams`): Klassifiziert wird auf den **beschrifteten Boxen** des Testsets (Klassifikation getrennt von der Erkennung). Je Clip wird die **bessere Zuordnung** (A/B getauscht oder nicht; Torwart/Schiedsrichter getauscht oder nicht) anhand der Wahrheit gewählt. Das ist ein Orakel und daher **optimistisch**.
- **Bericht:** `team_report.json` (`schema_version` 1) und `team_report.md`, dazu Overlay-Bilder (Fehler zuerst, rot).
- Alle Parameter stehen mit `team_`-Präfix in `default.toml` und `domain/settings.py`.

## Warum
- Menge pro Clip: "Team A" hat keine feste Farbe. Erst über viele Boxen zeigt sich, welche Farbgruppen es gibt.
- Reines NumPy: keine neue Abhängigkeit, keine Lizenzfolgen, deterministisch und im Test mit künstlichen Daten prüfbar.
- Zwei größte Gruppen = Teams: einfachste Regel, die ohne Referenzfarben auskommt.
- Messung auf beschrifteten Boxen: Fehler der Erkennung (T3) vermischen sich nicht mit Fehlern der Teamzuordnung.

## Alternativen
- **Einzelbox-Port** (`classify(Bild, Box)`): verworfen, weil die Gruppierung über alle Boxen eines Clips läuft; ein Einzelaufruf müsste den Zustand verstecken.
- **Feste Referenzfarben** je Mannschaft: verworfen, weil das Wissen über die Trikots vorab nötig wäre und jedes neue Spiel Handarbeit braucht.
- **Embedding-Modell hinter demselben Port** (Bildmerkmale eines Modells statt Medianfarbe): bleibt möglich, weil der Port nur Mengen und Klassen kennt. Nicht jetzt, weil es Gewicht, Lizenz und Laufzeit bringt, bevor die einfache Basislinie bekannt ist.
- **scikit-learn für k-Means:** verworfen, neue Abhängigkeit für ein kleines Verfahren.

## Gemessene Basislinie (Halbzeit 1, clip1 bis clip3, `data/ergebnis/t5a_h1/team_report.md`)
Boxen: 1.352 beschriftete (Summe der Verwechslungstabelle); unbekannt 75 (zählt als falsch).

| Wert | Anteil |
|---|---|
| gesamt | 66,1 % |
| nah (Höhe >= 52,06 px, Median) | 73,1 % |
| fern | 59,2 % |
| team_a | 84,4 % |
| team_b | 66,9 % |
| Torwart | 10,5 % |
| Schiedsrichter | 0 % |

Befunde:
- Die Torwart- und Schiedsrichter-Zuordnung funktioniert **nicht**: 46 von 57 Torwart-Boxen gehen an team_a, 88 von 124 Schiedsrichter-Boxen an team_b.
- In **allen drei Clips** gibt es eine **dritte große Farbgruppe** (87 bis 133 Boxen; clip1 151/135/87/50, clip2 144/140/133/5, clip3 169/159/103/1). **Ursache offen:** Möglich sind Licht und Schatten, Zuschauer oder Ordner im Hintergrund, Gegner mit zwei Trikotfarben; geprüft ist keine davon.
- **Parameter sind geraten** (`team_*` in `default.toml`), nicht an echten Videos abgestimmt.
- **Optimistisch:** Die Zuordnung je Clip nutzt die Wahrheit. Ohne Orakel wäre die Quote niedriger.
- Ein Spiel, eine Perspektive, eine Halbzeit: keine Aussage über andere Aufnahmen.

## Entscheidung des Auftraggebers
Die Basislinie wird so committet (Stopp-Grund "Trefferquote deutlich schlecht" ausgewertet). Die Verbesserung (Torwart/Schiedsrichter, dritte Farbgruppe) wird ein Punkt in T5b oder später.

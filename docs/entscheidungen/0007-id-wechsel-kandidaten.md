# 0007: ID-Wechsel als automatische Kandidaten statt Handzählung (T4)

Datum: 2026-11-23. Spezifikation v1.5.

## Was
Die Handzählung der ID-Wechsel (T4) entfällt. Stattdessen berechnet `domain/id_switch.py` aus `tracks.json` Kandidaten: Eine Spur endet mitten im Bild, und kurz danach beginnt in der Nähe eine neue. Ergebnis: `id_switch_candidates.json`, Kennzahl "Kandidaten pro Spur-Minute" in `summary.json` und je Kandidat ein Vergleichsbild in `render/switches/`. Die Schwellen (`switch_max_gap_seconds`, `switch_max_distance_heights`) stehen in der Konfiguration.

## Warum
Die Handzählung kostet 1 bis 1,5 Stunden Zeit des Entwicklers und ist nicht wiederholbar, wenn sich Parameter ändern. Die Kandidaten-Rate lässt sich nach jeder Parameteränderung sofort neu berechnen. Die Vergleichsbilder erlauben eine schnelle Sichtprüfung.

## Alternativen
- Handzählung an 6 bis 8 Spielern (bisherige Regel): genauer, aber langsam und nicht wiederholbar.
- Beschriftete Referenzspuren: genaueste Messung, braucht ein Beschriftungswerkzeug; für Woche 5 vorgesehen.
- T4 ohne ID-Kennzahl abschließen: verworfen, weil dann die Entscheidung über T4b (Kamerabewegung) keine Zahl hätte.

## Grenzen
Indikator, keine Zählung. Zu viel gezählt: Kamerabewegung, Gedränge, Zuschauer. Zu wenig: Lücken über der Schwelle. Die Standardschwellen sind geraten. Auf run-003 wirken von 8 per Auge angesehenen Kandidaten 6 echt und 2 falsch; das ist eine grobe Einschätzung, keine Messung.

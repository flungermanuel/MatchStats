# 0003: Testset (T2): Label Studio, COCO-JSON, gleichmäßige Bildauswahl

Datum: 2026-11-16

## Was
- **Beschriftungswerkzeug:** Label Studio, lokal, installiert per pip in einer eigenen Umgebung
  `.venv-labelstudio\` (nicht in der Projektumgebung `.venv\`). Ohne Docker. Lizenz Apache 2.0.
  Nutzungsdaten aus (`COLLECT_ANALYTICS=false`), Erreichbarkeit nur über `127.0.0.1`, Daten in
  `data\labelstudio\`. Start über `tools\start_labelstudio.ps1`.
- **Format:** COCO-JSON mit Pixelwerten. Box als `[x, y, Breite, Höhe]`, Ursprung links oben.
  Vier Klassen: `team_a`, `team_b`, `goalkeeper`, `referee`.
- **Bildauswahl:** 20 Bilder pro Clip, jeweils die Mitte von 20 gleich langen Abschnitten,
  gezogen mit ffmpeg (`select`-Filter, ein Durchlauf, Bild genau nach Bildnummer). Dateiname mit
  Bildnummer (`clip<N>_f<NNNNN>.png`), dazu `manifest.json` mit Zeitpunkt und Bildnummer.
- **Keine Vorbeschriftung in T2:** Die Spezifikation erlaubt Vorbeschriften durch einen Detektor mit
  Prüfpflicht. Wir nutzen das in T2 nicht. Das ist eine strengere Umsetzung als die Spezifikation
  verlangt; die Spezifikation bleibt unverändert.
- **Ordner `tools/`:** neuer Top-Level-Ordner nur für das PowerShell-Startskript. Er enthält keinen
  Python-Code und ist kein Paket.
- **Toleranz:** Eine Box darf am Bildrand höchstens 1 Pixel überstehen (Rundung beim Export).
- **Annahme:** konstante Bildrate (CFR). Die Bildnummer ist `round(Zeit x Bildrate)`. Die Clips sind
  progressiv mit 25 fps (T0). Bei variabler Bildrate wäre die Bildnummer falsch.

## Warum
- **Lokal statt Docker:** Docker ist auf Windows ein zusätzlicher Aufwand. Mit pip in einer eigenen
  Umgebung läuft Label Studio ohne weitere Software.
- **Daten bleiben lokal:** Keine Daten an externe Dienste (CLAUDE.md). Nur `127.0.0.1` und keine
  Nutzungsdaten.
- **COCO-JSON:** weit verbreitetes Format für Objekterkennung, mit klar festgelegten Feldern, die der
  Lader streng prüfen kann.
- **Gleichmäßige Auswahl:** Die Spezifikation verlangt, dass die Bilder nicht von Hand ausgesucht
  werden, damit die Basislinie nicht geschönt ist. Abschnittsmitten sind deterministisch und
  nachvollziehbar.
- **Pixelwerte:** Die spätere Auswertung (IoU, Schwelle 0,5) rechnet in Pixeln. Pixel im Testset
  vermeiden Umrechnungen.
- **Keine Vorbeschriftung:** Ein Detektor, der die Testbilder vorab beschriftet, prägt die Boxen. Der
  spätere Detektor (T3) würde dann an Boxen gemessen, die aus ihm selbst oder einem ähnlichen Modell
  stammen. Das würde die Basislinie verzerren.

## Alternativen
- **CVAT:** mehr Funktionen, braucht aber Docker. Auf dem Entwicklungsrechner ist das der größere
  Aufwand.
- **Eigenes Format oder eigenes Werkzeug:** mehr Code, mehr Fehlerquellen, kein Gewinn für T2.
- **Zufällige Bildauswahl:** einfacher, kann aber Bilder dicht beieinander oder nur eine Spielphase
  liefern. Die Spezifikation verlangt gleichmäßig.
- **Vorbeschriften durch den Detektor:** erlaubt laut Spezifikation, verschoben auf eine spätere
  Stufe (dann mit Kennzeichnung im Bericht).

## Offen
- Das Präfix, das Label Studio vor Dateinamen setzt, und die Pixelwerte im Export sind im Code
  angenommen und noch **nicht an einer echten Exportdatei geprüft**. Der Lader ignoriert das Präfix
  über das Muster am Dateiende.
- Die Einrichtung von `.venv-labelstudio\` (Installationsbefehl) ist im README noch nicht beschrieben.
- Die Spezifikation nennt COCO-JSON und Label Studio noch als Vorschlag. Eine Anpassung liegt beim
  Auftraggeber.

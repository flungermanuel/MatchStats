# T3 Recherche: Personenerkennung auf der CPU (Entwurf)

Stand: 16.11.2026. Belegt = Quelle genannt; vermutet = eigene Schlussfolgerung, vor Nutzung messen.

## 1. Ultralytics YOLO (n/s)

| Punkt | Aussage | Status |
|---|---|---|
| Lizenz | Zwei Optionen: AGPL-3.0 oder kostenpflichtige Enterprise-Lizenz. Unter AGPL fallen auch Modelle/Trainingscode. Gilt für YOLO11 und YOLO26 gleich. | belegt: https://www.ultralytics.com/license , https://pypi.org/project/ultralytics |
| Folgen AGPL | Privat/lokal nutzen ist unproblematisch. Veröffentlichung als Portfolio (GitHub) ist möglich, wenn das ganze Projekt dann ebenfalls AGPL-3.0 ist. Weiterverteilung ohne Quellcode oder als Netzdienst ist problematisch. Rechtsberatung ist das nicht. | vermutet (Standard-AGPL-Lesart) |
| Python 3.13 | Paket 8.4.215: `requires-python >=3.8`, Abhängigkeiten torch, torchvision, opencv-python, numpy ohne 3.13-Sperre; Extra `export-openvino` (openvino, nncf). Windows: torch 2.4.0 ausgeschlossen. | belegt: https://pypi.org/pypi/ultralytics/json |
| torch-CPU-Wheels für 3.13/Windows | Meines Wissens ab torch 2.5 vorhanden; nicht geprüft. Vor Installation prüfen: `pip download torch --no-deps --index-url https://download.pytorch.org/whl/cpu` | vermutet |
| CPU-Zeit | Intel Core Ultra X7 358H (neuer als 155H), ms/Bild bei 640: YOLO26n PyTorch 29,3 / OpenVINO FP32 14,4 / INT8 10,0; YOLO26s 59,3 / 35,0 / 16,7. Eine 155H ist vermutlich langsamer. Für 1280 Eingabe ca. 4x Rechenaufwand (Annahme). | belegt (Zahlen): https://docs.ultralytics.com/integrations/openvino/ ; Rest vermutet |
| OpenVINO-Export | `pip install "ultralytics[export-openvino]"`, dann `model.export(format="openvino")`; Laden über `YOLO(ordner)`; ca. 2x schneller als PyTorch-CPU. INT8 braucht Kalibrierdaten (Mehraufwand, lohnt später). Aufwand gering. | belegt: gleiche Quelle |

Hinweis: Der Detektor muss ohnehin hinter dem Port in `infrastructure/` liegen (Projektregel).

## 2. RF-DETR (Roboflow, Apache 2.0)

| Punkt | Aussage | Status |
|---|---|---|
| Version / Python | `rfdetr` 1.12.1 (12.11.2026), `requires-python >=3.10`, Klassifizierer 3.10 bis 3.14 inkl. 3.13 | belegt: https://pypi.org/pypi/rfdetr/json |
| Abhängigkeiten (Kern) | torch>=2.2, torchvision, numpy, requests, tqdm, transformers 5.x, pydantic, supervision>=0.29, pyDeprecate. opencv nur im Extra `stream`. ONNX/OpenVINO über Extra (`onnx`, `openvino`). Installationsgröße (torch + transformers) groß, geschätzt 1 bis 2 GB. | belegt (Liste); Größe vermutet |
| Lizenz | Nano, Small, Medium, Large: Apache 2.0. XL/2XL: eigene Lizenz (PML 1.0), nicht nötig. | belegt: https://rfdetr.roboflow.com/latest/learn/run/detection/ |
| COCO-Gewichte | Vortrainiert auf COCO (80 Klassen, Person enthalten), `COCO_CLASSES` im Paket. | belegt: gleiche Quelle |
| Größen | Nano 48,4 AP, 384x384; Small 53,0 AP, 512x512; Medium 54,7 AP, 576x576 (COCO, kleine Eingaben). | belegt: gleiche Quelle |
| CPU-Geschwindigkeit | Veröffentlichte Latenzen (2,3 / 3,5 / 4,4 ms) sind T4-GPU mit TensorRT, für uns nicht aussagekräftig. Keine CPU-Zahlen gefunden. Transformer mit 30 M Parametern, vermutlich langsamer als YOLO-n/s auf CPU. Feste kleine Eingabe (384 bis 576) schadet bei weit entfernten Spielern. | vermutet, messen |
| Windows | Keine Besonderheiten gefunden; CUDA-Extras nur Linux (irrelevant). Dokumentation zu CPU-Betrieb knapp (`compile=False`). | belegt (Extras), Rest unklar |

## 3. Kachel-Inferenz (SAHI-Ansatz)

SAHI (MIT-Lizenz, Python >=3.10, nutzt opencv/shapely) ist eine mögliche Bibliothek; der Ansatz lässt sich auch selbst in ca. 50 Zeilen schreiben (Kacheln zuschneiden, Boxen zurückrechnen, zusammenführen). Letzteres hält die Schichtenregel (kein SAHI im Kern) einfach. Quelle: https://obss.github.io/sahi/guides/sliced-inference/

- Kachelgröße = Trainingsauflösung des Modells (bei YOLO 512 bis 640). Überlappung Start 0,2, bei Randverlusten 0,3 bis 0,4. Standard-Zusammenführung GreedyNMM (Boxen mitteln), Alternative NMS; Metrik IOS (aggressiver) oder IOU, Schwelle 0,5. Optional zusätzlich Gesamtbild (bringt große/nahe Personen ohne Zerschneiden). Alles belegt (SAHI-Doku). Für Fußball-Personen mit NMS/IOU 0,5 zu starten ist vermutet sinnvoll, weil sich Spieler im Gedränge überlappen (IOS könnte sie fälschlich verschmelzen).
- Rechenbeispiel 1920x1080 (eigene Rechnung): 640er Kacheln, Überlappung 0,2 = 4x2 = 8 Kacheln (+1 Gesamtbild = 9). 960x540er Kacheln, Überlappung 0,2 = 3x3 = 9 Kacheln. Kosten ca. 8 bis 9 mal ein Einzelbild bei 640.
- Zeitschätzung (vermutet): YOLO-n OpenVINO ca. 15 ms x 9 = 130 bis 250 ms/Bild auf 155H; YOLO-s ca. 35 ms x 9 = 300 bis 500 ms. Bei `detect_every=5` (5 Detektionen/s bei 25 fps) = ca. 1 bis 2,5 s Rechenzeit je Videosekunde, machbar.
- Kachelgrenzen: Spieler am Rand werden doppelt/halb erkannt; Überlappung größer als die Spielergröße in Pixeln (ca. 60 bis 150 px) wählen.

## 4. Empfehlung

Erst messen (60 Testbilder, Metriken aus Spezifikation, nah/fern getrennt):
1. YOLO (n und s, COCO, Klasse person) mit OpenVINO, Eingabe 640 ganzes Bild vs. 1280 vs. Kacheln 640/0,2. Das ist die schnellste Baseline mit besten CPU-Belegen.
2. RF-DETR Small/Medium auf Ganzbild und Kacheln als Apache-2.0-Alternative; CPU-Zeit unbekannt, daher nur kurzer Test.
3. Erwartung (vermutet): Ganzbild 640 verfehlt ferne Spieler; Kacheln erhöhen Recall deutlich, kosten Faktor ca. 9.

Risiken:
- Python 3.13: rfdetr belegt kompatibel; ultralytics ohne Sperre; torch-Wheels 3.13 und openvino/nncf auf 3.13 vorab prüfen. Fallback: 3.12-Umgebung (CLAUDE.md erlaubt mindestens 3.12).
- Installationsgröße: torch (CPU) plus Extras mehrere GB; beide Detektoren parallel in einer Umgebung doppelt Abhängigkeiten (transformers).
- Zeit bei 60 Bildern: YOLO-s mit Kacheln etwa 20 bis 30 s, RF-DETR unbekannt, wohl im Minutenbereich.
- Modellgewichte werden beim ersten Lauf heruntergeladen (Netzzugriff, Lizenz der Gewichte: Ultralytics AGPL, RF-DETR Apache).

Vorher klären:
1. Lizenz: Wird das Repo öffentlich? Falls ja: AGPL-3.0 für das Projekt akzeptieren, oder RF-DETR als Standard wählen.
2. Python 3.13 bleibt, oder 3.12 als Fallback erlaubt?
3. Speicherplatz/Download-Größe (mehrere GB) akzeptabel?
4. Zielzeit: Wie viel Rechenzeit pro Spielminute ist okay (bestimmt Kacheln, n vs. s, INT8)?
5. SAHI als Abhängigkeit oder eigene Kachel-Funktion?

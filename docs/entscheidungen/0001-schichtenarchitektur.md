# 0001: Schichtenarchitektur und Werkzeuge (T1)

Datum: 2026-11-12

## Was
- Vier Schichten: `domain` <- `application` <- `infrastructure` <- `cli`. Abhängigkeiten zeigen
  nur nach innen. Ein automatischer Test (`tests/test_architecture.py`) erzwingt das.
- Schnittstellen (Ports, z. B. Detektor) liegen in `application/`, Implementierungen in
  `infrastructure/`.
- Werkzeuge: `venv` + `pip`, `pyproject.toml` (setuptools, src-Layout), `pytest`, `ruff`,
  `argparse`, Konfiguration als TOML (`tomllib` aus der Standardbibliothek). Keine
  Laufzeit-Abhängigkeiten in T1.
- Python 3.13 (3.14 ist installiert, aber für PyTorch/OpenVINO noch riskant).

## Warum
- Später kommen Weboberfläche, Dienst, Warteschlange und Agenten dazu. Mit getrennten Schichten
  lässt sich z. B. die CLI durch eine API ersetzen, ohne die Pipeline anzufassen.
- Detektor austauschbar (YOLO AGPL-3.0, RF-DETR Apache 2.0): Die Pipeline kennt nur die
  Schnittstelle.
- Kennzahlen werden aus gespeicherten Spuren berechnet, nicht aus dem Video: Speichern liegt in
  der Infrastruktur, Rechnen in application/domain.

## Alternativen
- Flache Struktur ohne Schichten: schneller am Anfang, aber später schwer zu trennen.
- `uv`/`poetry`: bequemer, aber ein weiteres Werkzeug ohne Nutzen für T1.
- YAML-Konfiguration: bräuchte eine Zusatzbibliothek; TOML ist in Python eingebaut.
- Import-Linter-Bibliothek für den Schichtentest: nicht nötig, ein kleiner AST-Test genügt.

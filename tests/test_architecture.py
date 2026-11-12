"""Schichtentest: Abhängigkeiten dürfen nur "nach innen" zeigen.

    cli  ->  infrastructure  ->  application  ->  domain

- domain:         kennt nur sich selbst (reine Datentypen und Regeln)
- application:    darf domain nutzen (Pipeline-Ablauf, Schnittstellen/Ports)
- infrastructure: darf domain und application nutzen (Dateien, Video, Modelle)
- cli:            darf alles (verdrahtet die Schichten)
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "matchstats"

ERLAUBT = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure"},
}


def _matchstats_imports(path: Path) -> set[str]:
    """Liefert die Schichten, die eine Datei aus matchstats importiert."""
    layer_of_file = path.relative_to(SRC).parts[0]
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            # relative Imports wie "from ..domain import x" -> Ziel aus Pfad ableiten
            parts = (node.module or "").split(".")
            found.add(parts[0] if node.level >= 2 and parts[0] else layer_of_file)
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[0] == "matchstats" and len(parts) > 1:
                found.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "matchstats" and len(parts) > 1:
                    found.add(parts[1])
    return found


def test_layers_only_depend_inward():
    violations = []
    for layer, allowed in ERLAUBT.items():
        for path in (SRC / layer).rglob("*.py"):
            illegal = _matchstats_imports(path) - allowed
            if illegal:
                violations.append(f"{path.relative_to(SRC)} importiert {sorted(illegal)}")
    assert not violations, "\n".join(violations)


def test_detector_libraries_stay_in_infrastructure():
    """Detektor-spezifischer Code (YOLO, RF-DETR) gehört nur nach infrastructure."""
    verboten = {"ultralytics", "rfdetr"}
    violations = []
    for layer in ("domain", "application", "cli.py"):
        target = SRC / layer
        files = [target] if target.is_file() else list(target.rglob("*.py"))
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                if verboten & set(names):
                    violations.append(str(path.relative_to(SRC)))
    assert not violations, violations

"""Kommandozeile: `matchstats run clip.mp4 --out ergebnis/`. Verdrahtet die Schichten."""

import argparse
import sys
from pathlib import Path

from matchstats.application.pipeline import run_pipeline
from matchstats.infrastructure.config_loader import load_settings
from matchstats.infrastructure.result_store import save_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matchstats")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Ein Video verarbeiten")
    run.add_argument("clip", type=Path, help="Pfad zum Video (z. B. clip.mp4)")
    run.add_argument("--out", type=Path, required=True, help="Ausgabeordner (z. B. ergebnis/)")
    run.add_argument("--config", type=Path, default=None, help="Eigene Konfiguration (TOML)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.clip.is_file():
        print(f"Fehler: Video nicht gefunden: {args.clip}", file=sys.stderr)
        return 2

    settings = load_settings(args.config)
    result = run_pipeline(args.clip.name, settings)
    target = save_result(result, args.out)
    print(f"Fertig: {target}")
    return 0


def console_main() -> None:
    sys.exit(main())

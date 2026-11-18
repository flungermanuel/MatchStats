"""Kommandozeile: `run`, `sample-frames` und `evaluate`. Verdrahtet die Schichten."""

import argparse
import sys
from pathlib import Path

from matchstats.application.pipeline import run_pipeline
from matchstats.infrastructure.config_loader import load_settings
from matchstats.infrastructure.evaluation_job import DETECTOR_NAMES, run_evaluation
from matchstats.infrastructure.frame_sampler import FrameSamplingError, sample_frames
from matchstats.infrastructure.result_store import save_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matchstats")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Ein Video verarbeiten")
    run.add_argument("clip", type=Path, help="Pfad zum Video (z. B. clip.mp4)")
    run.add_argument("--out", type=Path, required=True, help="Ausgabeordner (z. B. ergebnis/)")
    run.add_argument("--config", type=Path, default=None, help="Eigene Konfiguration (TOML)")

    sample = sub.add_parser("sample-frames", help="Testbilder gleichmäßig aus Videos ziehen")
    sample.add_argument("clips", type=Path, nargs="+", help="Ein oder mehrere Videos")
    sample.add_argument("--out", type=Path, required=True, help="Ausgabeordner für PNGs")
    sample.add_argument("--count", type=int, default=None, help="Bilder pro Clip")
    sample.add_argument("--config", type=Path, default=None, help="Eigene Konfiguration (TOML)")

    evaluate = sub.add_parser("evaluate", help="Detektoren auf dem beschrifteten Testset messen")
    evaluate.add_argument("--testset", type=Path, default=Path("data/testset/coco.json"))
    evaluate.add_argument("--images", type=Path, default=Path("data/testset/images"))
    evaluate.add_argument("--out", type=Path, required=True, help="Ausgabeordner für den Bericht")
    evaluate.add_argument("--detectors", nargs="+", choices=DETECTOR_NAMES, default=DETECTOR_NAMES)
    evaluate.add_argument("--overlays", type=int, default=6, help="Beispielbilder je Variante")
    evaluate.add_argument("--config", type=Path, default=None, help="Eigene Konfiguration (TOML)")
    return parser


def _run_command(args: argparse.Namespace) -> int:
    if not args.clip.is_file():
        print(f"Fehler: Video nicht gefunden: {args.clip}", file=sys.stderr)
        return 2

    settings = load_settings(args.config)
    result = run_pipeline(args.clip.name, settings)
    target = save_result(result, args.out)
    print(f"Fertig: {target}")
    return 0


def _sample_frames_command(args: argparse.Namespace) -> int:
    for clip in args.clips:
        if not clip.is_file():
            print(f"Fehler: Video nicht gefunden: {clip}", file=sys.stderr)
            return 2

    count = args.count if args.count is not None else load_settings(args.config).frames_per_clip
    try:
        for clip in args.clips:
            frames = sample_frames(clip, args.out, count)
            print(f"{clip.name}: {len(frames)} Bilder nach {args.out}")
    except (FrameSamplingError, FileNotFoundError) as err:
        print(f"Fehler beim Ziehen der Bilder: {err}", file=sys.stderr)
        return 2
    return 0


def _evaluate_command(args: argparse.Namespace) -> int:
    for path in (args.testset, args.images):
        if not path.exists():
            print(f"Fehler: nicht gefunden: {path}", file=sys.stderr)
            return 2
    run_evaluation(
        args.testset, args.images, args.out, load_settings(args.config),
        tuple(args.detectors), args.overlays,
    )  # fmt: skip
    print(f"Fertig: {args.out / 'report.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sample-frames":
        return _sample_frames_command(args)
    if args.command == "evaluate":
        return _evaluate_command(args)
    return _run_command(args)


def console_main() -> None:
    sys.exit(main())

"""Kommandozeile: run, sample-frames, evaluate, match, clip, track. Verdrahtet die Schichten."""

import argparse
import sys
from pathlib import Path

from matchstats.application.library import LibraryError
from matchstats.application.pipeline import run_pipeline
from matchstats.domain.library import ANGLES, CAMERA_MOTIONS, Match, RecordingProfile
from matchstats.infrastructure.clip_table import format_clip_table
from matchstats.infrastructure.config_loader import load_settings
from matchstats.infrastructure.evaluation_job import (
    DETECTOR_NAMES,
    run_evaluation,
    run_library_evaluation,
)
from matchstats.infrastructure.file_library import FileLibrary
from matchstats.infrastructure.frame_sampler import FrameSamplingError, sample_frames
from matchstats.infrastructure.result_store import save_result
from matchstats.infrastructure.testset_loader import TestsetFormatError

DEFAULT_LIBRARY = Path("data/library")
# Gleich wie tracking_job.VARIANTS; hier fest, damit cv2/scipy nicht beim Import geladen werden.
TRACK_VARIANTS = ("whole", "tiles")


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
    evaluate.add_argument("--game", default=None, help="Spiel-ID: alle Clips einer Halbzeit messen")
    evaluate.add_argument("--half", type=int, choices=(1, 2), help="Halbzeit (mit --game)")
    _add_library_option(evaluate)

    match = sub.add_parser("match", help="Spiele der Bibliothek verwalten")
    match_sub = match.add_subparsers(dest="action", required=True)
    match_add = match_sub.add_parser("add", help="Neues Spiel anlegen")
    match_add.add_argument("id", help="Spiel-ID, z. B. spiel-001")
    match_add.add_argument("--name", required=True)
    match_add.add_argument("--date", default=None, help="Datum (JJJJ-MM-TT)")
    match_add.add_argument("--notes", default="")
    _add_library_option(match_add)

    clip = sub.add_parser("clip", help="Clips der Bibliothek verwalten")
    clip_sub = clip.add_subparsers(dest="action", required=True)
    clip_import = clip_sub.add_parser("import", help="Video als Clip in ein Spiel kopieren")
    clip_import.add_argument("video", type=Path)
    clip_import.add_argument("--game", required=True, help="Spiel-ID")
    clip_import.add_argument("--clip", required=True, help="Clip-ID, z. B. clip1")
    clip_import.add_argument("--half", type=int, choices=(1, 2), default=None)
    clip_import.add_argument("--angle", choices=ANGLES, default=None)
    clip_import.add_argument("--camera-motion", choices=CAMERA_MOTIONS, default=None)
    clip_import.add_argument("--notes", default="")
    _add_library_option(clip_import)
    clip_list = clip_sub.add_parser("list", help="Clips eines Spiels auflisten")
    clip_list.add_argument("--game", required=True, help="Spiel-ID")
    clip_list.add_argument("--half", type=int, choices=(1, 2), default=None)
    _add_library_option(clip_list)

    track = sub.add_parser("track", help="Personen erkennen und zu Spuren verbinden")
    track.add_argument("--game", required=True, help="Spiel-ID")
    track.add_argument("--clip", required=True, help="Clip-ID")
    track.add_argument(
        "--variant", choices=TRACK_VARIANTS, default="whole", help="Ganzbild oder Kacheln"
    )
    track.add_argument("--run", default=None, help="Vorhandenen Lauf weiterverwenden (run-NNN)")
    track.add_argument("--no-render", action="store_true", help="Kein Video und keine Kontaktbögen")
    track.add_argument("--config", type=Path, default=None, help="Eigene Konfiguration (TOML)")
    track.add_argument(
        "--camera",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Kameraausgleich erzwingen oder abschalten (sonst gilt das Aufnahme-Profil)",
    )
    _add_library_option(track)
    return parser


def _add_library_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="Bibliotheksordner")


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
    if args.game is not None:
        return _evaluate_game_command(args)
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


def _evaluate_game_command(args: argparse.Namespace) -> int:
    if args.half is None:
        print("Fehler: --game braucht --half", file=sys.stderr)
        return 2
    try:
        run_library_evaluation(
            FileLibrary(args.library), args.game, args.half, args.out, load_settings(args.config),
            tuple(args.detectors), args.overlays,
        )  # fmt: skip
    except (LibraryError, TestsetFormatError, ValueError, OSError) as err:
        # ValueError: ungültige Konfiguration; OSError: fehlende Bild- oder Videodatei
        print(f"Fehler: {err}", file=sys.stderr)
        return 2
    print(f"Fertig: {args.out / 'report.md'}")
    return 0


def _match_command(args: argparse.Namespace) -> int:
    try:
        FileLibrary(args.library).add_match(
            Match(id=args.id, name=args.name, date=args.date, notes=args.notes)
        )
    except LibraryError as err:
        print(f"Fehler: {err}", file=sys.stderr)
        return 2
    print(f"Spiel {args.id} angelegt")
    return 0


def _clip_command(args: argparse.Namespace) -> int:
    library = FileLibrary(args.library)
    try:
        if args.action == "import":
            profile = RecordingProfile(args.angle, args.camera_motion, args.notes)
            clip = library.import_clip(args.game, args.video, args.clip, args.half, profile, {})
            print(f"Clip {clip.id} importiert nach {library.clip_dir(args.game, clip.id)}")
        else:
            print(format_clip_table(library.list_clips(args.game, half=args.half)))
    except LibraryError as err:
        print(f"Fehler: {err}", file=sys.stderr)
        return 2
    return 0


def _track_command(args: argparse.Namespace) -> int:
    # Erst hier importieren: cv2/scipy stehen nur im Extra "track".
    from matchstats.infrastructure.tracking_job import run_track_job

    if args.run is not None and args.config is not None:
        print("Warnung: --config wird mit --run ignoriert (Einstellungen des Laufs gelten)",
              file=sys.stderr)  # fmt: skip
    if args.run is not None and args.camera is not None:
        print("Warnung: --camera/--no-camera wird mit --run ignoriert "
              "(Einstellungen des Laufs gelten)", file=sys.stderr)  # fmt: skip
    try:
        job = run_track_job(
            FileLibrary(args.library), args.game, args.clip, args.variant,
            args.config, args.run, render=not args.no_render,
            overrides=None if args.camera is None else {"camera_compensation": args.camera},
        )  # fmt: skip
    except (LibraryError, ValueError, OSError) as err:
        print(f"Fehler: {err}", file=sys.stderr)
        return 2
    summary = job.summary
    print(f"Lauf {job.run_id}: {job.run_dir}")
    print(
        f"Spuren: {summary['track_count']}, pro Minute: {summary['tracks_per_minute']}, "
        f"mittlere Länge (s): {summary['mean_track_seconds']}, "
        f"gesehen: {summary['visible_share']}"
    )
    print(
        f"Kandidaten für ID-Wechsel: {summary['id_switch_candidates']}, "
        f"pro Spur-Minute: {summary['id_switch_candidates_per_track_minute']}"
    )
    seconds = summary["stage_seconds"]
    print(
        f"Laufzeit (s): Erkennung {seconds['detection']}, Kamera {seconds['camera']}, "
        f"Tracking {seconds['tracking']}, "
        f"Darstellung {seconds['render']}; "
        f"Erkennung wiederverwendet: {summary['detections_reused']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sample-frames":
        return _sample_frames_command(args)
    if args.command == "evaluate":
        return _evaluate_command(args)
    if args.command == "match":
        return _match_command(args)
    if args.command == "clip":
        return _clip_command(args)
    if args.command == "track":
        return _track_command(args)
    return _run_command(args)


def console_main() -> None:
    sys.exit(main())

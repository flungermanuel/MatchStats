"""Zieht gleichmäßig verteilte Einzelbilder (PNG) aus einem Clip, per ffprobe/ffmpeg.

Das Video wird nur gestreamt (ein Durchlauf), nie komplett in den Speicher geladen.
Bildgenau wird über den select-Filter nach Bildnummer erreicht, nicht über Zeit-Seeking.

Annahme: konstante Bildrate (CFR). Die Bildnummer ist round(Zeit * fps); die T0-Clips sind
progressiv mit 25 fps. `time_s` ist die Soll-Zeit, nicht die gemessene Zeitmarke des Bildes.
Ein Fehlschlag lässt vorhandene Bilder und das Manifest unverändert.
"""

import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from matchstats.domain.sampling import SampledFrame, frame_number, uniform_timestamps

MANIFEST = "manifest.json"


class FrameSamplingError(RuntimeError):
    """Bilder konnten nicht aus dem Clip gezogen werden."""


def _parse_number(value: object, what: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise FrameSamplingError(f"Ungültiger Wert für {what}: {value!r}") from err
    if not math.isfinite(number):
        raise FrameSamplingError(f"Ungültiger Wert für {what}: {value!r}")
    return number


def _probe(clip: Path) -> tuple[float, float]:
    """Liefert (Dauer in Sekunden, Bilder pro Sekunde) des ersten Videostreams."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=avg_frame_rate,duration:format=duration",
                "-of", "json", str(clip),
            ],
            capture_output=True,
            text=True,
            check=True,
        )  # fmt: skip
        info = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as err:
        raise FrameSamplingError(f"ffprobe ist fehlgeschlagen für {clip.name}: {err}") from err

    streams = info.get("streams") if isinstance(info, dict) else None
    if not streams or not isinstance(streams[0], dict):
        raise FrameSamplingError(f"{clip.name} enthält keinen Videostream")
    stream = streams[0]

    rate = stream.get("avg_frame_rate")
    if not isinstance(rate, str):
        raise FrameSamplingError(f"{clip.name}: Bildrate fehlt")
    num, _, den = rate.partition("/")
    denominator = _parse_number(den or 1, "Bildrate")
    fps = _parse_number(num, "Bildrate") / denominator if denominator else 0.0
    if fps <= 0:
        raise FrameSamplingError(f"{clip.name}: Bildrate unbekannt ({rate})")

    raw_duration = stream.get("duration")
    if raw_duration in (None, "N/A"):
        fmt = info.get("format")
        raw_duration = fmt.get("duration") if isinstance(fmt, dict) else None
    duration = _parse_number(raw_duration, "Dauer")
    if duration <= 0:
        raise FrameSamplingError(f"{clip.name}: Dauer unbekannt ({raw_duration})")
    return duration, fps


def _extract(clip: Path, numbers: list[int], tmp_dir: Path) -> list[Path]:
    """Schreibt die Bilder mit den gegebenen (aufsteigenden) Nummern als PNGs nach tmp_dir."""
    expr = "+".join(f"eq(n\\,{n})" for n in numbers)
    pattern = tmp_dir / "%05d.png"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
                "-vf", f"select='{expr}'", "-fps_mode", "passthrough",
                "-start_number", "0", str(pattern),
            ],
            check=True,
        )  # fmt: skip
    except (OSError, subprocess.SubprocessError) as err:
        raise FrameSamplingError(f"ffmpeg ist fehlgeschlagen für {clip.name}: {err}") from err
    files = [tmp_dir / f"{i:05d}.png" for i in range(len(numbers))]
    missing = [n for n, f in zip(numbers, files, strict=True) if not f.is_file()]
    if missing:
        raise FrameSamplingError(f"Bilder {missing} konnten nicht aus {clip.name} gelesen werden")
    return files


def _read_manifest(out_dir: Path) -> list[dict]:
    path = out_dir / MANIFEST
    if not path.is_file():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ValueError("keine Liste von Einträgen")
    except (OSError, ValueError) as err:
        raise FrameSamplingError(f"Manifest {path} ist nicht lesbar: {err}") from err
    return entries


def _write_manifest(
    out_dir: Path, entries: list[dict], clip_name: str, frames: list[SampledFrame]
) -> None:
    """Ersetzt die Einträge dieses Clips im Manifest, andere Clips bleiben erhalten."""
    entries = [e for e in entries if e.get("clip") != clip_name]
    entries += [
        {
            "clip": f.clip,
            "time_s": f.time_s,
            "frame_number": f.frame_number,
            "file_name": f.file_name,
        }
        for f in frames
    ]
    tmp = out_dir / (MANIFEST + ".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(out_dir / MANIFEST)


def sample_frames(clip: Path, out_dir: Path, count: int) -> list[SampledFrame]:
    """Zieht `count` gleichmäßig verteilte Bilder aus dem Clip nach `out_dir`.

    Wirft FileNotFoundError (Clip fehlt) oder FrameSamplingError (alles andere).
    """
    clip = Path(clip)
    out_dir = Path(out_dir)
    if not clip.is_file():
        raise FileNotFoundError(f"Video nicht gefunden: {clip}")

    duration, fps = _probe(clip)
    stamps = uniform_timestamps(duration, count)
    numbers = [frame_number(t, fps) for t in stamps]
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        old_entries = _read_manifest(out_dir)
        tmp_dir = Path(tempfile.mkdtemp(prefix="_tmp_", dir=out_dir))
    except OSError as err:
        raise FrameSamplingError(f"Ausgabeordner nicht nutzbar: {err}") from err

    try:
        temp_files = _extract(clip, numbers, tmp_dir)

        # Erst jetzt, nach vollem Erfolg, die alten Bilder dieses Clips ersetzen.
        old_pattern = re.compile(re.escape(clip.stem) + r"_f\d{5}\.png")
        for old in out_dir.iterdir():
            if old.is_file() and old_pattern.fullmatch(old.name):
                old.unlink()

        frames: list[SampledFrame] = []
        for stamp, number, temp in zip(stamps, numbers, temp_files, strict=True):
            name = f"{clip.stem}_f{number:05d}.png"
            temp.replace(out_dir / name)
            frames.append(SampledFrame(clip.name, stamp, number, name))
        _write_manifest(out_dir, old_entries, clip.name, frames)
    except OSError as err:
        raise FrameSamplingError(f"Dateifehler beim Schreiben der Bilder: {err}") from err
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return frames

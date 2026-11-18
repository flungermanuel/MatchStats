"""Stellt Clips als einfache Texttabelle dar (für `matchstats clip list`)."""

from matchstats.domain.library import Clip

_HEADER = ("Clip", "Halbzeit", "Perspektive", "Kamera", "fps", "Auflösung", "Dauer (s)")


def _text(value: object) -> str:
    return "-" if value is None else str(value)  # unbekannt bleibt sichtbar unbekannt


def format_clip_table(clips: list[Clip]) -> str:
    rows = [
        (
            c.id, _text(c.half), _text(c.profile.angle), _text(c.profile.camera_motion),
            f"{c.fps:g}", f"{c.width}x{c.height}", f"{c.duration_s:.1f}",
        )
        for c in clips
    ]  # fmt: skip
    table = [_HEADER, *rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(_HEADER))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)) for row in table]
    return "\n".join(lines)

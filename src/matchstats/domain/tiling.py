"""Kachel-Geometrie: Bild in überlappende Rechtecke zerlegen (rein, keine I/O)."""


def _starts(length: int, tile: int, overlap: float) -> list[int]:
    if length <= tile:
        return [0]
    step = max(1, int(tile * (1 - overlap)))
    starts = list(range(0, length - tile, step))
    starts.append(length - tile)  # letzte Kachel schließt bündig mit dem Bildrand ab
    return starts


def tile_rects(
    width: int, height: int, tile_size: int, overlap: float
) -> list[tuple[int, int, int, int]]:
    """Liefert Kacheln als (x, y, Breite, Höhe). `overlap` ist der Überlappungsanteil (0 bis <1).

    Ist das Bild kleiner als die Kachel, gibt es eine einzige Kachel in Bildgröße.
    """
    if not 0 <= overlap < 1:
        raise ValueError("overlap muss in [0, 1) liegen")
    if tile_size < 1:
        raise ValueError("tile_size muss mindestens 1 sein")
    tile_w, tile_h = min(tile_size, width), min(tile_size, height)
    return [
        (x, y, tile_w, tile_h)
        for y in _starts(height, tile_h, overlap)
        for x in _starts(width, tile_w, overlap)
    ]

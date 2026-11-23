"""Hilfsskript (T4b): Kamerabewegung über die Zeit und ID-Wechsel-Kandidaten als Bild.

Liest nur Dateien eines Laufs mit Kameraausgleich (camera.json) und optional die Kandidaten
eines Vergleichslaufs ohne Ausgleich. Nicht Teil der Pipeline.

Aufruf:
    python tools/plot_camera_motion.py <lauf_mit_kamera> [<lauf_ohne_kamera>] --out bild.png
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidates(run_dir: Path) -> list[dict]:
    path = run_dir / "id_switch_candidates.json"
    return _load(path)["candidates"] if path.exists() else []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("with_camera", type=Path)
    parser.add_argument("without_camera", type=Path, nargs="?")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    camera = _load(args.with_camera / "camera.json")
    fps = float(camera["fps"])
    t, dx, dy, zoom, unknown = [], [], [], [], []
    for entry in camera["frames"]:
        time = entry["frame"] / fps
        m = entry["matrix"]
        if m is None:
            unknown.append(time)  # fehlend bleibt fehlend: Lücke in der Kurve
            t.append(time)
            dx.append(math.nan)
            dy.append(math.nan)
            zoom.append(math.nan)
            continue
        t.append(time)
        dx.append(m[0][2])
        dy.append(m[1][2])
        zoom.append(math.sqrt(abs(m[0][0] * m[1][1] - m[0][1] * m[1][0])))

    rows = 3 if args.without_camera else 2
    fig, ax = plt.subplots(rows, 1, figsize=(12, 2.6 * rows + 1), sharex=True)
    ax[0].plot(t, dx, lw=0.8, label="dx (px je Bild)")
    ax[0].plot(t, dy, lw=0.8, label="dy (px je Bild)")
    for u in unknown:
        ax[0].axvline(u, color="red", alpha=0.08, lw=1)
    ax[0].set_ylabel("Schwenk")
    ax[0].legend(loc="upper right")
    ax[1].plot(t, zoom, lw=0.8, color="#a85f1f")
    ax[1].axhline(1.0, color="grey", lw=0.5)
    ax[1].set_ylabel("Zoomfaktor je Bild")

    if args.without_camera:
        ax[2].set_ylim(0, 2)
        for c in _candidates(args.without_camera):
            ax[2].axvspan(c["end_frame"] / fps, c["start_frame"] / fps, 0.5, 1.0, color="grey")
        for c in _candidates(args.with_camera):
            ax[2].axvspan(c["end_frame"] / fps, c["start_frame"] / fps, 0.0, 0.5, color="red")
        n_without = len(_candidates(args.without_camera))
        n_with = len(_candidates(args.with_camera))
        ax[2].set_yticks([0.5, 1.5], [f"mit ({n_with})", f"ohne ({n_without})"])
        ax[2].set_ylabel("Kandidaten")
    ax[-1].set_xlabel("Zeit im Clip (s); rote Striche oben: Schätzung fehlgeschlagen (null)")
    fig.suptitle("Geschätzte Kamerabewegung und ID-Wechsel-Kandidaten")
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=110)
    print(f"Bild: {args.out}")


if __name__ == "__main__":
    main()

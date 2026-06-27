"""Measure the trainer party-indicator strip across fixtures to find a
rain-robust signal. Prints edge_frac (current signal), mean saturation, and a
compact-blob count for each fixture's strip, and saves the strip crops."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from battle.battle_reader import load_calibration, read_enemy_bars  # noqa: E402

CAL = load_calibration(ROOT / "calibration.toml")
FIXTURES = ROOT / "tests" / "fixtures"
OUT = ROOT / "scripts" / "_trainer_strips"
OUT.mkdir(exist_ok=True)

NAMES = [
    "full_health_trainer_battle_no_status.png",
    "full_health_trainer_battle_poisoned.png",
    "full_health_no_status.png",
    "full_health_water.png",
    "red_health_no_status_cave.png",
    "1920x1080_resolution.png",
    "double_battle_no_status.png",
]


def compact_blobs(strip_bgr: np.ndarray) -> int:
    gray = cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    n = 0
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w < 4 or h < 4:
            continue
        ar = w / h
        if 0.4 <= ar <= 2.6 and 16 <= w * h <= 1500:
            n += 1
    return n


def main() -> None:
    cal = CAL.trainer
    for name in NAMES:
        p = FIX / name
        frame = cv2.imread(str(p))
        if frame is None:
            print(f"{name:45} MISSING")
            continue
        bars = read_enemy_bars(frame, CAL)
        if not bars:
            print(f"{name:45} no bars")
            continue
        bar = bars[0]
        y0, y1 = bar.y + cal.dy0, bar.y + cal.dy1
        x0, x1 = bar.x, bar.x + cal.width_px
        strip = frame[y0:y1, x0:x1]
        gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_frac = float(np.mean(edges)) / 255.0
        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
        hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        # Hue diversity: how many 10-degree hue bins hold a meaningful share of the
        # colourful (saturated, not-too-dark) pixels. A uniform sky or blue+white
        # rain lights up 1-2 bins; a Pokemon mini-sprite spans many.
        colourful = (sat > 90) & (val > 60)
        total = int(np.count_nonzero(colourful))
        hue_bins = 0
        if total:
            hist = np.bincount((hue[colourful] // 10).astype(int), minlength=18)
            hue_bins = int(np.count_nonzero(hist >= max(8, 0.02 * total)))
        blobs = compact_blobs(strip)
        cv2.imwrite(str(OUT / f"strip_{name}"), strip)
        kind = "TRAINER" if "trainer" in name else "wild   "
        print(
            f"{kind} {name:45} bar=({bar.x:4},{bar.y:4}) "
            f"edge={edge_frac:.4f} blobs={blobs} hue_bins={hue_bins}"
        )


if __name__ == "__main__":
    main()


"""Read the battle chat log (OCR) for the current turn number.

PokeMMO prints "Turn N started!" in the battle chat, which sits at a stable
window position (bottom-left), unlike the letterboxed battle viewport. This is
the most reliable turn signal when the chat is visible.
"""

from __future__ import annotations

import re

import cv2
import numpy as np

from battle_reader import ChatCalibration
from ocr_engine import run_ocr

# "Turn 2 started!" — tolerate OCR spacing/case noise.
_TURN = re.compile(r"turn\s*(\d{1,3})\s*start", re.IGNORECASE)


def parse_turn_number(texts: list[str]) -> int | None:
    """Highest "Turn N started" number among OCR text lines, or None."""
    best: int | None = None
    for line in texts:
        for m in _TURN.finditer(line):
            n = int(m.group(1))
            best = n if best is None else max(best, n)
    return best


def read_turn_number(frame_bgr: np.ndarray, cal: ChatCalibration) -> int | None:
    """OCR the chat region and return the current turn number (1-based), or
    None if no "Turn N started" line is visible/readable."""
    h, w = frame_bgr.shape[:2]
    crop = frame_bgr[int(h * cal.top) : int(h * cal.bottom), int(w * cal.left) : int(w * cal.right)]
    if crop.size == 0:
        return None
    up = cv2.resize(crop, None, fx=cal.upscale, fy=cal.upscale, interpolation=cv2.INTER_CUBIC)
    return parse_turn_number(run_ocr(up))

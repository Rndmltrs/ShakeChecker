"""Read battle text via OCR: the turn number from the chat log, and the catch
event from the in-viewport narration box.

PokeMMO prints "Turn N started!" in the battle chat (stable window position,
bottom-left). The capture ("Gotcha! / X was caught!") is read from the
in-viewport narration box instead — the chat log lags the action by ~1s, so at
the catch moment it still shows the previous battle's catch line.
"""

from __future__ import annotations

import re

import cv2
import numpy as np
from rapidfuzz import fuzz

from battle_reader import ChatCalibration, NarrationCalibration
from ocr_engine import run_ocr

# "Turn 2 started!" — tolerate OCR spacing/case noise.
_TURN = re.compile(r"turn\s*(\d{1,3})\s*start", re.IGNORECASE)


def parse_turn_number(texts: list[str]) -> int | None:
    """Highest "Turn N started" number among OCR text lines, or None.

    NB: the catch is deliberately NOT read from the chat. The chat log lags the
    actual battle by ~1s, so at the moment a Pokemon is caught it still shows the
    PREVIOUS battle's catch line — read_catch_banner reads the live in-viewport
    box instead."""
    best: int | None = None
    for line in texts:
        for m in _TURN.finditer(line):
            n = int(m.group(1))
            best = n if best is None else max(best, n)
    return best


def read_turn_number(frame_bgr: np.ndarray, cal: ChatCalibration) -> int | None:
    """Current turn number (1-based) from the chat, or None if not readable."""
    h, w = frame_bgr.shape[:2]
    crop = frame_bgr[int(h * cal.top) : int(h * cal.bottom), int(w * cal.left) : int(w * cal.right)]
    if crop.size == 0:
        return None
    up = cv2.resize(crop, None, fx=cal.upscale, fy=cal.upscale, interpolation=cv2.INTER_CUBIC)
    return parse_turn_number(run_ocr(up))


def is_catch_banner(texts: list[str]) -> bool:
    """True if the OCR'd narration text shows a capture ("Gotcha! / X was
    caught!"). OCR mangles "Gotcha"->"Gotoha" and splits/drops "was", so we
    key on the surviving keywords rather than the exact phrase: a "caught"
    token, or a fuzzy "gotcha" match."""
    for raw in texts:
        for token in re.split(r"[^A-Za-z]+", raw.lower()):
            if not token:
                continue
            if "caught" in token:
                return True
            if fuzz.ratio(token, "gotcha") >= 75:  # "gotoha" ~= 83
                return True
    return False


def read_catch_banner(frame_bgr: np.ndarray, cal: NarrationCalibration) -> bool:
    """OCR the in-viewport narration box and report whether it shows a capture.

    This is the authoritative catch signal: the box updates with the current
    frame, whereas the chat log lags ~1s (and at the catch moment still shows
    the PREVIOUS battle's catch line). See [narration] in calibration.toml."""
    h, w = frame_bgr.shape[:2]
    crop = frame_bgr[int(h * cal.top) : int(h * cal.bottom), int(w * cal.left) : int(w * cal.right)]
    if crop.size == 0:
        return False
    up = cv2.resize(crop, None, fx=cal.upscale, fy=cal.upscale, interpolation=cv2.INTER_CUBIC)
    return is_catch_banner(run_ocr(up))

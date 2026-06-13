"""Read the enemy species name via OCR and resolve it to a species entry.

OCR output is never trusted directly: the level marker and trailing icons are
stripped and the remainder is fuzzy-matched (rapidfuzz) against the English
species list from species_core.json. The OCR engine is loaded lazily so this
module (and the pure matching logic) imports cheaply for tests.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import cv2
import numpy as np
from rapidfuzz import fuzz, process

from battle_reader import BarReading, NameCalibration

# Cut the OCR string at the level marker ("Lv", "Lu", "Iv" misreads) so only
# the name remains; everything after (level number, gender, caught ball) is noise.
_LEVEL_MARKER = re.compile(r"\b[li][vu]\b", re.IGNORECASE)


def clean_ocr_text(raw: str) -> str:
    return _LEVEL_MARKER.split(raw, maxsplit=1)[0].strip()


def match_species_name(raw_text: str, names: list[str], min_score: float) -> str | None:
    """Best species name for an OCR string, or None below `min_score`."""
    candidate = clean_ocr_text(raw_text)
    if not candidate:
        return None
    match = process.extractOne(candidate, names, scorer=fuzz.WRatio, processor=str.lower)
    if match is None:
        return None
    name, score, _ = match
    return name if score >= min_score else None


class NameReader:
    """Crops the name region, OCRs it and resolves it to a species dict
    ({id, name, catch_rate, ...} from species_core.json)."""

    def __init__(self, cal: NameCalibration, species_path: Path | str) -> None:
        self._cal = cal
        species = json.loads(Path(species_path).read_text("utf-8"))
        self._names = [s["name"] for s in species]
        self._by_name = {s["name"]: s for s in species}
        self._ocr = None  # lazy: avoid loading ONNX models until first use

    def _run_ocr(self, image: np.ndarray) -> str:
        if self._ocr is None:
            from rapidocr_onnxruntime import RapidOCR

            self._ocr = RapidOCR()
        result, _ = self._ocr(image)
        if not result:
            return ""
        return " ".join(text for _box, text, _score in result)

    def read(self, frame_bgr: np.ndarray, bar: BarReading) -> dict | None:
        """Species dict for the enemy whose bar is `bar`, or None if the name
        could not be read/matched."""
        c = self._cal
        y0, y1 = bar.y + c.dy0, bar.y + c.dy1
        x0, x1 = bar.x + c.dx0, bar.x + c.dx1
        if y0 < 0 or x0 < 0 or y1 > frame_bgr.shape[0] or x1 > frame_bgr.shape[1]:
            return None
        crop = frame_bgr[y0:y1, x0:x1]
        if crop.size == 0:
            return None
        up = cv2.resize(crop, None, fx=c.upscale, fy=c.upscale, interpolation=cv2.INTER_CUBIC)
        name = match_species_name(self._run_ocr(up), self._names, c.min_match_score)
        return self._by_name.get(name) if name else None

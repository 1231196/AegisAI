"""PaddleOCR fallback for scanned/image PDF pages (US-009).

Model instantiation loads detection + recognition + angle-classification
weights and is expensive (multi-second, one-time download on first
run) — the engine is a lazily-created, process-wide singleton so every
page across every document reuses it instead of reloading per call.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_engine():
    from paddleocr import PaddleOCR

    logger.info(
        "loading PaddleOCR engine (lang=%s) - first call only, downloads "
        "model weights on first run",
        settings.ocr_lang,
    )
    return PaddleOCR(use_angle_cls=True, lang=settings.ocr_lang, show_log=False)


def ocr_image(png_bytes: bytes) -> str:
    """OCR a single rasterised page image (PNG bytes) -> recognised text."""
    import cv2

    engine = get_ocr_engine()
    image_array = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    result = engine.ocr(image_array, cls=True)
    return "\n".join(_extract_lines(result))


def _extract_lines(ocr_result) -> list[str]:
    """Normalise across PaddleOCR API shapes.

    Classic (``.ocr()``, PaddleOCR <3): one outer list per input image,
    each entry ``[box, (text, score)]``.
    Newer (PaddleOCR 3.x, structured results): one dict per input
    image with a ``rec_texts`` key.
    """
    lines: list[str] = []
    for page in ocr_result or []:
        if isinstance(page, dict):
            lines.extend(page.get("rec_texts", []))
            continue
        for item in page or []:
            try:
                _box, (text, _score) = item
                lines.append(text)
            except (TypeError, ValueError):
                logger.warning("unrecognised PaddleOCR result item shape: %r", item)
    return lines

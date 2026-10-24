"""OCR pipeline with image preprocessing and Tesseract."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.config import get_settings
from app.ai.ocr_text import fix_rupee_ocr_errors

logger = logging.getLogger(__name__)
settings = get_settings()


if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD



@dataclass
class OCRResultData:
    raw_text: str
    confidence_score: float
    preprocessing_applied: list[str]


def _load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Cannot read image: {path}")
    return img


def _pdf_to_images(path: Path) -> list[np.ndarray]:
    
    pages = convert_from_path(
        str(path),
        dpi=200,
        poppler_path=settings.POPPLER_PATH
    )
    images: list[np.ndarray] = []
    for page in pages:
        arr = np.array(page.convert("RGB"))
        images.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    return images


def preprocess_image(img: np.ndarray) -> tuple[np.ndarray, list[str]]:
    steps: list[str] = []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    steps.append("grayscale")

    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    steps.append("denoising")

    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    steps.append("thresholding")

    try:
        osd = pytesseract.image_to_osd(thresh, output_type=pytesseract.Output.DICT)
        angle = int(osd.get("rotate", 0))
        if angle != 0:
            h, w = thresh.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(thresh, matrix, (w, h))
            steps.append(f"orientation_correction_{angle}")
    except Exception as exc:
        logger.debug("OSD orientation skipped: %s", exc)

    return thresh, steps


def _run_tesseract(img: np.ndarray) -> tuple[str, float]:
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config="--psm 6"
    )
    lines: dict[tuple[int, int, int, int], list[str]] = {}
    confidences: list[float] = []
    for i, text in enumerate(data["text"]):
        conf = float(data["conf"][i])
        if text.strip() and conf > 0:
            line_key = tuple(data[key][i] for key in ("page_num", "block_num", "par_num", "line_num"))
            lines.setdefault(line_key, []).append(text)
            confidences.append(conf)
    raw = "\n".join(" ".join(words) for words in lines.values())
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return raw, avg_conf / 100.0


def extract_text_from_file(file_path: str | Path) -> OCRResultData:
    path = Path(file_path)
    suffix = path.suffix.lower()
    all_steps: list[str] = []
    combined_text: list[str] = []
    confidences: list[float] = []

    if suffix == ".pdf":
        images = _pdf_to_images(path)
    else:
        images = [_load_image(path)]

    for img in images:
        processed, steps = preprocess_image(img)
        all_steps.extend(steps)
        text, conf = _run_tesseract(processed)
        if text.strip():
            combined_text.append(text)
            confidences.append(conf)

    raw = "\n\n".join(combined_text).strip()
    raw = fix_rupee_ocr_errors(raw)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    if avg_conf < settings.OCR_MIN_CONFIDENCE and raw:
        logger.warning("Low OCR confidence: %.2f", avg_conf)

    return OCRResultData(
        raw_text=raw or "",
        confidence_score=round(avg_conf, 4),
        preprocessing_applied=list(dict.fromkeys(all_steps)),
    )

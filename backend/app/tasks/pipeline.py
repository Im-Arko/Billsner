"""
OCR Pipeline — Tesseract & PaddleOCR support with image preprocessing.
Handles PDFs (via pdf2image), images (PIL), confidence scoring, and cleanup.
"""

import asyncio
import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter

from app.core.config import settings

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Image enhancement pipeline for better OCR accuracy."""

    @staticmethod
    def to_grayscale(img: Image.Image) -> Image.Image:
        return img.convert("L")

    @staticmethod
    def denoise(img: Image.Image) -> Image.Image:
        return img.filter(ImageFilter.MedianFilter(size=3))

    @staticmethod
    def threshold(img: Image.Image) -> Image.Image:
        """Adaptive thresholding for binarization."""
        arr = np.array(img)
        threshold_val = arr.mean()
        binary = (arr > threshold_val).astype(np.uint8) * 255
        return Image.fromarray(binary)

    @staticmethod
    def correct_orientation(img: Image.Image) -> Image.Image:
        """Auto-rotate using EXIF data if present."""
        try:
            from PIL import ImageOps
            return ImageOps.exif_transpose(img)
        except Exception:
            return img

    @classmethod
    def preprocess(cls, img: Image.Image) -> Image.Image:
        """Full preprocessing chain."""
        img = cls.correct_orientation(img)
        img = cls.to_grayscale(img)
        img = cls.denoise(img)
        img = cls.threshold(img)
        return img


class TesseractOCR:
    """OCR using pytesseract with confidence extraction."""

    def __init__(self):
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            self.pytesseract = pytesseract
        except ImportError:
            raise RuntimeError("pytesseract not installed. Run: pip install pytesseract")

    def extract(self, img: Image.Image) -> Tuple[str, float]:
        """Returns (text, confidence_score 0-100)."""
        data = self.pytesseract.image_to_data(
            img, output_type=self.pytesseract.Output.DICT, lang="eng+hin"
        )
        words = [w for w, c in zip(data["text"], data["conf"]) if int(c) > 0 and w.strip()]
        confidences = [float(c) for c in data["conf"] if int(c) > 0]

        text = self.pytesseract.image_to_string(img, lang="eng+hin")
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return text.strip(), round(avg_conf, 2)


class PaddleOCREngine:
    """OCR using PaddleOCR for multilingual and complex layouts."""

    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except ImportError:
            raise RuntimeError("paddleocr not installed. Run: pip install paddleocr")

    def extract(self, img: Image.Image) -> Tuple[str, float]:
        arr = np.array(img)
        result = self._ocr.ocr(arr, cls=True)
        if not result or not result[0]:
            return "", 0.0

        lines = []
        scores = []
        for line in result[0]:
            text = line[1][0]
            score = line[1][1]
            lines.append(text)
            scores.append(score)

        full_text = "\n".join(lines)
        avg_conf = (sum(scores) / len(scores) * 100) if scores else 0.0
        return full_text.strip(), round(avg_conf, 2)


class OCRPipeline:
    """
    Main OCR orchestrator.
    - Handles images and PDFs
    - Preprocesses images
    - Routes to configured OCR engine
    - Returns structured results
    """

    def __init__(self):
        if settings.OCR_ENGINE == "tesseract":
            self.engine = TesseractOCR()
        else:
            self.engine = PaddleOCREngine()
        self.preprocessor = ImagePreprocessor()

    async def process_file(self, file_path: str) -> dict:
        """
        Main entry point. Returns:
        {
            "raw_text": str,
            "confidence_score": float,
            "ocr_engine": str,
            "page_count": int,
        }
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return await asyncio.get_event_loop().run_in_executor(
                None, self._process_pdf, file_path
            )
        elif suffix in {".jpg", ".jpeg", ".png"}:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._process_image, file_path
            )
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def _process_image(self, file_path: str) -> dict:
        img = Image.open(file_path)
        preprocessed = self.preprocessor.preprocess(img)
        text, confidence = self.engine.extract(preprocessed)
        return {
            "raw_text": text,
            "confidence_score": confidence,
            "ocr_engine": settings.OCR_ENGINE,
            "page_count": 1,
        }

    def _process_pdf(self, file_path: str) -> dict:
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise RuntimeError("pdf2image not installed. Run: pip install pdf2image")

        images = convert_from_path(file_path, dpi=300)
        all_text = []
        all_conf = []

        for img in images:
            preprocessed = self.preprocessor.preprocess(img)
            text, conf = self.engine.extract(preprocessed)
            all_text.append(text)
            all_conf.append(conf)

        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
        avg_conf = sum(all_conf) / len(all_conf) if all_conf else 0.0

        return {
            "raw_text": combined_text,
            "confidence_score": round(avg_conf, 2),
            "ocr_engine": settings.OCR_ENGINE,
            "page_count": len(images),
        }


# Singleton
_ocr_pipeline: Optional[OCRPipeline] = None


def get_ocr_pipeline() -> OCRPipeline:
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OCRPipeline()
    return _ocr_pipeline

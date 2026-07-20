from paddleocr import PaddleOCR
import numpy as np
from typing import Tuple, Optional
from loguru import logger
import logging

class OCREngine:
    """
    Wraps PaddleOCR for offline text recognition.
    """

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        logging.getLogger("ppocr").setLevel(logging.ERROR)
        
        logger.info(f"Initializing PaddleOCR (lang={lang}, use_gpu={use_gpu})")
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu, show_log=False)

    def extract_text(self, cell_image: np.ndarray) -> Tuple[Optional[str], float]:
        if cell_image is None or cell_image.size == 0:
            return None, 0.0
            
        try:
            result = self.ocr.ocr(cell_image, cls=True)
            
            if not result or result[0] is None:
                return None, 0.0
                
            print(f"RAW PADDLEOCR RESULT: {result[0]}")
            
            texts = []
            total_conf = 0.0
            
            for line in result[0]:
                box, (text, conf) = line
                texts.append(text)
                total_conf += conf
                
            combined_text = " ".join(texts).strip()
            avg_conf = total_conf / len(result[0]) if result[0] else 0.0
            
            return combined_text, avg_conf
            
        except Exception as e:
            logger.error(f"OCR Failed on cell: {e}")
            return None, 0.0

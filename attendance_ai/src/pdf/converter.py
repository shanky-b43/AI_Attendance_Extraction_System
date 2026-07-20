import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
from loguru import logger


class PDFConverter:
    """
    Converts PDF documents into high-resolution images.
    """

    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.zoom = dpi / 72.0
        self.matrix = fitz.Matrix(self.zoom, self.zoom)

    def convert_pdf_to_images(self, pdf_path: str | Path) -> List[Tuple[int, np.ndarray]]:
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF file not found: {path}")
            raise FileNotFoundError(f"PDF file not found: {path}")

        logger.info(f"Converting PDF to images: {path.name}")
        images = []
        try:
            doc = fitz.open(path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=self.matrix)
                
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                if pix.n == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                elif pix.n == 4:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    if len(img_array.shape) == 2 or img_array.shape[2] == 1:
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
                        
                images.append((page_num + 1, img_array))
                logger.debug(f"Converted page {page_num + 1} of {path.name}")
                
            doc.close()
            logger.info(f"Successfully converted {len(images)} pages from {path.name}")
        except Exception as e:
            logger.exception(f"Failed to convert PDF {path.name}: {e}")
            raise
            
        return images

import cv2
import numpy as np
from typing import Tuple, Optional
from loguru import logger

class TableDetector:
    """
    Detects the main attendance table in an image.
    """

    def __init__(self, min_area: int = 10000):
        self.min_area = min_area

    def detect(self, enhanced_binary: np.ndarray, original_image: np.ndarray) -> Optional[np.ndarray]:
        logger.debug("Starting table detection using global ink projection")
        
        # Use the raw binary image to find the absolute bounds of all ink (text + lines)
        horizontal_projection = np.sum(enhanced_binary, axis=1)
        vertical_projection = np.sum(enhanced_binary, axis=0)
        
        y_indices = np.where(horizontal_projection > 255 * 5)[0] # Require at least 5 pixels of ink
        x_indices = np.where(vertical_projection > 255 * 5)[0]
        
        if len(y_indices) == 0 or len(x_indices) == 0:
            logger.warning("No content found on page.")
            return None
            
        y1, y2 = y_indices[0], y_indices[-1]
        x1, x2 = x_indices[0], x_indices[-1]
        
        w = x2 - x1
        h = y2 - y1
        
        if w * h < self.min_area:
            logger.warning("Content area too small.")
            return None
            
        logger.debug(f"Found table at x={x1}, y={y1}, w={w}, h={h}")
        
        pad = 5
        cx1 = max(0, x1 - pad)
        cy1 = max(0, y1 - pad)
        cx2 = min(original_image.shape[1], x2 + pad)
        cy2 = min(original_image.shape[0], y2 + pad)
        
        table_crop = original_image[cy1:cy2, cx1:cx2]
        return table_crop

    def get_lines(self, table_binary: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        scale = 30 # Standard scaling
        
        # Isolate horizontal lines - DO NOT use MORPH_CLOSE, as it bridges text characters into lines!
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, table_binary.shape[1] // scale), 1))
        h_lines = cv2.morphologyEx(table_binary, cv2.MORPH_OPEN, h_kernel, iterations=1)
        
        # Isolate vertical lines - close gaps first to handle faint/broken lines
        # Dilate first to handle slightly skewed/diagonal lines in photos!
        v_dilate = np.ones((2, 2), np.uint8)
        thick_binary = cv2.dilate(table_binary, v_dilate)
        
        v_close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
        v_closed = cv2.morphologyEx(thick_binary, cv2.MORPH_CLOSE, v_close_kernel)
        
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(1, table_binary.shape[0] // scale)))
        v_lines = cv2.morphologyEx(v_closed, cv2.MORPH_OPEN, v_kernel, iterations=1)
        
        return h_lines, v_lines

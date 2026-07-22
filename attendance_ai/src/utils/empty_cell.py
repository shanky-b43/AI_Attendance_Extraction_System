import cv2
import numpy as np
from enum import Enum

class CellState(Enum):
    BLANK = "BLANK"
    BLACK_BOX = "BLACK_BOX"
    CONTENT = "CONTENT"

def get_cell_state(cell_image: np.ndarray, blank_threshold: float = 0.025, black_box_threshold: float = 0.85) -> CellState:
    """
    Analyzes the cell image to determine if it is blank, a black box, or contains content (handwriting/text).
    Uses morphological operations to remove grid lines for accurate ink counting.
    """
    if cell_image is None or cell_image.size == 0:
        return CellState.BLANK
        
    gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY) if len(cell_image.shape) == 3 else cell_image
    
    # Binarize the image (ink becomes white, background becomes black)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 10)
    
    # Aggressive margins to remove adjacent text and border artifacts
    margin_y = int(thresh.shape[0] * 0.15)
    margin_x = int(thresh.shape[1] * 0.10)
    
    if margin_y > 0 and margin_x > 0 and margin_y * 2 < thresh.shape[0] and margin_x * 2 < thresh.shape[1]:
        core_thresh = thresh[margin_y:-margin_y, margin_x:-margin_x]
    else:
        core_thresh = thresh
        
    # Remove straight horizontal and vertical lines (table grids)
    h_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    v_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    
    h_lines = cv2.morphologyEx(core_thresh, cv2.MORPH_OPEN, h_kern)
    v_lines = cv2.morphologyEx(core_thresh, cv2.MORPH_OPEN, v_kern)
    
    cleaned_thresh = cv2.subtract(core_thresh, h_lines)
    cleaned_thresh = cv2.subtract(cleaned_thresh, v_lines)
    
    ink_pixels = cv2.countNonZero(cleaned_thresh)
    total_pixels = cleaned_thresh.shape[0] * cleaned_thresh.shape[1]
    
    if total_pixels == 0:
        return CellState.BLANK
        
    ratio = ink_pixels / total_pixels
    
    if ratio < blank_threshold:
        return CellState.BLANK
    elif ratio > black_box_threshold:
        return CellState.BLACK_BOX
    else:
        return CellState.CONTENT

import cv2
import numpy as np

def is_cell_empty(cell_image: np.ndarray, threshold: float = 0.02) -> bool:
    if cell_image is None or cell_image.size == 0:
        return True
        
    gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY) if len(cell_image.shape) == 3 else cell_image
    
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 10)
    
    ink_pixels = cv2.countNonZero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    
    if total_pixels == 0:
        return True
        
    ratio = ink_pixels / total_pixels
    
    return ratio < threshold

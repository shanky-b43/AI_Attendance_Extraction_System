import cv2
import numpy as np
from loguru import logger

class ImageEnhancer:
    """
    Handles image preprocessing: deskew, noise removal, contrast enhancement, and sharpening.
    """

    @staticmethod
    def enhance_for_table_detection(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        return thresh

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray = cv2.bitwise_not(gray)
        
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # Handle OpenCV minAreaRect angle conventions properly
        # We only want to deskew small angles (deviation from horizontal/vertical)
        if angle > 45:
            angle = angle - 90
        elif angle < -45:
            angle = angle + 90
            
        # The angle is now in [-45, 45]. minAreaRect returns the angle of the rectangle.
        # We just negate it to counter-rotate.
        angle = -angle
            
        if abs(angle) < 0.5:
            return image
            
        logger.debug(f"Deskewing image by {angle:.2f} degrees")
        
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        return rotated

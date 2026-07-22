from dataclasses import dataclass
from src.config.parser import AttendanceRulesConfig, OcrConfig
from src.utils.empty_cell import CellState

@dataclass
class AttendanceDecision:
    status: str
    confidence: float
    detected_text: str
    source: str

class AttendanceEngine:
    """
    Implements business rules for attendance classification based on user-defined states.
    """

    def __init__(self, rules_config: AttendanceRulesConfig, ocr_config: OcrConfig):
        self.rules = rules_config
        self.ocr_config = ocr_config
        
        self.present_set = {x.lower() for x in self.rules.present_text}
        self.absent_set = {x.lower() for x in self.rules.absent_text}

    def evaluate(self, cell_state: CellState, ocr_text: str, ocr_conf: float) -> AttendanceDecision:
        if cell_state == CellState.BLANK:
            return AttendanceDecision(
                status=self.rules.blank,
                confidence=1.0,
                detected_text="",
                source="Blank Cell"
            )

        if cell_state == CellState.BLACK_BOX:
            return AttendanceDecision(
                status=self.rules.black_box,
                confidence=1.0,
                detected_text="[Black Box]",
                source="Black Box"
            )
            
        # If it's CONTENT, check OCR text first
        if ocr_text:
            text_lower = ocr_text.strip().lower()
            
            if text_lower in self.present_set:
                return AttendanceDecision(
                    status="Present",
                    confidence=ocr_conf,
                    detected_text=ocr_text,
                    source="OCR Rule Match"
                )
                
            if text_lower in self.absent_set:
                return AttendanceDecision(
                    status="Absent",
                    confidence=ocr_conf,
                    detected_text=ocr_text,
                    source="OCR Rule Match"
                )


        # If OCR text is empty but cell has CONTENT, or OCR didn't match a rule, assume it's a signature
        return AttendanceDecision(
             status=self.rules.handwritten_signature,
             confidence=0.8,
             detected_text=ocr_text if ocr_text else "[Handwritten Signature]",
             source="Handwriting Fallback"
        )

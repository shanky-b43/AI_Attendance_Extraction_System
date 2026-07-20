from dataclasses import dataclass
from src.config.parser import AttendanceRulesConfig, OcrConfig

@dataclass
class AttendanceDecision:
    status: str
    confidence: float
    detected_text: str
    source: str

class AttendanceEngine:
    """
    Implements business rules for attendance classification.
    """

    def __init__(self, rules_config: AttendanceRulesConfig, ocr_config: OcrConfig):
        self.rules = rules_config
        self.ocr_config = ocr_config
        
        self.present_set = {x.lower() for x in self.rules.present_marks}
        self.absent_set = {x.lower() for x in self.rules.absent_marks}

    def evaluate(self, is_empty: bool, ocr_text: str, ocr_conf: float) -> AttendanceDecision:
        if is_empty:
            return AttendanceDecision(
                status="Absent",
                confidence=1.0,
                detected_text="",
                source="Empty Cell"
            )

        if not ocr_text:
             return AttendanceDecision(
                 status="Present",
                 confidence=0.5,
                 detected_text="[Signature/Handwriting]",
                 source="Non-empty Unknown"
             )
             
        if ocr_conf < self.ocr_config.confidence_threshold:
            return AttendanceDecision(
                 status="Review",
                 confidence=ocr_conf,
                 detected_text=ocr_text,
                 source="Low Confidence"
            )

        text_lower = ocr_text.strip().lower()

        if text_lower in self.present_set:
            return AttendanceDecision(
                 status="Present",
                 confidence=ocr_conf,
                 detected_text=ocr_text,
                 source="Rule Match"
            )
            
        if text_lower in self.absent_set:
            return AttendanceDecision(
                 status="Absent",
                 confidence=ocr_conf,
                 detected_text=ocr_text,
                 source="Rule Match"
            )

        return AttendanceDecision(
             status="Present",
             confidence=ocr_conf,
             detected_text=ocr_text,
             source="Fallback (Handwriting/Name)"
        )

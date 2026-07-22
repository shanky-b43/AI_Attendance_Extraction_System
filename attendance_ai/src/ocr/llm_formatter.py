import re
from loguru import logger
from typing import Dict, List

class RuleFormatter:
    """
    Cleans raw OCR text instantly using deterministic Regex rules,
    completely replacing the slow LLM approach.
    """
    def __init__(self):
        pass

    def clean_uid(self, text: str) -> str:
        # Common OCR fixes for UIDs (e.g. 23BAI70077)
        # Often 8 is read instead of B
        text = text.upper().replace(" ", "")
        
        # If it looks roughly like a UID, apply specific fixes
        # typical format: 23 BAI 70077 -> 2 digits, 3-4 letters, 5 digits
        text = re.sub(r'^(\d{2})8', r'\g<1>B', text) # Fix 238AI -> 23BAI
        
        # Strict pattern match if possible
        match = re.search(r'(\d{2}[A-Z]{3,4}\d{4,5})', text)
        if match:
            return match.group(1)
        return text

    def clean_groups(self, text: str) -> str:
        text = text.upper()
        # Keep only G and digits
        cleaned = re.sub(r'[^G\d]', '', text)
        if cleaned.startswith("G"):
            return cleaned
        if "G" in cleaned:
            return cleaned[cleaned.index("G"):]
        return text

    def clean_room(self, text: str) -> str:
        # Keep only digits
        return re.sub(r'\D', '', text)
        
    def clean_sno(self, text: str) -> str:
        return re.sub(r'\D', '', text)

    def clean_block(self, text: str) -> str:
        text = text.upper()
        # Match something like D3, E3
        match = re.search(r'([A-Z]\d)', text)
        if match:
            return match.group(1)
        return text

    def clean_name(self, text: str) -> str:
        # Remove weird punctuation and title case
        cleaned = re.sub(r'[^a-zA-Z\s]', '', text)
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned.title()

    def format_row(self, raw_texts: List[str]) -> Dict[str, str]:
        # Safely pad the list to 7 elements
        padded = raw_texts + [""] * (7 - len(raw_texts))
        
        s_no = self.clean_sno(padded[0])
        s_g_no = self.clean_sno(padded[1])
        groups = self.clean_groups(padded[2])
        uid = self.clean_uid(padded[3])
        name = self.clean_name(padded[4])
        room_no = self.clean_room(padded[5])
        block = self.clean_block(padded[6])
        
        parsed = {
            "S_No": s_no,
            "S_G_No": s_g_no,
            "Groups": groups,
            "UID": uid,
            "Name": name,
            "Room_No": room_no,
            "Block": block
        }
        
        logger.debug(f"RuleFormatter cleaned row: {parsed}")
        return parsed

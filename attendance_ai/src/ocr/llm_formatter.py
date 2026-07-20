import requests
import json
import re
from loguru import logger
from typing import Dict, List

class LLMFormatter:
    """
    Passes raw OCR text to local Ollama (qwen3:8b) for spelling correction and JSON formatting.
    """
    def __init__(self, model: str = "qwen3:8b", endpoint: str = "http://localhost:11434/api/generate"):
        self.model = model
        self.endpoint = endpoint

    def format_row(self, raw_texts: List[str]) -> Dict[str, str]:
        prompt = f"""
You are a highly accurate data cleaner for a student attendance system.
I will give you an array of 7 messy OCR text strings extracted from a single row of an attendance sheet.
The columns are in order: [S. No, S. G No., Groups, UID, Name, Room No, Block]
Your task is to fix any OCR spelling errors (especially in names or IDs like '8AI' -> 'BAI'), remove garbage characters, and output exactly the cleaned text in a strict JSON format.

Input Array: {json.dumps(raw_texts)}

Respond ONLY with a JSON object. Do not include markdown formatting or explanations.
Format:
{{
  "S_No": "...",
  "S_G_No": "...",
  "Groups": "...",
  "UID": "...",
  "Name": "...",
  "Room_No": "...",
  "Block": "..."
}}
"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            logger.debug(f"Sending request to Ollama ({self.model})...")
            response = requests.post(self.endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            result_text = data.get("response", "").strip()
            
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                result_text = match.group(0)
                
            parsed = json.loads(result_text)
            logger.debug(f"Ollama returned: {parsed}")
            return parsed
            
        except Exception as e:
            logger.error(f"LLM formatting failed: {e}. Falling back to raw text.")
            return {
                "S_No": raw_texts[0] if len(raw_texts) > 0 else "",
                "S_G_No": raw_texts[1] if len(raw_texts) > 1 else "",
                "Groups": raw_texts[2] if len(raw_texts) > 2 else "",
                "UID": raw_texts[3] if len(raw_texts) > 3 else "",
                "Name": raw_texts[4] if len(raw_texts) > 4 else "",
                "Room_No": raw_texts[5] if len(raw_texts) > 5 else "",
                "Block": raw_texts[6] if len(raw_texts) > 6 else ""
            }

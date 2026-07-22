import os
import time
import json
from loguru import logger
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class GeminiVisionEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or .env file.")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-flash-latest"

    def parse_attendance_sheet(self, image_data) -> list[dict]:
        """
        Sends the image to Gemini's Vision API and returns a list of dictionaries 
        containing the attendance data. Includes automatic rate limit handling.
        """
        import numpy as np
        import cv2
        from PIL import Image
        import io

        if isinstance(image_data, np.ndarray):
            image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
        elif isinstance(image_data, str):
            pil_image = Image.open(image_data)
        else:
            raise ValueError("Unsupported image format")
        
        prompt = """
        You are an AI trained to extract tabular data from attendance sheets.
        Extract the table from the provided image into a strict JSON array of objects.
        
        The image contains 8 columns:
        S.No, S.G. No., Groups, UID, Name, Room No., Block, Signature
        
        Rules for extraction:
        1. Output ONLY a valid JSON array of arrays (a 2D array). No markdown, no explanations.
        2. Do NOT output JSON objects. Each row must be an array of exactly 8 strings in this order:
           [S_No, S_G_No, Groups, UID, Name, Room_No, Block, Signature]
        3. For the "Signature" column, evaluate attendance using these STRICT rules in order of priority:
           - PRIORITY 1: If the box explicitly contains the clear full word "Absent" or "absent" (do NOT confuse cursive signatures like "Anish" or "Ayush" with the word "Absent"), output "Absent" (even if there is a signature).
           - PRIORITY 2: If the box explicitly contains the full word "Present" or "present", output "Present".
           - PRIORITY 3: If the box contains the capital letter 'A' or 'AB' alone (do not confuse with small squiggles), output "Absent".
           - PRIORITY 4: If the box is completely empty, blank, or just has a dash, output "Absent".
           - PRIORITY 5: If the box contains the letter 'P', 'p', 'D', or 'd', output "Present".
           - PRIORITY 6: If the box contains a handwritten signature (cursive scribble or name), output "Present".
           - PRIORITY 7: If there is any ink/mark that is not clearly an 'A' or 'AB', default to "Present".
        4. If a field is empty (other than signature), leave it as an empty string "".
        """

        max_retries = 20
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending image to Gemini Vision API (Attempt {attempt+1}/{max_retries})...")
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[pil_image, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        max_output_tokens=8192
                    )
                )
                
                response_text = response.text.strip()
                
                # Try to parse the JSON. 
                # If the model wraps it in markdown ```json ... ```, strip it.
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                    
                response_text = response_text.strip()
                
                try:
                    raw_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # Attempt to fix missing OR overly duplicated trailing brackets (Gemini hallucination bug)
                    try:
                        # BULLETPROOF FALLBACK: Extract all 8-element string arrays from the text using regex
                        # This ignores all hallucinated trailing brackets and broken outer JSON structure
                        import re
                        matches = re.findall(r'\[\s*(?:"(?:[^"\\]|\\.)*"\s*,\s*){7}"(?:[^"\\]|\\.)*"\s*\]', response_text)
                        
                        if matches:
                            raw_data = [json.loads(m) for m in matches]
                        else:
                            raise json.JSONDecodeError("No valid rows found via regex fallback.", response_text, 0)
                    except Exception:
                        logger.error(f"Failed to parse JSON from Gemini. Raw response:\n{response_text}")
                        return []
                
                keys = ["S_No", "S_G_No", "Groups", "UID", "Name", "Room_No", "Block", "Signature"]
                data = []
                
                # If Gemini returned a dict wrapper like {"table": [...]}, unwrap it
                if isinstance(raw_data, dict):
                    for k, v in raw_data.items():
                        if isinstance(v, list):
                            raw_data = v
                            break
                    if isinstance(raw_data, dict): # still a dict?
                        raw_data = []

                if isinstance(raw_data, list):
                    for row in raw_data:
                        if isinstance(row, list) and len(row) >= 8:
                            data.append(dict(zip(keys, row)))
                        elif isinstance(row, dict):
                            data.append(row)
                
                logger.info(f"Successfully extracted {len(data)} rows via Gemini Vision.")
                
                if len(data) == 0:
                    logger.warning(f"0 rows extracted! Raw Gemini Output was:\n{response_text}")
                
                return data


            except Exception as e:
                # Gemini rate limits or internal errors
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg:
                    logger.warning("Gemini Rate Limit (HTTP 429) reached. Sleeping for 60 seconds...")
                    time.sleep(60)
                elif "503" in error_msg or "unavailable" in error_msg:
                    logger.warning("Gemini Server Overloaded (HTTP 503). Sleeping for 30 seconds...")
                    time.sleep(30)
                else:
                    logger.error(f"Gemini API Error: {e}")
                    if attempt == max_retries - 1:
                        return []
                    time.sleep(5) # short backoff for other errors
                    
        return []

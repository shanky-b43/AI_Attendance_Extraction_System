import os
import time
import json
import base64
import io
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class OpenRouterVisionEngine:
    def __init__(self, model: str = "openrouter/free"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables or .env file.")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    def _image_to_base64_url(self, image_data) -> str:
        """Convert image data (numpy array or file path) to a base64 data URL."""
        import numpy as np
        import cv2
        from PIL import Image

        if isinstance(image_data, np.ndarray):
            image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
        elif isinstance(image_data, str):
            pil_image = Image.open(image_data)
        else:
            raise ValueError("Unsupported image format")

        # Convert to PNG bytes
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def parse_attendance_sheet(self, image_data) -> list[dict]:
        """
        Sends the image to OpenRouter's Vision API and returns a list of dictionaries
        containing the attendance data. Includes automatic rate limit handling.
        """
        base64_url = self._image_to_base64_url(image_data)

        prompt = """
        You are an AI trained to extract tabular data from attendance sheets.
        Extract the table from the provided image into a strict JSON array of objects.
        
        The image contains 8 columns:
        S.No, S.G. No., Groups, UID, Name, Room No., Block, Signature
        
        Rules for extraction:
        1. Output ONLY a valid JSON array of arrays (a 2D array). No markdown, no explanations.
        2. Do NOT output JSON objects. Each row must be an array of exactly 8 strings in this order:
           [S_No, S_G_No, Groups, UID, Name, Room_No, Block, Signature]
           
        CRITICAL ALIGNMENT INSTRUCTION:
        There are NO horizontal grid lines in the "Signature" column. Students often write their signatures floating slightly above or below their actual row, or overlapping other rows. 
        You MUST carefully track the invisible horizontal line from each student's Name straight across to the right side of the page. Do NOT assume a row is empty just because the signature drifted into the row above or below it.
        
        ROW ANCHOR RULE: Use the S.No number in the leftmost column as your PRIMARY anchor for each row. For every S.No, draw an imaginary horizontal band spanning from the top edge of that row's S.No cell to the bottom edge of that same cell.
        - Any ink or mark found within that horizontal band belongs to THAT row's Signature cell, even if the ink visually appears closer to an adjacent row.
        - If a signature clearly spans two rows' horizontal bands (i.e., it is positioned between two rows), assign it to the UPPER row.
        - NEVER shift a signature down to the next row just because it is written low or near the bottom of its cell.
           
        3. For the "Signature" column, evaluate attendance using these STRICT rules:
           - Rule A (Clear Absence): If the box contains the isolated letter 'A', 'a', 'AB', 'Ab', 'ab' (often with a circle drawn around it), output "Absent".
           - Rule B (Empty): If the box is completely empty (just blank white space), or contains ONLY a tiny dot or dash (-), output "Absent".
           - Rule C (Clear Presence): If the box contains the isolated letter 'P', 'p', 'D', or 'd' (sometimes circled), output "Present".
           - Rule D (Signatures & Scribbles): If the box contains ANY cursive handwriting, signature, scribble, or ink (even if it has a strikethrough line drawn through it, like a name crossed out), output "Present". 
           - Rule E (A vs Signatures): NEVER classify a cursive name signature (like "Anish", "Ayush", "Ashutosh", "Aditya") as "Absent" just because it starts with A. Only isolated A/AB marks mean Absent.
           - Rule F (Combinations): If there is an 'A' and a 'D' together, or any ambiguous combination of ink, default to "Present".
        4. If a field is empty (other than signature), leave it as an empty string "".
        """

        max_retries = 20
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending image to OpenRouter Vision API (Attempt {attempt+1}/{max_retries}, Model: {self.model})...")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": base64_url}
                                }
                            ],
                        }
                    ],
                    temperature=0.0,
                    max_tokens=8192,
                )

                response_text = response.choices[0].message.content.strip()

                # Strip markdown code fences if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                response_text = response_text.strip()

                try:
                    raw_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # BULLETPROOF FALLBACK: Extract all 8-element string arrays using regex
                    try:
                        import re
                        matches = re.findall(r'\[\s*(?:"(?:[^"\\]|\\.)*"\s*,\s*){7}"(?:[^"\\]|\\.)*"\s*\]', response_text)

                        if matches:
                            raw_data = [json.loads(m) for m in matches]
                        else:
                            raise json.JSONDecodeError("No valid rows found via regex fallback.", response_text, 0)
                    except Exception:
                        logger.error(f"Failed to parse JSON from OpenRouter. Raw response:\n{response_text}")
                        return []

                keys = ["S_No", "S_G_No", "Groups", "UID", "Name", "Room_No", "Block", "Signature"]
                data = []

                # If model returned a dict wrapper like {"table": [...]}, unwrap it
                if isinstance(raw_data, dict):
                    for k, v in raw_data.items():
                        if isinstance(v, list):
                            raw_data = v
                            break
                    if isinstance(raw_data, dict):  # still a dict?
                        raw_data = []

                if isinstance(raw_data, list):
                    for row in raw_data:
                        if isinstance(row, list) and len(row) >= 8:
                            data.append(dict(zip(keys, row)))
                        elif isinstance(row, dict):
                            data.append(row)

                logger.info(f"Successfully extracted {len(data)} rows via OpenRouter Vision.")

                if len(data) == 0:
                    logger.warning(f"0 rows extracted! Raw OpenRouter Output was:\n{response_text}")

                return data

            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg or "rate" in error_msg:
                    logger.warning("OpenRouter Rate Limit (HTTP 429) reached. Sleeping for 60 seconds...")
                    time.sleep(60)
                elif "503" in error_msg or "unavailable" in error_msg:
                    logger.warning("OpenRouter Server Overloaded (HTTP 503). Sleeping for 30 seconds...")
                    time.sleep(30)
                else:
                    logger.error(f"OpenRouter API Error: {e}")
                    if attempt == max_retries - 1:
                        return []
                    time.sleep(5)  # short backoff for other errors

        return []

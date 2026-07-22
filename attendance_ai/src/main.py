import os
import sys
from pathlib import Path

# Add project root to sys.path so 'src' can be resolved
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from loguru import logger

from src.config.parser import load_config, Config
from src.utils.logger import setup_logger
from src.pdf.converter import PDFConverter

from src.preprocessing.enhancer import ImageEnhancer
from src.table.detector import TableDetector
from src.utils.empty_cell import get_cell_state, CellState
from src.ocr.engine import OCREngine
from src.ocr.llm_formatter import RuleFormatter
from src.attendance.engine import AttendanceEngine
from src.excel.generator import ExcelGenerator
from src.vision.gemini_engine import GeminiVisionEngine
import numpy as np


class AttendanceSystem:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        setup_logger(self.config.paths)
        logger.info("Initializing AI Attendance Recognition System...")
        
        self.pdf_converter = PDFConverter(dpi=300)
        if self.config.app.use_vision_api:
            logger.info("Vision API mode enabled. Initializing Gemini Vision engine...")
            self.vision_engine = GeminiVisionEngine()
        else:
            self.enhancer = ImageEnhancer()
            self.table_detector = TableDetector()
            self.ocr_engine = OCREngine(lang=self.config.ocr.lang, use_gpu=self.config.ocr.use_gpu)
            self.llm_formatter = RuleFormatter()
            self.attendance_engine = AttendanceEngine(self.config.attendance_rules, self.config.ocr)
        
        self._ensure_directories()

    def _ensure_directories(self):
        dirs = [
            self.config.paths.output_excel,
            self.config.paths.output_logs,
            self.config.paths.output_debug,
            self.config.paths.output_crops,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
    def process_all(self):
        logger.info("Starting batch processing...")
        
        pdf_dir = self.config.paths.input_pdfs
        if pdf_dir.exists():
            for pdf_file in pdf_dir.glob("*.pdf"):
                self.process_pdf(pdf_file)
                
        img_dir = self.config.paths.input_images
        valid_exts = {".png", ".jpg", ".jpeg"}
        if img_dir.exists():
            for img_file in img_dir.iterdir():
                if img_file.suffix.lower() in valid_exts:
                    self.process_image(img_file)
                    
        logger.info("Batch processing completed.")

    def process_pdf(self, pdf_path: Path):
        logger.info(f"Processing PDF: {pdf_path.name}")
        try:
            excel_gen = ExcelGenerator(self.config.paths.output_excel, filename=f"{pdf_path.stem}.xlsx")
            pages = self.pdf_converter.convert_pdf_to_images(pdf_path)
            for page_num, img_array in pages:
                self._process_single_image(img_array, pdf_path.name, page_num, excel_gen)
            excel_gen.save()
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path.name}: {e}")

    def process_image(self, img_path: Path):
        logger.info(f"Processing Image: {img_path.name}")
        try:
            excel_gen = ExcelGenerator(self.config.paths.output_excel, filename=f"{img_path.stem}.xlsx")
            img_array = cv2.imread(str(img_path))
            if img_array is None:
                raise ValueError(f"Could not read image file {img_path}")
            self._process_single_image(img_array, img_path.name, 1, excel_gen)
            excel_gen.save()
        except Exception as e:
            logger.error(f"Failed to process Image {img_path.name}: {e}")

    def _process_single_image(self, img_array, filename: str, page_num: int, excel_gen):
        logger.debug(f"Running pipeline for {filename} (Page {page_num})")
        
        if self.config.app.use_vision_api:
            data = self.vision_engine.parse_attendance_sheet(img_array)
            for row_idx, row in enumerate(data):
                excel_gen.add_record({
                    "s_no": str(row.get("S_No", "")),
                    "s_g_no": str(row.get("S_G_No", "")),
                    "groups": str(row.get("Groups", "")),
                    "uid": str(row.get("UID", "")),
                    "name": str(row.get("Name", "")),
                    "room_no": str(row.get("Room_No", "")),
                    "block": str(row.get("Block", "")),
                    "attendance": str(row.get("Signature", "")),
                    "detected_text": "Vision API",
                    "confidence": 1.0,
                    "decision_source": "Hugging Face Vision",
                    "file_name": filename,
                    "page_number": page_num
                })
                logger.info(f"Vision API Row {row_idx+1}: {row.get('Name', '')} - {row.get('Signature', '')}")
            return
            
        deskewed = self.enhancer.deskew(img_array)
        enhanced_binary = self.enhancer.enhance_for_table_detection(deskewed)
        
        table_crop = self.table_detector.detect(enhanced_binary, deskewed)
        if table_crop is None:
            logger.warning(f"No table detected in {filename} page {page_num}")
            return
            
        if self.config.app.debug_mode:
            cv2.imwrite(str(self.config.paths.output_debug / f"table_{filename}_p{page_num}.png"), table_crop)

        # Detect column boundaries
        gray_table = cv2.cvtColor(table_crop, cv2.COLOR_BGR2GRAY)
        binary_table = cv2.adaptiveThreshold(gray_table, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 10)
        _, v_lines = self.table_detector.get_lines(binary_table)
        
        v_proj = np.sum(v_lines, axis=0)
        x_peaks = np.where(v_proj > 255 * 10)[0]
        
        cols_x = []
        if len(x_peaks) > 0:
            current_col_x = [x_peaks[0]]
            for x in x_peaks[1:]:
                if x - current_col_x[-1] < 10:
                    current_col_x.append(x)
                else:
                    cols_x.append(int(np.mean(current_col_x)))
                    current_col_x = [x]
            cols_x.append(int(np.mean(current_col_x)))
            
        logger.debug(f"Detected column boundaries: {cols_x}")
            
        logger.info(f"Running full-table OCR for {filename} page {page_num}...")
        ocr_result = self.ocr_engine.ocr.ocr(table_crop, cls=True)
        
        if not ocr_result or not ocr_result[0]:
            logger.warning(f"No text detected in table for {filename}")
            return
            
        boxes = []
        for line in ocr_result[0]:
            box = line[0]
            text = line[1][0]
            score = line[1][1]
            
            x1, y1 = int(box[0][0]), int(box[0][1])
            x2, y2 = int(box[2][0]), int(box[2][1])
            
            boxes.append({'text': text, 'x': x1, 'y': y1, 'w': x2 - x1, 'h': y2 - y1, 'cy': (y1 + y2) // 2, 'score': score})
            
        # Group into rows by Y-coordinate
        boxes.sort(key=lambda b: b['cy'])
        rows = []
        current_row = [boxes[0]]
        
        for box in boxes[1:]:
            avg_cy = np.mean([b['cy'] for b in current_row])
            if abs(box['cy'] - avg_cy) < 15:
                current_row.append(box)
            else:
                rows.append(current_row)
                current_row = [box]
        rows.append(current_row)
        
        logger.info(f"Extracted {len(rows)} potential rows")
        
        data_rows = []
        for row in rows:
            row.sort(key=lambda b: b['x'])
            if len(row) >= 5 and row[0]['text'].isdigit():
                data_rows.append(row)
                
        logger.info(f"Found {len(data_rows)} data rows.")
        
        for row_idx, row in enumerate(data_rows):
            texts = [b['text'] for b in row]
            
            raw_texts = [""] * 8
            
            # Determine row Y boundaries based on OCR boxes
            min_y = min([b['y'] for b in row])
            max_y = max([b['y'] + b['h'] for b in row])
            # Add some padding to capture the full cell
            min_y = max(0, min_y - 5)
            max_y = min(table_crop.shape[0], max_y + 5)
            
            # Determine 8th column X boundaries
            sig_x1, sig_x2 = 0, table_crop.shape[1]
            if len(cols_x) >= 9:
                # Assuming 8 columns, there are 9 lines
                sig_x1 = cols_x[7]
                sig_x2 = cols_x[8]
            elif len(cols_x) >= 8:
                sig_x1 = cols_x[7]
                sig_x2 = table_crop.shape[1]
            else:
                # Fallback if lines not perfectly detected: use rightmost OCR box as reference
                if len(row) >= 7:
                    sig_x1 = row[6]['x'] + row[6]['w'] + 5
            
            # Crop the signature cell
            sig_crop = table_crop[min_y:max_y, sig_x1:sig_x2]
            
            if self.config.app.debug_mode and sig_crop.size > 0:
                cv2.imwrite(str(self.config.paths.output_crops / f"{filename}_p{page_num}_r{row_idx}_sig.png"), sig_crop)
                
            cell_state = get_cell_state(sig_crop)
            
            # Figure out what OCR text belongs to the signature column
            att_ocr_text = ""
            att_ocr_conf = 1.0
            
            # If the last OCR box falls into the signature column X range
            for b in row:
                if b['x'] > sig_x1 - 10:  # Box starts inside or very close to signature column
                    att_ocr_text = b['text']
                    att_ocr_conf = b['score']
                    break
                    
            if len(row) >= 8 and not att_ocr_text:
                 # Fallback: if there are 8+ boxes but none matched the X logic, just take the 8th
                 att_ocr_text = row[7]['text']
                 att_ocr_conf = row[7]['score']

            raw_texts[:min(8, len(texts))] = texts[:min(8, len(texts))]
                
            formatted_data = self.llm_formatter.format_row(raw_texts[:7])
            
            decision = self.attendance_engine.evaluate(cell_state, att_ocr_text, att_ocr_conf)
            
            excel_gen.add_record({
                "s_no": formatted_data.get("S_No", ""),
                "s_g_no": formatted_data.get("S_G_No", ""),
                "groups": formatted_data.get("Groups", ""),
                "uid": formatted_data.get("UID", "UNKNOWN"),
                "name": formatted_data.get("Name", "UNKNOWN"),
                "room_no": formatted_data.get("Room_No", ""),
                "block": formatted_data.get("Block", ""),
                "attendance": decision.status,
                "detected_text": decision.detected_text,
                "confidence": decision.confidence,
                "decision_source": decision.source,
                "file_name": filename,
                "page_number": page_num
            })
            
            logger.info(f"--- ROW {row_idx+1} ---")
            logger.info(f"Raw OCR    : {texts}")
            logger.info(f"AI Cleaned : {formatted_data}")
            logger.info(f"Attendance : {decision.status} [{decision.source}] (State: {cell_state.name})")
            logger.info("-" * 20)


if __name__ == "__main__":
    config_file = Path("config.yaml")
    if not config_file.exists():
        print(f"Error: {config_file} not found in current directory.", file=sys.stderr)
        sys.exit(1)
        
    try:
        system = AttendanceSystem(config_path=str(config_file))
        system.process_all()
    except Exception as e:
        print(f"Fatal error during execution: {e}", file=sys.stderr)
        sys.exit(1)

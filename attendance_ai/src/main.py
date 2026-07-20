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
from src.utils.empty_cell import is_cell_empty
from src.ocr.engine import OCREngine
from src.ocr.llm_formatter import LLMFormatter
from src.attendance.engine import AttendanceEngine
from src.excel.generator import ExcelGenerator
import numpy as np


class AttendanceSystem:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        setup_logger(self.config.paths)
        logger.info("Initializing AI Attendance Recognition System...")
        
        self.pdf_converter = PDFConverter(dpi=300)
        self.enhancer = ImageEnhancer()
        self.table_detector = TableDetector()
        self.ocr_engine = OCREngine(lang=self.config.ocr.lang, use_gpu=self.config.ocr.use_gpu)
        self.llm_formatter = LLMFormatter()
        self.attendance_engine = AttendanceEngine(self.config.attendance_rules, self.config.ocr)
        self.excel_generator = ExcelGenerator(self.config.paths.output_excel)
        
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
                    
        self.excel_generator.save()
        logger.info("Batch processing completed.")

    def process_pdf(self, pdf_path: Path):
        logger.info(f"Processing PDF: {pdf_path.name}")
        try:
            pages = self.pdf_converter.convert_pdf_to_images(pdf_path)
            for page_num, img_array in pages:
                self._process_single_image(img_array, pdf_path.name, page_num)
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path.name}: {e}")

    def process_image(self, img_path: Path):
        logger.info(f"Processing Image: {img_path.name}")
        try:
            img_array = cv2.imread(str(img_path))
            if img_array is None:
                raise ValueError(f"Could not read image file {img_path}")
            self._process_single_image(img_array, img_path.name, 1)
        except Exception as e:
            logger.error(f"Failed to process Image {img_path.name}: {e}")

    def _process_single_image(self, img_array, filename: str, page_num: int):
        logger.debug(f"Running pipeline for {filename} (Page {page_num})")
        
        deskewed = self.enhancer.deskew(img_array)
        enhanced_binary = self.enhancer.enhance_for_table_detection(deskewed)
        
        table_crop = self.table_detector.detect(enhanced_binary, deskewed)
        if table_crop is None:
            logger.warning(f"No table detected in {filename} page {page_num}")
            return
            
        if self.config.app.debug_mode:
            cv2.imwrite(str(self.config.paths.output_debug / f"table_{filename}_p{page_num}.png"), table_crop)
            
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
            if len(row) >= 8:
                raw_texts[:8] = texts[:8]
                att_ocr_text = texts[7]
                att_ocr_conf = row[7]['score']
                is_empty = False
            elif len(row) == 7:
                # Missing signature
                raw_texts[:7] = texts
                att_ocr_text = ""
                att_ocr_conf = 1.0
                is_empty = True
            else:
                # Less than 7 or other issues
                raw_texts[:len(texts)] = texts
                att_ocr_text = ""
                att_ocr_conf = 1.0
                is_empty = True
                
            formatted_data = self.llm_formatter.format_row(raw_texts[:7])
            
            decision = self.attendance_engine.evaluate(is_empty, att_ocr_text, att_ocr_conf)
            
            self.excel_generator.add_record({
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
            logger.info(f"Attendance : {decision.status} [{decision.source}]")
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

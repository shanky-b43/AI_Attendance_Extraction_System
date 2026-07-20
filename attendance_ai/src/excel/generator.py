import openpyxl
from pathlib import Path
from loguru import logger
from typing import Dict

class ExcelGenerator:
    """
    Generates Excel reports for attendance results.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "attendance_result.xlsx"
        self._init_workbook()

    def _init_workbook(self):
        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active
        self.ws.title = "Attendance Results"
        
        headers = [
            "S. No",
            "S. G No.",
            "Groups",
            "UID",
            "Name",
            "Room No",
            "Block",
            "Signature (Attendance)",
            "Detected Text",
            "Confidence",
            "Decision Source",
            "File Name",
            "Page Number"
        ]
        
        self.ws.append(headers)
        
        for cell in self.ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)
            
    def add_record(self, record: Dict):
        row = [
            record.get("s_no", ""),
            record.get("s_g_no", ""),
            record.get("groups", ""),
            record.get("uid", ""),
            record.get("name", ""),
            record.get("room_no", ""),
            record.get("block", ""),
            record.get("attendance", ""),
            record.get("detected_text", ""),
            record.get("confidence", 0.0),
            record.get("decision_source", ""),
            record.get("file_name", ""),
            record.get("page_number", 1)
        ]
        self.ws.append(row)

    def save(self):
        try:
            self.wb.save(self.output_file)
            logger.info(f"Successfully saved Excel report to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to save Excel file: {e}")

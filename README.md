# AI_Attendance_Extraction_System

An offline, production-ready AI application that automatically extracts attendance information from scanned PDF or image files and generates an Excel report.

Features
Offline Processing: No cloud APIs or internet connection required.
Multi-format Support: Processes PDFs, PNGs, and JPEGs.
Computer Vision Pipeline: Deskews images, detects tables, and extracts rows/cells automatically.
Empty Cell Detection: Skips OCR on blank cells using pixel intensity analysis.
OCR Engine: Uses PaddleOCR for robust offline text recognition.
Rule Engine: Applies configurable business rules to determine Present/Absent/Review statuses.
Debug Mode: Saves intermediate crops (tables, rows, cells) for manual verification.
Architecture Pipeline
Input -> PDF Converter -> Image Enhancement -> Table Detection -> Row Detection -> Cell Extraction -> Empty Cell Check -> OCR -> Rule Engine -> Excel Output

Folder Structure
attendance_ai/
├── input/
│   ├── pdfs/            # Place multi-page or single-page PDFs here
│   └── images/          # Place JPG/PNG images here
├── output/
│   ├── excel/           # Final attendance_result.xlsx
│   ├── logs/            # Execution logs
│   ├── debug/           # Full page & table debug images
│   └── crops/           # Individual cell crops (Reg No, Name, Attendance)
├── src/                 # Source code modules
├── config.yaml          # Application configuration
├── requirements.txt     # Python dependencies
└── main.py              # Main execution script
Installation
Ensure you have Python 3.10 or 3.11 installed.
Install dependencies:
pip install -r requirements.txt
Configuration
All settings are stored in config.yaml.

Edit attendance_rules to define what constitutes a present/absent mark.
Edit ocr.confidence_threshold (default 0.90) to determine when an item is flagged for Review.
Toggle app.debug_mode to enable/disable saving of cropped cell images.
How to Run
Place your scanned attendance sheets in input/pdfs/ or input/images/.
Run the main pipeline:
python src/main.py
Check output/excel/attendance_result.xlsx for the results.
Troubleshooting
PaddleOCR Installation Issues: Ensure you have the C++ build tools installed on Windows.
No Table Detected: Check output/debug/ to see the enhanced binary image. Ensure the scanned document has visible horizontal and vertical lines.
Future Improvements
Add Ollama/LLM fallback for low-confidence handwriting recognition.
Support for varying column layouts via dynamic mapping.

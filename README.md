<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<body>
<div class="container">

  <h1>AI Attendance Extraction System</h1>
  <p class="subtitle">An offline, production-ready AI application that automatically extracts attendance information from scanned PDF or image files and generates an Excel report.</p>

  <div class="badge-row">
    <span class="badge">100% Offline</span>
    <span class="badge">PaddleOCR</span>
    <span class="badge">Python 3.10 / 3.11</span>
    <span class="badge">PDF · PNG · JPEG</span>
  </div>

  <h2>Features</h2>
  <div class="feature-grid">
    <div class="feature-card">
      <strong>Offline Processing</strong>
      <span>No cloud APIs or internet connection required.</span>
    </div>
    <div class="feature-card">
      <strong>Multi-format Support</strong>
      <span>Processes PDFs, PNGs, and JPEGs.</span>
    </div>
    <div class="feature-card">
      <strong>Computer Vision Pipeline</strong>
      <span>Deskews images, detects tables, and extracts rows/cells automatically.</span>
    </div>
    <div class="feature-card">
      <strong>Empty Cell Detection</strong>
      <span>Skips OCR on blank cells using pixel intensity analysis.</span>
    </div>
    <div class="feature-card">
      <strong>OCR Engine</strong>
      <span>Uses PaddleOCR for robust offline text recognition.</span>
    </div>
    <div class="feature-card">
      <strong>Rule Engine</strong>
      <span>Applies configurable business rules to determine Present / Absent / Review statuses.</span>
    </div>
    <div class="feature-card">
      <strong>Debug Mode</strong>
      <span>Saves intermediate crops (tables, rows, cells) for manual verification.</span>
    </div>
  </div>

  <h2>Architecture Pipeline</h2>
  <div class="pipeline">
    <span class="pipe-step">Input</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">PDF Converter</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Image Enhancement</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Table Detection</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Row Detection</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Cell Extraction</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Empty Cell Check</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">OCR</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Rule Engine</span><span class="pipe-arrow">→</span>
    <span class="pipe-step">Excel Output</span>
  </div>

  <h2>Folder Structure</h2>
  <div class="folder-tree">attendance_ai/
├── input/
│   ├── pdfs/            <span class="comment"># Place multi-page or single-page PDFs here</span>
│   └── images/          <span class="comment"># Place JPG/PNG images here</span>
├── output/
│   ├── excel/           <span class="comment"># Final attendance_result.xlsx</span>
│   ├── logs/            <span class="comment"># Execution logs</span>
│   ├── debug/           <span class="comment"># Full page & table debug images</span>
│   └── crops/           <span class="comment"># Individual cell crops (Reg No, Name, Attendance)</span>
├── src/                 <span class="comment"># Source code modules</span>
├── config.yaml          <span class="comment"># Application configuration</span>
├── requirements.txt     <span class="comment"># Python dependencies</span>
└── main.py              <span class="comment"># Main execution script</span></div>

  <h2>Installation</h2>
  <p>Ensure you have Python 3.10 or 3.11 installed.</p>
  <p>Install dependencies:</p>
  <pre><code>pip install -r requirements.txt</code></pre>

  <h2>Configuration</h2>
  <p>All settings are stored in <code>config.yaml</code>.</p>
  <ul>
    <li>Edit <code>attendance_rules</code> to define what constitutes a present/absent mark.</li>
    <li>Edit <code>ocr.confidence_threshold</code> (default <code>0.90</code>) to determine when an item is flagged for Review.</li>
    <li>Toggle <code>app.debug_mode</code> to enable/disable saving of cropped cell images.</li>
  </ul>

  <h2>How to Run</h2>
  <div class="steps">
    <ol>
      <li>Place your scanned attendance sheets in <code>input/pdfs/</code> or <code>input/images/</code>.</li>
      <li>Run the main pipeline:
        <pre><code>python src/main.py</code></pre>
      </li>
      <li>Check <code>output/excel/attendance_result.xlsx</code> for the results.</li>
    </ol>
  </div>

  <h2>Troubleshooting</h2>
  <table>
    <tr><th>Issue</th><th>Fix</th></tr>
    <tr>
      <td>PaddleOCR Installation Issues</td>
      <td>Ensure you have the C++ build tools installed on Windows.</td>
    </tr>
    <tr>
      <td>No Table Detected</td>
      <td>Check <code>output/debug/</code> to see the enhanced binary image. Ensure the scanned document has visible horizontal and vertical lines.</td>
    </tr>
  </table>

  <h2>Future Improvements</h2>
  <ul>
    <li>Add Ollama/LLM fallback for low-confidence handwriting recognition.</li>
    <li>Support for varying column layouts via dynamic mapping.</li>
  </ul>

  <div class="footer-note">
    AI_Attendance_Extraction_System — offline OCR-based attendance pipeline.
  </div>

</div>
</body>
</html>

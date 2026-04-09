# PDF Document Scanner

A Python utility for extracting text and barcodes from PDF and image files (PNG, JPG) using open-source tools (Tesseract OCR and pyzbar). Designed to identify specific document identifiers like INBSHIP and BATCH numbers with built-in OCR error correction. AWS Lambda compatible for serverless document processing.

## Features

- **Text Extraction**: Uses Tesseract OCR to extract text from PDFs and images
- **Barcode Detection**: Detects and decodes barcodes using pyzbar
- **Identifier Recognition**: Finds specific patterns (INBSHIP, BATCH numbers) with configurable regex patterns
- **OCR Error Correction**: Normalizes common OCR mistakes (O→0, I→1, S→5, etc.)
- **Multi-format Support**: Handles PDF, PNG, and JPG files
- **AWS Lambda Ready**: Designed as a Lambda handler for serverless deployment
- **Flexible Detection**: Testing mode returns all matches; production mode stops at first match

## Tech Stack

- **Python 3.x**
- **PyPDF2**: PDF manipulation
- **Tesseract OCR**: Text extraction from images
- **pyzbar**: Barcode detection
- **Pillow (PIL)**: Image processing

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pdf-document-scanner.git
   cd pdf-document-scanner
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Ensure Tesseract OCR is installed on your system:
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `apt-get install tesseract-ocr`
   - **Windows**: Download installer from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

The main entry point is the `lambda_handler` function in `lambda_handler_no_textract.py`:

```python
import json
import base64
from lambda_handler_no_textract import lambda_handler

# Read an image file
with open('image.png', 'rb') as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

# Create event payload
event = {
    "body": image_base64,
    "isBase64Encoded": True,
    "options": {
        "extract_barcodes": True
    }
}

# Process document
result = lambda_handler(event, None)
print(json.loads(result['body']))
```

Run tests with:
```bash
python test_lambda.py
```

## Configuration

Edit `lambda_handler_no_textract.py` to configure:
- `ENABLE_BARCODE_DETECTION`: Enable/disable barcode scanning
- `TESTING_MODE`: Return all matches vs. stop at first match
- Custom regex patterns for identifier detection

## License

MIT
# PDF Document Scanner with OCR and Barcode Detection

A Python tool for extracting identifiers from PDF and image documents using Tesseract OCR and barcode detection, without requiring AWS Textract. Designed to extract INBSHIP and BATCH identifiers from shipping/logistics documents with configurable detection strategies.

## Features

- **OCR Text Extraction**: Uses Tesseract to extract text from PDFs and images
- **Barcode Detection**: Scans for barcodes using pyzbar library
- **Pattern Matching**: Identifies specific identifiers (INBSHIP, BATCH numbers) with OCR error tolerance
- **Configurable Detection**: Supports testing mode for comprehensive analysis or production mode for fast matching
- **Multi-Format Support**: Handles PDF, JPG, and PNG files
- **AWS Lambda Ready**: Designed as serverless function with base64-encoded input/output

## Tech Stack

- **Python** 3.6+
- **PyPDF2** - PDF processing
- **Tesseract OCR** - Text extraction
- **pyzbar** - Barcode detection
- **Pillow (PIL)** - Image processing

## Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install system dependencies**:
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `apt-get install tesseract-ocr`
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

## Usage

```python
from lambda_handler_no_textract import DocumentProcessor

processor = DocumentProcessor()

# Extract identifiers from a document
# The DocumentProcessor supports PDF and image files
# Configure detection strategy via ENABLE_BARCODE_DETECTION and TESTING_MODE
```

For AWS Lambda, the handler expects:
```json
{
  "body": "<base64-encoded-image>",
  "isBase64Encoded": true,
  "options": {
    "extract_barcodes": true
  }
}
```

Run tests with:
```bash
python test_lambda.py
```

## Configuration

- `ENABLE_BARCODE_DETECTION`: Enable/disable barcode scanning
- `TESTING_MODE`: When True, tries all detection methods; when False, returns first match
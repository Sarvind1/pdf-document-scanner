# PDF Document Scanner

A Python library for extracting identifiers from PDF documents and images using OCR and barcode detection. Designed to identify INBSHIP and BATCH codes from documents without requiring AWS Textract.

## Features

- **Barcode Detection**: Extract barcodes using pyzbar
- **OCR Text Extraction**: Uses Tesseract for robust text recognition
- **Pattern Matching**: Configurable regex patterns to identify INBSHIP and BATCH codes
- **Error Recovery**: Handles common OCR errors (O→0, I→1, etc.)
- **Multiple Formats**: Supports PDF, JPG, PNG inputs
- **Testing Mode**: Process documents with all methods for debugging and comparison
- **AWS Lambda Compatible**: Can run as a Lambda handler with base64-encoded inputs

## Tech Stack

- **PyPDF2**: PDF document parsing and processing
- **Pillow (PIL)**: Image manipulation and conversion
- **pytesseract**: OCR engine (uses Tesseract)
- **pyzbar**: Barcode and QR code detection
- **Python 3.7+**

## Setup

### Prerequisites

Install system dependencies:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Installation

```bash
pip install -r requirements.txt
```

Required packages:
- PyPDF2
- Pillow
- pytesseract
- pyzbar

## Usage

### Basic Usage

```python
from lambda_handler_no_textract import DocumentProcessor

processor = DocumentProcessor()
processor.ENABLE_BARCODE_DETECTION = True
processor.TESTING_MODE = False  # Stop at first match

# Process a PDF file
results = processor.process_file('document.pdf')
print(results)
```

### AWS Lambda

The module includes a Lambda handler for serverless deployment:

```python
event = {
    "body": base64_encoded_image,
    "isBase64Encoded": True,
    "options": {
        "extract_barcodes": True
    }
}

result = lambda_handler(event, None)
```

### Testing

Run the test suite:

```bash
python test_lambda.py
```

## Configuration

Edit `DocumentProcessor` settings:
- `ENABLE_BARCODE_DETECTION`: Enable/disable barcode extraction
- `TESTING_MODE`: Return all results (True) or stop at first match (False)

Detection priority (when `TESTING_MODE=False`):
1. INBSHIP via barcode
2. INBSHIP via OCR
3. BATCH via OCR
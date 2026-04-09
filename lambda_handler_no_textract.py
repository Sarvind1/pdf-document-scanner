import json
import re
from io import BytesIO
from typing import List, Dict, Optional
import base64
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import pytesseract
from pyzbar import pyzbar

class DocumentProcessor:
    """
    Document processor using open-source tools (no AWS Textract needed)
    - Tesseract OCR for text extraction
    - pyzbar for barcode detection
    - Supports: PDF, JPG, PNG
    """

    # ============================================
    # CONFIGURATION
    # ============================================
    ENABLE_BARCODE_DETECTION = True   # Enable/disable barcode detection
    TESTING_MODE = False               # When True: tries all methods and returns all results
                                       # When False: stops at first match

    # Detection Strategy (when TESTING_MODE = False):
    # 1. Try INBSHIP via barcode
    # 2. Try INBSHIP via text (OCR)
    # 3. Try BATCH via text (OCR)
    # Returns as soon as one is found
    # ============================================

    def __init__(self):
        # Define specific patterns for identifiers
        # BATCH = BATCH + 7 digits, INBSHIP = INBSHIP + 5 digits
        # OCR-friendly patterns that handle common errors (O->0, I->1, etc.)
        self.patterns = {
            'inbship': [
                re.compile(r'INBSHIP\s*(\d{5})', re.IGNORECASE),
                re.compile(r'INBSHIP[#:\s]+(\d{5})', re.IGNORECASE)
            ],
            'batch': [
                re.compile(r'BATCH\s*(\d{7})', re.IGNORECASE),
                re.compile(r'BATCH[#:\s]+(\d{7})', re.IGNORECASE),
                # OCR-friendly: handle O->0 errors at start of number
                re.compile(r'BATCH([O0o]\d{6})', re.IGNORECASE),
                re.compile(r'BATCH[#:\s]+([O0o]\d{6})', re.IGNORECASE)
            ]
        }

    def _normalize_ocr_digits(self, text: str) -> str:
        """
        Normalize common OCR errors in digit strings
        O->0, I/l->1, S->5, B->8
        """
        # Only normalize characters that look like numbers
        replacements = {
            'O': '0',
            'o': '0',
            'I': '1',
            'l': '1',
            'S': '5',
            's': '5',
            'B': '8'
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _detect_file_type(self, file_bytes: bytes) -> str:
        """
        Detect file type from magic bytes
        Returns: 'pdf', 'jpeg', 'png', or 'unknown'
        """
        if file_bytes.startswith(b'%PDF'):
            return 'pdf'
        elif file_bytes.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        else:
            return 'unknown'

    def _convert_image_to_pdf(self, image_bytes: bytes) -> bytes:
        """
        Convert image (JPG, PNG) to PDF format
        """
        try:
            # Open image using PIL
            image = Image.open(BytesIO(image_bytes))

            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image

            # Save as PDF
            pdf_output = BytesIO()
            image.save(pdf_output, format='PDF')
            pdf_output.seek(0)

            return pdf_output.read()

        except Exception as e:
            print(f"Error converting image to PDF: {str(e)}")
            raise

    def _pdf_page_to_image(self, page_bytes: bytes) -> Image.Image:
        """
        Convert PDF page to PIL Image for OCR processing
        """
        try:
            # For Lambda, we'll need pdf2image or similar
            # For now, try to open as image directly or use PyMuPDF
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=page_bytes, filetype="pdf")
                page = doc[0]
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                return Image.open(BytesIO(img_bytes))
            except ImportError:
                # Fallback: try to open directly (works if page_bytes is already an image)
                return Image.open(BytesIO(page_bytes))

        except Exception as e:
            print(f"Error converting PDF page to image: {str(e)}")
            raise

    def process_document(self, file_bytes: bytes, extract_barcodes: bool = True) -> List[Dict]:
        """
        Main processing function for documents (PDF, JPG, PNG)
        Strategy: Try barcode detection first, fall back to text extraction

        Args:
            file_bytes: Document file as bytes (PDF, JPG, or PNG)
            extract_barcodes: Whether to try barcode detection first

        Returns:
            List of page-wise extraction results with base64 page data
        """
        results = []

        try:
            # Detect file type
            file_type = self._detect_file_type(file_bytes)
            print(f"Detected file type: {file_type}")

            # Handle different file types
            if file_type in ('jpeg', 'png'):
                # For images, keep original bytes and convert to PDF
                original_image_bytes = file_bytes
                pdf_bytes = self._convert_image_to_pdf(file_bytes)
                page_bytes_list = [(pdf_bytes, original_image_bytes)]  # (PDF for output, original for OCR)
                print(f"Converted {file_type.upper()} image to PDF")
            elif file_type == 'pdf':
                # Split PDF into individual pages
                pdf_pages = self._split_pdf_to_pages(file_bytes)
                page_bytes_list = [(p, None) for p in pdf_pages]  # (PDF, no original)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            total_pages = len(page_bytes_list)
            print(f"Processing document with {total_pages} pages")

            # Process each page individually
            for page_num, (page_pdf_bytes, original_image_bytes) in enumerate(page_bytes_list, start=1):
                page_result = {
                    'page': page_num,
                    'method': None,
                    'field': None,
                    'data': None,
                    'confidence': 0.0,
                    'page_data_base64': base64.b64encode(page_pdf_bytes).decode('utf-8')
                }

                # In testing mode, collect all results
                all_test_results = [] if self.TESTING_MODE else None

                # Convert page to image for processing
                # Use original image if available (better quality for OCR)
                try:
                    if original_image_bytes:
                        # Direct image file - best quality
                        image = Image.open(BytesIO(original_image_bytes))
                    else:
                        # PDF page - needs conversion
                        image = self._pdf_page_to_image(page_pdf_bytes)
                except Exception as e:
                    print(f"Error loading image: {e}")
                    # Fallback: try opening as direct image
                    image = Image.open(BytesIO(page_pdf_bytes))

                found = False

                # Strategy: Try in order until one succeeds (unless testing mode)
                # 1. Try INBSHIP via barcode
                if self.ENABLE_BARCODE_DETECTION and extract_barcodes:
                    print(f"  Trying INBSHIP via barcode...")
                    barcodes = self._detect_barcodes_from_image(image)
                    if barcodes:
                        for barcode in barcodes:
                            inbship_match = re.search(r'INBSHIP(\d{5})', barcode, re.IGNORECASE)
                            if inbship_match:
                                result = {
                                    'method': 'barcode',
                                    'field': 'inbship',
                                    'data': inbship_match.group(1),
                                    'confidence': 100.0
                                }
                                print(f"    ✓ Found INBSHIP via barcode: {result['data']}")

                                if self.TESTING_MODE:
                                    all_test_results.append(result)
                                else:
                                    page_result.update(result)
                                    found = True
                                    break

                # 2. Try INBSHIP via text (OCR)
                if not found or self.TESTING_MODE:
                    print(f"  Trying INBSHIP via text (OCR)...")
                    text_result = self._extract_text_from_image(image)
                    if text_result.get('inbship'):
                        result = {
                            'method': 'text',
                            'field': 'inbship',
                            'data': text_result['inbship'],
                            'confidence': text_result.get('confidence', 0.0)
                        }
                        print(f"    ✓ Found INBSHIP via text: {result['data']}")

                        if self.TESTING_MODE:
                            all_test_results.append(result)
                        else:
                            page_result.update(result)
                            found = True

                # 3. Try BATCH via text (OCR)
                if not found or self.TESTING_MODE:
                    print(f"  Trying BATCH via text (OCR)...")
                    # Reuse text extraction if already done
                    if 'text_result' not in locals():
                        text_result = self._extract_text_from_image(image)

                    if text_result.get('batch'):
                        result = {
                            'method': 'text',
                            'field': 'batch',
                            'data': text_result['batch'],
                            'confidence': text_result.get('confidence', 0.0)
                        }
                        print(f"    ✓ Found BATCH via text: {result['data']}")

                        if self.TESTING_MODE:
                            all_test_results.append(result)
                        else:
                            page_result.update(result)
                            found = True

                # Handle results
                if self.TESTING_MODE:
                    # In testing mode, return all found results
                    if all_test_results:
                        for test_result in all_test_results:
                            result_copy = page_result.copy()
                            result_copy.update(test_result)
                            results.append(result_copy)
                    else:
                        # No results found
                        page_result['method'] = 'none'
                        page_result['field'] = None
                        results.append(page_result)
                else:
                    # Normal mode - return first match or none
                    if not found:
                        page_result['method'] = 'none'
                        page_result['field'] = None
                        print(f"  ✗ No identifiers found")
                    results.append(page_result)

        except Exception as e:
            print(f"Error in process_document: {str(e)}")
            raise

        return results

    def _split_pdf_to_pages(self, pdf_bytes: bytes) -> List[bytes]:
        """
        Split PDF into individual pages and return as bytes
        """
        pages = []
        try:
            pdf_reader = PdfReader(BytesIO(pdf_bytes))

            for page_num in range(len(pdf_reader.pages)):
                # Create a new PDF writer for this page
                pdf_writer = PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[page_num])

                # Write to bytes
                page_output = BytesIO()
                pdf_writer.write(page_output)
                page_output.seek(0)
                pages.append(page_output.read())

        except Exception as e:
            print(f"Error splitting PDF: {str(e)}")
            raise

        return pages

    def _detect_barcodes_from_image(self, image: Image.Image) -> List[str]:
        """
        Detect barcodes from an image using pyzbar
        """
        try:
            # Decode barcodes
            barcodes = pyzbar.decode(image)

            results = []
            for barcode in barcodes:
                # Get barcode data as string
                barcode_data = barcode.data.decode('utf-8')
                print(f"Detected barcode: {barcode_data}")

                # Check if it matches our patterns
                if re.search(r'(BATCH\d{7}|INBSHIP\d{5})', barcode_data, re.IGNORECASE):
                    results.append(barcode_data)

            return results

        except Exception as e:
            print(f"Barcode detection error: {str(e)}")
            return []

    def _extract_text_from_image(self, image: Image.Image) -> Dict:
        """
        Extract text from image using Tesseract OCR
        """
        try:
            # Use Tesseract to extract text
            text = pytesseract.image_to_string(image)

            # Extract patterns
            inbship = self._extract_with_patterns(text, 'inbship')
            batch = self._extract_with_patterns(text, 'batch')

            # Get confidence (Tesseract provides this)
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except:
                avg_confidence = 0.0

            return {
                'inbship': inbship,
                'batch': batch,
                'confidence': round(avg_confidence, 2)
            }

        except Exception as e:
            print(f"Text extraction error: {str(e)}")
            return {
                'inbship': None,
                'batch': None,
                'confidence': 0.0
            }

    def _extract_with_patterns(self, text: str, pattern_type: str) -> Optional[str]:
        """Try multiple patterns to extract value and normalize OCR errors"""
        patterns = self.patterns.get(pattern_type, [])

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                # Normalize OCR errors (O->0, I->1, etc.)
                normalized = self._normalize_ocr_digits(value)
                return normalized

        return None


def lambda_handler(event, _context):
    """
    Lambda handler using open-source OCR (no AWS Textract needed)
    Supports: PDF, JPG, PNG file formats

    Expected event:
    {
        "body": "<base64-encoded-file-content>",  # PDF, JPG, or PNG
        "isBase64Encoded": true,
        "options": {
            "extract_barcodes": true
        }
    }

    Response format:
    {
        "success": true,
        "results": [
            {
                "page": 1,
                "method": "barcode" | "text" | "none",
                "field": "inbship" | "batch" | null,
                "data": "12345",  // The actual value found
                "confidence": 100.0,
                "page_data_base64": "<base64-encoded-page-pdf>"
            }
        ],
        "summary": {
            "total_results": 1,
            "by_method": {
                "barcode": 1,
                "text": 0,
                "none": 0
            },
            "by_field": {
                "inbship": 1,
                "batch": 0
            }
        }
    }

    Note: In TESTING_MODE, multiple results per page may be returned (one for each method tried)
    """

    processor = DocumentProcessor()

    try:
        # Parse options
        options = event.get('options', {})
        extract_barcodes = options.get('extract_barcodes', True)

        # Get file bytes (supports PDF, JPG, PNG)
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            file_bytes = base64.b64decode(body)
        else:
            file_bytes = body.encode('utf-8') if isinstance(body, str) else body

        # Validate file
        if not file_bytes or len(file_bytes) < 100:
            raise ValueError("Invalid or empty file content")

        # Process document (PDF, JPG, or PNG)
        results = processor.process_document(file_bytes, extract_barcodes)

        # Calculate summary statistics
        summary = {
            'total_results': len(results),
            'by_method': {
                'barcode': sum(1 for r in results if r.get('method') == 'barcode'),
                'text': sum(1 for r in results if r.get('method') == 'text'),
                'none': sum(1 for r in results if r.get('method') == 'none')
            },
            'by_field': {
                'inbship': sum(1 for r in results if r.get('field') == 'inbship'),
                'batch': sum(1 for r in results if r.get('field') == 'batch')
            }
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'results': results,
                'summary': summary
            }, indent=2)
        }

    except Exception as e:
        print(f"Lambda error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
        }

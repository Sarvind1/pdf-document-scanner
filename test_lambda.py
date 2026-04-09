#!/usr/bin/env python3
"""
Test script for lambda_handler_no_textract
"""
import json
import base64
from lambda_handler_no_textract import lambda_handler

# Read the image file and encode it
with open('image.png', 'rb') as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

# Create test event with the image
event = {
    "body": image_base64,
    "isBase64Encoded": True,
    "options": {
        "extract_barcodes": True
    }
}

# Test with the actual image
print("Testing lambda_handler_no_textract with image.png...")
print("=" * 60)

result = lambda_handler(event, None)

print("\nResponse:")
print(json.dumps(json.loads(result['body']), indent=2))
print("\nStatus Code:", result['statusCode'])

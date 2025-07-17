import os
import sys
from ai_parse import extract_items_with_ai
from PIL import Image
import pytesseract
import json

# Test with one of the failed receipts
receipt_file = 'data/receipts/4Mq4vTyd3eaF.jpeg'

print(f"Testing AI parser on failed receipt: {receipt_file}")
print("="*60)

# Extract OCR text
text = pytesseract.image_to_string(Image.open(receipt_file), lang='aze')
print("OCR Text (first 800 chars):")
print(text[:800])
print("="*60)

# Extract items with AI
items = extract_items_with_ai(text, os.path.basename(receipt_file))

print(f"Number of items extracted: {len(items)}")
print("="*60)

# Print extracted items
for i, item in enumerate(items):
    print(f"Item {i+1}:")
    print(f"  Name: {item.get('item_name', 'N/A')}")
    print(f"  Quantity: {item.get('quantity', 'N/A')}")
    print(f"  Unit Price: {item.get('unit_price', 'N/A')}")
    print(f"  Line Total: {item.get('line_total', 'N/A')}")
    print(f"  Store: {item.get('store_name', 'N/A')}")
    print()

if items:
    print("JSON output:")
    print(json.dumps(items[0], indent=2))
else:
    print("No items extracted!")
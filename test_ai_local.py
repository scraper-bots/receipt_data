import os
import sys
from ai_parse import validate_and_clean_item, try_fallback_parsing
import json

# Test the validation function
test_items = [
    {
        "filename": "test.jpeg",
        "item_name": "Test Item",
        "quantity": "1.0",
        "unit_price": "2.50",
        "line_total": "2.50",
        "store_name": "Test Store"
    },
    {
        "filename": "test.jpeg",
        "item_name": "Bad Item",
        "quantity": "1000",  # Should be fixed to 1.0
        "unit_price": "2.50",
        "line_total": "2.50",
        "store_name": "Test Store"
    },
    {
        "filename": "test.jpeg",
        "item_name": "",  # Should be rejected
        "quantity": "1.0",
        "unit_price": "2.50",
        "line_total": "2.50",
        "store_name": "Test Store"
    }
]

print("Testing validate_and_clean_item function:")
print("="*50)

for i, item in enumerate(test_items):
    print(f"Test item {i+1}: {item['item_name']}")
    result = validate_and_clean_item(item)
    if result:
        print(f"  ✓ Valid: {result['item_name']} - {result['quantity']} × {result['unit_price']} = {result['line_total']}")
    else:
        print(f"  ✗ Invalid item rejected")
    print()

# Test fallback parsing
print("Testing fallback parsing:")
print("="*50)

malformed_response = '''
Here are the items:
{"item_name": "Test Item 1", "quantity": "1.0", "unit_price": "2.50", "line_total": "2.50"}
{"item_name": "Test Item 2", "quantity": "2.0", "unit_price": "1.25", "line_total": "2.50"}
'''

fallback_result = try_fallback_parsing(malformed_response, "test.jpeg")
print(f"Fallback parsing extracted {len(fallback_result)} items")
for item in fallback_result:
    if item:
        print(f"  - {item['item_name']}")

print("\nAI parser improvements added:")
print("1. ✓ Retry logic with exponential backoff")
print("2. ✓ Better JSON parsing and error handling")
print("3. ✓ Fallback parsing for malformed responses")
print("4. ✓ Improved validation and cleaning")
print("5. ✓ Better logging and debugging")
print("6. ✓ Enhanced system prompt with clearer instructions")
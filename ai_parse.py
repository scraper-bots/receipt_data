import os
import re
import json
import pandas as pd
from PIL import Image
import pytesseract
import logging
from openai import OpenAI
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
RECEIPTS_DIR = 'data/receipts'
OUTPUT_CSV = 'data/ai_improved.csv'
BATCH_SIZE = 2  # Minimal batches for completion
MAX_WORKERS = 1  # Single worker for stability

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('openai'))

# Thread-safe counter
counter_lock = threading.Lock()
processed_count = 0

def extract_items_with_ai(ocr_text, filename):
    """
    Improved AI extraction that focuses on extracting ALL items with realistic values.
    """
    
    system_prompt = """You are an expert at extracting ALL items from Azerbaijani receipt OCR text.

CRITICAL REQUIREMENTS:
1. Extract EVERY item from the receipt - most receipts have multiple items
2. Look for the items section that starts with "Məhsulun adı Say Qiymət Cəmi" 
3. Each item should have: name, quantity, unit_price, line_total
4. Fix OCR errors in quantities - decimal places get misread:
   - 1000 → 1.0 (OCR misreads decimal as 000)
   - 2000 → 2.0 (OCR misreads decimal as 000)  
   - 13000 → 1.0 (OCR error)
   - Keep small realistic quantities (1-10 typical for most items)
5. Fix prices to be realistic for Azerbaijan:
   - Water: 0.5-1.5 AZN
   - Bread/cookies: 0.5-3 AZN
   - Drinks: 1-5 AZN
   - If unit_price seems wrong, adjust to realistic value
6. Ensure quantity × unit_price = line_total (fix calculation errors)
7. Clean item names: remove ƏDV codes, quotes, prefixes
8. Return ALL items found, not just the first one

The receipt-level info should be the SAME for each item (store info, date, etc.)
"""
    
    user_prompt = f"""Extract ALL items from this Azerbaijani receipt. Return a JSON array where each object has these 30 fields:

RECEIPT: {filename}

Required fields for each item:
{{
    "filename": "{filename}",
    "store_name": "Store/business name (same for all items)",
    "store_address": "Store address (same for all items)", 
    "store_code": "Store code (same for all items)",
    "taxpayer_name": "Taxpayer name (same for all items)",
    "tax_id": "VOEN number (same for all items)",
    "receipt_number": "Receipt number (same for all items)",
    "cashier_name": "Cashier name (same for all items)",
    "date": "DD.MM.YYYY (same for all items)",
    "time": "HH:MM:SS (same for all items)",
    "item_name": "Clean item name (NO ƏDV codes, quotes, or prefixes)",
    "quantity": "Realistic quantity (fix OCR errors: 1000→1, 2000→2, etc.)",
    "unit_price": "Realistic price per unit in AZN (fix if unrealistic)",
    "line_total": "quantity × unit_price (must be mathematically correct)",
    "subtotal": "Receipt total (same for all items)",
    "vat_18_percent": "VAT amount (same for all items)",
    "total_tax": "Total tax (same for all items)",
    "cashless_payment": "Cashless amount (same for all items)",
    "cash_payment": "Cash amount (same for all items)", 
    "bonus_payment": "Bonus amount (same for all items)",
    "advance_payment": "Advance amount (same for all items)",
    "credit_payment": "Credit amount (same for all items)",
    "queue_number": "Queue number (same for all items)",
    "cash_register_model": "Register model (same for all items)",
    "cash_register_serial": "Register serial (same for all items)",
    "fiscal_id": "Fiscal ID (same for all items)",
    "fiscal_registration": "Fiscal registration (same for all items)",
    "refund_amount": "Refund amount (same for all items)",
    "refund_date": "Refund date (same for all items)",
    "refund_time": "Refund time (same for all items)"
}}

EXAMPLES OF QUANTITY FIXES:
- "Paket Araz 31\"60 5 K 1.000 0.05 0.05" → quantity: 1, unit_price: 0.05, line_total: 0.05
- "SIRAB QAZSIZ SU PET 2.000 0.59 1.18" → quantity: 2, unit_price: 0.59, line_total: 1.18
- "BIQ BON QOVYAD QRİL 1.000 2.10 2.10" → quantity: 1, unit_price: 2.10, line_total: 2.10

OCR TEXT:
{ocr_text}

Return ONLY a valid JSON array with one object per item found."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Remove code block markers if present
        if ai_response.startswith('```json'):
            ai_response = ai_response.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        extracted_items = json.loads(ai_response)
        
        # Validate and clean each item
        validated_items = []
        for item in extracted_items:
            validated_item = validate_and_clean_item(item)
            if validated_item:
                validated_items.append(validated_item)
        
        return validated_items
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {filename}: {e}")
        return []
    
    except Exception as e:
        logger.error(f"AI extraction error for {filename}: {e}")
        return []

def validate_and_clean_item(item):
    """
    Validate and clean individual item data.
    """
    
    
    try:
        # Ensure required fields exist
        if not item.get('item_name') or item['item_name'] in [None, "null", ""]:
            return None
        
        # Validate and fix mathematical calculations
        if all(item.get(field) not in [None, "null", ""] for field in ['quantity', 'unit_price', 'line_total']):
            quantity = float(item['quantity'])
            unit_price = float(item['unit_price'])
            line_total = float(item['line_total'])
            
            # Fix calculation if incorrect
            expected_total = quantity * unit_price
            if abs(line_total - expected_total) > 0.01:
                item['line_total'] = f"{expected_total:.2f}"
                logger.info(f"Fixed calculation for {item.get('item_name', 'unknown')}: {quantity} × {unit_price} = {expected_total:.2f}")
        
        # Validate realistic quantities (flag suspicious values)
        if item.get('quantity') and item['quantity'] not in [None, "null", ""]:
            quantity = float(item['quantity'])
            if quantity > 50:
                logger.warning(f"Suspicious quantity for {item.get('item_name', 'unknown')}: {quantity}")
        
        # Validate realistic prices for Azerbaijan market
        if item.get('unit_price') and item['unit_price'] not in [None, "null", ""]:
            unit_price = float(item['unit_price'])
            if unit_price > 500:  # Very expensive item
                logger.warning(f"High price for {item.get('item_name', 'unknown')}: {unit_price} AZN")
        
        # Format monetary values
        monetary_fields = ['unit_price', 'line_total', 'subtotal', 'vat_18_percent', 'total_tax',
                          'cashless_payment', 'cash_payment', 'bonus_payment', 'advance_payment',
                          'credit_payment', 'refund_amount']
        
        for field in monetary_fields:
            if item.get(field) and item[field] not in [None, "null", ""]:
                try:
                    value = float(item[field])
                    item[field] = f"{value:.2f}"
                except (ValueError, TypeError):
                    item[field] = "0.00"
        
        # Clean item names
        if item.get('item_name'):
            item_name = item['item_name']
            # Remove VAT codes and prefixes
            item_name = re.sub(r'^v?ƏDV[:\s]*\d+[:\s]*', '', item_name)
            item_name = re.sub(r'^"?ƏDV[:\s]*\d+[:\s]*', '', item_name)
            item_name = re.sub(r'^ƏDV-dən\s+azad\s+', '', item_name)
            item_name = re.sub(r'^Ticarət\s+əlavəsi[:\s]*\d*\s*', '', item_name)
            item_name = re.sub(r'^["\']+|["\']+$', '', item_name)
            item_name = re.sub(r'\s+', ' ', item_name).strip()
            item['item_name'] = item_name
        
        return item
        
    except Exception as e:
        logger.error(f"Error validating item: {e}")
        return None

def create_fallback_data(filename):
    """
    Create fallback data structure when AI extraction fails.
    """
    
    return [{
        'filename': filename,
        'store_name': None,
        'store_address': None,
        'store_code': None,
        'taxpayer_name': None,
        'tax_id': None,
        'receipt_number': None,
        'cashier_name': None,
        'date': None,
        'time': None,
        'item_name': None,
        'quantity': None,
        'unit_price': None,
        'line_total': None,
        'subtotal': None,
        'vat_18_percent': None,
        'total_tax': None,
        'cashless_payment': "0.00",
        'cash_payment': "0.00",
        'bonus_payment': "0.00",
        'advance_payment': "0.00",
        'credit_payment': "0.00",
        'queue_number': None,
        'cash_register_model': None,
        'cash_register_serial': None,
        'fiscal_id': None,
        'fiscal_registration': None,
        'refund_amount': None,
        'refund_date': None,
        'refund_time': None,
        'error': 'AI extraction failed'
    }]

def process_receipt_with_ai(filepath, filename):
    """
    Process a single receipt using improved AI extraction.
    """
    
    global processed_count
    
    try:
        # Extract OCR text
        text = pytesseract.image_to_string(Image.open(filepath), lang='aze')
        
        # Get all items with AI
        items = extract_items_with_ai(text, filename)
        
        if not items:
            items = create_fallback_data(filename)
        
        # Update progress counter
        with counter_lock:
            processed_count += 1
            logger.info(f"Processed {processed_count}/62: {filename} - Found {len(items)} items")
        
        return items
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")
        with counter_lock:
            processed_count += 1
        return create_fallback_data(filename)

def process_batch(batch_files, batch_num):
    """
    Process a batch of receipts with threading.
    """
    
    batch_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all files in batch
        future_to_file = {}
        for filename in batch_files:
            filepath = os.path.join(RECEIPTS_DIR, filename)
            future = executor.submit(process_receipt_with_ai, filepath, filename)
            future_to_file[future] = filename
        
        # Collect results
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                result = future.result()
                batch_results.extend(result)  # Each receipt returns multiple items
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                batch_results.extend(create_fallback_data(filename))
    
    logger.info(f"Completed batch {batch_num} with {len(batch_results)} total records")
    return batch_results

def main():
    """Main function to run improved AI-enhanced receipt processing."""
    
    global processed_count
    
    # Check if OpenAI API key is available
    if not os.getenv('openai'):
        logger.error("OpenAI API key not found in .env file")
        return
    
    logger.info("Starting IMPROVED AI-enhanced receipt processing...")
    
    all_receipts_data = []
    
    # Get image files
    image_files = [f for f in os.listdir(RECEIPTS_DIR) if f.lower().endswith(('.jpeg', '.jpg', '.png', '.tiff'))]
    
    total_files = len(image_files)
    logger.info(f"Found {total_files} receipt images to process")
    
    # Process in batches
    for i in range(0, total_files, BATCH_SIZE):
        batch_files = image_files[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        logger.info(f"Processing batch {batch_num}/{(total_files + BATCH_SIZE - 1) // BATCH_SIZE}")
        
        batch_results = process_batch(batch_files, batch_num)
        all_receipts_data.extend(batch_results)
        
        # Rate limiting between batches
        time.sleep(3)
    
    # Create DataFrame
    df = pd.DataFrame(all_receipts_data)
    
    # Define column order (30 columns)
    column_order = [
        'filename', 'store_name', 'store_address', 'store_code', 'taxpayer_name',
        'tax_id', 'receipt_number', 'cashier_name', 'date', 'time',
        'item_name', 'quantity', 'unit_price', 'line_total', 'subtotal',
        'vat_18_percent', 'total_tax', 'cashless_payment', 'cash_payment', 'bonus_payment',
        'advance_payment', 'credit_payment', 'queue_number', 'cash_register_model',
        'cash_register_serial', 'fiscal_id', 'fiscal_registration', 'refund_amount',
        'refund_date', 'refund_time'
    ]
    
    # Ensure all columns exist
    for col in column_order:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns
    df = df.reindex(columns=column_order)
    
    # Save to CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    
    logger.info(f"✅ IMPROVED AI extraction complete! Data saved to '{OUTPUT_CSV}'")
    logger.info(f"Total records: {len(df)}")
    logger.info(f"Unique receipts: {len(df['filename'].unique())}")
    
    # Show summary statistics
    print("\n=== IMPROVED EXTRACTION SUMMARY ===")
    print(f"Total receipts processed: {len(df['filename'].unique())}")
    print(f"Total items extracted: {len(df)}")
    print(f"Average items per receipt: {len(df) / len(df['filename'].unique()):.1f}")
    print(f"Receipts with store names: {len(df[df['store_name'].notna()])}")
    print(f"Receipts with addresses: {len(df[df['store_address'].notna()])}")
    print(f"Receipts with item data: {len(df[df['item_name'].notna()])}")
    print(f"Receipts with date/time: {len(df[df['date'].notna()])}")

if __name__ == '__main__':
    main()
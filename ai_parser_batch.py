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
RECEIPTS_DIR = 'receipts'
OUTPUT_CSV = 'receipts_ai_enhanced.csv'
BATCH_SIZE = 10  # Process 10 receipts at a time
MAX_WORKERS = 3  # Limit concurrent API calls

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('openai'))

# Thread-safe counter
counter_lock = threading.Lock()
processed_count = 0

def extract_text_with_ai(ocr_text, filename):
    """
    Use OpenAI API to extract structured data from OCR text with error correction.
    """
    
    system_prompt = """You are an expert at extracting structured data from Azerbaijani receipt OCR text. 
    
    Your task is to:
    1. Extract all available information into the specified 30 fields
    2. Fix mathematical calculation errors (ensure quantity × unit_price = line_total)
    3. Validate and correct suspicious quantities (if >100, check if it's likely an OCR error)
    4. Extract multiple payment methods if present
    5. Clean item names by removing VAT codes and prefixes
    6. Format all monetary values to 2 decimal places
    7. Return "null" for missing fields, not empty strings
    
    Important: Be very careful with quantities. If you see a quantity >100, it's likely an OCR error where decimal points were missed.
    For example, 1000.0 units of bread is unrealistic - it should probably be 1.0 or 10.0.
    """
    
    user_prompt = f"""Extract data from this Azerbaijani receipt OCR text into exactly these 30 fields:

    REQUIRED FIELDS (return as JSON):
    {{
        "filename": "{filename}",
        "store_name": "Store/business name",
        "store_address": "Store address",
        "store_code": "Store/object code",
        "taxpayer_name": "Taxpayer name (Vergi ödəyicisinin adı)",
        "tax_id": "VOEN tax identification number",
        "receipt_number": "Receipt/check number (Satış çeki)",
        "cashier_name": "Cashier name (Kassir)",
        "date": "Transaction date (DD.MM.YYYY format)",
        "time": "Transaction time (HH:MM:SS format)",
        "item_name": "Product/item name (cleaned, no VAT codes)",
        "quantity": "Item quantity (VALIDATE if >100, likely OCR error)",
        "unit_price": "Price per unit",
        "line_total": "Total for item (must equal quantity × unit_price)",
        "subtotal": "Receipt subtotal (Cəmi)",
        "vat_18_percent": "VAT 18% amount (ƏDV 18%)",
        "total_tax": "Total tax amount (Toplam vergi)",
        "cashless_payment": "Cashless payment amount (Nağdsız)",
        "cash_payment": "Cash payment amount (Nağd)",
        "bonus_payment": "Bonus payment amount (Bonus)",
        "advance_payment": "Advance payment amount (Avans)",
        "credit_payment": "Credit payment amount (Nisyə)",
        "queue_number": "Queue/sequence number (Növbə)",
        "cash_register_model": "Cash register model (NKA-nın modeli)",
        "cash_register_serial": "Cash register serial (NKA-nın zavod nömrəsi)",
        "fiscal_id": "Fiscal ID (Fiskal ID)",
        "fiscal_registration": "Fiscal registration (NMQ-nin qeydiyyat nömrəsi)",
        "refund_amount": "Refund amount (Geri qaytarılan məbləğ)",
        "refund_date": "Refund date (DD.MM.YYYY format)",
        "refund_time": "Refund time (HH:MM format)"
    }}

    CRITICAL VALIDATION RULES:
    - If quantity × unit_price ≠ line_total, fix the calculation
    - If quantity > 100, it's likely an OCR error - correct it to realistic value
    - Clean item names: remove "ƏDV:", "Ticarət əlavəsi:", quotes, etc.
    - Format all prices to 2 decimal places
    - Use "null" for missing fields
    - Extract ALL payment methods found

    OCR TEXT:
    {ocr_text}

    Return ONLY a valid JSON object with the 30 fields above."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        # Parse the JSON response
        ai_response = response.choices[0].message.content.strip()
        
        # Remove code block markers if present
        if ai_response.startswith('```json'):
            ai_response = ai_response.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        extracted_data = json.loads(ai_response)
        
        # Validate and clean the extracted data
        cleaned_data = validate_and_clean_data(extracted_data)
        
        return cleaned_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {filename}: {e}")
        return create_fallback_data(filename)
    
    except Exception as e:
        logger.error(f"OpenAI API error for {filename}: {e}")
        return create_fallback_data(filename)

def validate_and_clean_data(data):
    """
    Validate and clean the extracted data from AI.
    """
    
    # Ensure all 30 fields are present
    required_fields = [
        'filename', 'store_name', 'store_address', 'store_code', 'taxpayer_name',
        'tax_id', 'receipt_number', 'cashier_name', 'date', 'time',
        'item_name', 'quantity', 'unit_price', 'line_total', 'subtotal',
        'vat_18_percent', 'total_tax', 'cashless_payment', 'cash_payment', 'bonus_payment',
        'advance_payment', 'credit_payment', 'queue_number', 'cash_register_model',
        'cash_register_serial', 'fiscal_id', 'fiscal_registration', 'refund_amount',
        'refund_date', 'refund_time'
    ]
    
    # Initialize with null values
    cleaned_data = {}
    for field in required_fields:
        cleaned_data[field] = data.get(field, None)
    
    # Clean and validate specific fields
    try:
        # Validate mathematical calculations
        if all(cleaned_data.get(field) not in [None, "null", ""] for field in ['quantity', 'unit_price', 'line_total']):
            quantity = float(cleaned_data['quantity'])
            unit_price = float(cleaned_data['unit_price'])
            line_total = float(cleaned_data['line_total'])
            
            # Fix calculation if incorrect
            expected_total = quantity * unit_price
            if abs(line_total - expected_total) > 0.01:  # Allow small rounding differences
                cleaned_data['line_total'] = f"{expected_total:.2f}"
                logger.info(f"Fixed calculation for {cleaned_data['filename']}: {quantity} × {unit_price} = {expected_total:.2f}")
        
        # Validate suspicious quantities
        if cleaned_data.get('quantity') and cleaned_data['quantity'] not in [None, "null", ""]:
            quantity = float(cleaned_data['quantity'])
            if quantity > 100:
                logger.warning(f"Suspicious quantity detected in {cleaned_data['filename']}: {quantity}")
        
        # Format monetary values
        monetary_fields = ['unit_price', 'line_total', 'subtotal', 'vat_18_percent', 'total_tax',
                          'cashless_payment', 'cash_payment', 'bonus_payment', 'advance_payment',
                          'credit_payment', 'refund_amount']
        
        for field in monetary_fields:
            if cleaned_data.get(field) and cleaned_data[field] not in [None, "null", ""]:
                try:
                    value = float(cleaned_data[field])
                    cleaned_data[field] = f"{value:.2f}"
                except (ValueError, TypeError):
                    cleaned_data[field] = "0.00"
        
        # Clean item names
        if cleaned_data.get('item_name') and cleaned_data['item_name'] not in [None, "null", ""]:
            item_name = cleaned_data['item_name']
            # Remove VAT codes and prefixes
            item_name = re.sub(r'^v?ƏDV[:\s]*\d+[:\s]*', '', item_name)
            item_name = re.sub(r'^"?ƏDV[:\s]*\d+[:\s]*', '', item_name)
            item_name = re.sub(r'^ƏDV-dən\s+azad\s+', '', item_name)
            item_name = re.sub(r'^Ticarət\s+əlavəsi[:\s]*\d*\s*', '', item_name)
            item_name = re.sub(r'^["\']+|["\']+$', '', item_name)
            item_name = re.sub(r'\s+', ' ', item_name).strip()
            cleaned_data['item_name'] = item_name
        
    except Exception as e:
        logger.error(f"Error during data validation: {e}")
    
    return cleaned_data

def create_fallback_data(filename):
    """
    Create fallback data structure when AI extraction fails.
    """
    
    return {
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
    }

def process_receipt_with_ai(filepath, filename):
    """
    Process a single receipt using AI-enhanced extraction.
    """
    
    global processed_count
    
    try:
        # Extract OCR text
        text = pytesseract.image_to_string(Image.open(filepath), lang='aze')
        
        # Get receipt data with AI
        receipt_data = extract_text_with_ai(text, filename)
        
        # Update progress counter
        with counter_lock:
            processed_count += 1
            logger.info(f"Processed {processed_count}/62: {filename}")
        
        return receipt_data
        
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
                batch_results.append(result)
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                batch_results.append(create_fallback_data(filename))
    
    logger.info(f"Completed batch {batch_num} with {len(batch_results)} receipts")
    return batch_results

def main():
    """Main function to run AI-enhanced receipt processing in batches."""
    
    global processed_count
    
    # Check if OpenAI API key is available
    if not os.getenv('openai'):
        logger.error("OpenAI API key not found in .env file")
        return
    
    logger.info("Starting AI-enhanced receipt processing in batches...")
    
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
        time.sleep(2)
    
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
    
    logger.info(f"✅ AI-enhanced extraction complete! Data saved to '{OUTPUT_CSV}'")
    logger.info(f"Total records: {len(df)}")
    logger.info(f"Unique receipts: {len(df['filename'].unique())}")
    
    # Show summary statistics
    print("\n=== EXTRACTION SUMMARY ===")
    print(f"Total receipts processed: {len(df)}")
    print(f"Receipts with store names: {len(df[df['store_name'].notna()])}")
    print(f"Receipts with addresses: {len(df[df['store_address'].notna()])}")
    print(f"Receipts with item data: {len(df[df['item_name'].notna()])}")
    print(f"Receipts with date/time: {len(df[df['date'].notna()])}")

if __name__ == '__main__':
    main()
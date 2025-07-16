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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
RECEIPTS_DIR = 'receipts'
OUTPUT_CSV = 'receipts_ai_test.csv'
TEST_LIMIT = 3  # Only process first 3 receipts for testing

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('openai'))

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
    
    Common OCR errors to fix:
    - Large quantities (>100) might be decimal point errors
    - Price calculation errors should be corrected
    - Date/time format inconsistencies
    - Character encoding issues (İ/I, ə/a, etc.)
    """
    
    user_prompt = f"""Extract data from this Azerbaijani receipt OCR text into exactly these 30 fields:

    REQUIRED FIELDS:
    1. filename: {filename}
    2. store_name: Store/business name
    3. store_address: Store address
    4. store_code: Store/object code
    5. taxpayer_name: Taxpayer name (Vergi ödəyicisinin adı)
    6. tax_id: VOEN tax identification number
    7. receipt_number: Receipt/check number (Satış çeki)
    8. cashier_name: Cashier name (Kassir)
    9. date: Transaction date (DD.MM.YYYY format)
    10. time: Transaction time (HH:MM:SS format)
    11. item_name: Product/item name (cleaned, no VAT codes)
    12. quantity: Item quantity (validate if >100, likely OCR error)
    13. unit_price: Price per unit
    14. line_total: Total for item (must equal quantity × unit_price)
    15. subtotal: Receipt subtotal (Cəmi)
    16. vat_18_percent: VAT 18% amount (ƏDV 18%)
    17. total_tax: Total tax amount (Toplam vergi)
    18. cashless_payment: Cashless payment amount (Nağdsız)
    19. cash_payment: Cash payment amount (Nağd)
    20. bonus_payment: Bonus payment amount (Bonus)
    21. advance_payment: Advance payment amount (Avans)
    22. credit_payment: Credit payment amount (Nisyə)
    23. queue_number: Queue/sequence number (Növbə)
    24. cash_register_model: Cash register model (NKA-nın modeli)
    25. cash_register_serial: Cash register serial (NKA-nın zavod nömrəsi)
    26. fiscal_id: Fiscal ID (Fiskal ID)
    27. fiscal_registration: Fiscal registration (NMQ-nin qeydiyyat nömrəsi)
    28. refund_amount: Refund amount (Geri qaytarılan məbləğ)
    29. refund_date: Refund date (DD.MM.YYYY format)
    30. refund_time: Refund time (HH:MM format)

    IMPORTANT VALIDATION RULES:
    - If quantity × unit_price ≠ line_total, fix the calculation
    - If quantity > 100, check if it's likely an OCR error (e.g., decimal point issue)
    - Clean item names: remove "ƏDV:", "Ticarət əlavəsi:", quotes, etc.
    - Format all prices to 2 decimal places
    - Use "null" for missing fields
    - Extract ALL payment methods found, not just one

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
                logger.info(f"Fixed calculation: {quantity} × {unit_price} = {expected_total:.2f}")
        
        # Validate suspicious quantities
        if cleaned_data.get('quantity') and cleaned_data['quantity'] not in [None, "null", ""]:
            quantity = float(cleaned_data['quantity'])
            if quantity > 100:
                logger.warning(f"Suspicious quantity detected: {quantity}")
        
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
    
    try:
        # Extract OCR text
        logger.info(f"Processing {filename} with AI enhancement...")
        text = pytesseract.image_to_string(Image.open(filepath), lang='aze')
        
        # Get receipt data with AI
        receipt_data = extract_text_with_ai(text, filename)
        
        return [receipt_data]
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")
        return [create_fallback_data(filename)]

def main():
    """Test function to process first few receipts."""
    
    # Check if OpenAI API key is available
    if not os.getenv('openai'):
        logger.error("OpenAI API key not found in .env file")
        return
    
    logger.info("Starting AI-enhanced receipt processing (TEST MODE - first 3 receipts)...")
    
    all_receipts_data = []
    
    # Get image files
    image_files = [f for f in os.listdir(RECEIPTS_DIR) if f.lower().endswith(('.jpeg', '.jpg', '.png', '.tiff'))]
    
    # Process only first TEST_LIMIT receipts
    test_files = image_files[:TEST_LIMIT]
    
    for i, filename in enumerate(test_files):
        filepath = os.path.join(RECEIPTS_DIR, filename)
        
        # Process with AI
        receipt_data = process_receipt_with_ai(filepath, filename)
        all_receipts_data.extend(receipt_data)
        
        # Rate limiting for API calls
        time.sleep(1)
        
        logger.info(f"Processed {i + 1}/{len(test_files)} receipts")
    
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
    
    logger.info(f"✅ AI-enhanced TEST extraction complete! Data saved to '{OUTPUT_CSV}'")
    logger.info(f"Total records: {len(df)}")
    
    # Show sample results
    print("\n=== SAMPLE RESULTS ===")
    print(df[['filename', 'store_name', 'item_name', 'quantity', 'unit_price', 'line_total']].to_string())

if __name__ == '__main__':
    main()
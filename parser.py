import os
import re
import pandas as pd
from PIL import Image
import pytesseract
import logging

# Configure logging to hide unnecessary output and show errors
logging.basicConfig(level=logging.ERROR)

# --- CONFIGURATION ---
# Set the path to your Tesseract installation if it's not in your system's PATH
# For Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# For Linux/macOS, it's often found automatically if installed via package managers.

RECEIPTS_DIR = 'receipts'
OUTPUT_CSV = 'receipts.csv'

def parse_receipt_text(text, filename):
    """
    Enhanced parsing function that extracts all 25 required columns from Azerbaijani receipts.
    
    Args:
        text (str): The OCR-extracted text from a receipt.
        filename (str): The original filename of the receipt image.

    Returns:
        list: A list of dictionaries, where each dictionary represents one item
              on the receipt, including all 25 required columns.
    """
    
    # Comprehensive regex patterns for all 25 fields
    patterns = {
        'store_name': r'Obyektin adı:\s*(.*?)(?:\n|$)',
        'store_address': r'Obyektin ünvanı:\s*(.*?)(?:\n|$)',
        'store_code': r'Obyektin kodu:\s*(.*?)(?:\n|$)',
        'taxpayer_name': r'Vergi ödəyicisinin adı:\s*(.*?)(?:\n|$)',
        'voen': r'VÖEN:\s*(\d+)',
        'receipt_number': r'Satış çeki №\s*(\d+)',
        'cashier_name': r'Kassir:\s*(.*?)(?:\s+Tarix|\n|$)',
        'datetime': r'Tarix:\s*(\d{2}\.\d{2}\.\d{4})\s*Vaxt:\s*(\d{2}:\d{2}:\d{2})',
        'subtotal': r'Cəmi\s+(\d+\.\d{2})',
        'vat_18_percent': r'ƏDV 18%\s*=\s*(\d+\.\d{2})',
        'total_tax': r'Toplam vergi\s*=\s*(\d+\.\d{2})',
        'nagdsiz': r'Nağdsız:\s*(\d+\.\d{2})',
        'nagd': r'Nağd:\s*(\d+\.\d{2})',
        'bonus': r'Bonus:\s*(\d+\.\d{2})',
        'avans': r'Avans\s*\(beh\):\s*(\d+\.\d{2})',
        'nisye': r'Nisyə:\s*(\d+\.\d{2})',
        'queue_number': r'Növbə ərzində vurulmuş çek sayı:\s*(\d+)',
        'nka_model': r'NKA-nın modeli:\s*(.*?)(?:\n|$)',
        'nka_serial': r'NKA-nın zavod nömrəsi:\s*(.*?)(?:\n|$)',
        'fiscal_id': r'Fiskal ID:\s*(\S+)',
        'nmq_registration': r'NMQ-nin qeydiyyat nömrəsi:\s*(.*?)(?:\n|$)',
        'refund_amount': r'Geri qaytarılan məbləğ:\s*(\d+\.\d{2})',
        'refund_date': r'Geri qaytarılma tarixi:\s*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})'
    }

    # Extract general receipt info
    data = {}
    
    # Initialize all 25 columns with None
    columns = [
        'filename', 'store_name', 'store_address', 'store_code', 'taxpayer_name',
        'voen', 'receipt_number', 'cashier_name', 'date', 'time',
        'item_name', 'quantity', 'unit_price', 'line_total', 'subtotal',
        'vat_18_percent', 'total_tax', 'payment_methods', 'queue_number',
        'nka_model', 'nka_serial', 'fiscal_id', 'nmq_registration',
        'refund_amount', 'refund_date'
    ]
    
    for col in columns:
        data[col] = None
    
    # Set filename
    data['filename'] = filename
    
    # Extract fields using patterns
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            if key == 'datetime':
                data['date'] = match.group(1)
                data['time'] = match.group(2)
            else:
                data[key] = match.group(1).strip()
    
    # Process payment methods - combine all non-zero payment types
    payment_methods = []
    payment_types = ['nagdsiz', 'nagd', 'bonus', 'avans', 'nisye']
    
    for payment_type in payment_types:
        if data.get(payment_type):
            try:
                amount = float(data[payment_type])
                if amount > 0:
                    payment_methods.append(payment_type)
            except (ValueError, TypeError):
                pass
    
    data['payment_methods'] = ', '.join(payment_methods) if payment_methods else None
    
    # --- Enhanced Item Extraction ---
    items_data = []
    try:
        # Find the items section more precisely
        items_block_match = re.search(
            r'Məhsulun adı\s+Say\s+Qiymət\s+Cəmi\s*\n(.*?)(?=\n-+\s*\nCəmi|\nCəmi\s+\d+\.\d{2})', 
            text, re.DOTALL | re.MULTILINE
        )
        
        if items_block_match:
            items_block = items_block_match.group(1)
            # Split into lines and filter out VAT and empty lines
            item_lines = [line.strip() for line in items_block.split('\n') 
                         if line.strip() and not line.strip().startswith('*ƏDV')]

            i = 0
            while i < len(item_lines):
                line = item_lines[i].strip()
                
                # Enhanced regex for item parsing - handles various formats
                item_match = re.match(r'(.+?)\s*\(([^)]+)\)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', line)
                
                if not item_match:
                    # Try without unit indicator
                    item_match = re.match(r'(.+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', line)
                
                if item_match:
                    if len(item_match.groups()) == 5:  # With unit indicator
                        item_name = item_match.group(1).strip()
                        quantity = float(item_match.group(3))
                        unit_price = float(item_match.group(4))
                        line_total = float(item_match.group(5))
                    else:  # Without unit indicator
                        item_name = item_match.group(1).strip()
                        quantity = float(item_match.group(2))
                        unit_price = float(item_match.group(3))
                        line_total = float(item_match.group(4))

                    items_data.append({
                        'item_name': item_name,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'line_total': line_total
                    })
                elif i + 1 < len(item_lines):
                    # Handle multi-line item names
                    combined_line = f"{line} {item_lines[i+1].strip()}"
                    item_match = re.match(r'(.+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', combined_line)
                    if item_match:
                        item_name = item_match.group(1).strip()
                        quantity = float(item_match.group(2))
                        unit_price = float(item_match.group(3))
                        line_total = float(item_match.group(4))

                        items_data.append({
                            'item_name': item_name,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'line_total': line_total
                        })
                        i += 1
                i += 1
    except Exception as e:
        print(f"Could not parse items for {filename}: {e}")

    # If no items were parsed, create a single record with receipt-level info
    if not items_data:
        data['error'] = 'Item parsing failed'
        return [data]

    # Combine general receipt info with each item
    full_receipt_data = []
    for item in items_data:
        record = data.copy()
        record.update(item)
        full_receipt_data.append(record)
        
    return full_receipt_data

def process_receipts_folder(directory, output_file):
    """
    Processes all images in a directory, extracts receipt data, and saves to CSV.
    """
    all_receipts_data = []
    
    if not os.path.exists(directory):
        print(f"Error: Directory not found at '{directory}'")
        return

    print(f"Starting processing of receipts in '{directory}'...")
    
    # Get a list of image files to process
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(('.jpeg', '.jpg', '.png', '.tiff'))]
    
    if not image_files:
        print("No image files found in the directory.")
        return

    for filename in image_files:
        filepath = os.path.join(directory, filename)
        try:
            print(f"Processing {filename}...")
            # Use pytesseract to do OCR on the image, specifying Azerbaijani language
            text = pytesseract.image_to_string(Image.open(filepath), lang='aze')
            
            # Parse the extracted text
            parsed_data = parse_receipt_text(text, filename)
            if parsed_data:
                all_receipts_data.extend(parsed_data)
                
        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")
            all_receipts_data.append({'filename': filename, 'error': str(e)})

    if not all_receipts_data:
        print("No data could be extracted from any of the images.")
        return

    # Create a DataFrame and save it to a CSV file
    df = pd.DataFrame(all_receipts_data)
    
    # Define the exact 25 columns in the required order
    column_order = [
        'filename', 'store_name', 'store_address', 'store_code', 'taxpayer_name',
        'voen', 'receipt_number', 'cashier_name', 'date', 'time',
        'item_name', 'quantity', 'unit_price', 'line_total', 'subtotal',
        'vat_18_percent', 'total_tax', 'payment_methods', 'queue_number',
        'nka_model', 'nka_serial', 'fiscal_id', 'nmq_registration',
        'refund_amount', 'refund_date'
    ]
    
    # Ensure all columns exist in the dataframe
    for col in column_order:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns to match the required 25-column structure
    df = df.reindex(columns=column_order)

    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Success! All data has been extracted and saved to '{output_file}'")


# --- RUN THE SCRIPT ---
if __name__ == '__main__':
    process_receipts_folder(RECEIPTS_DIR, OUTPUT_CSV)
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
    Parses the raw text extracted from a receipt image to find key information.
    
    Args:
        text (str): The OCR-extracted text from a receipt.
        filename (str): The original filename of the receipt image.

    Returns:
        list: A list of dictionaries, where each dictionary represents one item
              on the receipt, including shared receipt-level details.
    """
    # Regex patterns to find specific pieces of information
    # Using re.DOTALL to match across newlines and re.MULTILINE for ^ and $ anchors
    patterns = {
        'market': r'Obyektin adı:\s*(.*?)\n',
        'voen': r'VÖEN:\s*(\d+)',
        'datetime': r'Tarix:\s*(\d{2}\.\d{2}\.\d{4})\s*Vaxt:\s*(\d{2}:\d{2}:\d{2})',
        'fiscal_id': r'Fiskal ID\s*(\S+)',
        'total': r'^Cəmi\s+(\d+\.\d{2})',
        'vat_refund': r'Geri qaytarılan məbləğ:\s*(\d+\.\d{2})'
    }

    # Extract general receipt info
    data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            if key == 'datetime':
                data['date'] = match.group(1)
                data['time'] = match.group(2)
            else:
                data[key] = match.group(1).strip()
        else:
            if key == 'datetime':
                data['date'], data['time'] = None, None
            else:
                data[key] = None
    
    # --- Item Extraction ---
    # This is the most complex part. We isolate the block of text containing the items.
    items_data = []
    try:
        # Find the block of text between the item header and the final total
        items_block_match = re.search(r'Məhsulun adı.*?\n(.*?)(?=\n^Cəmi\s+\d+\.\d{2})', text, re.DOTALL | re.MULTILINE)
        
        if items_block_match:
            items_block = items_block_match.group(1)
            # Split into lines and filter out irrelevant lines (like VAT info)
            item_lines = [line for line in items_block.split('\n') if line.strip() and '*ƏDV' not in line]

            i = 0
            while i < len(item_lines):
                line = item_lines[i].strip()
                
                # Regex to find lines ending in numbers (qty, price, total)
                # It captures the item name and the three numeric values
                item_match = re.match(r'(.+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', line)
                
                if item_match:
                    item_name = item_match.group(1).strip()
                    # Clean up item name by removing unit indicators if they were captured
                    item_name = re.sub(r'\s+\(ədəd\)$|\s+\(kg\)$', '', item_name).strip()

                    items_data.append({
                        'item_name': item_name,
                        'quantity': float(item_match.group(2)),
                        'unit_price': float(item_match.group(3)),
                        'total_price': float(item_match.group(4))
                    })
                elif i + 1 < len(item_lines):
                    # Check if the current line is a name and the next line contains the numbers
                    # This handles cases where the item name is very long and wraps to a new line
                    combined_line = f"{line} {item_lines[i+1].strip()}"
                    item_match = re.match(r'(.+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', combined_line)
                    if item_match:
                        item_name = item_match.group(1).strip()
                        item_name = re.sub(r'\s+\(ədəd\)$|\s+\(kg\)$', '', item_name).strip()

                        items_data.append({
                            'item_name': item_name,
                            'quantity': float(item_match.group(2)),
                            'unit_price': float(item_match.group(3)),
                            'total_price': float(item_match.group(4))
                        })
                        i += 1 # Skip the next line as it's been processed
                i += 1
    except Exception as e:
        print(f"Could not parse items for {filename}: {e}")

    # If no items were parsed, add a placeholder row with available receipt info
    if not items_data:
        record = data.copy()
        record['filename'] = filename
        record['error'] = 'Item parsing failed'
        return [record]

    # Combine general receipt info with each item
    full_receipt_data = []
    for item in items_data:
        record = data.copy()
        record.update(item)
        record['filename'] = filename
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
    
    # Reorder columns for a clean output
    column_order = [
        'filename', 'market', 'date', 'time', 'total', 'voen', 'fiscal_id', 'vat_refund',
        'item_name', 'quantity', 'unit_price', 'total_price', 'error'
    ]
    # Filter columns to only include those that exist in the dataframe
    df = df.reindex(columns=[col for col in column_order if col in df.columns])

    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Success! All data has been extracted and saved to '{output_file}'")


# --- RUN THE SCRIPT ---
if __name__ == '__main__':
    process_receipts_folder(RECEIPTS_DIR, OUTPUT_CSV)
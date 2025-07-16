import pandas as pd
import numpy as np

def analyze_receipts_data():
    # Load the CSV file
    df = pd.read_csv('/Users/ismatsamadov/receipt_data/receipts.csv')
    
    print("=== COMPREHENSIVE DATA QUALITY ANALYSIS ===")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    
    # 1. DATA EXTRACTION ACCURACY
    print("\n1. DATA EXTRACTION ACCURACY")
    print("="*50)
    
    # Count missing critical fields
    critical_fields = ['store_name', 'date', 'time']
    missing_critical = {}
    for field in critical_fields:
        missing_count = df[field].isna().sum()
        missing_critical[field] = missing_count
        print(f"{field}: {missing_count} missing ({missing_count/len(df)*100:.1f}%)")
    
    # Check for completely empty rows (only filename filled)
    non_filename_cols = [col for col in df.columns if col != 'filename']
    empty_rows = df[non_filename_cols].isna().all(axis=1).sum()
    print(f"Completely empty rows (only filename): {empty_rows} ({empty_rows/len(df)*100:.1f}%)")
    
    # 2. DATA CLEANLINESS PERCENTAGES
    print("\n2. DATA CLEANLINESS PERCENTAGES")
    print("="*50)
    
    field_analysis = {}
    for col in df.columns:
        total_count = len(df)
        non_null_count = df[col].notna().sum()
        null_count = df[col].isna().sum()
        
        # Check for empty strings
        empty_str_count = 0
        if df[col].dtype == 'object':
            empty_str_count = (df[col] == '').sum()
        
        valid_count = non_null_count - empty_str_count
        
        field_analysis[col] = {
            'total': total_count,
            'valid': valid_count,
            'null': null_count,
            'empty_str': empty_str_count,
            'valid_pct': valid_count/total_count*100,
            'missing_pct': (null_count + empty_str_count)/total_count*100
        }
        
        print(f"{col}: {valid_count/total_count*100:.1f}% valid, {(null_count + empty_str_count)/total_count*100:.1f}% missing")
    
    # 3. DATA INTEGRITY ISSUES
    print("\n3. DATA INTEGRITY ISSUES")
    print("="*50)
    
    # Mathematical errors (quantity × unit_price ≠ line_total)
    valid_items = df.dropna(subset=['quantity', 'unit_price', 'line_total'])
    if len(valid_items) > 0:
        calculated_total = valid_items['quantity'] * valid_items['unit_price']
        math_errors = abs(calculated_total - valid_items['line_total']) > 0.01
        print(f"Mathematical errors: {math_errors.sum()} out of {len(valid_items)} items ({math_errors.sum()/len(valid_items)*100:.1f}%)")
    
    # Suspicious quantities
    quantity_data = df['quantity'].dropna()
    suspicious_quantities = (quantity_data > 100) | (quantity_data < 0)
    print(f"Suspicious quantities (>100 or <0): {suspicious_quantities.sum()} out of {len(quantity_data)} ({suspicious_quantities.sum()/len(quantity_data)*100:.1f}%)")
    
    # Payment method extraction failures
    payment_cols = ['cashless_payment', 'cash_payment', 'bonus_payment', 'advance_payment', 'credit_payment']
    payment_data = df[payment_cols].fillna(0)
    all_zero_payments = (payment_data == 0).all(axis=1)
    print(f"Payment method extraction failures (all = 0.00): {all_zero_payments.sum()} out of {len(df)} ({all_zero_payments.sum()/len(df)*100:.1f}%)")
    
    # 4. FIELD-BY-FIELD ANALYSIS
    print("\n4. FIELD-BY-FIELD ANALYSIS")
    print("="*50)
    
    # Item information completeness
    item_fields = ['item_name', 'quantity', 'unit_price', 'line_total']
    complete_items = df[item_fields].notna().all(axis=1)
    print(f"Complete item information: {complete_items.sum()} out of {len(df)} ({complete_items.sum()/len(df)*100:.1f}%)")
    
    # 5. SPECIFIC STATISTICS
    print("\n5. SPECIFIC STATISTICS")
    print("="*50)
    
    # Overall data quality score
    non_filename_fields = [col for col in df.columns if col != 'filename']
    filled_fields = df[non_filename_fields].notna().sum().sum()
    total_fields = len(df) * len(non_filename_fields)
    overall_quality = filled_fields / total_fields * 100
    print(f"Overall data quality score: {overall_quality:.1f}%")
    
    # Most problematic fields
    missing_pct = {col: field_analysis[col]['missing_pct'] for col in field_analysis}
    most_problematic = sorted(missing_pct.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\nMost problematic fields (highest missing %):")
    for field, pct in most_problematic:
        print(f"  {field}: {pct:.1f}% missing")
    
    # Extraction success rate by receipt
    unique_receipts = df['filename'].nunique()
    receipts_with_data = df.groupby('filename')[non_filename_fields].apply(lambda x: x.notna().any().any()).sum()
    print(f"\nExtraction success rate by receipt: {receipts_with_data}/{unique_receipts} ({receipts_with_data/unique_receipts*100:.1f}%)")
    
    # Show some problematic examples
    print("\n6. PROBLEMATIC EXAMPLES")
    print("="*50)
    
    # Show rows with mathematical errors
    if len(valid_items) > 0 and math_errors.sum() > 0:
        print("Mathematical errors (first 5):")
        error_rows = valid_items[math_errors]
        for idx, row in error_rows.head().iterrows():
            calc = row['quantity'] * row['unit_price']
            print(f"  Row {idx}: {row['quantity']} × {row['unit_price']} = {calc:.2f} but line_total = {row['line_total']}")
    
    # Show rows with suspicious quantities
    if suspicious_quantities.sum() > 0:
        print("\nSuspicious quantities (first 5):")
        suspicious_rows = df[df['quantity'].isin(quantity_data[suspicious_quantities])]
        for idx, row in suspicious_rows.head().iterrows():
            print(f"  Row {idx}: quantity = {row['quantity']} for item '{row['item_name']}'")
    
    return df, field_analysis

if __name__ == "__main__":
    df, analysis = analyze_receipts_data()
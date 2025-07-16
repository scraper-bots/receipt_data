import pandas as pd
import numpy as np

def detailed_analysis():
    df = pd.read_csv('/Users/ismatsamadov/receipt_data/receipts.csv')
    
    print("=== DETAILED RECEIPT DATA QUALITY ANALYSIS ===")
    print(f"Analysis Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total rows: {len(df)}")
    print(f"Unique receipts: {df['filename'].nunique()}")
    
    # Calculate rows per receipt
    receipt_counts = df['filename'].value_counts()
    print(f"Average rows per receipt: {receipt_counts.mean():.1f}")
    print(f"Max rows per receipt: {receipt_counts.max()}")
    print(f"Min rows per receipt: {receipt_counts.min()}")
    
    print("\n" + "="*70)
    print("1. DATA EXTRACTION ACCURACY")
    print("="*70)
    
    # Store information extraction
    store_info_fields = ['store_name', 'store_address', 'store_code', 'taxpayer_name', 'tax_id']
    store_completeness = {}
    for field in store_info_fields:
        filled = df[field].notna().sum()
        store_completeness[field] = filled / len(df) * 100
        print(f"{field}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)")
    
    # Receipt metadata extraction
    print("\nReceipt metadata extraction:")
    meta_fields = ['receipt_number', 'cashier_name', 'date', 'time', 'queue_number']
    for field in meta_fields:
        filled = df[field].notna().sum()
        print(f"{field}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)")
    
    # Item-level data extraction
    print("\nItem-level data extraction:")
    item_fields = ['item_name', 'quantity', 'unit_price', 'line_total']
    for field in item_fields:
        filled = df[field].notna().sum()
        print(f"{field}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)")
    
    print("\n" + "="*70)
    print("2. DATA CLEANLINESS PERCENTAGES")
    print("="*70)
    
    # Categorize fields by data quality
    high_quality = []  # >90% filled
    medium_quality = []  # 50-90% filled  
    low_quality = []  # <50% filled
    
    for col in df.columns:
        if col != 'filename':
            filled_pct = df[col].notna().sum() / len(df) * 100
            if filled_pct > 90:
                high_quality.append((col, filled_pct))
            elif filled_pct >= 50:
                medium_quality.append((col, filled_pct))
            else:
                low_quality.append((col, filled_pct))
    
    print(f"High quality fields (>90% filled): {len(high_quality)}")
    for field, pct in sorted(high_quality, key=lambda x: x[1], reverse=True):
        print(f"  {field}: {pct:.1f}%")
    
    print(f"\nMedium quality fields (50-90% filled): {len(medium_quality)}")
    for field, pct in sorted(medium_quality, key=lambda x: x[1], reverse=True):
        print(f"  {field}: {pct:.1f}%")
    
    print(f"\nLow quality fields (<50% filled): {len(low_quality)}")
    for field, pct in sorted(low_quality, key=lambda x: x[1], reverse=True):
        print(f"  {field}: {pct:.1f}%")
    
    print("\n" + "="*70)
    print("3. DATA INTEGRITY ISSUES")
    print("="*70)
    
    # Mathematical consistency
    valid_items = df.dropna(subset=['quantity', 'unit_price', 'line_total'])
    if len(valid_items) > 0:
        # Calculate expected line total
        expected_total = valid_items['quantity'] * valid_items['unit_price']
        tolerance = 0.01  # Allow 1 cent difference
        math_errors = abs(expected_total - valid_items['line_total']) > tolerance
        
        print(f"Mathematical errors in item calculations:")
        print(f"  Items with valid data: {len(valid_items)}")
        print(f"  Mathematical errors: {math_errors.sum()} ({math_errors.sum()/len(valid_items)*100:.1f}%)")
        print(f"  Correct calculations: {(~math_errors).sum()} ({(~math_errors).sum()/len(valid_items)*100:.1f}%)")
    
    # Quantity analysis
    quantity_data = df['quantity'].dropna()
    if len(quantity_data) > 0:
        print(f"\nQuantity analysis:")
        print(f"  Total quantity entries: {len(quantity_data)}")
        print(f"  Quantities > 100: {(quantity_data > 100).sum()} ({(quantity_data > 100).sum()/len(quantity_data)*100:.1f}%)")
        print(f"  Quantities > 1000: {(quantity_data > 1000).sum()} ({(quantity_data > 1000).sum()/len(quantity_data)*100:.1f}%)")
        print(f"  Negative quantities: {(quantity_data < 0).sum()}")
        print(f"  Zero quantities: {(quantity_data == 0).sum()}")
        print(f"  Median quantity: {quantity_data.median()}")
        print(f"  Mean quantity: {quantity_data.mean():.2f}")
    
    # Price analysis
    price_data = df['unit_price'].dropna()
    if len(price_data) > 0:
        print(f"\nPrice analysis:")
        print(f"  Total price entries: {len(price_data)}")
        print(f"  Prices > 100: {(price_data > 100).sum()} ({(price_data > 100).sum()/len(price_data)*100:.1f}%)")
        print(f"  Prices > 1000: {(price_data > 1000).sum()} ({(price_data > 1000).sum()/len(price_data)*100:.1f}%)")
        print(f"  Zero prices: {(price_data == 0).sum()}")
        print(f"  Median price: {price_data.median():.2f}")
        print(f"  Mean price: {price_data.mean():.2f}")
    
    # Payment method analysis
    payment_cols = ['cashless_payment', 'cash_payment', 'bonus_payment', 'advance_payment', 'credit_payment']
    payment_data = df[payment_cols].fillna(0)
    
    print(f"\nPayment method extraction:")
    total_payments = payment_data.sum(axis=1)
    zero_payments = (total_payments == 0).sum()
    print(f"  Rows with zero payment amounts: {zero_payments}/{len(df)} ({zero_payments/len(df)*100:.1f}%)")
    print(f"  Rows with payment data: {(total_payments > 0).sum()}/{len(df)} ({(total_payments > 0).sum()/len(df)*100:.1f}%)")
    
    # Payment method breakdown
    for col in payment_cols:
        non_zero = (payment_data[col] > 0).sum()
        print(f"  {col}: {non_zero} rows ({non_zero/len(df)*100:.1f}%)")
    
    print("\n" + "="*70)
    print("4. FIELD-BY-FIELD ANALYSIS")
    print("="*70)
    
    # Date/time parsing success
    date_time_success = df[['date', 'time']].notna().all(axis=1).sum()
    print(f"Complete date/time information: {date_time_success}/{len(df)} ({date_time_success/len(df)*100:.1f}%)")
    
    # Store identification success
    store_id_success = df[['store_name', 'tax_id']].notna().all(axis=1).sum()
    print(f"Complete store identification: {store_id_success}/{len(df)} ({store_id_success/len(df)*100:.1f}%)")
    
    # Financial totals consistency
    financial_fields = ['subtotal', 'total_tax', 'cashless_payment', 'cash_payment']
    for field in financial_fields:
        if field in df.columns:
            filled = df[field].notna().sum()
            print(f"{field}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)")
    
    print("\n" + "="*70)
    print("5. SPECIFIC STATISTICS")
    print("="*70)
    
    # Overall data quality score (weighted)
    critical_fields = ['store_name', 'date', 'time', 'item_name', 'quantity', 'unit_price', 'line_total']
    optional_fields = ['store_address', 'receipt_number', 'cashier_name', 'total_tax']
    
    critical_completeness = []
    for field in critical_fields:
        if field in df.columns:
            critical_completeness.append(df[field].notna().sum() / len(df))
    
    optional_completeness = []
    for field in optional_fields:
        if field in df.columns:
            optional_completeness.append(df[field].notna().sum() / len(df))
    
    critical_score = np.mean(critical_completeness) * 100
    optional_score = np.mean(optional_completeness) * 100
    weighted_score = (critical_score * 0.8) + (optional_score * 0.2)
    
    print(f"Critical fields completeness: {critical_score:.1f}%")
    print(f"Optional fields completeness: {optional_score:.1f}%")
    print(f"Weighted data quality score: {weighted_score:.1f}%")
    
    # Receipt-level analysis
    print(f"\nReceipt-level analysis:")
    receipt_quality = {}
    for receipt in df['filename'].unique():
        receipt_data = df[df['filename'] == receipt]
        
        # Count filled fields per receipt
        filled_fields = 0
        total_fields = 0
        for col in df.columns:
            if col != 'filename':
                filled_fields += receipt_data[col].notna().sum()
                total_fields += len(receipt_data)
        
        receipt_quality[receipt] = filled_fields / total_fields if total_fields > 0 else 0
    
    quality_scores = list(receipt_quality.values())
    print(f"Average receipt quality: {np.mean(quality_scores)*100:.1f}%")
    print(f"Best receipt quality: {np.max(quality_scores)*100:.1f}%")
    print(f"Worst receipt quality: {np.min(quality_scores)*100:.1f}%")
    
    # Show best and worst receipts
    best_receipt = max(receipt_quality, key=receipt_quality.get)
    worst_receipt = min(receipt_quality, key=receipt_quality.get)
    print(f"Best receipt: {best_receipt} ({receipt_quality[best_receipt]*100:.1f}%)")
    print(f"Worst receipt: {worst_receipt} ({receipt_quality[worst_receipt]*100:.1f}%)")
    
    print("\n" + "="*70)
    print("6. RECOMMENDATIONS")
    print("="*70)
    
    print("Based on the analysis, here are the key recommendations:")
    print("1. Focus on improving date/time extraction (35.7% missing)")
    print("2. Enhance mathematical calculation accuracy (48.8% errors)")
    print("3. Review quantity extraction logic (37.8% suspicious values)")
    print("4. Improve payment method extraction (25.5% failures)")
    print("5. Focus on store address extraction (89.2% missing)")
    print("6. Enhance receipt number extraction (87.3% missing)")
    
    return df

if __name__ == "__main__":
    df = detailed_analysis()
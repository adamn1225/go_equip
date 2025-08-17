import pandas as pd
import json
from pathlib import Path

def remove_duplicates_csv(input_file, output_file=None, key_columns=['Phone', 'Seller/Company']):
    """
    Remove duplicates from CSV file based on specified columns
    """
    if output_file is None:
        output_file = input_file.replace('.csv', '_deduped.csv')
    
    # Read CSV
    df = pd.read_csv(input_file)
    
    print(f"Original CSV records: {len(df)}")
    print(f"Available columns: {list(df.columns)}")
    
    # Find the best columns to use for deduplication
    available_key_columns = [col for col in key_columns if col in df.columns]
    
    if available_key_columns:
        # Remove rows where ALL key columns are empty/null
        mask = df[available_key_columns].notna().any(axis=1)
        df_clean = df[mask]
        
        print(f"Records with valid key data: {len(df_clean)}")
        
        # Remove duplicates based on key columns, only considering non-null values
        df_deduped = df_clean.drop_duplicates(subset=available_key_columns, keep='first')
        print(f"Removed duplicates based on: {available_key_columns}")
    else:
        print(f"None of the preferred columns found. Removing exact duplicate rows.")
        # Remove exact duplicates
        df_deduped = df.drop_duplicates(keep='first')
    
    print(f"Deduplicated CSV records: {len(df_deduped)}")
    print(f"Duplicates removed: {len(df) - len(df_deduped)}")
    
    # Save deduplicated CSV
    df_deduped.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    
    return df_deduped

def remove_duplicates_json(input_file, output_file=None, key_fields=['phone', 'seller']):
    """
    Remove duplicates from JSON file based on specified fields
    """
    if output_file is None:
        output_file = input_file.replace('.json', '_deduped.json')
    
    # Read JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and 'data' in data:
        records = data['data']
    else:
        records = [data]  # Single record
    
    print(f"Original JSON records: {len(records)}")
    
    # Remove duplicates
    seen = set()
    deduped_records = []
    
    for record in records:
        # Create a key for duplicate detection using multiple fields
        key_parts = []
        for field in key_fields:
            if field in record and record[field]:
                key_parts.append(str(record[field]).lower().strip())
        
        if key_parts:
            key = '||'.join(key_parts)  # Combine fields with separator
        else:
            # Fallback to string representation of entire record
            key = str(sorted(record.items()))
        
        if key not in seen:
            seen.add(key)
            deduped_records.append(record)
    
    print(f"Deduplicated JSON records: {len(deduped_records)}")
    print(f"Duplicates removed: {len(records) - len(deduped_records)}")
    
    # Preserve original JSON structure
    if isinstance(data, list):
        output_data = deduped_records
    elif isinstance(data, dict) and 'data' in data:
        output_data = data.copy()
        output_data['data'] = deduped_records
    else:
        output_data = deduped_records[0] if deduped_records else {}
    
    # Save deduplicated JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to: {output_file}")
    
    return output_data

def main():
    """
    Main function to process files in current directory
    """
    current_dir = Path('.')
    
    # Find CSV files
    csv_files = list(current_dir.glob('*.csv'))
    json_files = list(current_dir.glob('*.json'))
    
    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"  - {f}")
    print(f"Found {len(json_files)} JSON files:")
    for f in json_files:
        print(f"  - {f}")
    
    print("\n=== CSV Deduplication ===")
    for csv_file in csv_files:
        if '_deduped' not in csv_file.name:  # Skip already processed files
            print(f"\nProcessing: {csv_file}")
            try:
                # Try different key columns in order of preference
                df = pd.read_csv(csv_file)
                
                # Use phone and company name for deduplication
                key_columns = ['Phone', 'Seller/Company']
                remove_duplicates_csv(str(csv_file), key_columns=key_columns)
                    
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")
    
    print("\n=== JSON Deduplication ===")
    for json_file in json_files:
        if '_deduped' not in json_file.name:  # Skip already processed files
            print(f"\nProcessing: {json_file}")
            try:
                # Try different key fields
                with open(json_file, 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                
                # Determine structure and key field
                if isinstance(sample_data, list) and sample_data:
                    sample_record = sample_data[0]
                elif isinstance(sample_data, dict) and 'data' in sample_data:
                    sample_record = sample_data['data'][0] if sample_data['data'] else {}
                else:
                    sample_record = sample_data
                
                key_fields = ['email', 'Email', 'phone', 'Phone', 'name', 'Name']
                key_field = None
                
                for field in key_fields:
                    if field in sample_record:
                        key_field = field
                        break
                
                remove_duplicates_json(str(json_file))
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

# Additional utility functions
def compare_files(original_file, deduped_file):
    """
    Compare original and deduplicated files
    """
    if original_file.endswith('.csv'):
        df_orig = pd.read_csv(original_file)
        df_dedup = pd.read_csv(deduped_file)
        
        print(f"Original: {len(df_orig)} records")
        print(f"Deduplicated: {len(df_dedup)} records")
        print(f"Removed: {len(df_orig) - len(df_dedup)} duplicates")
        
    elif original_file.endswith('.json'):
        with open(original_file, 'r') as f:
            orig_data = json.load(f)
        with open(deduped_file, 'r') as f:
            dedup_data = json.load(f)
        
        orig_count = len(orig_data) if isinstance(orig_data, list) else len(orig_data.get('data', []))
        dedup_count = len(dedup_data) if isinstance(dedup_data, list) else len(dedup_data.get('data', []))
        
        print(f"Original: {orig_count} records")
        print(f"Deduplicated: {dedup_count} records")
        print(f"Removed: {orig_count - dedup_count} duplicates")

if __name__ == "__main__":
    main()
    
    # Example usage for specific files:
    # remove_duplicates_csv('seller_contacts_20250815_125706.csv', key_column='email')
    # remove_duplicates_json('contacts.json', key_field='email')
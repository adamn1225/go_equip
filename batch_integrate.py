#!/usr/bin/env python3
"""
Batch Integration Script
Process all unprocessed scraped data files at once
"""

import json
import glob
import os
from datetime import datetime
from integrate_scraped_data import integrate_scraped_data

def get_processed_files():
    """Get list of files that have already been processed"""
    processed_file = "processed_files.json"
    if os.path.exists(processed_file):
        with open(processed_file, 'r') as f:
            return json.load(f)
    return []

def mark_file_processed(filename):
    """Mark a file as processed"""
    processed_file = "processed_files.json"
    processed_files = get_processed_files()
    
    if filename not in processed_files:
        processed_files.append(filename)
        
    with open(processed_file, 'w') as f:
        json.dump(processed_files, f, indent=2)

def batch_integrate():
    """Process all unprocessed seller_contacts_*.json files"""
    
    # Find all scraped data files
    pattern = "seller_contacts_*.json"
    all_files = glob.glob(pattern)
    
    if not all_files:
        print("❌ No seller_contacts_*.json files found")
        return
    
    # Get list of already processed files
    processed_files = get_processed_files()
    
    # Filter to only unprocessed files
    new_files = [f for f in all_files if f not in processed_files]
    
    if not new_files:
        print("✅ All files have already been processed!")
        return
    
    print(f"🔍 Found {len(new_files)} new files to process:")
    for file in new_files:
        print(f"   📄 {file}")
    
    print("\n🚀 Starting batch integration...")
    
    master_file = "master_contact_database.json"
    
    for file in new_files:
        print(f"\n📥 Processing: {file}")
        try:
            integrate_scraped_data(file, master_file)
            mark_file_processed(file)
            print(f"✅ Successfully processed: {file}")
        except Exception as e:
            print(f"❌ Error processing {file}: {e}")
            continue
    
    print("\n🎉 Batch integration complete!")
    print("   All new scraped data has been integrated into the master database.")

if __name__ == "__main__":
    batch_integrate()

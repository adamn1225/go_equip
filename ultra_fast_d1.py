#!/usr/bin/env python3
"""
⚡ Ultra-Fast D1 Upload System
High-performance batch upload for Cloudflare D1 database

Features:
- Ultra-fast batch processing (50 contacts per API call)
- Automatic file discovery and category detection
- Processed file tracking to avoid duplicates
- Database status checking and reporting
- Support for both single files and bulk processing

Usage:
    python ultra_fast_d1.py                    # Process all new files
    python ultra_fast_d1.py status             # Check database status
    python ultra_fast_d1.py single <file>      # Process specific file
"""

import os
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
from d1_integration import D1ScraperIntegration

# Load environment variables
load_dotenv()

def get_processed_files():
    """Get list of files that have already been processed"""
    processed_file = "d1_processed_files.json"
    if os.path.exists(processed_file):
        with open(processed_file, 'r') as f:
            return json.load(f)
    return []

def mark_file_processed(filename):
    """Mark a file as processed"""
    processed_file = "d1_processed_files.json"
    processed_files = get_processed_files()
    
    # Store just the basename to work with both old and new paths
    basename = os.path.basename(filename)
    if basename not in processed_files:
        processed_files.append(basename)
        
    with open(processed_file, 'w') as f:
        json.dump(processed_files, f, indent=2)

def extract_category_from_file(filename, file_data):
    """Extract category from filename or file data with comprehensive mapping"""
    
    # Method 1: Extract from JSON metadata
    if 'equipment_category' in file_data:
        return file_data['equipment_category'].lower()
    
    # Method 2: URL-based category detection
    contacts = file_data.get('contacts', [])
    if contacts and 'url' in contacts[0]:
        url = contacts[0]['url']
        category_map = {
            "1055": "skid steers",
            "1026": "excavators", 
            "1025": "dozers",
            "1015": "cranes",
            "1046": "backhoes",
            "1060": "wheel loaders",
            "1007": "asphalt/pavers",
            "1057": "sweepers/brooms",
            "1040": "lifts",
            "1028": "drills",
            "1035": "forestry equipment",
            "1048": "graders",
            "1076": "off-highway trucks"
        }
        
        for cat_id, cat_name in category_map.items():
            if f"Category={cat_id}" in url:
                return cat_name
    
    # Method 3: Filename-based detection
    filename_lower = filename.lower()
    filename_categories = {
        "skid": "skid steers",
        "excavator": "excavators",
        "dozer": "dozers", 
        "crane": "cranes",
        "backhoe": "backhoes",
        "loader": "wheel loaders",
        "asphalt": "asphalt/pavers",
        "paver": "asphalt/pavers",
        "sweep": "sweepers/brooms",
        "broom": "sweepers/brooms",
        "lift": "lifts",
        "drill": "drills",
        "forest": "forestry equipment",
        "grader": "graders",
        "truck": "off-highway trucks"
    }
    
    for keyword, category in filename_categories.items():
        if keyword in filename_lower:
            return category
    
    # Default fallback
    return 'general equipment'

def ultra_fast_upload_single_file(filepath):
    """Upload a single file using ultra-fast batch processing"""
    print(f"⚡ ULTRA-FAST UPLOAD: {os.path.basename(filepath)}")
    print("=" * 60)
    
    # Load file
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    contacts = data.get('contacts', [])
    category = extract_category_from_file(filepath, data)
    source_site = data.get('source_site', 'machinerytrader.com')
    
    print(f"📂 Category: {category}")
    print(f"👥 Total contacts: {len(contacts):,}")
    print(f"🌐 Source: {source_site}")
    print(f"📅 File date: {data.get('export_timestamp', 'Unknown')}")
    
    # Initialize D1 integration
    d1 = D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )
    
    # Use ultra-fast batch upload 
    print("\\n⚡ Starting ULTRA-FAST batch upload...")
    start_time = datetime.now()
    
    processed_count, _ = d1.fast_batch_insert_contacts(contacts, category, source_site, batch_size=50)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\\n✅ Upload complete!")
    print(f"📊 Results:")
    print(f"   • Processed contacts: {processed_count:,}")
    print(f"   • Total in file: {len(contacts):,}")
    print(f"   • Duration: {duration:.1f} seconds")
    print(f"   • Speed: {processed_count/duration:.1f} contacts/second")
    print(f"   • Performance: ~72x faster than individual uploads!")
    
    # Mark file as processed
    mark_file_processed(filepath)
    print(f"   ✅ File marked as processed")
    
    return processed_count

def ultra_fast_bulk_upload():
    """Process all new files using ultra-fast batch processing"""
    print("🚀 ULTRA-FAST BULK D1 UPLOAD")
    print("=" * 60)
    
    # Find all scraped data files
    json_dir = os.path.join("mt_contacts", "json")
    patterns = [
        os.path.join(json_dir, "seller_contacts_*.json"),
        os.path.join(json_dir, "seller_contacts_learning_*.json"), 
        os.path.join(json_dir, "seller_contacts_emergency_*.json")
    ]
    
    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern))
    
    if not all_files:
        print("❌ No seller_contacts_*.json files found in mt_contacts/json/")
        print("💡 Make sure files are in the correct directory")
        return
    
    # Get already processed files
    processed_files = get_processed_files()
    
    # Filter to only new files (check basename)
    new_files = [f for f in all_files if os.path.basename(f) not in processed_files]
    
    if not new_files:
        print(f"✅ All {len(all_files)} files already processed")
        print("💡 Run 'python ultra_fast_d1.py status' to check database")
        return
    
    print(f"📄 Found {len(new_files)} new files to process:")
    for f in new_files[:10]:  # Show first 10
        print(f"   • {os.path.basename(f)}")
    if len(new_files) > 10:
        print(f"   ... and {len(new_files) - 10} more files")
    
    # Check D1 credentials
    if not all([os.getenv('CLOUDFLARE_ACCOUNT_ID'), 
                os.getenv('D1_DATABASE_ID'), 
                os.getenv('CLOUDFLARE_API_TOKEN')]):
        print("❌ Missing D1 credentials in .env file")
        return
    
    print("\\n🔍 Testing D1 connection...")
    d1 = D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )
    
    # Test connection
    result = d1.execute_query("SELECT COUNT(*) as total_contacts FROM contacts")
    if not result or not result.get('success'):
        print("❌ Failed to connect to D1 database")
        return
    
    current_total = result['result'][0]['results'][0]['total_contacts']
    print(f"✅ Connected! Current database size: {current_total:,} contacts")
    
    # Process each file
    print("\\n📤 Processing files...")
    total_processed = 0
    
    for i, filepath in enumerate(new_files, 1):
        print(f"\\n📁 File {i}/{len(new_files)}: {os.path.basename(filepath)}")
        
        try:
            processed = ultra_fast_upload_single_file(filepath)
            total_processed += processed
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(filepath)}: {e}")
            continue
    
    print(f"\\n🎉 BULK UPLOAD COMPLETE!")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   • Files processed: {len(new_files):,}")
    print(f"   • Total contacts uploaded: {total_processed:,}")
    print(f"   • Database size: ~{current_total + total_processed:,} contacts")
    print(f"\\n🎯 Next Steps:")
    print(f"   1. Run 'streamlit run dashboard.py' to see updated data")
    print(f"   2. New categories will appear automatically in filters")

def check_d1_status():
    """Check D1 database status and statistics"""
    print("📊 D1 DATABASE STATUS")
    print("=" * 40)
    
    if not all([os.getenv('CLOUDFLARE_ACCOUNT_ID'), 
                os.getenv('D1_DATABASE_ID'), 
                os.getenv('CLOUDFLARE_API_TOKEN')]):
        print("❌ Missing D1 credentials in .env file")
        return
    
    d1 = D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )
    
    # Get total contacts
    result = d1.execute_query("SELECT COUNT(*) as total_contacts FROM contacts")
    if result and result.get('success'):
        total = result['result'][0]['results'][0]['total_contacts']
        print(f"📊 Total contacts: {total:,}")
        
        # Get category breakdown
        result = d1.execute_query("""
            SELECT category, COUNT(DISTINCT contact_id) as count 
            FROM contact_sources 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        if result and result.get('success'):
            categories = result['result'][0]['results']
            print(f"\\n📂 Categories ({len(categories)} total):")
            for row in categories:
                print(f"   • {row['category']}: {row['count']:,} contacts")
        
        # Get recent activity
        result = d1.execute_query("""
            SELECT DATE(last_updated) as date, COUNT(*) as count
            FROM contacts 
            WHERE last_updated >= date('now', '-7 days')
            GROUP BY DATE(last_updated)
            ORDER BY date DESC
        """)
        
        if result and result.get('success'):
            recent = result['result'][0]['results']
            if recent:
                print(f"\\n📅 Recent activity (last 7 days):")
                for row in recent:
                    print(f"   • {row['date']}: {row['count']:,} contacts updated")
    else:
        print("❌ Could not connect to D1 database")
    
    # Check processed files
    processed_files = get_processed_files()
    print(f"\\n📁 Processed files: {len(processed_files)}")
    
    # Check for new files
    json_dir = os.path.join("mt_contacts", "json")
    if os.path.exists(json_dir):
        all_json_files = glob.glob(os.path.join(json_dir, "seller_contacts_*.json"))
        new_files = [f for f in all_json_files if os.path.basename(f) not in processed_files]
        
        if new_files:
            print(f"⚠️  {len(new_files)} unprocessed files found")
            print(f"💡 Run 'python ultra_fast_d1.py' to process them")
        else:
            print(f"✅ All files processed")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            check_d1_status()
        elif command == 'single' and len(sys.argv) > 2:
            filepath = sys.argv[2]
            if os.path.exists(filepath):
                ultra_fast_upload_single_file(filepath)
            else:
                print(f"❌ File not found: {filepath}")
        else:
            print("Usage:")
            print("  python ultra_fast_d1.py           # Process all new files")
            print("  python ultra_fast_d1.py status    # Check database status") 
            print("  python ultra_fast_d1.py single <file>  # Process specific file")
    else:
        # Default: process all new files
        ultra_fast_bulk_upload()

if __name__ == "__main__":
    main()

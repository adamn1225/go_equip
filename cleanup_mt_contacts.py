#!/usr/bin/env python3
"""
📁 Scraped Data Cleanup Tool
Helps manage and organize scraped contact files

Features:
- Remove duplicate files
- Archive old files by date
- Clean up invalid/corrupted files
- Generate cleanup reports
"""

import os
import json
import glob
import shutil
from datetime import datetime
from collections import defaultdict
import hashlib

def get_file_hash(filepath):
    """Calculate MD5 hash of file content"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_duplicate_files():
    """Find duplicate files based on content hash"""
    json_dir = os.path.join("mt_contacts", "json")
    csv_dir = os.path.join("mt_contacts", "csv")
    
    print("🔍 Scanning for duplicate files...")
    
    hash_map = defaultdict(list)
    
    # Check JSON files
    for filepath in glob.glob(os.path.join(json_dir, "*.json")):
        try:
            file_hash = get_file_hash(filepath)
            hash_map[file_hash].append(filepath)
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    # Check CSV files  
    for filepath in glob.glob(os.path.join(csv_dir, "*.csv")):
        try:
            file_hash = get_file_hash(filepath)
            hash_map[file_hash].append(filepath)
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    
    if duplicates:
        print(f"\\n📋 Found {len(duplicates)} groups of duplicate files:")
        for file_hash, files in duplicates.items():
            print(f"\\n🔗 Duplicate group ({len(files)} files):")
            for f in files:
                print(f"   • {os.path.basename(f)}")
    else:
        print("✅ No duplicate files found")
    
    return duplicates

def find_invalid_files():
    """Find files with invalid/corrupted data"""
    json_dir = os.path.join("mt_contacts", "json")
    
    print("\\n🔍 Scanning for invalid JSON files...")
    
    invalid_files = []
    
    for filepath in glob.glob(os.path.join(json_dir, "*.json")):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check for required fields
            if not data.get('contacts'):
                print(f"⚠️  No contacts found in {os.path.basename(filepath)}")
                invalid_files.append(filepath)
                continue
                
            # Check contact quality
            contacts = data['contacts']
            valid_contacts = 0
            
            for contact in contacts:
                # Count contacts with actual data (not just URLs)
                if any(field in contact for field in ['phone', 'seller_company', 'location', 'serial_number']):
                    valid_contacts += 1
            
            # If less than 10% of contacts have real data, flag as invalid
            if valid_contacts < len(contacts) * 0.1:
                print(f"⚠️  Low quality data in {os.path.basename(filepath)} ({valid_contacts}/{len(contacts)} valid contacts)")
                invalid_files.append(filepath)
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {os.path.basename(filepath)}")
            invalid_files.append(filepath)
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
            invalid_files.append(filepath)
    
    return invalid_files

def archive_old_files(days_old=30):
    """Move old files to archive folder"""
    json_dir = os.path.join("mt_contacts", "json")
    csv_dir = os.path.join("mt_contacts", "csv")
    archive_dir = os.path.join("mt_contacts", "archive")
    
    os.makedirs(archive_dir, exist_ok=True)
    
    print(f"\\n📦 Archiving files older than {days_old} days...")
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    archived_count = 0
    
    for directory in [json_dir, csv_dir]:
        if not os.path.exists(directory):
            continue
            
        for filepath in glob.glob(os.path.join(directory, "*")):
            if os.path.getmtime(filepath) < cutoff_time:
                filename = os.path.basename(filepath)
                archive_path = os.path.join(archive_dir, filename)
                
                if not os.path.exists(archive_path):
                    shutil.move(filepath, archive_path)
                    print(f"📦 Archived: {filename}")
                    archived_count += 1
                else:
                    os.remove(filepath)
                    print(f"🗑️  Removed duplicate: {filename}")
                    archived_count += 1
    
    print(f"✅ Archived {archived_count} files")

def cleanup_menu():
    """Interactive cleanup menu"""
    print("🧹 Scraped Data Cleanup Tool")
    print("=" * 40)
    
    while True:
        print("\\nChoose an option:")
        print("1. 🔍 Find duplicate files")
        print("2. 🚫 Find invalid files")
        print("3. 📦 Archive old files (30+ days)")
        print("4. 📊 Generate cleanup report")
        print("5. 🗑️  Remove all duplicates")
        print("6. 🗑️  Remove invalid files")
        print("0. ❌ Exit")
        
        choice = input("\\nEnter choice (0-6): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            find_duplicate_files()
        elif choice == "2":
            find_invalid_files()
        elif choice == "3":
            archive_old_files()
        elif choice == "4":
            generate_cleanup_report()
        elif choice == "5":
            remove_duplicates()
        elif choice == "6":
            remove_invalid_files()
        else:
            print("❌ Invalid choice")

def remove_duplicates():
    """Remove duplicate files, keeping the newest"""
    duplicates = find_duplicate_files()
    
    if not duplicates:
        return
    
    print("\\n🗑️  Removing duplicates (keeping newest)...")
    
    removed_count = 0
    for file_hash, files in duplicates.items():
        # Sort by modification time, keep newest
        files.sort(key=os.path.getmtime, reverse=True)
        newest = files[0]
        
        for filepath in files[1:]:
            try:
                os.remove(filepath)
                print(f"🗑️  Removed: {os.path.basename(filepath)}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {filepath}: {e}")
    
    print(f"✅ Removed {removed_count} duplicate files")

def remove_invalid_files():
    """Remove invalid/corrupted files"""
    invalid_files = find_invalid_files()
    
    if not invalid_files:
        print("✅ No invalid files found")
        return
    
    print(f"\\n🗑️  Found {len(invalid_files)} invalid files")
    confirm = input("Remove them? (y/N): ").lower()
    
    if confirm == 'y':
        removed_count = 0
        for filepath in invalid_files:
            try:
                os.remove(filepath)
                print(f"🗑️  Removed: {os.path.basename(filepath)}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {filepath}: {e}")
        
        print(f"✅ Removed {removed_count} invalid files")
    else:
        print("❌ Cancelled")

def generate_cleanup_report():
    """Generate detailed cleanup report"""
    json_dir = os.path.join("mt_contacts", "json")
    csv_dir = os.path.join("mt_contacts", "csv")
    
    print("\\n📊 Generating cleanup report...")
    
    # Count files
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    
    # Calculate sizes
    total_size = 0
    for files in [json_files, csv_files]:
        for filepath in files:
            total_size += os.path.getsize(filepath)
    
    # Find duplicates and invalid files
    duplicates = find_duplicate_files()
    invalid_files = find_invalid_files()
    
    # Generate report
    report = f"""
📊 SCRAPED DATA CLEANUP REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================

📁 File Counts:
   • JSON files: {len(json_files):,}
   • CSV files: {len(csv_files):,}
   • Total files: {len(json_files) + len(csv_files):,}

💾 Storage:
   • Total size: {total_size / 1024 / 1024:.1f} MB

🔍 Analysis:
   • Duplicate groups: {len(duplicates)}
   • Invalid files: {len(invalid_files)}

🧹 Recommendations:
"""
    
    if duplicates:
        duplicate_count = sum(len(files) - 1 for files in duplicates.values())
        report += f"   • Remove {duplicate_count} duplicate files\\n"
    
    if invalid_files:
        report += f"   • Remove {len(invalid_files)} invalid files\\n"
    
    # Count old files
    cutoff_time = datetime.now().timestamp() - (30 * 24 * 60 * 60)
    old_files = []
    for files in [json_files, csv_files]:
        for filepath in files:
            if os.path.getmtime(filepath) < cutoff_time:
                old_files.append(filepath)
    
    if old_files:
        report += f"   • Archive {len(old_files)} old files (30+ days)\\n"
    
    if not duplicates and not invalid_files and not old_files:
        report += "   ✅ Files are well organized!\\n"
    
    print(report)
    
    # Save report
    report_file = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"💾 Report saved: {report_file}")

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("mt_contacts/json", exist_ok=True)
    os.makedirs("mt_contacts/csv", exist_ok=True)
    
    cleanup_menu()

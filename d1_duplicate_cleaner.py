#!/usr/bin/env python3
"""
🧹 D1 Database Duplicate Cleanup Tool
Safely removes duplicate contacts from Cloudflare D1 database

Usage:
    python d1_duplicate_cleaner.py analyze     # Analyze duplicates (safe)
    python d1_duplicate_cleaner.py backup      # Create backup table
    python d1_duplicate_cleaner.py clean       # Remove duplicates (keep newest)
    python d1_duplicate_cleaner.py restore     # Restore from backup
    python d1_duplicate_cleaner.py status      # Check database status
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from d1_integration import D1ScraperIntegration

# Load environment variables
load_dotenv()

def get_d1_connection():
    """Get D1 database connection"""
    if not all([os.getenv('CLOUDFLARE_ACCOUNT_ID'), 
                os.getenv('D1_DATABASE_ID'), 
                os.getenv('CLOUDFLARE_API_TOKEN')]):
        print("❌ Missing D1 credentials in .env file")
        return None
    
    return D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )

def analyze_duplicates():
    """Analyze duplicates in the database"""
    print("🔍 DUPLICATE ANALYSIS")
    print("=" * 60)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    # Get total contacts
    result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
    if not result or not result.get('success'):
        print("❌ Failed to connect to database")
        return
    
    total_contacts = result['result'][0]['results'][0]['total']
    print(f"📊 Total contacts in database: {total_contacts:,}")
    
    # Phone number duplicates
    print("\\n📞 Phone Number Duplicates:")
    result = d1.execute_query("""
        SELECT COUNT(*) as duplicate_sets,
               SUM(duplicate_count - 1) as total_duplicates
        FROM (
            SELECT COUNT(*) as duplicate_count
            FROM contacts 
            WHERE primary_phone IS NOT NULL AND primary_phone != ""
            GROUP BY primary_phone 
            HAVING COUNT(*) > 1
        )
    """)
    
    if result and result.get('success'):
        stats = result['result'][0]['results'][0]
        if stats['duplicate_sets']:
            print(f"   • {stats['duplicate_sets']:,} phone numbers have duplicates")
            print(f"   • {stats['total_duplicates']:,} duplicate records by phone")
        else:
            print("   • No phone duplicates found")
    
    # Company name duplicates
    print("\\n🏢 Company Name Duplicates:")
    result = d1.execute_query("""
        SELECT COUNT(*) as duplicate_sets,
               SUM(duplicate_count - 1) as total_duplicates
        FROM (
            SELECT COUNT(*) as duplicate_count
            FROM contacts 
            WHERE seller_company IS NOT NULL AND seller_company != ""
            GROUP BY seller_company 
            HAVING COUNT(*) > 1
        )
    """)
    
    if result and result.get('success'):
        stats = result['result'][0]['results'][0]
        if stats['duplicate_sets']:
            print(f"   • {stats['duplicate_sets']:,} company names have duplicates")
            print(f"   • {stats['total_duplicates']:,} duplicate records by company")
        else:
            print("   • No company duplicates found")
    
    # Exact duplicates (phone + company)
    print("\\n🔄 Exact Duplicates (Phone + Company):")
    result = d1.execute_query("""
        SELECT COUNT(*) as duplicate_sets,
               SUM(duplicate_count - 1) as total_duplicates
        FROM (
            SELECT COUNT(*) as duplicate_count
            FROM contacts 
            WHERE primary_phone IS NOT NULL AND seller_company IS NOT NULL
            GROUP BY primary_phone, seller_company
            HAVING COUNT(*) > 1
        )
    """)
    
    if result and result.get('success'):
        stats = result['result'][0]['results'][0]
        if stats['duplicate_sets']:
            print(f"   • {stats['duplicate_sets']:,} exact duplicate sets")
            print(f"   • {stats['total_duplicates']:,} exact duplicate records")
            estimated_unique = total_contacts - stats['total_duplicates']
            duplicate_percent = (stats['total_duplicates'] / total_contacts) * 100
            print(f"   • Estimated unique contacts: {estimated_unique:,}")
            print(f"   • Duplicate percentage: {duplicate_percent:.1f}%")
        else:
            print("   • No exact duplicates found")
    
    # Top duplicates by phone
    print("\\n📱 Top Phone Number Duplicates:")
    result = d1.execute_query("""
        SELECT primary_phone, COUNT(*) as duplicate_count
        FROM contacts 
        WHERE primary_phone IS NOT NULL AND primary_phone != ""
        GROUP BY primary_phone 
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        LIMIT 10
    """)
    
    if result and result.get('success'):
        duplicates = result['result'][0]['results']
        for i, dup in enumerate(duplicates, 1):
            print(f"   {i}. {dup['primary_phone']}: {dup['duplicate_count']} copies")
    
    print(f"\\n💡 Recommendations:")
    if total_contacts > 20000:
        print(f"   • Your database has {total_contacts:,} contacts - likely has many duplicates")
        print(f"   • Run 'python d1_duplicate_cleaner.py backup' before cleaning")
        print(f"   • Then run 'python d1_duplicate_cleaner.py clean' to remove duplicates")
    else:
        print(f"   • Database size looks reasonable")
        print(f"   • Check if recent uploads created duplicates")

def create_backup():
    """Create backup table before cleanup"""
    print("💾 CREATING BACKUP TABLE")
    print("=" * 40)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    # Check if backup already exists
    result = d1.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts_backup'")
    if result and result.get('success') and result['result'][0]['results']:
        print("⚠️  Backup table already exists!")
        response = input("Do you want to replace it? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Backup cancelled")
            return
        
        # Drop existing backup
        print("🗑️  Dropping existing backup...")
        d1.execute_query("DROP TABLE contacts_backup")
    
    # Create backup
    print("💾 Creating backup table...")
    result = d1.execute_query("CREATE TABLE contacts_backup AS SELECT * FROM contacts")
    
    if result and result.get('success'):
        # Verify backup
        result = d1.execute_query("SELECT COUNT(*) as backup_count FROM contacts_backup")
        if result and result.get('success'):
            backup_count = result['result'][0]['results'][0]['backup_count']
            print(f"✅ Backup created successfully!")
            print(f"📊 Backed up {backup_count:,} contacts")
            print(f"💡 If something goes wrong, run 'python d1_duplicate_cleaner.py restore'")
        else:
            print("❌ Failed to verify backup")
    else:
        print("❌ Failed to create backup")

def clean_duplicates():
    """Remove duplicate contacts (keep newest)"""
    print("🧹 CLEANING DUPLICATE CONTACTS")
    print("=" * 40)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    # Check if backup exists
    result = d1.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts_backup'")
    if not (result and result.get('success') and result['result'][0]['results']):
        print("⚠️  No backup table found!")
        print("💡 Run 'python d1_duplicate_cleaner.py backup' first")
        response = input("Continue without backup? This is RISKY! (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Cleanup cancelled for safety")
            return
    
    # Get current count
    result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
    if not result or not result.get('success'):
        print("❌ Failed to get current contact count")
        return
    
    before_count = result['result'][0]['results'][0]['total']
    print(f"📊 Contacts before cleanup: {before_count:,}")
    
    # Method 1: Remove exact duplicates (same phone + company), keep newest
    print("\\n🔄 Removing exact duplicates (same phone + company)...")
    
    # First, get the IDs of duplicate records to delete
    print("   📋 Finding duplicate records...")
    find_duplicates_sql = """
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY primary_phone, seller_company 
                   ORDER BY last_updated DESC, rowid DESC
               ) as rn
        FROM contacts
        WHERE primary_phone IS NOT NULL 
        AND primary_phone != ""
        AND seller_company IS NOT NULL 
        AND seller_company != ""
    ) ranked
    WHERE rn > 1
    """
    
    result = d1.execute_query(find_duplicates_sql)
    
    if not result or not result.get('success'):
        print("❌ Failed to find duplicates")
        return
        
    duplicate_ids = [row['id'] for row in result['result'][0]['results']]
    
    if not duplicate_ids:
        print("✅ No exact duplicates found!")
        return
    
    print(f"   🗑️  Found {len(duplicate_ids)} duplicate records to remove")
    
    # Delete from contact_sources first (due to foreign key constraint)
    print("   🔗 Removing contact_sources references...")
    for i in range(0, len(duplicate_ids), 100):  # Process in batches
        batch_ids = duplicate_ids[i:i+100]
        id_list = "', '".join(batch_ids)
        delete_sources_sql = f"DELETE FROM contact_sources WHERE contact_id IN ('{id_list}')"
        
        sources_result = d1.execute_query(delete_sources_sql)
        if not sources_result or not sources_result.get('success'):
            print(f"⚠️  Warning: Failed to delete contact_sources for batch {i//100 + 1}")
    
    # Now delete from contacts
    print("   👥 Removing duplicate contacts...")
    for i in range(0, len(duplicate_ids), 100):  # Process in batches  
        batch_ids = duplicate_ids[i:i+100]
        id_list = "', '".join(batch_ids)
        delete_contacts_sql = f"DELETE FROM contacts WHERE id IN ('{id_list}')"
        
        contacts_result = d1.execute_query(delete_contacts_sql)
        if not contacts_result or not contacts_result.get('success'):
            print(f"❌ Failed to delete contacts for batch {i//100 + 1}")
            return
        
        print(f"      ✅ Deleted batch {i//100 + 1}/{(len(duplicate_ids)-1)//100 + 1}")
    
    result = {"success": True}  # Mark as successful if we got here
    
    if result and result.get('success'):
        # Get new count
        result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
        if result and result.get('success'):
            after_count = result['result'][0]['results'][0]['total']
            removed_count = before_count - after_count
            
            print(f"✅ Cleanup completed!")
            print(f"📊 Results:")
            print(f"   • Contacts before: {before_count:,}")
            print(f"   • Contacts after: {after_count:,}")
            print(f"   • Duplicates removed: {removed_count:,}")
            print(f"   • Space saved: {(removed_count/before_count)*100:.1f}%")
            
            if removed_count > 0:
                print(f"\\n💡 Next steps:")
                print(f"   1. Run 'python d1_duplicate_cleaner.py analyze' to verify")
                print(f"   2. Test your application with the cleaned data")
                print(f"   3. If satisfied, you can drop the backup table")
        else:
            print("❌ Failed to get final count")
    else:
        print("❌ Cleanup failed!")
        print(f"💡 If data was corrupted, run 'python d1_duplicate_cleaner.py restore'")

def restore_from_backup():
    """Restore contacts table from backup"""
    print("🔄 RESTORING FROM BACKUP")
    print("=" * 30)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    # Check if backup exists
    result = d1.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts_backup'")
    if not (result and result.get('success') and result['result'][0]['results']):
        print("❌ No backup table found!")
        return
    
    # Get backup count
    result = d1.execute_query("SELECT COUNT(*) as backup_count FROM contacts_backup")
    if not result or not result.get('success'):
        print("❌ Failed to read backup table")
        return
    
    backup_count = result['result'][0]['results'][0]['backup_count']
    print(f"📊 Backup contains {backup_count:,} contacts")
    
    response = input(f"Are you sure you want to restore? This will REPLACE current data! (y/N): ").lower().strip()
    if response != 'y':
        print("❌ Restore cancelled")
        return
    
    # Drop current table and restore from backup
    print("🗑️  Dropping current contacts table...")
    d1.execute_query("DROP TABLE contacts")
    
    print("🔄 Restoring from backup...")
    result = d1.execute_query("CREATE TABLE contacts AS SELECT * FROM contacts_backup")
    
    if result and result.get('success'):
        print(f"✅ Restore completed!")
        print(f"📊 Restored {backup_count:,} contacts")
    else:
        print("❌ Restore failed!")

def check_status():
    """Check database status"""
    print("📊 DATABASE STATUS")
    print("=" * 30)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    # Main table
    result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
    if result and result.get('success'):
        total = result['result'][0]['results'][0]['total']
        print(f"📋 Contacts table: {total:,} records")
    
    # Backup table
    result = d1.execute_query("SELECT COUNT(*) as backup_total FROM contacts_backup")
    if result and result.get('success'):
        backup_total = result['result'][0]['results'][0]['backup_total']
        print(f"💾 Backup table: {backup_total:,} records")
    else:
        print("💾 Backup table: Not found")
    
    # Contact sources
    result = d1.execute_query("SELECT COUNT(*) as sources_total FROM contact_sources")
    if result and result.get('success'):
        sources_total = result['result'][0]['results'][0]['sources_total']
        print(f"🔗 Contact sources: {sources_total:,} records")
    
    # Categories
    result = d1.execute_query("SELECT category, COUNT(*) as count FROM contact_sources GROUP BY category ORDER BY count DESC")
    if result and result.get('success'):
        categories = result['result'][0]['results']
        print(f"\\n📂 Categories ({len(categories)} total):")
        for cat in categories:
            print(f"   • {cat['category']}: {cat['count']:,} contacts")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) < 2:
        print("🧹 D1 Database Duplicate Cleanup Tool")
        print("=" * 40)
        print("Usage:")
        print("  python d1_duplicate_cleaner.py analyze   # Analyze duplicates (safe)")
        print("  python d1_duplicate_cleaner.py backup    # Create backup table")
        print("  python d1_duplicate_cleaner.py clean     # Remove duplicates (keep newest)")
        print("  python d1_duplicate_cleaner.py restore   # Restore from backup")
        print("  python d1_duplicate_cleaner.py status    # Check database status")
        print()
        print("⚠️  IMPORTANT: Always run 'backup' before 'clean'!")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'analyze':
        analyze_duplicates()
    elif command == 'backup':
        create_backup()
    elif command == 'clean':
        clean_duplicates()
    elif command == 'restore':
        restore_from_backup()
    elif command == 'status':
        check_status()
    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Available commands: analyze, backup, clean, restore, status")

if __name__ == "__main__":
    main()

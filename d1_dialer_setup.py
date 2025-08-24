#!/usr/bin/env python3
"""
📞 D1 Dialer Setup Tool
Creates and manages unique phone numbers table for multi-line dialer system

This ensures sales reps don't call the same number multiple times while
preserving all contact data for reference.

Usage:
    python d1_dialer_setup.py create      # Create unique_phones table
    python d1_dialer_setup.py populate    # Populate with unique numbers
    python d1_dialer_setup.py status      # Check table status
    python d1_dialer_setup.py export      # Export unique numbers for dialer
"""

import os
import json
import csv
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

def create_unique_phones_table():
    """Create unique phone numbers table for dialer"""
    print("📞 CREATING UNIQUE PHONES TABLE")
    print("=" * 60)
    
    d1 = get_d1_connection()
    if not d1:
        return False
    
    # Create unique phones table with dialer-specific fields
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS unique_phones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE NOT NULL,
        company_name TEXT,
        contact_name TEXT,
        location TEXT,
        equipment_category TEXT,
        first_seen_date TEXT,
        last_updated TEXT,
        total_listings INTEGER DEFAULT 1,
        call_status TEXT DEFAULT 'not_called',
        call_attempts INTEGER DEFAULT 0,
        last_call_date TEXT,
        call_result TEXT,
        sales_notes TEXT,
        priority_score INTEGER DEFAULT 50,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """
    
    # Create index for fast lookups
    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_unique_phones_number ON unique_phones(phone_number);
    CREATE INDEX IF NOT EXISTS idx_unique_phones_status ON unique_phones(call_status);
    CREATE INDEX IF NOT EXISTS idx_unique_phones_priority ON unique_phones(priority_score DESC);
    CREATE INDEX IF NOT EXISTS idx_unique_phones_category ON unique_phones(equipment_category);
    """
    
    try:
        # Create table
        result = d1.execute_query(create_table_sql)
        if not result or not result.get('success'):
            print(f"❌ Failed to create table: {result.get('errors', 'Unknown error')}")
            return False
        
        print("✅ Created unique_phones table")
        
        # Create indexes
        for index_sql in create_index_sql.strip().split(';'):
            if index_sql.strip():
                result = d1.execute_query(index_sql.strip() + ';')
                if not result or not result.get('success'):
                    print(f"⚠️ Warning: Failed to create index: {result.get('errors', 'Unknown error')}")
        
        print("✅ Created database indexes")
        return True
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def populate_unique_phones():
    """Populate unique phones table from contacts"""
    print("📊 POPULATING UNIQUE PHONES TABLE")
    print("=" * 60)
    
    d1 = get_d1_connection()
    if not d1:
        return False
    
    try:
        # Clear existing data
        print("🧹 Clearing existing unique phones data...")
        result = d1.execute_query("DELETE FROM unique_phones")
        if not result or not result.get('success'):
            print(f"❌ Failed to clear table: {result.get('errors', 'Unknown error')}")
            return False
        
        print("🔄 Extracting unique phone numbers with proper aggregation...")
        
        # Use a subquery to get unique phones with aggregated data
        populate_sql = """
        INSERT INTO unique_phones (
            phone_number, 
            company_name, 
            contact_name, 
            location, 
            equipment_category,
            first_seen_date,
            last_updated,
            total_listings,
            priority_score
        )
        SELECT 
            phone_data.primary_phone,
            phone_data.best_company,
            '' as contact_name,
            phone_data.best_location,
            phone_data.best_category,
            phone_data.first_seen,
            phone_data.last_seen,
            phone_data.listing_count,
            CASE 
                WHEN phone_data.listing_count >= 10 THEN 90
                WHEN phone_data.listing_count >= 5 THEN 75
                WHEN phone_data.listing_count >= 3 THEN 60
                ELSE 50
            END as priority_score
        FROM (
            SELECT 
                c.primary_phone,
                MAX(c.seller_company) as best_company,
                MAX(c.primary_location) as best_location,
                MAX(COALESCE(cs.category, 'unknown')) as best_category,
                MIN(c.last_updated) as first_seen,
                MAX(c.last_updated) as last_seen,
                COUNT(*) as listing_count
            FROM contacts c
            LEFT JOIN contact_sources cs ON c.id = cs.contact_id
            WHERE c.primary_phone IS NOT NULL 
            AND c.primary_phone != ''
            AND LENGTH(c.primary_phone) >= 10
            GROUP BY c.primary_phone
        ) AS phone_data
        ORDER BY phone_data.listing_count DESC
        """
        
        print("🔄 Extracting unique phone numbers...")
        result = d1.execute_query(populate_sql)
        if not result or not result.get('success'):
            print(f"❌ Failed to populate table: {result.get('errors', 'Unknown error')}")
            return False
        
        # Get count of unique phones
        result = d1.execute_query("SELECT COUNT(*) as total FROM unique_phones")
        if result and result.get('success') and result.get('result'):
            # Handle the nested result structure from D1
            total_data = result['result']
            if isinstance(total_data, list) and len(total_data) > 0:
                if 'results' in total_data[0]:
                    total = total_data[0]['results'][0]['total']
                else:
                    total = total_data[0]['total']
                print(f"✅ Successfully populated {total:,} unique phone numbers")
            else:
                print("✅ Table populated (count unavailable)")
        else:
            print("✅ Table populated (count check failed)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error populating table: {e}")
        return False

def show_dialer_status():
    """Show dialer table status and statistics"""
    print("📞 DIALER STATUS REPORT")
    print("=" * 60)
    
    d1 = get_d1_connection()
    if not d1:
        return
    
    try:
        # Check if table exists
        result = d1.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='unique_phones'
        """)
        
        if not result or not result.get('success') or not result.get('result'):
            print("❌ unique_phones table does not exist")
            print("💡 Run: python d1_dialer_setup.py create")
            return
        
        # Get basic stats
        stats_queries = {
            "Total Unique Numbers": "SELECT COUNT(*) as count FROM unique_phones",
            "Not Called": "SELECT COUNT(*) as count FROM unique_phones WHERE call_status = 'not_called'",
            "Called": "SELECT COUNT(*) as count FROM unique_phones WHERE call_status != 'not_called'",
            "High Priority (>= 75)": "SELECT COUNT(*) as count FROM unique_phones WHERE priority_score >= 75",
            "Multiple Listings (3+)": "SELECT COUNT(*) as count FROM unique_phones WHERE total_listings >= 3"
        }
        
        print("📊 DIALER STATISTICS:")
        for label, query in stats_queries.items():
            result = d1.execute_query(query)
            if result and result.get('success') and result.get('result'):
                # Handle nested D1 result structure
                result_data = result['result']
                if isinstance(result_data, list) and len(result_data) > 0:
                    if 'results' in result_data[0]:
                        count = result_data[0]['results'][0]['count']
                    else:
                        count = result_data[0]['count']
                    print(f"   • {label}: {count:,}")
                else:
                    print(f"   • {label}: N/A")
        
        # Show top categories
        print("\n📂 TOP EQUIPMENT CATEGORIES:")
        result = d1.execute_query("""
            SELECT equipment_category, COUNT(*) as count 
            FROM unique_phones 
            GROUP BY equipment_category 
            ORDER BY count DESC 
            LIMIT 10
        """)
        
        if result and result.get('success') and result.get('result'):
            result_data = result['result']
            if isinstance(result_data, list) and len(result_data) > 0:
                if 'results' in result_data[0]:
                    categories = result_data[0]['results']
                else:
                    categories = result_data
                    
                for row in categories:
                    category = row.get('equipment_category', 'Unknown')
                    count = row.get('count', 0)
                    print(f"   • {category}: {count:,} numbers")
        
        # Show priority distribution
        print("\n🎯 PRIORITY DISTRIBUTION:")
        result = d1.execute_query("""
            SELECT 
                CASE 
                    WHEN priority_score >= 90 THEN 'Very High (90+)'
                    WHEN priority_score >= 75 THEN 'High (75-89)'
                    WHEN priority_score >= 60 THEN 'Medium (60-74)'
                    ELSE 'Standard (50-59)'
                END as priority_group,
                COUNT(*) as count
            FROM unique_phones 
            GROUP BY priority_group 
            ORDER BY MIN(priority_score) DESC
        """)
        
        if result and result.get('success') and result.get('result'):
            result_data = result['result']
            if isinstance(result_data, list) and len(result_data) > 0:
                if 'results' in result_data[0]:
                    priorities = result_data[0]['results']
                else:
                    priorities = result_data
                    
                for row in priorities:
                    priority = row.get('priority_group', 'Unknown')
                    count = row.get('count', 0)
                    print(f"   • {priority}: {count:,} numbers")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def export_dialer_list():
    """Export unique phone numbers for dialer system"""
    print("📤 EXPORTING DIALER LIST")
    print("=" * 60)
    
    d1 = get_d1_connection()
    if not d1:
        return False
    
    try:
        # Get all unique phones sorted by priority
        result = d1.execute_query("""
            SELECT 
                phone_number,
                company_name,
                contact_name,
                location,
                equipment_category,
                total_listings,
                priority_score,
                call_status,
                call_attempts,
                last_call_date
            FROM unique_phones 
            ORDER BY priority_score DESC, total_listings DESC
        """)
        
        if not result or not result.get('success'):
            print(f"❌ Failed to export data: {result.get('errors', 'Unknown error')}")
            return False
        
        # Handle D1's nested result structure
        result_data = result['result']
        if isinstance(result_data, list) and len(result_data) > 0:
            if 'results' in result_data[0]:
                contacts = result_data[0]['results']
            else:
                contacts = result_data
        else:
            contacts = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export CSV for dialer
        csv_filename = f"dialer_list_{timestamp}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'phone_number', 'company_name', 'contact_name', 'location',
                'equipment_category', 'total_listings', 'priority_score',
                'call_status', 'call_attempts', 'last_call_date'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(contacts)
        
        # Export JSON for API integration
        json_filename = f"dialer_list_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_numbers': len(contacts),
                'contacts': contacts
            }, jsonfile, indent=2)
        
        print(f"✅ Exported {len(contacts):,} unique numbers:")
        print(f"   • CSV: {csv_filename}")
        print(f"   • JSON: {json_filename}")
        
        # Show priority breakdown
        priority_counts = {}
        for contact in contacts:
            score = contact['priority_score']
            if score >= 90:
                group = 'Very High (90+)'
            elif score >= 75:
                group = 'High (75-89)'
            elif score >= 60:
                group = 'Medium (60-74)'
            else:
                group = 'Standard (50-59)'
            
            priority_counts[group] = priority_counts.get(group, 0) + 1
        
        print("\n🎯 EXPORT PRIORITY BREAKDOWN:")
        for group, count in priority_counts.items():
            print(f"   • {group}: {count:,} numbers")
        
        return True
        
    except Exception as e:
        print(f"❌ Error exporting: {e}")
        return False

def update_call_result(phone_number, call_status, call_result=None, sales_notes=None):
    """Update call result for a phone number"""
    d1 = get_d1_connection()
    if not d1:
        return False
    
    try:
        update_sql = """
        UPDATE unique_phones 
        SET 
            call_status = ?,
            call_attempts = call_attempts + 1,
            last_call_date = datetime('now'),
            call_result = ?,
            sales_notes = ?,
            updated_at = datetime('now')
        WHERE phone_number = ?
        """
        
        result = d1.execute_query(update_sql, [call_status, call_result, sales_notes, phone_number])
        return result and result.get('success')
        
    except Exception as e:
        print(f"❌ Error updating call result: {e}")
        return False

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        success = create_unique_phones_table()
        if success:
            print("\n💡 Next step: python d1_dialer_setup.py populate")
    
    elif command == 'populate':
        success = populate_unique_phones()
        if success:
            print("\n💡 Next step: python d1_dialer_setup.py status")
    
    elif command == 'status':
        show_dialer_status()
    
    elif command == 'export':
        success = export_dialer_list()
        if success:
            print("\n💡 Files ready for dialer system integration")
    
    else:
        print("❌ Unknown command")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()

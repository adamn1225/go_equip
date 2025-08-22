#!/usr/bin/env python3
"""
Migrate data from JSON category files to Cloudflare D1 database
Uses the D1 HTTP API for data insertion
"""

import json
import requests
import os
from datetime import datetime
import re

class D1DatabaseManager:
    def __init__(self, account_id, database_id, api_token):
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def execute_query(self, sql, params=None):
        """Execute a SQL query on D1 database"""
        payload = {
            "sql": sql
        }
        if params:
            payload["params"] = params
        
        response = requests.post(f"{self.base_url}/query", 
                               headers=self.headers, 
                               json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Query failed: {response.status_code} - {response.text}")
            return None
    
    def batch_insert_contacts(self, contacts_batch):
        """Insert multiple contacts in a batch"""
        sql_statements = []
        
        for contact_id, contact in contacts_batch.items():
            # Extract state from location
            location = contact.get('primary_location', '')
            state = 'Unknown'
            city = ''
            
            if location:
                match = re.search(r',\s*([A-Za-z\s]+)$', location)
                if match:
                    state = match.group(1).strip()
                city_match = re.search(r'^([^,]+)', location)
                if city_match:
                    city = city_match.group(1).strip()
            
            # Insert main contact
            contact_sql = """
                INSERT OR REPLACE INTO contacts 
                (id, seller_company, primary_phone, primary_location, email, website,
                 total_listings, priority_score, priority_level, first_contact_date, 
                 last_updated, notes, city, state) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            contact_params = [
                contact_id,
                contact.get('seller_company', ''),
                contact.get('primary_phone', ''),
                contact.get('primary_location', ''),
                contact.get('email', ''),
                contact.get('website', ''),
                contact.get('total_listings', 1),
                0,  # priority_score - calculate later
                contact.get('contact_priority', 'medium'),
                contact.get('first_contact_date', datetime.now().strftime('%Y-%m-%d')),
                contact.get('last_updated', datetime.now().isoformat()),
                contact.get('notes', ''),
                city,
                state
            ]
            
            sql_statements.append({"sql": contact_sql, "params": contact_params})
            
            # Insert sources
            for source in contact.get('sources', []):
                source_sql = """
                    INSERT INTO contact_sources 
                    (contact_id, site, category, first_seen, listing_count, page_url) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                source_params = [
                    contact_id,
                    source.get('site', ''),
                    source.get('category', ''),
                    source.get('first_seen', datetime.now().strftime('%Y-%m-%d')),
                    source.get('listing_count', 1),
                    source.get('page_url', '')
                ]
                sql_statements.append({"sql": source_sql, "params": source_params})
            
            # Insert additional info as JSON
            additional_info = contact.get('additional_info', {})
            if additional_info:
                info_sql = """
                    INSERT OR REPLACE INTO contact_additional_info 
                    (contact_id, serial_numbers, auction_dates, alternate_locations,
                     equipment_years, equipment_makes, equipment_models, 
                     listing_prices, listing_urls) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                info_params = [
                    contact_id,
                    json.dumps(additional_info.get('serial_numbers', [])),
                    json.dumps(additional_info.get('auction_dates', [])),
                    json.dumps(additional_info.get('alternate_locations', [])),
                    json.dumps(additional_info.get('equipment_years', [])),
                    json.dumps(additional_info.get('equipment_makes', [])),
                    json.dumps(additional_info.get('equipment_models', [])),
                    json.dumps(additional_info.get('listing_prices', [])),
                    json.dumps(additional_info.get('listing_urls', []))
                ]
                sql_statements.append({"sql": info_sql, "params": info_params})
        
        # Execute batch
        response = requests.post(f"{self.base_url}/query", 
                               headers=self.headers, 
                               json=sql_statements)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Batch insert failed: {response.status_code} - {response.text}")
            return None

def migrate_category_to_d1(category_file, db_manager):
    """Migrate a single category file to D1"""
    print(f"📥 Loading {category_file}...")
    
    with open(category_file, 'r') as f:
        category_data = json.load(f)
    
    contacts = category_data.get('contacts', {})
    category_name = category_data.get('metadata', {}).get('category', 'unknown')
    
    print(f"   Found {len(contacts)} contacts in {category_name}")
    
    # Process in batches of 50 (D1 has limits)
    batch_size = 50
    contact_items = list(contacts.items())
    
    for i in range(0, len(contact_items), batch_size):
        batch = dict(contact_items[i:i+batch_size])
        print(f"   📤 Uploading batch {i//batch_size + 1}/{(len(contact_items) + batch_size - 1)//batch_size}")
        
        result = db_manager.batch_insert_contacts(batch)
        if not result:
            print(f"   ❌ Failed to upload batch {i//batch_size + 1}")
            return False
    
    print(f"   ✅ Successfully migrated {len(contacts)} contacts from {category_name}")
    return True

def main():
    """Main migration function"""
    print("🚀 Starting migration from JSON to Cloudflare D1...")
    
    # D1 Configuration - you'll need to get these from Cloudflare dashboard
    # Configuration - YOUR CREDENTIALS
    ACCOUNT_ID = "c0ae0f2da2cc0cf49cc5a01d3f24b30e"
    DATABASE_ID = "9d210ee0-682c-4007-bde1-53bb20b62226"  # From our creation
    API_TOKEN = "nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9"
    
    db_manager = D1DatabaseManager(ACCOUNT_ID, DATABASE_ID, API_TOKEN)
    
    # Test connection
    print("🔍 Testing D1 connection...")
    test_result = db_manager.execute_query("SELECT COUNT(*) as count FROM contacts")
    if test_result:
        print("   ✅ D1 connection successful!")
        current_count = test_result.get('result', [{}])[0].get('count', 0)
        print(f"   Current contacts in D1: {current_count}")
    else:
        print("   ❌ Failed to connect to D1")
        return
    
    # Find all category files
    category_dir = "category_databases"
    if not os.path.exists(category_dir):
        print(f"❌ Category databases directory not found: {category_dir}")
        return
    
    category_files = [f for f in os.listdir(category_dir) if f.endswith('_contacts.json')]
    print(f"📁 Found {len(category_files)} category files to migrate")
    
    # Migrate each category
    total_migrated = 0
    for category_file in category_files:
        file_path = os.path.join(category_dir, category_file)
        if migrate_category_to_d1(file_path, db_manager):
            total_migrated += 1
    
    print(f"\n🎉 Migration complete!")
    print(f"   ✅ Successfully migrated {total_migrated}/{len(category_files)} categories")
    
    # Verify final count
    final_result = db_manager.execute_query("SELECT COUNT(*) as count FROM contacts")
    if final_result:
        final_count = final_result.get('result', [{}])[0].get('count', 0)
        print(f"   📊 Total contacts in D1: {final_count}")

if __name__ == "__main__":
    main()

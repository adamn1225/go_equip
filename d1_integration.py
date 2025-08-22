#!/usr/bin/env python3
"""
Direct integration of scraped data into Cloudflare D1 database
Replaces JSON-based integration for better performance and scalability
"""

import json
import requests
import os
import hashlib
from datetime import datetime
import re
import sys

class D1ScraperIntegration:
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
        payload = {"sql": sql}
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
    
    def create_contact_id(self, phone, company):
        """Create a consistent contact ID from phone/company"""
        key = f"{phone}|{company}".lower().strip()
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def extract_location_parts(self, location):
        """Extract city and state from location string"""
        if not location:
            return '', 'Unknown'
        
        # Extract state (after comma)
        state_match = re.search(r',\s*([A-Za-z\s]+)$', location)
        state = state_match.group(1).strip() if state_match else 'Unknown'
        
        # Extract city (before comma)
        city_match = re.search(r'^([^,]+)', location)
        city = city_match.group(1).strip() if city_match else ''
        
        return city, state
    
    def contact_exists(self, contact_id):
        """Check if contact already exists in database"""
        result = self.execute_query(
            "SELECT id FROM contacts WHERE id = ?", 
            [contact_id]
        )
        
        if result and result.get('result'):
            return len(result['result']) > 0
        return False
    
    def insert_contact(self, contact_data, category, source_site):
        """Insert or update a single contact"""
        phone = contact_data.get('phone', '').strip()
        company = contact_data.get('seller_company', '').strip()
        location = contact_data.get('location', '').strip()
        
        if not phone and not company:
            return False, "No phone or company"
        
        contact_id = self.create_contact_id(phone, company)
        city, state = self.extract_location_parts(location)
        
        # Check if contact exists
        exists = self.contact_exists(contact_id)
        
        if exists:
            # Update existing contact
            update_sql = """
                UPDATE contacts 
                SET total_listings = total_listings + 1,
                    last_updated = ? 
                WHERE id = ?
            """
            self.execute_query(update_sql, [datetime.now().isoformat(), contact_id])
            
            # Check if this source already exists
            source_check = self.execute_query(
                "SELECT id FROM contact_sources WHERE contact_id = ? AND site = ? AND category = ?",
                [contact_id, source_site, category]
            )
            
            if not (source_check and source_check.get('result')):
                # Add new source
                source_sql = """
                    INSERT INTO contact_sources 
                    (contact_id, site, category, first_seen, listing_count) 
                    VALUES (?, ?, ?, ?, 1)
                """
                self.execute_query(source_sql, [
                    contact_id, source_site, category, 
                    datetime.now().strftime('%Y-%m-%d')
                ])
            else:
                # Update source listing count
                update_source_sql = """
                    UPDATE contact_sources 
                    SET listing_count = listing_count + 1 
                    WHERE contact_id = ? AND site = ? AND category = ?
                """
                self.execute_query(update_source_sql, [contact_id, source_site, category])
            
            return True, "Updated existing contact"
        
        else:
            # Insert new contact
            contact_sql = """
                INSERT INTO contacts 
                (id, seller_company, primary_phone, primary_location, 
                 total_listings, first_contact_date, last_updated, city, state) 
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            """
            
            result = self.execute_query(contact_sql, [
                contact_id, company, phone, location,
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().isoformat(),
                city, state
            ])
            
            if result:
                # Insert source
                source_sql = """
                    INSERT INTO contact_sources 
                    (contact_id, site, category, first_seen, listing_count) 
                    VALUES (?, ?, ?, ?, 1)
                """
                self.execute_query(source_sql, [
                    contact_id, source_site, category,
                    datetime.now().strftime('%Y-%m-%d')
                ])
                
                # Insert equipment data if available
                if any(contact_data.get(field) for field in ['year', 'make', 'model', 'price']):
                    equipment_sql = """
                        INSERT INTO equipment_data 
                        (contact_id, equipment_year, equipment_make, 
                         equipment_model, listing_price, listing_url) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    self.execute_query(equipment_sql, [
                        contact_id,
                        contact_data.get('year', ''),
                        contact_data.get('make', ''),
                        contact_data.get('model', ''),
                        contact_data.get('price', ''),
                        contact_data.get('url', '')
                    ])
                
                return True, "Inserted new contact"
            
            return False, "Failed to insert contact"
    
    def integrate_scraped_file(self, scraped_file):
        """Integrate a complete scraped JSON file"""
        print(f"📥 Loading scraped data from {scraped_file}...")
        
        with open(scraped_file, 'r') as f:
            scraped_data = json.load(f)
        
        contacts = scraped_data.get('contacts', [])
        category = scraped_data.get('equipment_category', 'general').lower()
        source_site = scraped_data.get('source_site', 'unknown')
        
        print(f"   Found {len(contacts)} contacts in category: {category}")
        print(f"   Source site: {source_site}")
        
        new_contacts = 0
        updated_contacts = 0
        skipped_contacts = 0
        
        for i, contact in enumerate(contacts, 1):
            if i % 100 == 0:
                print(f"   Processing contact {i}/{len(contacts)}...")
            
            success, message = self.insert_contact(contact, category, source_site)
            
            if success:
                if "new" in message:
                    new_contacts += 1
                else:
                    updated_contacts += 1
            else:
                skipped_contacts += 1
        
        print(f"\n✅ Integration Complete!")
        print(f"   📊 New contacts added: {new_contacts}")
        print(f"   🔄 Existing contacts updated: {updated_contacts}")
        print(f"   ⚠️  Contacts skipped: {skipped_contacts}")
        
        # Get total count
        total_result = self.execute_query("SELECT COUNT(*) as count FROM contacts")
        if total_result:
            total_count = total_result.get('result', [{}])[0].get('count', 0)
            print(f"   📈 Total contacts in database: {total_count}")

def load_config():
    """Load D1 configuration from environment or config file"""
    config_file = 'd1_config.json'
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Get from environment or prompt
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    api_token = os.getenv('CLOUDFLARE_API_TOKEN')
    
    if not account_id:
        account_id = input("Enter your Cloudflare Account ID: ")
    if not api_token:
        api_token = input("Enter your Cloudflare API Token: ")
    
    config = {
        'account_id': account_id,
        'database_id': '9d210ee0-682c-4007-bde1-53bb20b62226',
        'api_token': api_token
    }
    
    # Save config for next time
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config

def main():
    """Main integration function"""
    if len(sys.argv) < 2:
        print("Usage: python3 d1_integration.py <scraped_file.json>")
        sys.exit(1)
    
    scraped_file = sys.argv[1]
    
    if not os.path.exists(scraped_file):
        print(f"❌ File not found: {scraped_file}")
        sys.exit(1)
    
    print("🚀 Starting D1 integration...")
    
    # Load configuration
    config = load_config()
    
    # Initialize D1 integration
    d1_integration = D1ScraperIntegration(
        config['account_id'],
        config['database_id'],
        config['api_token']
    )
    
    # Test connection
    print("🔍 Testing D1 connection...")
    test_result = d1_integration.execute_query("SELECT COUNT(*) as count FROM contacts")
    if not test_result:
        print("❌ Failed to connect to D1 database")
        sys.exit(1)
    
    current_count = test_result.get('result', [{}])[0].get('count', 0)
    print(f"   ✅ Connected! Current contacts: {current_count}")
    
    # Integrate the file
    d1_integration.integrate_scraped_file(scraped_file)
    
    print("\n🎉 D1 integration successful!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test migration script for 100 contacts
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime
import re

def parse_location(location_str):
    """Parse location string to extract city and state"""
    if not location_str or location_str.strip() == '':
        return '', 'Unknown'
    
    if ',' in location_str:
        parts = location_str.split(',')
        city = parts[0].strip()
        state = parts[1].strip()
        return city, state
    else:
        return '', location_str.strip()

def escape_sql(value):
    if value is None or value == 'None' or value == 'N/A':
        return 'NULL'
    return "'" + str(value).replace("'", "''") + "'"

def main():
    print("🧪 Testing migration with 100 contacts...")
    
    # Load test data
    with open('test_excavator_100.json', 'r') as f:
        data = json.load(f)
    
    contacts = data.get('contacts', {})
    print(f"   Found {len(contacts)} test contacts")
    
    # Create SQL statements
    sql_statements = []
    
    for contact_id, contact in contacts.items():
        # Parse location
        city, state = parse_location(contact.get('primary_location', ''))
        
        # Clean phone and email
        phone = contact.get('primary_phone', '').strip()
        if phone in ('N/A', 'None', ''):
            phone = None
            
        email = contact.get('email', '').strip()
        if email in ('N/A', 'None', ''):
            email = None
        
        # Insert contact
        contact_sql = f"""INSERT OR IGNORE INTO contacts (
            id, seller_company, primary_phone, email, 
            primary_location, city, state, total_listings
        ) VALUES (
            {escape_sql(contact_id)},
            {escape_sql(contact.get('seller_company', 'Unknown'))},
            {escape_sql(phone)},
            {escape_sql(email)},
            {escape_sql(contact.get('primary_location', ''))},
            {escape_sql(city)},
            {escape_sql(state)},
            {contact.get('total_listings', 1)}
        );"""
        sql_statements.append(contact_sql)
        
        # Insert source
        source_sql = f"""INSERT OR IGNORE INTO contact_sources (
            contact_id, site, category, first_seen, listing_count
        ) VALUES (
            {escape_sql(contact_id)},
            'excavator_scraper',
            'excavator',
            {escape_sql(datetime.now().date().isoformat())},
            {contact.get('total_listings', 1)}
        );"""
        sql_statements.append(source_sql)
    
    # Write SQL to temp file
    sql_content = '\n'.join(sql_statements)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
        temp_file.write(sql_content)
        temp_file_path = temp_file.name
    
    try:
        print("   📤 Executing test migration...")
        
        cmd = [
            'wrangler', 'd1', 'execute', 'equipment-contacts', '--remote',
            '--file', temp_file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              env={**os.environ, 
                                   'CLOUDFLARE_API_TOKEN': 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9',
                                   'CLOUDFLARE_ACCOUNT_ID': 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'})
        
        if result.returncode == 0:
            print("   ✅ Test migration successful!")
            
            # Check count
            count_cmd = [
                'wrangler', 'd1', 'execute', 'equipment-contacts', '--remote',
                '--command', 'SELECT COUNT(*) as count FROM contacts'
            ]
            
            count_result = subprocess.run(count_cmd, capture_output=True, text=True,
                                        env={**os.environ, 
                                             'CLOUDFLARE_API_TOKEN': 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9',
                                             'CLOUDFLARE_ACCOUNT_ID': 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'})
            
            print("   📊 Current database status:")
            print(count_result.stdout)
        else:
            print("   ❌ Test migration failed")
            print(f"   Error: {result.stderr}")
            
    finally:
        os.unlink(temp_file_path)

if __name__ == "__main__":
    main()

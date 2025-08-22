#!/usr/bin/env python3
"""
Migrate data from JSON category files to Cloudflare D1 database using Wrangler CLI
This approach is more reliable than the HTTP API for batch insertions
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
    
    # Common patterns: "City, State" or "City, ST" or "State" only
    if ',' in location_str:
        parts = location_str.split(',')
        city = parts[0].strip()
        state = parts[1].strip()
        
        # Handle state abbreviations and full names
        state_map = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
        }
        
        if state in state_map:
            state = state_map[state]
            
        return city, state
    else:
        # No comma, might be state only
        location_clean = location_str.strip()
        state_map = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
        }
        
        if location_clean in state_map:
            return '', state_map[location_clean]
        elif location_clean in state_map.values():
            return '', location_clean
        else:
            return '', location_clean

def create_sql_insert_file(contacts_data, category_name):
    """Create a temporary SQL file with INSERT statements"""
    sql_statements = []
    
    for contact_id, contact in contacts_data.items():
        # Parse location
        city, state = parse_location(contact.get('primary_location', ''))
        
        # Clean phone number
        phone = contact.get('primary_phone', '').strip()
        if phone == 'N/A' or phone == 'None':
            phone = ''
        
        # Clean email
        email = contact.get('email', '').strip()
        if email == 'N/A' or email == 'None':
            email = ''
        
        # Escape single quotes in strings
        def escape_sql(value):
            if value is None:
                return 'NULL'
            return "'" + str(value).replace("'", "''") + "'"
        
        # Insert into contacts table
        contact_sql = f"""INSERT OR IGNORE INTO contacts (
            id, seller_company, primary_phone, email, 
            primary_location, city, state, 
            total_listings, first_contact_date, last_updated
        ) VALUES (
            {escape_sql(contact_id)},
            {escape_sql(contact.get('seller_company', 'Unknown'))},
            {escape_sql(phone)},
            {escape_sql(email)},
            {escape_sql(contact.get('primary_location', ''))},
            {escape_sql(city)},
            {escape_sql(state)},
            {contact.get('total_listings', 0)},
            {escape_sql(datetime.now().date().isoformat())},
            {escape_sql(datetime.now().isoformat())}
        );"""
        sql_statements.append(contact_sql)
        
        # Insert into contact_sources table for category
        source_sql = f"""INSERT OR IGNORE INTO contact_sources (
            contact_id, site, category, first_seen, listing_count
        ) VALUES (
            {escape_sql(contact_id)},
            {escape_sql(f"{category_name}_scraper")},
            {escape_sql(category_name)},
            {escape_sql(datetime.now().date().isoformat())},
            {contact.get('total_listings', 0)}
        );"""
        sql_statements.append(source_sql)
        
        # Insert equipment data if available
        equipment_years = contact.get('equipment_years', [])
        equipment_makes = contact.get('equipment_makes', [])
        equipment_models = contact.get('equipment_models', [])
        equipment_prices = contact.get('equipment_prices', [])
        
        if equipment_years or equipment_makes or equipment_models:
            max_equipment = max(len(equipment_years), len(equipment_makes), len(equipment_models))
            for i in range(max_equipment):
                year = equipment_years[i] if i < len(equipment_years) else None
                make = equipment_makes[i] if i < len(equipment_makes) else None
                model = equipment_models[i] if i < len(equipment_models) else None
                price = equipment_prices[i] if i < len(equipment_prices) else None
                
                # Clean price - extract numeric value
                price_numeric = None
                if price:
                    price_clean = re.sub(r'[^\d.]', '', str(price))
                    try:
                        price_numeric = float(price_clean) if price_clean else None
                    except ValueError:
                        price_numeric = None
                
                equipment_sql = f"""INSERT INTO equipment_data (
                    contact_id, equipment_year, equipment_make, equipment_model, listing_price
                ) VALUES (
                    {escape_sql(contact_id)},
                    {escape_sql(str(year)) if year else 'NULL'},
                    {escape_sql(make)},
                    {escape_sql(model)},
                    {escape_sql(str(price)) if price else 'NULL'}
                );"""
                sql_statements.append(equipment_sql)
    
    return '\n'.join(sql_statements)

def migrate_category_to_d1(category_file_path):
    """Migrate a single category file to D1 using Wrangler CLI"""
    category_name = os.path.basename(category_file_path).replace('_contacts.json', '').replace('_', ' ')
    
    print(f"📥 Loading {category_file_path}...")
    
    try:
        with open(category_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        contacts = data.get('contacts', {})
        print(f"   Found {len(contacts)} contacts in {category_name}")
        
        if not contacts:
            print("   ⚠️ No contacts found, skipping")
            return False
        
        # Create SQL insert file
        print("   📝 Generating SQL insert statements...")
        sql_content = create_sql_insert_file(contacts, category_name)
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_file.write(sql_content)
            temp_file_path = temp_file.name
        
        try:
            print(f"   📤 Executing migration via Wrangler...")
            
            # Execute via wrangler CLI
            cmd = [
                'wrangler', 'd1', 'execute', 'equipment-contacts', '--remote',
                '--file', temp_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  env={**os.environ, 
                                       'CLOUDFLARE_API_TOKEN': 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9',
                                       'CLOUDFLARE_ACCOUNT_ID': 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'})
            
            if result.returncode == 0:
                print(f"   ✅ Successfully migrated {category_name}")
                return True
            else:
                print(f"   ❌ Migration failed for {category_name}")
                print(f"   Error: {result.stderr}")
                return False
                
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"   ❌ Error processing {category_file_path}: {str(e)}")
        return False

def main():
    print("🚀 Starting migration from JSON to Cloudflare D1 via Wrangler...")
    
    # Test connection first
    print("🔍 Testing D1 connection...")
    test_cmd = [
        'wrangler', 'd1', 'execute', 'equipment-contacts', '--remote',
        '--command', 'SELECT COUNT(*) as count FROM contacts'
    ]
    
    result = subprocess.run(test_cmd, capture_output=True, text=True,
                          env={**os.environ, 
                               'CLOUDFLARE_API_TOKEN': 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9',
                               'CLOUDFLARE_ACCOUNT_ID': 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'})
    
    if result.returncode == 0:
        print("   ✅ D1 connection successful!")
        # Extract count from output (wrangler output format)
        output_lines = result.stdout.strip().split('\\n')
        for line in output_lines:
            if 'count' in line and '│' in line:
                try:
                    count = int(line.split('│')[1].strip())
                    print(f"   Current contacts in D1: {count}")
                    break
                except:
                    pass
    else:
        print("   ❌ Failed to connect to D1")
        print(f"   Error: {result.stderr}")
        return
    
    # Find all category files
    category_dir = "category_databases"
    if not os.path.exists(category_dir):
        print(f"❌ Category databases directory not found: {category_dir}")
        return
    
    category_files = [f for f in os.listdir(category_dir) if f.endswith('_contacts.json')]
    category_files.sort()  # Process in alphabetical order
    print(f"📁 Found {len(category_files)} category files to migrate")
    
    # Migrate each category
    total_migrated = 0
    for category_file in category_files:
        file_path = os.path.join(category_dir, category_file)
        if migrate_category_to_d1(file_path):
            total_migrated += 1
        print()  # Add spacing between categories
    
    print(f"🎉 Migration complete!")
    print(f"   ✅ Successfully migrated {total_migrated}/{len(category_files)} categories")
    
    # Verify final count
    print("🔍 Verifying final migration results...")
    final_cmd = [
        'wrangler', 'd1', 'execute', 'equipment-contacts', '--remote',
        '--command', 'SELECT COUNT(*) as total_contacts FROM contacts'
    ]
    
    final_result = subprocess.run(final_cmd, capture_output=True, text=True,
                                env={**os.environ, 
                                     'CLOUDFLARE_API_TOKEN': 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9',
                                     'CLOUDFLARE_ACCOUNT_ID': 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'})
    
    if final_result.returncode == 0:
        # Extract count from output
        output_lines = final_result.stdout.strip().split('\\n')
        for line in output_lines:
            if 'total_contacts' in line and '│' in line:
                try:
                    count = int(line.split('│')[1].strip())
                    print(f"   📊 Total contacts in D1: {count:,}")
                    break
                except:
                    pass

if __name__ == "__main__":
    main()

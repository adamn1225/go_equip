#!/usr/bin/env python3
"""
Integrate Latest Scraped Data into Master Contact Database
Processes the latest JSON export and updates master_contact_database.json
"""

import json
import hashlib
from datetime import datetime
import re
import glob
import os
import sys

def create_contact_id(phone, company):
    """Create a consistent contact ID from phone/company"""
    key = f"{phone}|{company}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()[:12]

def clean_phone_number(phone):
    """Clean and standardize phone numbers"""
    if not phone:
        return ""
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    # Return empty if too short or too long
    if len(digits) < 10 or len(digits) > 11:
        return phone  # Return original if unclear
    return phone.strip()

def extract_state(location):
    """Extract state from location string"""
    if not location:
        return "Unknown"
    # Look for state at the end (after comma)
    match = re.search(r',\s*([A-Za-z\s]+)$', location)
    if match:
        return match.group(1).strip()
    return "Unknown"

def integrate_scraped_data(scraped_file, master_file):
    """Integrate scraped data into master database"""
    
    # Load scraped data
    print(f"📥 Loading scraped data from {scraped_file}...")
    with open(scraped_file, 'r') as f:
        scraped_data = json.load(f)
    
    scraped_contacts = scraped_data.get('contacts', [])
    category = scraped_data.get('equipment_category', 'drills').lower()
    source_site = scraped_data.get('source_site', 'machinerytrader.com')
    
    print(f"   Found {len(scraped_contacts)} contacts in category: {category}")
    
    # Load existing master database
    try:
        print(f"📥 Loading existing master database from {master_file}...")
        with open(master_file, 'r') as f:
            master_data = json.load(f)
    except FileNotFoundError:
        print("   Creating new master database...")
        master_data = {
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Master contact log for duplicate detection across multiple sites and categories"
            },
            "contacts": {}
        }
    
    existing_contacts = master_data.get('contacts', {})
    
    # Process each scraped contact
    new_contacts = 0
    updated_contacts = 0
    skipped_contacts = 0
    all_categories = set()
    
    print(f"🔄 Processing {len(scraped_contacts)} scraped contacts...")
    
    for contact in scraped_contacts:
        # Extract contact info
        phone = clean_phone_number(contact.get('phone', ''))
        company = contact.get('seller_company', '').strip()
        location = contact.get('location', '').strip()
        serial_number = contact.get('serial_number', '').strip()
        auction_date = contact.get('auction_date', '').strip()
        
        # Extract equipment details (NEW!)
        year = contact.get('year', '').strip()
        make = contact.get('make', '').strip()
        model = contact.get('model', '').strip()
        price = contact.get('price', '').strip()
        url = contact.get('url', '').strip()
        
        # Track category
        if category:
            all_categories.add(category)

        # Skip contacts without essential info
        if not phone and not company:
            skipped_contacts += 1
            continue
        
        # Create contact ID
        contact_id = create_contact_id(phone, company)
        
        # Check if contact already exists
        if contact_id in existing_contacts:
            # Update existing contact
            existing_contact = existing_contacts[contact_id]
            
            # Add new source if not already present
            sources = existing_contact.get('sources', [])
            source_exists = False
            
            for source in sources:
                if source.get('site') == source_site and source.get('category') == category:
                    source['listing_count'] = source.get('listing_count', 0) + 1
                    source_exists = True
                    break
            
            if not source_exists:
                sources.append({
                    "site": source_site,
                    "category": category,
                    "first_seen": datetime.now().strftime("%Y-%m-%d"),
                    "page_url": "",
                    "listing_count": 1
                })
            
            # Update additional info
            additional_info = existing_contact.get('additional_info', {})
            
            if serial_number and serial_number not in additional_info.get('serial_numbers', []):
                additional_info.setdefault('serial_numbers', []).append(serial_number)
            
            if auction_date and auction_date not in additional_info.get('auction_dates', []):
                additional_info.setdefault('auction_dates', []).append(auction_date)
            
            if location and location not in additional_info.get('alternate_locations', []):
                additional_info.setdefault('alternate_locations', []).append(location)
                
            # Add equipment details to additional info
            if year:
                additional_info.setdefault('equipment_years', [])
                if year not in additional_info['equipment_years']:
                    additional_info['equipment_years'].append(year)
                    
            if make:
                additional_info.setdefault('equipment_makes', [])
                if make not in additional_info['equipment_makes']:
                    additional_info['equipment_makes'].append(make)
                    
            if model:
                additional_info.setdefault('equipment_models', [])
                if model not in additional_info['equipment_models']:
                    additional_info['equipment_models'].append(model)
                    
            if price:
                additional_info.setdefault('listing_prices', [])
                if price not in additional_info['listing_prices']:
                    additional_info['listing_prices'].append(price)
                    
            if url:
                additional_info.setdefault('listing_urls', [])
                if url not in additional_info['listing_urls']:
                    additional_info['listing_urls'].append(url)
            
            # Update contact
            existing_contact['sources'] = sources
            existing_contact['total_listings'] = sum(s.get('listing_count', 1) for s in sources)
            existing_contact['last_updated'] = datetime.now().isoformat()
            existing_contact['additional_info'] = additional_info
            
            updated_contacts += 1
            
        else:
            # Create new contact
            new_contact = {
                "contact_id": contact_id,
                "primary_phone": phone,
                "seller_company": company,
                "primary_location": location,
                "email": "",  # Not available in current scrape
                "sources": [{
                    "site": source_site,
                    "category": category,
                    "first_seen": datetime.now().strftime("%Y-%m-%d"),
                    "page_url": url if url else "",
                    "listing_count": 1
                }],
                "total_listings": 1,
                "first_contact_date": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().isoformat(),
                "additional_info": {
                    "serial_numbers": [serial_number] if serial_number else [],
                    "auction_dates": [auction_date] if auction_date else [],
                    "alternate_locations": [location] if location else [],
                    "equipment_years": [year] if year else [],
                    "equipment_makes": [make] if make else [],
                    "equipment_models": [model] if model else [],
                    "listing_prices": [price] if price else [],
                    "listing_urls": [url] if url else []
                },
                "contact_priority": "medium",
                "notes": ""
            }
            
            existing_contacts[contact_id] = new_contact
            new_contacts += 1
    
    # Update master database metadata
    master_data['contacts'] = existing_contacts
    master_data['metadata']['total_unique_contacts'] = len(existing_contacts)
    master_data['metadata']['last_updated'] = datetime.now().isoformat()

    # Update categories in metadata
    prev_categories = set(master_data['metadata'].get('categories', []))
    all_categories = prev_categories.union(all_categories)
    master_data['metadata']['categories'] = sorted(all_categories)

    # Calculate total sources
    total_sources = 0
    for contact in existing_contacts.values():
        total_sources += len(contact.get('sources', []))
    master_data['metadata']['total_sources'] = total_sources
    
    # Save updated master database
    print(f"💾 Saving updated master database...")
    with open(master_file, 'w') as f:
        json.dump(master_data, f, indent=2)
    
    # Summary
    print(f"\n✅ Integration Complete!")
    print(f"   📊 New contacts added: {new_contacts}")
    print(f"   🔄 Existing contacts updated: {updated_contacts}")
    print(f"   ⚠️  Contacts skipped (insufficient data): {skipped_contacts}")
    print(f"   📈 Total unique contacts now: {len(existing_contacts)}")
    print(f"   🏷️  Category integrated: {category}")
    print(f"   📅 Database last updated: {master_data['metadata']['last_updated']}")

def get_latest_scraped_file():
    """Find the most recent seller_contacts_*.json file"""
    pattern = "seller_contacts_[0-9]*_[0-9]*.json"
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No seller_contacts_*.json files found")
    
    # Sort by modification time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def main():
    """Main function"""
    
    # Check if specific file was provided as argument
    if len(sys.argv) > 1:
        scraped_file = sys.argv[1]
        if not os.path.exists(scraped_file):
            print(f"❌ Error: File '{scraped_file}' not found")
            return
    else:
        # Auto-detect latest file
        try:
            scraped_file = get_latest_scraped_file()
            print(f"🔍 Auto-detected latest file: {scraped_file}")
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            return
    
    master_file = "master_contact_database.json"
    
    print("🚀 Starting data integration...")
    print(f"   Source file: {scraped_file}")
    print(f"   Master database: {master_file}")
    
    try:
        integrate_scraped_data(scraped_file, master_file)
        print("\n🎉 Data integration successful!")
        print("   The master contact database now includes your latest drills category data.")
        print("   You can now run the dashboard to see the updated analytics.")
        
    except Exception as e:
        print(f"\n❌ Error during integration: {e}")
        print("   Please check your input files and try again.")

if __name__ == "__main__":
    main()

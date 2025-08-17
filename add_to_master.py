#!/usr/bin/env python3
"""
Add new contacts from scraping runs to the master contact database
Handles duplicate detection and source tracking across multiple sites
"""

import json
import uuid
from datetime import datetime

def add_to_master_log(new_contacts_file, master_log_file="master_contact_database.json", 
                     site_name="unknown", category="unknown"):
    """
    Add new contacts to master log with duplicate detection
    """
    print(f"🔄 Adding contacts from {site_name} ({category}) to master log...")
    
    # Load master log
    try:
        with open(master_log_file, 'r', encoding='utf-8') as f:
            master_log = json.load(f)
    except FileNotFoundError:
        print(f"❌ Master log file not found: {master_log_file}")
        return False
    
    # Load new contacts
    try:
        with open(new_contacts_file, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ New contacts file not found: {new_contacts_file}")
        return False
    
    # Handle both old format (list) and new format (dict with contacts key)
    if isinstance(new_data, list):
        new_contacts = new_data
    elif isinstance(new_data, dict) and 'contacts' in new_data:
        new_contacts = new_data['contacts']
    else:
        print("❌ Unrecognized contact file format")
        return False
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    # Create phone number lookup for existing contacts
    existing_phones = {}
    for contact_id, contact in master_log['contacts'].items():
        phone = contact['primary_phone'].strip()
        if phone:
            clean_phone = ''.join(filter(str.isdigit, phone))
            if clean_phone:  # Only add if not empty after cleaning
                existing_phones[clean_phone] = contact_id
    
    new_added = 0
    duplicates_updated = 0
    
    print(f"📊 Processing {len(new_contacts)} new contacts...")
    
    for new_contact in new_contacts:
        # Handle both old and new contact formats
        phone = new_contact.get('phone', '') or new_contact.get('primary_phone', '')
        seller = new_contact.get('seller', '') or new_contact.get('seller_company', '')
        
        phone = str(phone).strip()  # Ensure phone is string and stripped
        
        if phone:
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            if clean_phone and clean_phone in existing_phones:
                # Update existing contact
                existing_id = existing_phones[clean_phone]
                existing_contact = master_log['contacts'][existing_id]
                
                # Check if this site/category combo already exists
                source_exists = any(
                    s.get('site') == site_name and s.get('category') == category
                    for s in existing_contact['sources']
                )
                
                if not source_exists:
                    # Add new source
                    new_source = {
                        "site": site_name,
                        "category": category,
                        "first_seen": current_date,
                        "page_url": new_contact.get('url', ''),
                        "listing_count": 1
                    }
                    existing_contact['sources'].append(new_source)
                    existing_contact['total_listings'] += 1
                    existing_contact['last_updated'] = current_timestamp
                    duplicates_updated += 1
                # If source exists, we could increment listing count but for now just skip
                
            else:
                # Add new contact
                contact_id = uuid.uuid4().hex[:12]  # Short unique ID
                new_master_contact = {
                    "contact_id": contact_id,
                    "primary_phone": phone,
                    "seller_company": seller,
                    "primary_location": new_contact.get('location', ''),
                    "email": new_contact.get('email', ''),
                    "sources": [{
                        "site": site_name,
                        "category": category,
                        "first_seen": current_date,
                        "page_url": new_contact.get('url', ''),
                        "listing_count": 1
                    }],
                    "total_listings": 1,
                    "first_contact_date": current_date,
                    "last_updated": current_timestamp,
                    "additional_info": {
                        "serial_numbers": [new_contact.get('serial_number', '')] if new_contact.get('serial_number') else [],
                        "auction_dates": [new_contact.get('auction_date', '')] if new_contact.get('auction_date') else [],
                        "alternate_locations": [new_contact.get('location', '')] if new_contact.get('location') else []
                    },
                    "contact_priority": "medium",
                    "notes": ""
                }
                master_log['contacts'][contact_id] = new_master_contact
                
                # Add to lookup for future duplicates in this batch
                if clean_phone:
                    existing_phones[clean_phone] = contact_id
                
                new_added += 1
        else:
            # Handle contacts without phone numbers (always add as new)
            contact_id = uuid.uuid4().hex[:12]
            new_master_contact = {
                "contact_id": contact_id,
                "primary_phone": "",
                "seller_company": seller,
                "primary_location": new_contact.get('location', ''),
                "email": new_contact.get('email', ''),
                "sources": [{
                    "site": site_name,
                    "category": category,
                    "first_seen": current_date,
                    "page_url": new_contact.get('url', ''),
                    "listing_count": 1
                }],
                "total_listings": 1,
                "first_contact_date": current_date,
                "last_updated": current_timestamp,
                "additional_info": {
                    "serial_numbers": [new_contact.get('serial_number', '')] if new_contact.get('serial_number') else [],
                    "auction_dates": [new_contact.get('auction_date', '')] if new_contact.get('auction_date') else [],
                    "alternate_locations": [new_contact.get('location', '')] if new_contact.get('location') else []
                },
                "contact_priority": "low",  # Lower priority for contacts without phone
                "notes": "No phone number available"
            }
            master_log['contacts'][contact_id] = new_master_contact
            new_added += 1
    
    # Update metadata
    master_log['metadata']['last_updated'] = current_timestamp
    master_log['metadata']['total_unique_contacts'] = len(master_log['contacts'])
    master_log['metadata']['total_sources'] = sum(len(contact['sources']) for contact in master_log['contacts'].values())
    
    # Save updated master log
    with open(master_log_file, 'w', encoding='utf-8') as f:
        json.dump(master_log, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Master log updated!")
    print(f"📊 Summary:")
    print(f"  - New contacts added: {new_added}")
    print(f"  - Existing contacts updated: {duplicates_updated}")
    print(f"  - Total unique contacts: {len(master_log['contacts'])}")
    print(f"  - Total source entries: {master_log['metadata']['total_sources']}")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python add_to_master.py <new_contacts.json> <site_name> <category>")
        print("Example: python add_to_master.py seller_contacts_20250817.json tractorhouse.com farm_equipment")
        sys.exit(1)
    
    new_file = sys.argv[1]
    site = sys.argv[2]
    cat = sys.argv[3]
    
    success = add_to_master_log(new_file, "master_contact_database.json", site, cat)
    if success:
        print(f"\n🎯 Next steps:")
        print(f"1. Check master_contact_database.json for the updated data")
        print(f"2. Run analysis on multi-site contacts to find cross-platform sellers")
    else:
        print("❌ Failed to update master log")
        sys.exit(1)

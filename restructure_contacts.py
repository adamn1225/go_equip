import json
import hashlib
from datetime import datetime
from pathlib import Path
import re

def normalize_phone(phone):
    """Normalize phone number for comparison"""
    if not phone:
        return ""
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    # Handle different formats
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return phone  # Return original if can't normalize

def generate_contact_id(phone, seller_company):
    """Generate unique ID for contact based on phone and company"""
    key = f"{normalize_phone(phone)}_{seller_company}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:12]

def restructure_contacts_to_master_log(input_file, output_file=None):
    """Convert existing JSON to master contact log with duplicate detection"""
    
    if output_file is None:
        output_file = input_file.replace('.json', '_master_log.json')
    
    # Load existing data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    contacts = data.get('contacts', [])
    print(f"Processing {len(contacts)} contacts...")
    
    # Master log structure
    master_log = {
        "metadata": {
            "created_date": datetime.now().isoformat(),
            "total_unique_contacts": 0,
            "total_sources": 0,
            "version": "1.0",
            "description": "Master contact log for duplicate detection across multiple sites and categories"
        },
        "contacts": {}
    }
    
    # Process each contact
    duplicates_found = 0
    
    for contact in contacts:
        phone = contact.get('phone', '')
        seller_company = contact.get('seller_company', contact.get('seller', ''))
        location = contact.get('location', '')
        
        # Skip contacts without phone or company
        if not phone and not seller_company:
            continue
            
        # Generate unique ID
        contact_id = generate_contact_id(phone, seller_company)
        
        # Check if contact already exists
        if contact_id in master_log['contacts']:
            # Duplicate found - update existing record
            existing = master_log['contacts'][contact_id]
            duplicates_found += 1
            
            # Add to sources if not already present
            source_exists = any(
                s['site'] == 'machinerytrader.com' and 
                s['category'] == 'construction' 
                for s in existing['sources']
            )
            
            if not source_exists:
                existing['sources'].append({
                    "site": "machinerytrader.com",
                    "category": "construction", 
                    "first_seen": "2025-08-15",
                    "page_url": contact.get('url', ''),
                    "listing_count": 1
                })
                existing['total_listings'] += 1
            else:
                # Increment listing count for existing source
                for source in existing['sources']:
                    if (source['site'] == 'machinerytrader.com' and 
                        source['category'] == 'construction'):
                        source['listing_count'] += 1
                        existing['total_listings'] += 1
                        break
        else:
            # New contact - add to master log
            master_log['contacts'][contact_id] = {
                "contact_id": contact_id,
                "primary_phone": normalize_phone(phone),
                "seller_company": seller_company,
                "primary_location": location,
                "email": contact.get('email', ''),
                "sources": [
                    {
                        "site": "machinerytrader.com",
                        "category": "construction",
                        "first_seen": "2025-08-15", 
                        "page_url": contact.get('url', ''),
                        "listing_count": 1
                    }
                ],
                "total_listings": 1,
                "first_contact_date": "2025-08-15",
                "last_updated": datetime.now().isoformat(),
                "additional_info": {
                    "serial_numbers": [contact.get('serial_number', '')] if contact.get('serial_number') else [],
                    "auction_dates": [contact.get('auction_date', '')] if contact.get('auction_date') else [],
                    "alternate_locations": [location] if location else []
                },
                "contact_priority": "medium",  # Can be: low, medium, high
                "notes": ""
            }
    
    # Update metadata
    master_log['metadata']['total_unique_contacts'] = len(master_log['contacts'])
    master_log['metadata']['total_sources'] = sum(
        len(contact['sources']) for contact in master_log['contacts'].values()
    )
    
    # Save master log
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_log, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Master log created: {output_file}")
    print(f"📊 Unique contacts: {len(master_log['contacts'])}")
    print(f"🔄 Duplicates merged: {duplicates_found}")
    print(f"🌐 Total source entries: {master_log['metadata']['total_sources']}")
    
    return master_log

def add_new_contacts_to_master_log(new_contacts_file, master_log_file, site_name, category):
    """Add new contacts from a scraping session to existing master log"""
    
    # Load master log
    with open(master_log_file, 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    
    # Load new contacts
    with open(new_contacts_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)
    
    new_contacts = new_data.get('contacts', [])
    print(f"Adding {len(new_contacts)} new contacts from {site_name}...")
    
    new_unique = 0
    duplicates_updated = 0
    
    for contact in new_contacts:
        phone = contact.get('phone', '')
        seller_company = contact.get('seller_company', contact.get('seller', ''))
        
        if not phone and not seller_company:
            continue
            
        contact_id = generate_contact_id(phone, seller_company)
        
        if contact_id in master_log['contacts']:
            # Update existing contact
            existing = master_log['contacts'][contact_id]
            
            # Check if this source already exists
            source_exists = any(
                s['site'] == site_name and s['category'] == category
                for s in existing['sources']
            )
            
            if not source_exists:
                existing['sources'].append({
                    "site": site_name,
                    "category": category,
                    "first_seen": datetime.now().strftime('%Y-%m-%d'),
                    "page_url": contact.get('url', ''),
                    "listing_count": 1
                })
                existing['total_listings'] += 1
                duplicates_updated += 1
            
            existing['last_updated'] = datetime.now().isoformat()
            
        else:
            # Add new contact
            master_log['contacts'][contact_id] = {
                "contact_id": contact_id,
                "primary_phone": normalize_phone(phone),
                "seller_company": seller_company,
                "primary_location": contact.get('location', ''),
                "email": contact.get('email', ''),
                "sources": [
                    {
                        "site": site_name,
                        "category": category,
                        "first_seen": datetime.now().strftime('%Y-%m-%d'),
                        "page_url": contact.get('url', ''),
                        "listing_count": 1
                    }
                ],
                "total_listings": 1,
                "first_contact_date": datetime.now().strftime('%Y-%m-%d'),
                "last_updated": datetime.now().isoformat(),
                "additional_info": {
                    "serial_numbers": [],
                    "auction_dates": [],
                    "alternate_locations": []
                },
                "contact_priority": "medium",
                "notes": ""
            }
            new_unique += 1
    
    # Update metadata
    master_log['metadata']['total_unique_contacts'] = len(master_log['contacts'])
    master_log['metadata']['total_sources'] = sum(
        len(contact['sources']) for contact in master_log['contacts'].values()
    )
    master_log['metadata']['last_updated'] = datetime.now().isoformat()
    
    # Save updated master log
    with open(master_log_file, 'w', encoding='utf-8') as f:
        json.dump(master_log, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Master log updated!")
    print(f"➕ New unique contacts: {new_unique}")
    print(f"🔄 Existing contacts updated: {duplicates_updated}")
    print(f"📊 Total unique contacts: {len(master_log['contacts'])}")
    
    return master_log

def get_contact_stats(master_log_file):
    """Get statistics from master log"""
    with open(master_log_file, 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    
    contacts = master_log['contacts']
    
    # Site statistics
    site_stats = {}
    multi_site_contacts = 0
    
    for contact in contacts.values():
        if len(contact['sources']) > 1:
            multi_site_contacts += 1
            
        for source in contact['sources']:
            site = source['site']
            if site not in site_stats:
                site_stats[site] = {'contacts': 0, 'listings': 0}
            site_stats[site]['contacts'] += 1
            site_stats[site]['listings'] += source['listing_count']
    
    print(f"\n📊 Master Log Statistics:")
    print(f"Total unique contacts: {len(contacts)}")
    print(f"Multi-site contacts: {multi_site_contacts}")
    print(f"\n🌐 By Site:")
    for site, stats in site_stats.items():
        print(f"  {site}: {stats['contacts']} contacts, {stats['listings']} listings")

def main():
    """Main function to restructure existing data"""
    
    # Find JSON files in current directory
    json_files = list(Path('.').glob('seller_contacts_*.json'))
    
    if not json_files:
        print("No seller contact JSON files found!")
        return
    
    # Use the most recent file (by filename)
    latest_file = sorted(json_files)[-1]
    print(f"Using file: {latest_file}")
    
    # Create master log
    master_log = restructure_contacts_to_master_log(str(latest_file))
    
    # Show statistics
    get_contact_stats(f"{latest_file.stem}_master_log.json")
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Use '{latest_file.stem}_master_log.json' as your master contact database")
    print(f"2. When scraping new sites/categories, use add_new_contacts_to_master_log()")
    print(f"3. The system will automatically detect and merge duplicates")

# Example usage functions
def example_add_new_site():
    """Example of how to add contacts from a new site"""
    # This would be called after scraping a new site
    add_new_contacts_to_master_log(
        'new_contacts.json',           # New contacts file
        'contacts_master_log.json',    # Master log file  
        'tractorhouse.com',           # Site name
        'tractors'                    # Category
    )

if __name__ == "__main__":
    main()

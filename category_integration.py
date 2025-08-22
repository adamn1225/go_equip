#!/usr/bin/env python3
"""
Category-Based Integration Script
Integrates new scraped data directly into category-specific files
"""

import json
import os
import hashlib
from datetime import datetime
import re

def integrate_to_category_database(scraped_file, category_databases_dir="category_databases"):
    """Integrate scraped data into the appropriate category database"""
    
    # Load scraped data
    print(f"📥 Loading scraped data from {scraped_file}...")
    with open(scraped_file, 'r') as f:
        scraped_data = json.load(f)
    
    category = scraped_data.get('equipment_category', 'general').lower()
    category_clean = category.replace('/', '_').replace(' ', '_')
    category_file = f"{category_databases_dir}/{category_clean}_contacts.json"
    
    # Create directory if it doesn't exist
    os.makedirs(category_databases_dir, exist_ok=True)
    
    # Load existing category database or create new one
    if os.path.exists(category_file):
        print(f"📥 Loading existing {category} database...")
        with open(category_file, 'r') as f:
            category_data = json.load(f)
    else:
        print(f"📝 Creating new {category} database...")
        category_data = {
            "metadata": {
                "category": category,
                "created_date": datetime.now().isoformat(),
                "total_contacts": 0,
                "last_updated": datetime.now().isoformat()
            },
            "contacts": {}
        }
    
    # Process contacts (use same logic as original integration)
    contacts = category_data['contacts']
    scraped_contacts = scraped_data.get('contacts', [])
    
    new_contacts = 0
    updated_contacts = 0
    
    for contact in scraped_contacts:
        phone = contact.get('phone', '').strip()
        company = contact.get('seller_company', '').strip()
        
        if not phone and not company:
            continue
        
        # Create contact ID
        contact_id = hashlib.md5(f"{phone}|{company}".lower().encode()).hexdigest()[:12]
        
        if contact_id in contacts:
            # Update existing
            # (Add your existing update logic here)
            updated_contacts += 1
        else:
            # Add new contact
            contacts[contact_id] = {
                "contact_id": contact_id,
                "primary_phone": phone,
                "seller_company": company,
                "primary_location": contact.get('location', ''),
                "sources": [{
                    "site": scraped_data.get('source_site', 'unknown'),
                    "category": category,
                    "first_seen": datetime.now().strftime("%Y-%m-%d"),
                    "listing_count": 1
                }],
                "total_listings": 1,
                "first_contact_date": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().isoformat(),
                "contact_priority": "medium",
                "notes": ""
            }
            new_contacts += 1
    
    # Update metadata
    category_data['metadata']['total_contacts'] = len(contacts)
    category_data['metadata']['last_updated'] = datetime.now().isoformat()
    
    # Save updated category database
    print(f"💾 Saving updated {category} database...")
    with open(category_file, 'w') as f:
        json.dump(category_data, f, indent=2)
    
    print(f"✅ Integration complete for {category}!")
    print(f"   📊 New contacts: {new_contacts}")
    print(f"   🔄 Updated contacts: {updated_contacts}")
    print(f"   📈 Total contacts in {category}: {len(contacts)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        integrate_to_category_database(sys.argv[1])
    else:
        print("Usage: python3 category_integration.py <scraped_file>")

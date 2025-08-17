#!/usr/bin/env python3
"""
Properly fix categories based on first_contact_date
"""

import json
from datetime import datetime

def fix_categories_properly():
    """Fix categories based on actual scraping dates"""
    
    with open('master_contact_database.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔧 Properly categorizing {len(data['contacts'])} contacts...")
    
    updated_count = 0
    
    for contact_id, contact in data['contacts'].items():
        first_contact_date = contact.get('first_contact_date', '')
        
        for source in contact.get('sources', []):
            # Categorize based on when they were first scraped
            if first_contact_date == '2025-08-15':
                # First scrape was excavators  
                if source.get('category') != 'excavator':
                    source['category'] = 'excavator'
                    updated_count += 1
            elif first_contact_date == '2025-08-17':
                # Second scrape was dozers
                if source.get('category') != 'dozer':
                    source['category'] = 'dozer'
                    updated_count += 1
    
    # Update metadata
    data['metadata']['last_updated'] = datetime.now().isoformat()
    data['metadata']['category_fix_v2_applied'] = True
    
    # Save updated data
    with open('master_contact_database.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated {updated_count} source categories")
    print("🎯 Categories now properly mapped:")
    print("   - 2025-08-15 contacts (4,919) → excavator") 
    print("   - 2025-08-17 contacts (667) → dozer")

if __name__ == "__main__":
    fix_categories_properly()

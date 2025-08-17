#!/usr/bin/env python3
"""
Fix categories in existing master database
Maps generic 'construction' categories to specific equipment types based on patterns
"""

import json
from datetime import datetime

def fix_categories():
    """Fix categories in the master database"""
    
    with open('master_contact_database.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔧 Fixing categories in {len(data['contacts'])} contacts...")
    
    updated_count = 0
    
    for contact_id, contact in data['contacts'].items():
        for source in contact.get('sources', []):
            # If category is generic 'construction', try to infer actual type
            if source.get('category') in ['construction', 'machinerytrader.com']:
                # Pattern-based detection for existing data
                company = contact.get('seller_company', '').lower()
                location = contact.get('primary_location', '').lower()
                
                # Simple heuristic - if it was scraped recently, it's probably dozer
                # Since your last scrape was dozers (Category=1025)
                if contact.get('last_updated', '').startswith('2025-08-17'):
                    source['category'] = 'dozer'
                    updated_count += 1
                # Earlier scrapes were likely excavators
                elif contact.get('last_updated', '').startswith('2025-08-15'):
                    source['category'] = 'excavator' 
                    updated_count += 1
                else:
                    # Default to excavator for older data
                    source['category'] = 'excavator'
                    updated_count += 1
    
    # Update metadata
    data['metadata']['last_updated'] = datetime.now().isoformat()
    data['metadata']['category_fix_applied'] = True
    
    # Save updated data
    with open('master_contact_database.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated {updated_count} source categories")
    print("🎯 Categories now mapped based on scraping dates:")
    print("   - 2025-08-17 contacts → dozer") 
    print("   - 2025-08-15 contacts → excavator")

if __name__ == "__main__":
    fix_categories()

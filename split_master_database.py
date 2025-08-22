#!/usr/bin/env python3
"""
Split Master Database by Category
Creates separate JSON files for each equipment category to manage file sizes
"""

import json
import os
from datetime import datetime
from collections import defaultdict

def split_master_database():
    """Split the master database into category-specific files"""
    
    # Load the massive master database
    print("📥 Loading master database...")
    with open('master_contact_database.json', 'r') as f:
        master_data = json.load(f)
    
    contacts = master_data['contacts']
    total_contacts = len(contacts)
    print(f"   Total contacts: {total_contacts}")
    
    # Group contacts by category
    category_contacts = defaultdict(dict)
    category_stats = defaultdict(int)
    
    print("🔄 Grouping contacts by category...")
    
    for contact_id, contact in contacts.items():
        # Get all categories for this contact
        contact_categories = set()
        
        for source in contact.get('sources', []):
            category = source.get('category', '').lower().strip()
            if category:
                contact_categories.add(category)
        
        # Add contact to each category file
        for category in contact_categories:
            category_contacts[category][contact_id] = contact
            category_stats[category] += 1
    
    # Create directory for category files
    os.makedirs('category_databases', exist_ok=True)
    
    # Save each category to its own file
    print("\n💾 Creating category-specific database files...")
    
    for category, cat_contacts in category_contacts.items():
        filename = f"category_databases/{category.replace('/', '_').replace(' ', '_')}_contacts.json"
        
        category_data = {
            "metadata": {
                "category": category,
                "created_date": datetime.now().isoformat(),
                "total_contacts": len(cat_contacts),
                "parent_database": "master_contact_database.json",
                "last_updated": master_data['metadata']['last_updated']
            },
            "contacts": cat_contacts
        }
        
        with open(filename, 'w') as f:
            json.dump(category_data, f, indent=2)
        
        print(f"   ✅ {category}: {len(cat_contacts)} contacts -> {filename}")
    
    # Create a lightweight master index
    master_index = {
        "metadata": {
            "created_date": datetime.now().isoformat(),
            "total_contacts": total_contacts,
            "total_categories": len(category_stats),
            "split_date": datetime.now().isoformat(),
            "description": "Index of split category databases"
        },
        "categories": dict(category_stats),
        "category_files": {
            category: f"category_databases/{category.replace('/', '_').replace(' ', '_')}_contacts.json"
            for category in category_stats.keys()
        }
    }
    
    with open('master_database_index.json', 'w') as f:
        json.dump(master_index, f, indent=2)
    
    print(f"\n🎉 Database split complete!")
    print(f"   📊 Created {len(category_stats)} category files")
    print(f"   📁 Files saved in: category_databases/")
    print(f"   🗂️  Master index: master_database_index.json")
    print(f"   💽 Original file size reduction: ~{len(category_stats)}x smaller per category")

if __name__ == "__main__":
    split_master_database()

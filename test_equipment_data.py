#!/usr/bin/env python3
"""
Test Equipment Data Processing
Quick test to verify equipment data is being loaded correctly
"""

import json
import pandas as pd

def test_equipment_data():
    """Test if equipment data is present in the master database"""
    
    try:
        # Load master database
        with open('master_contact_database.json', 'r') as f:
            data = json.load(f)
        
        contacts = data.get('contacts', {})
        
        print(f"📊 Testing Equipment Data in Master Database")
        print(f"   Total contacts: {len(contacts):,}")
        
        # Count equipment data availability
        equipment_data_count = 0
        pricing_data_count = 0
        makes_count = 0
        models_count = 0
        years_count = 0
        
        sample_equipment_data = []
        
        for contact_id, contact in contacts.items():
            additional_info = contact.get('additional_info', {})
            
            equipment_years = additional_info.get('equipment_years', [])
            equipment_makes = additional_info.get('equipment_makes', [])
            equipment_models = additional_info.get('equipment_models', [])
            listing_prices = additional_info.get('listing_prices', [])
            
            has_equipment = bool(equipment_years or equipment_makes or equipment_models)
            has_pricing = bool(listing_prices)
            
            if has_equipment:
                equipment_data_count += 1
                
            if has_pricing:
                pricing_data_count += 1
                
            if equipment_years:
                years_count += 1
            if equipment_makes:
                makes_count += 1
            if equipment_models:
                models_count += 1
            
            # Collect samples for display
            if len(sample_equipment_data) < 5 and has_equipment:
                sample_equipment_data.append({
                    'company': contact.get('seller_company', 'Unknown'),
                    'years': equipment_years[:3],  # First 3 years
                    'makes': equipment_makes[:3],  # First 3 makes
                    'models': equipment_models[:3],  # First 3 models
                    'prices': listing_prices[:3]  # First 3 prices
                })
        
        print(f"\n🔧 Equipment Data Summary:")
        print(f"   Contacts with equipment data: {equipment_data_count:,} ({equipment_data_count/len(contacts)*100:.1f}%)")
        print(f"   Contacts with pricing data: {pricing_data_count:,} ({pricing_data_count/len(contacts)*100:.1f}%)")
        print(f"   Contacts with years: {years_count:,}")
        print(f"   Contacts with makes: {makes_count:,}")
        print(f"   Contacts with models: {models_count:,}")
        
        if sample_equipment_data:
            print(f"\n📋 Sample Equipment Data:")
            for i, sample in enumerate(sample_equipment_data, 1):
                print(f"   {i}. {sample['company']}")
                if sample['years']:
                    print(f"      Years: {', '.join(sample['years'])}")
                if sample['makes']:
                    print(f"      Makes: {', '.join(sample['makes'])}")
                if sample['models']:
                    print(f"      Models: {', '.join(sample['models'])}")
                if sample['prices']:
                    print(f"      Prices: {', '.join(sample['prices'])}")
                print()
        
        # Test if new scraper data structure works
        if equipment_data_count > 0:
            print("✅ Equipment data found! The enhanced scraper is working.")
            print("   Your dashboard will display equipment analytics.")
        else:
            print("⚠️  No equipment data found yet.")
            print("   New scraper will capture this data going forward.")
        
        return equipment_data_count > 0
        
    except FileNotFoundError:
        print("❌ Master database not found.")
        return False
    except Exception as e:
        print(f"❌ Error testing equipment data: {e}")
        return False

if __name__ == "__main__":
    test_equipment_data()

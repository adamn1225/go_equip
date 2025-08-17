#!/usr/bin/env python3
"""
High-Value Target Finder
Identify and analyze the most valuable contacts for business outreach
"""

import json
import pandas as pd
from collections import defaultdict
import re

def load_contacts(master_log_file="master_contact_database.json"):
    """Load contacts from master database"""
    with open(master_log_file, 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    return master_log['contacts']

def find_dealer_networks():
    """Identify major equipment dealer networks"""
    contacts = load_contacts()
    
    print("🏢 MAJOR EQUIPMENT DEALER NETWORKS")
    print("="*80)
    
    # Group by company name (fuzzy matching)
    company_groups = defaultdict(list)
    
    for contact_id, contact in contacts.items():
        company = contact['seller_company'].strip()
        if company:
            # Normalize company name for grouping
            normalized = re.sub(r'\b(Inc|LLC|Corp|Co\.|Ltd|Equipment|Machinery)\b', '', company, flags=re.IGNORECASE).strip()
            normalized = re.sub(r'[^\w\s]', '', normalized).strip().lower()
            
            if len(normalized) > 3:  # Skip very short names
                company_groups[normalized].append({
                    'contact_id': contact_id,
                    'original_name': company,
                    'phone': contact['primary_phone'],
                    'location': contact['primary_location'],
                    'listings': contact['total_listings']
                })
    
    # Find companies with multiple locations/contacts
    dealer_networks = []
    for normalized_name, contacts_list in company_groups.items():
        if len(contacts_list) > 1:
            total_listings = sum(c['listings'] for c in contacts_list)
            locations = set(c['location'] for c in contacts_list if c['location'])
            
            dealer_networks.append({
                'network_name': normalized_name,
                'locations': len(locations),
                'contacts': len(contacts_list),
                'total_listings': total_listings,
                'details': contacts_list
            })
    
    # Sort by total impact (listings + locations)
    dealer_networks.sort(key=lambda x: x['total_listings'] + x['locations']*5, reverse=True)
    
    print(f"🎯 Found {len(dealer_networks)} potential dealer networks:\n")
    
    for i, network in enumerate(dealer_networks[:15], 1):
        print(f"{i}. {network['network_name'].title()}")
        print(f"   📍 {network['locations']} locations | 📞 {network['contacts']} contacts | 📝 {network['total_listings']} listings")
        
        # Show top locations for this network
        location_summary = defaultdict(int)
        for contact in network['details']:
            if contact['location']:
                location_summary[contact['location']] += contact['listings']
        
        top_locations = sorted(location_summary.items(), key=lambda x: x[1], reverse=True)[:3]
        locations_str = " | ".join([f"{loc} ({listings})" for loc, listings in top_locations])
        print(f"   🏢 Top locations: {locations_str}")
        print()
    
    return dealer_networks

def find_regional_powerhouses():
    """Find high-volume sellers by region"""
    contacts = load_contacts()
    
    print("\n🗺️  REGIONAL EQUIPMENT POWERHOUSES")
    print("="*80)
    
    # Group by state
    state_sellers = defaultdict(list)
    
    for contact_id, contact in contacts.items():
        location = contact['primary_location']
        if location and contact['total_listings'] >= 10:  # Only high-volume sellers
            # Extract state
            state_match = re.search(r',\s*([A-Za-z\s]+)$', location)
            if state_match:
                state = state_match.group(1).strip()
                if len(state) <= 20:  # Reasonable state name
                    state_sellers[state].append({
                        'company': contact['seller_company'],
                        'phone': contact['primary_phone'],
                        'location': contact['primary_location'],
                        'listings': contact['total_listings']
                    })
    
    # Show top states and their powerhouse sellers
    for state in sorted(state_sellers.keys(), key=lambda s: len(state_sellers[s]), reverse=True)[:10]:
        sellers = sorted(state_sellers[state], key=lambda s: s['listings'], reverse=True)
        total_listings = sum(s['listings'] for s in sellers)
        
        print(f"🏛️  {state}: {len(sellers)} powerhouse sellers, {total_listings} total listings")
        
        for seller in sellers[:5]:  # Top 5 in each state
            print(f"   📞 {seller['phone']} - {seller['company']}")
            print(f"      📝 {seller['listings']} listings | 📍 {seller['location']}")
        
        if len(sellers) > 5:
            print(f"   ... and {len(sellers)-5} more")
        print()

def find_suspicious_duplicates():
    """Find potential duplicate contacts that might be the same business"""
    contacts = load_contacts()
    
    print("\n🔍 POTENTIAL DUPLICATE BUSINESSES")
    print("="*80)
    
    # Group by phone number
    phone_groups = defaultdict(list)
    
    for contact_id, contact in contacts.items():
        phone = contact['primary_phone']
        if phone:
            clean_phone = ''.join(filter(str.isdigit, phone))
            if clean_phone:
                phone_groups[clean_phone].append({
                    'contact_id': contact_id,
                    'company': contact['seller_company'],
                    'phone': contact['primary_phone'],
                    'location': contact['primary_location'],
                    'listings': contact['total_listings']
                })
    
    # Find groups with different company names (potential data issues)
    suspicious_groups = []
    
    for phone, contacts_list in phone_groups.items():
        if len(contacts_list) > 1:
            companies = set(c['company'] for c in contacts_list if c['company'])
            if len(companies) > 1:  # Same phone, different companies
                total_listings = sum(c['listings'] for c in contacts_list)
                suspicious_groups.append({
                    'phone': contacts_list[0]['phone'],
                    'companies': list(companies),
                    'total_listings': total_listings,
                    'contacts': contacts_list
                })
    
    suspicious_groups.sort(key=lambda x: x['total_listings'], reverse=True)
    
    print(f"⚠️  Found {len(suspicious_groups)} phone numbers with multiple company names:\n")
    
    for i, group in enumerate(suspicious_groups[:10], 1):
        print(f"{i}. Phone: {group['phone']} | Total listings: {group['total_listings']}")
        print(f"   Companies: {' | '.join(group['companies'])}")
        
        for contact in group['contacts']:
            print(f"   📍 {contact['location']} - {contact['company']} ({contact['listings']} listings)")
        print()
    
    return suspicious_groups

def generate_outreach_targets():
    """Generate prioritized list for business outreach"""
    contacts = load_contacts()
    
    print("\n🎯 TOP OUTREACH TARGETS")
    print("="*80)
    
    # Score contacts based on multiple factors
    scored_contacts = []
    
    for contact_id, contact in contacts.items():
        score = 0
        reasons = []
        
        # Listing volume scoring
        listings = contact['total_listings']
        if listings >= 50:
            score += 100
            reasons.append(f"Very high volume ({listings} listings)")
        elif listings >= 20:
            score += 70
            reasons.append(f"High volume ({listings} listings)")
        elif listings >= 10:
            score += 40
            reasons.append(f"Medium volume ({listings} listings)")
        elif listings >= 5:
            score += 20
            reasons.append(f"Low volume ({listings} listings)")
        
        # Company name indicators
        company = contact['seller_company'].lower()
        if any(word in company for word in ['equipment', 'machinery', 'rentals', 'rental']):
            score += 30
            reasons.append("Equipment dealer/rental")
        
        if any(word in company for word in ['cat', 'caterpillar', 'john deere', 'komatsu', 'volvo']):
            score += 25
            reasons.append("Major brand dealer")
        
        # Phone number quality
        if contact['primary_phone'] and len(contact['primary_phone']) >= 10:
            score += 10
            reasons.append("Valid phone")
        
        # Location quality
        if contact['primary_location'] and ',' in contact['primary_location']:
            score += 5
            reasons.append("Complete location")
        
        if score >= 30:  # Minimum threshold
            scored_contacts.append({
                'contact_id': contact_id,
                'score': score,
                'company': contact['seller_company'],
                'phone': contact['primary_phone'],
                'location': contact['primary_location'],
                'listings': contact['total_listings'],
                'reasons': reasons
            })
    
    # Sort by score
    scored_contacts.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"🏆 Top {min(25, len(scored_contacts))} outreach targets:\n")
    
    for i, target in enumerate(scored_contacts[:25], 1):
        print(f"{i}. {target['company']} (Score: {target['score']})")
        print(f"   📞 {target['phone']}")
        print(f"   📍 {target['location']}")
        print(f"   📝 {target['listings']} listings")
        print(f"   💡 {' | '.join(target['reasons'])}")
        print()
    
    # Export to CSV
    import pandas as pd
    df = pd.DataFrame(scored_contacts)
    filename = "high_priority_outreach_targets.csv"
    df.to_csv(filename, index=False)
    print(f"💾 Full outreach targets exported to: {filename}")
    
    return scored_contacts

def main():
    """Run all high-value analyses"""
    print("🚀 HIGH-VALUE TARGET ANALYSIS")
    print("="*80)
    
    try:
        dealer_networks = find_dealer_networks()
        find_regional_powerhouses()
        suspicious = find_suspicious_duplicates()
        targets = generate_outreach_targets()
        
        print("\n📋 ANALYSIS SUMMARY")
        print("="*80)
        print(f"• Dealer networks identified: {len(dealer_networks)}")
        print(f"• Suspicious duplicates found: {len(suspicious)}")
        print(f"• Qualified outreach targets: {len(targets)}")
        
        print("\n💡 Next Steps:")
        print("1. Review high_priority_outreach_targets.csv for contact details")
        print("2. Cross-reference dealer networks for bulk partnership opportunities")
        print("3. Clean up suspicious duplicates to improve data quality")
        print("4. Focus on regional powerhouses for geographic expansion")
        
    except FileNotFoundError:
        print("❌ Master contact database not found. Please ensure master_contact_database.json exists.")

if __name__ == "__main__":
    main()

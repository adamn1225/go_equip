#!/usr/bin/env python3
"""
Business Intelligence Dashboard
Quick insights and actionable intelligence from contact database
"""

import json
import pandas as pd
from collections import defaultdict, Counter
import re

def quick_insights():
    """Generate quick business insights for decision making"""
    print("📊 BUSINESS INTELLIGENCE DASHBOARD")
    print("="*80)
    
    # Load master database
    with open("master_contact_database.json", 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    
    contacts = master_log['contacts']
    
    print(f"🎯 DATABASE OVERVIEW:")
    print(f"  • Total unique contacts: {len(contacts):,}")
    print(f"  • Database created: {master_log['metadata']['created_date']}")
    
    # High-value segments
    high_volume = [c for c in contacts.values() if c['total_listings'] >= 10]
    major_dealers = [c for c in contacts.values() if any(brand in c['seller_company'].lower() 
                     for brand in ['cat', 'caterpillar', 'john deere', 'komatsu', 'volvo', 'case'])]
    equipment_companies = [c for c in contacts.values() if any(word in c['seller_company'].lower() 
                          for word in ['equipment', 'machinery', 'rental', 'rentals'])]
    
    print(f"\n💎 HIGH-VALUE SEGMENTS:")
    print(f"  • High-volume sellers (10+ listings): {len(high_volume):,}")
    print(f"  • Major brand dealers: {len(major_dealers):,}")
    print(f"  • Equipment/rental companies: {len(equipment_companies):,}")
    
    # Geographic hotspots
    state_counts = defaultdict(int)
    for contact in contacts.values():
        location = contact['primary_location']
        if location:
            match = re.search(r',\s*([A-Za-z\s]+)$', location)
            if match:
                state = match.group(1).strip()
                if len(state) <= 20:
                    state_counts[state] += 1
    
    top_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    print(f"\n🗺️  TOP MARKETS:")
    for state, count in top_states:
        print(f"  • {state}: {count:,} sellers")
    
    # Actionable recommendations
    print(f"\n💡 IMMEDIATE ACTION ITEMS:")
    
    # Top 5 highest-volume contacts for immediate outreach
    top_volume = sorted(contacts.values(), key=lambda x: x['total_listings'], reverse=True)[:5]
    print(f"\n1️⃣  PRIORITY OUTREACH (Top 5 by volume):")
    for contact in top_volume:
        company = contact['seller_company'] or "Unknown Company"
        phone = contact['primary_phone'] or "No Phone"
        print(f"   📞 {phone} - {company} ({contact['total_listings']} listings)")
    
    # Major equipment dealer networks to target
    print(f"\n2️⃣  DEALER NETWORKS TO TARGET:")
    dealer_keywords = ['wheeler machinery', 'holt cat', 'empire southwest', 'tractor & equipment']
    
    for keyword in dealer_keywords:
        matching_contacts = [c for c in contacts.values() 
                           if keyword in c['seller_company'].lower()]
        if matching_contacts:
            total_listings = sum(c['total_listings'] for c in matching_contacts)
            locations = set(c['primary_location'] for c in matching_contacts if c['primary_location'])
            print(f"   🏢 {keyword.title()}: {len(matching_contacts)} locations, {total_listings} total listings")
    
    # Data quality issues to fix
    no_phone = len([c for c in contacts.values() if not c['primary_phone']])
    print(f"\n3️⃣  DATA QUALITY CLEANUP:")
    print(f"   ⚠️  {no_phone} contacts missing phone numbers")
    
    # ROI calculations
    avg_listings_per_contact = sum(c['total_listings'] for c in contacts.values()) / len(contacts)
    
    print(f"\n4️⃣  BUSINESS METRICS:")
    print(f"   📈 Average listings per seller: {avg_listings_per_contact:.1f}")
    print(f"   🎯 High-value contact rate: {len(high_volume)/len(contacts)*100:.1f}%")
    print(f"   🏢 Equipment dealer rate: {len(equipment_companies)/len(contacts)*100:.1f}%")
    
    return {
        'total_contacts': len(contacts),
        'high_volume': len(high_volume),
        'major_dealers': len(major_dealers),
        'equipment_companies': len(equipment_companies),
        'top_states': top_states,
        'top_volume_contacts': top_volume
    }

def generate_outreach_list():
    """Generate focused outreach list with contact details"""
    with open("master_contact_database.json", 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    
    contacts = master_log['contacts']
    
    # Score and rank contacts for outreach priority
    scored_contacts = []
    
    for contact_id, contact in contacts.items():
        score = 0
        
        # Volume scoring
        listings = contact['total_listings']
        if listings >= 20:
            score += 100
        elif listings >= 10:
            score += 60
        elif listings >= 5:
            score += 30
        
        # Company type scoring
        company = contact['seller_company'].lower()
        if 'equipment' in company or 'machinery' in company:
            score += 25
        if 'rental' in company:
            score += 20
        if any(brand in company for brand in ['cat', 'caterpillar', 'john deere', 'komatsu']):
            score += 30
        
        # Contact quality scoring
        if contact['primary_phone'] and len(contact['primary_phone']) >= 10:
            score += 15
        
        if score >= 40:  # Minimum threshold for outreach
            scored_contacts.append({
                'contact_id': contact_id,
                'score': score,
                'company': contact['seller_company'],
                'phone': contact['primary_phone'],
                'location': contact['primary_location'],
                'listings': contact['total_listings']
            })
    
    # Sort by score
    scored_contacts.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n📋 OUTREACH-READY CONTACT LIST")
    print("="*80)
    print(f"Generated {len(scored_contacts)} qualified leads")
    
    # Export top contacts
    top_contacts = scored_contacts[:50]  # Top 50 for focused outreach
    
    outreach_data = []
    for i, contact in enumerate(top_contacts, 1):
        outreach_data.append({
            'Rank': i,
            'Score': contact['score'],
            'Company': contact['company'],
            'Phone': contact['phone'],
            'Location': contact['location'],
            'Listings': contact['listings'],
            'Priority': 'High' if contact['score'] >= 80 else 'Medium' if contact['score'] >= 60 else 'Standard'
        })
    
    # Save to CSV
    df = pd.DataFrame(outreach_data)
    filename = "priority_outreach_contacts.csv"
    df.to_csv(filename, index=False)
    
    print(f"💾 Top 50 contacts saved to: {filename}")
    
    # Show preview
    print(f"\n🏆 TOP 10 OUTREACH TARGETS:")
    for i, contact in enumerate(top_contacts[:10], 1):
        print(f"{i:2d}. {contact['company']} (Score: {contact['score']})")
        print(f"    📞 {contact['phone']} | 📝 {contact['listings']} listings")
        print(f"    📍 {contact['location']}")
        print()
    
    return outreach_data

def market_analysis():
    """Quick market analysis for strategic planning"""
    with open("master_contact_database.json", 'r', encoding='utf-8') as f:
        master_log = json.load(f)
    
    contacts = master_log['contacts']
    
    print(f"\n🌐 MARKET ANALYSIS")
    print("="*80)
    
    # State-level analysis
    state_data = defaultdict(lambda: {'sellers': 0, 'listings': 0, 'high_volume': 0})
    
    for contact in contacts.values():
        location = contact['primary_location']
        if location:
            match = re.search(r',\s*([A-Za-z\s]+)$', location)
            if match:
                state = match.group(1).strip()
                if len(state) <= 20:
                    state_data[state]['sellers'] += 1
                    state_data[state]['listings'] += contact['total_listings']
                    if contact['total_listings'] >= 10:
                        state_data[state]['high_volume'] += 1
    
    # Top markets by different metrics
    print(f"📊 TOP MARKETS BY SELLER COUNT:")
    by_sellers = sorted(state_data.items(), key=lambda x: x[1]['sellers'], reverse=True)[:10]
    for state, data in by_sellers:
        avg_listings = data['listings'] / data['sellers'] if data['sellers'] > 0 else 0
        print(f"  {state}: {data['sellers']:,} sellers | Avg: {avg_listings:.1f} listings/seller")
    
    print(f"\n📊 TOP MARKETS BY TOTAL LISTINGS:")
    by_listings = sorted(state_data.items(), key=lambda x: x[1]['listings'], reverse=True)[:10]
    for state, data in by_listings:
        print(f"  {state}: {data['listings']:,} total listings | {data['sellers']:,} sellers")
    
    print(f"\n📊 TOP MARKETS BY HIGH-VOLUME SELLERS:")
    by_high_volume = sorted(state_data.items(), key=lambda x: x[1]['high_volume'], reverse=True)[:10]
    for state, data in by_high_volume:
        if data['high_volume'] > 0:
            rate = data['high_volume'] / data['sellers'] * 100
            print(f"  {state}: {data['high_volume']} high-volume sellers ({rate:.1f}% rate)")

def main():
    """Run business intelligence dashboard"""
    try:
        insights = quick_insights()
        outreach_data = generate_outreach_list()
        market_analysis()
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"1. Review priority_outreach_contacts.csv for immediate calling list")
        print(f"2. Focus on top 3 states for market expansion")
        print(f"3. Target equipment dealer networks for bulk partnerships")
        print(f"4. Clean up contacts missing phone numbers")
        
    except FileNotFoundError:
        print("❌ Master contact database not found. Please run the scraper first.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Master Contact Database Analysis Tool
Analyze seller patterns, multi-site presence, and contact quality across Sandhills network
"""

import json
import pandas as pd
from collections import defaultdict, Counter
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

class ContactAnalyzer:
    def __init__(self, master_log_file="master_contact_database.json"):
        """Initialize the analyzer with the master contact database"""
        self.master_log_file = master_log_file
        self.master_log = None
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load and parse the master contact database"""
        try:
            with open(self.master_log_file, 'r', encoding='utf-8') as f:
                self.master_log = json.load(f)
            print(f"✅ Loaded master database with {len(self.master_log['contacts'])} contacts")
            self._create_dataframe()
        except FileNotFoundError:
            print(f"❌ Master log file not found: {self.master_log_file}")
            return False
    
    def _create_dataframe(self):
        """Convert contact data to pandas DataFrame for analysis"""
        records = []
        
        for contact_id, contact in self.master_log['contacts'].items():
            # Base contact info
            base_record = {
                'contact_id': contact_id,
                'primary_phone': contact['primary_phone'],
                'seller_company': contact['seller_company'],
                'primary_location': contact['primary_location'],
                'email': contact.get('email', ''),
                'total_listings': contact['total_listings'],
                'first_contact_date': contact['first_contact_date'],
                'contact_priority': contact.get('contact_priority', 'medium'),
                'num_sources': len(contact['sources'])
            }
            
            # Add source information
            sites = []
            categories = []
            for source in contact['sources']:
                sites.append(source['site'])
                categories.append(source['category'])
            
            base_record.update({
                'sites': ', '.join(set(sites)),
                'categories': ', '.join(set(categories)),
                'unique_sites': len(set(sites)),
                'unique_categories': len(set(categories)),
                'is_multi_site': len(set(sites)) > 1,
                'is_multi_category': len(set(categories)) > 1
            })
            
            records.append(base_record)
        
        self.df = pd.DataFrame(records)
        print(f"📊 Created analysis DataFrame with {len(self.df)} contacts")
    
    def _calculate_priority_score(self, row):
        """Calculate priority score for a contact based on multiple factors"""
        score = 0
        
        # Listing volume scoring (most important factor)
        listings = row['total_listings']
        if listings >= 50:
            score += 100  # Major dealer/distributor
        elif listings >= 25:
            score += 80   # Large regional dealer
        elif listings >= 15:
            score += 60   # Active dealer
        elif listings >= 8:
            score += 40   # Regular seller
        elif listings >= 3:
            score += 20   # Occasional seller
        
        # Company type and brand recognition
        company = str(row['seller_company']).lower()
        
        # Major brand dealers (Cat, John Deere, etc.)
        major_brands = ['wheeler machinery', 'holt cat', 'caterpillar', 'cat used', 'cat financial',
                       'john deere', 'komatsu', 'volvo', 'case', 'new holland', 'kubota',
                       'empire southwest', 'ring power', 'altorfer', 'fabick cat', 'thompson tractor',
                       'boyd cat', 'milton cat', 'warren cat', 'peterson cat']
        
        for brand in major_brands:
            if brand in company:
                score += 25
                break
        
        # Equipment-focused companies
        equipment_keywords = ['equipment', 'machinery', 'tractor', 'construction', 'rental', 'rentals']
        if any(keyword in company for keyword in equipment_keywords):
            score += 15
        
        # Contact quality bonuses
        if row['primary_phone'] and len(str(row['primary_phone'])) >= 10:
            score += 10
        
        if row['email']:
            score += 10
        
        if row['primary_location'] and ',' in str(row['primary_location']):
            score += 5  # Complete location (city, state)
        
        # Multi-site bonus (future feature)
        if row.get('is_multi_site', False):
            score += 20
        
        return score
    
    def _get_priority_level(self, score):
        """Convert score to priority level"""
        if score >= 120:
            return 'premium'    # Major dealers, multi-brand, high volume
        elif score >= 80:
            return 'high'       # Regional dealers, good volume
        elif score >= 50:
            return 'medium'     # Active sellers, some equipment focus
        elif score >= 25:
            return 'low'        # Occasional sellers
        else:
            return 'minimal'    # Very low activity
    
    def multi_site_analysis(self):
        """Analyze sellers active on multiple sites"""
        print("\n" + "="*80)
        print("🌐 MULTI-SITE SELLER ANALYSIS")
        print("="*80)
        
        multi_site_contacts = self.df[self.df['is_multi_site'] == True]
        
        print(f"📊 Multi-Site Statistics:")
        print(f"  • Total contacts: {len(self.df):,}")
        print(f"  • Multi-site contacts: {len(multi_site_contacts):,} ({len(multi_site_contacts)/len(self.df)*100:.1f}%)")
        print(f"  • Single-site contacts: {len(self.df) - len(multi_site_contacts):,}")
        
        if len(multi_site_contacts) > 0:
            print(f"\n🏆 TOP MULTI-SITE SELLERS:")
            top_multi_site = multi_site_contacts.nlargest(10, 'unique_sites')
            
            for _, contact in top_multi_site.iterrows():
                print(f"  📞 {contact['primary_phone']} - {contact['seller_company']}")
                print(f"     🌐 Sites: {contact['sites']}")
                print(f"     📝 Listings: {contact['total_listings']} | Sites: {contact['unique_sites']}")
                print(f"     📍 Location: {contact['primary_location']}")
                print()
            
            # Site combination analysis
            print(f"🔗 POPULAR SITE COMBINATIONS:")
            site_combos = multi_site_contacts['sites'].value_counts().head(10)
            for sites, count in site_combos.items():
                print(f"  • {sites}: {count} sellers")
        
        return multi_site_contacts
    
    def contact_quality_analysis(self):
        """Analyze contact data quality and completeness"""
        print("\n" + "="*80)
        print("📋 CONTACT QUALITY ANALYSIS")
        print("="*80)
        
        # Basic completeness statistics
        total_contacts = len(self.df)
        
        quality_stats = {
            'has_phone': len(self.df[self.df['primary_phone'] != '']),
            'has_email': len(self.df[self.df['email'] != '']),
            'has_both': len(self.df[(self.df['primary_phone'] != '') & (self.df['email'] != '')]),
            'has_company': len(self.df[self.df['seller_company'] != '']),
            'has_location': len(self.df[self.df['primary_location'] != ''])
        }
        
        print(f"📊 Data Completeness:")
        for field, count in quality_stats.items():
            percentage = (count / total_contacts) * 100
            print(f"  • {field.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
        
        # Phone number analysis
        phone_patterns = defaultdict(int)
        invalid_phones = []
        
        for _, contact in self.df.iterrows():
            phone = contact['primary_phone']
            if phone:
                # Check phone format patterns
                if re.match(r'^\(\d{3}\)\s?\d{3}[-.]?\d{4}$', phone):
                    phone_patterns['Standard US Format'] += 1
                elif re.match(r'^\d{3}[-.]?\d{3}[-.]?\d{4}$', phone):
                    phone_patterns['US Format (no parens)'] += 1
                elif len(phone.replace('-', '').replace('.', '').replace('(', '').replace(')', '').replace(' ', '')) == 10:
                    phone_patterns['10 digits (various formats)'] += 1
                else:
                    phone_patterns['Non-standard format'] += 1
                    if len(invalid_phones) < 5:  # Show first 5 examples
                        invalid_phones.append(phone)
        
        print(f"\n📞 Phone Number Formats:")
        for pattern, count in phone_patterns.items():
            percentage = (count / quality_stats['has_phone']) * 100 if quality_stats['has_phone'] > 0 else 0
            print(f"  • {pattern}: {count:,} ({percentage:.1f}%)")
        
        if invalid_phones:
            print(f"\n⚠️  Non-standard phone examples: {', '.join(invalid_phones[:5])}")
        
        # Calculate priority scores for each contact
        self.df['priority_score'] = self.df.apply(self._calculate_priority_score, axis=1)
        self.df['priority_level'] = self.df['priority_score'].apply(self._get_priority_level)
        
        # High-value contacts (improved scoring system)
        high_value = self.df[self.df['priority_level'].isin(['high', 'premium'])]
        medium_value = self.df[self.df['priority_level'] == 'medium']
        
        print(f"\n💎 High-Value Contacts:")
        print(f"  • Premium contacts: {len(self.df[self.df['priority_level'] == 'premium']):,}")
        print(f"  • High-priority contacts: {len(self.df[self.df['priority_level'] == 'high']):,}")
        print(f"  • Medium-priority contacts: {len(medium_value):,}")
        print(f"  • Total qualified contacts: {len(high_value):,}")
        
        return quality_stats
    
    def geographic_analysis(self):
        """Analyze geographic distribution of sellers"""
        print("\n" + "="*80)
        print("🗺️  GEOGRAPHIC ANALYSIS")
        print("="*80)
        
        # Extract states from locations
        state_pattern = r'\b([A-Z]{2})\b$|,\s*([A-Za-z\s]+)$'
        states = []
        
        for location in self.df['primary_location']:
            if location:
                # Try to extract state
                match = re.search(state_pattern, location)
                if match:
                    state = match.group(1) or match.group(2)
                    if state and len(state) <= 20:  # Reasonable state name length
                        states.append(state.strip())
        
        if states:
            state_counts = Counter(states)
            print(f"🏛️  TOP STATES BY SELLER COUNT:")
            
            for state, count in state_counts.most_common(15):
                percentage = (count / len(self.df)) * 100
                print(f"  • {state}: {count:,} sellers ({percentage:.1f}%)")
        
        # City analysis (rough)
        cities = []
        for location in self.df['primary_location']:
            if location and ',' in location:
                city = location.split(',')[0].strip()
                if city and len(city) > 2:
                    cities.append(city)
        
        if cities:
            city_counts = Counter(cities)
            print(f"\n🏙️  TOP CITIES BY SELLER COUNT:")
            
            for city, count in city_counts.most_common(10):
                percentage = (count / len(self.df)) * 100
                print(f"  • {city}: {count:,} sellers ({percentage:.1f}%)")
        
        return state_counts if 'state_counts' in locals() else None
    
    def listing_volume_analysis(self):
        """Analyze seller activity by listing volume"""
        print("\n" + "="*80)
        print("📈 LISTING VOLUME ANALYSIS")
        print("="*80)
        
        # Volume distribution
        volume_ranges = [
            (1, 1, "Single listing"),
            (2, 5, "Low volume (2-5)"),
            (6, 15, "Medium volume (6-15)"),
            (16, 50, "High volume (16-50)"),
            (51, float('inf'), "Very high volume (50+)")
        ]
        
        print(f"📊 Seller Volume Distribution:")
        
        for min_vol, max_vol, label in volume_ranges:
            if max_vol == float('inf'):
                count = len(self.df[self.df['total_listings'] >= min_vol])
            else:
                count = len(self.df[(self.df['total_listings'] >= min_vol) & (self.df['total_listings'] <= max_vol)])
            
            percentage = (count / len(self.df)) * 100
            print(f"  • {label}: {count:,} sellers ({percentage:.1f}%)")
        
        # Top volume sellers
        print(f"\n🏆 TOP VOLUME SELLERS:")
        top_volume = self.df.nlargest(15, 'total_listings')
        
        for _, seller in top_volume.iterrows():
            print(f"  📞 {seller['primary_phone']} - {seller['seller_company']}")
            print(f"     📝 {seller['total_listings']} listings | 🌐 {seller['unique_sites']} sites")
            print(f"     📍 {seller['primary_location']}")
            print()
        
        return top_volume
    
    def site_performance_analysis(self):
        """Analyze performance across different sites"""
        print("\n" + "="*80)
        print("🌐 SITE PERFORMANCE ANALYSIS")
        print("="*80)
        
        # Count contacts by site
        site_stats = defaultdict(lambda: {'contacts': 0, 'total_listings': 0})
        
        for _, contact in self.df.iterrows():
            sites = contact['sites'].split(', ') if contact['sites'] else []
            for site in sites:
                site_stats[site]['contacts'] += 1
                # Approximate listings per site (total divided by number of sites)
                site_stats[site]['total_listings'] += contact['total_listings'] / len(sites)
        
        print(f"📊 Performance by Site:")
        
        for site, stats in sorted(site_stats.items(), key=lambda x: x[1]['contacts'], reverse=True):
            avg_listings = stats['total_listings'] / stats['contacts'] if stats['contacts'] > 0 else 0
            print(f"  🌐 {site}:")
            print(f"     • Sellers: {stats['contacts']:,}")
            print(f"     • Est. Total Listings: {int(stats['total_listings']):,}")
            print(f"     • Avg Listings/Seller: {avg_listings:.1f}")
            print()
        
        return site_stats
    
    def export_analysis_report(self, filename=None):
        """Export detailed analysis to files"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"contact_analysis_report_{timestamp}"
        
        # Export high-value contacts (using new priority system)
        high_value = self.df[
            self.df['priority_level'].isin(['premium', 'high'])
        ].sort_values(['priority_score', 'total_listings'], ascending=False)
        
        medium_value = self.df[
            self.df['priority_level'] == 'medium'
        ].sort_values(['priority_score', 'total_listings'], ascending=False)
        
        high_value_file = f"{filename}_high_value_contacts.csv"
        high_value.to_csv(high_value_file, index=False)
        print(f"💾 High-value contacts exported: {high_value_file}")
        
        # Export multi-site sellers
        multi_site = self.df[self.df['is_multi_site'] == True].sort_values('unique_sites', ascending=False)
        multi_site_file = f"{filename}_multi_site_sellers.csv"
        multi_site.to_csv(multi_site_file, index=False)
        print(f"💾 Multi-site sellers exported: {multi_site_file}")
        
        # Export full analysis dataset
        full_file = f"{filename}_full_analysis.csv"
        self.df.to_csv(full_file, index=False)
        print(f"💾 Full analysis dataset exported: {full_file}")
        
        return {
            'high_value': high_value_file,
            'multi_site': multi_site_file,
            'full': full_file
        }
    
    def run_full_analysis(self):
        """Run all analysis functions and generate comprehensive report"""
        print("🚀 STARTING COMPREHENSIVE CONTACT ANALYSIS")
        print("="*80)
        
        if self.df is None:
            print("❌ No data loaded. Please check the master database file.")
            return False
        
        # Run all analyses
        multi_site_data = self.multi_site_analysis()
        quality_stats = self.contact_quality_analysis()
        geographic_data = self.geographic_analysis()
        volume_data = self.listing_volume_analysis()
        site_stats = self.site_performance_analysis()
        
        # Export reports
        print("\n" + "="*80)
        print("💾 EXPORTING ANALYSIS REPORTS")
        print("="*80)
        
        exported_files = self.export_analysis_report()
        
        # Summary
        print("\n" + "="*80)
        print("📋 ANALYSIS COMPLETE - KEY INSIGHTS")
        print("="*80)
        
        print(f"🎯 Database Overview:")
        print(f"  • Total unique contacts: {len(self.df):,}")
        print(f"  • Multi-site sellers: {len(self.df[self.df['is_multi_site']]):,}")
        print(f"  • High-volume sellers (5+ listings): {len(self.df[self.df['total_listings'] >= 5]):,}")
        print(f"  • Complete contact info: {quality_stats['has_both']:,}")
        
        print(f"\n💡 Recommendations:")
        print(f"  1. Focus on multi-site sellers - they're likely serious equipment dealers")
        print(f"  2. High-volume sellers are prime targets for business relationships")
        print(f"  3. Clean up non-standard phone formats for better contact success")
        print(f"  4. Geographic clustering shows regional equipment markets")
        
        return True

def main():
    """Main function to run the analysis"""
    analyzer = ContactAnalyzer()
    
    if analyzer.df is not None:
        analyzer.run_full_analysis()
    else:
        print("Failed to load contact database. Please check the file path.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Interactive Contact Database Dashboard
Visual analytics and insights for equipment seller database
"""

import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter
import re
from datetime import datetime

# Authentication function
def check_password():
    """Simple password authentication for executive access"""
    def password_entered():
        if st.session_state["password"] == "ContactAnalytics2025!":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("# 🔐 Contact Analytics Dashboard")
        st.markdown("**Executive Access Required**")
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.info("Contact your system administrator for access credentials.")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("# 🔐 Contact Analytics Dashboard") 
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password. Please try again.")
        return False
    else:
        return True

class DashboardAnalyzer:
    def __init__(self, master_log_file="master_contact_database.json"):
        self.master_log_file = master_log_file
        self.load_data()
    
    def load_data(self):
        """Load and process contact data"""
        try:
            # Load from local file (works both locally and on Streamlit Cloud)
            with open(self.master_log_file, 'r', encoding='utf-8') as f:
                self.master_log = json.load(f)
            
            # Convert to DataFrame
            records = []
            for contact_id, contact in self.master_log['contacts'].items():
                record = {
                    'contact_id': contact_id,
                    'primary_phone': contact['primary_phone'],
                    'seller_company': contact['seller_company'],
                    'primary_location': contact['primary_location'],
                    'email': contact.get('email', ''),
                    'total_listings': contact['total_listings'],
                    'first_contact_date': contact['first_contact_date'],
                    'num_sources': len(contact['sources'])
                }
                
                # Extract state
                location = contact['primary_location']
                if location:
                    match = re.search(r',\s*([A-Za-z\s]+)$', location)
                    record['state'] = match.group(1).strip() if match else 'Unknown'
                else:
                    record['state'] = 'Unknown'
                
                # Extract categories from sources
                categories = []
                for source in contact.get('sources', []):
                    category = source.get('category', '').strip()
                    if category and category not in categories:
                        categories.append(category)
                record['categories'] = ', '.join(categories) if categories else 'construction'
                
                # Calculate priority score
                record['priority_score'] = self._calculate_priority_score(record)
                record['priority_level'] = self._get_priority_level(record['priority_score'])
                
                records.append(record)
            
            self.df = pd.DataFrame(records)
            
        except FileNotFoundError:
            st.error(f"Master database file not found: {self.master_log_file}")
            self.df = pd.DataFrame()
    
    def _calculate_priority_score(self, record):
        """Calculate priority score"""
        score = 0
        
        # Listing volume
        listings = record['total_listings']
        if listings >= 50:
            score += 100
        elif listings >= 25:
            score += 80
        elif listings >= 15:
            score += 60
        elif listings >= 8:
            score += 40
        elif listings >= 3:
            score += 20
        
        # Company analysis
        company = str(record['seller_company']).lower()
        
        # Major brands
        major_brands = ['wheeler machinery', 'holt cat', 'caterpillar', 'john deere', 'komatsu', 
                       'empire southwest', 'ring power', 'altorfer', 'fabick cat']
        if any(brand in company for brand in major_brands):
            score += 25
        
        # Equipment focus
        if any(word in company for word in ['equipment', 'machinery', 'rental']):
            score += 15
        
        # Contact quality
        if record['primary_phone'] and len(str(record['primary_phone'])) >= 10:
            score += 10
        
        if record['email']:
            score += 10
        
        return score
    
    def _get_priority_level(self, score):
        """Convert score to priority level"""
        if score >= 120:
            return 'Premium'
        elif score >= 80:
            return 'High'
        elif score >= 50:
            return 'Medium'
        elif score >= 25:
            return 'Low'
        else:
            return 'Minimal'

def main():
    # Check authentication first
    if not check_password():
        return
    
    st.set_page_config(
        page_title="Equipment Seller Database Dashboard",
        page_icon="🏗️",
        layout="wide"
    )
    
    st.title("🏗️ Equipment Seller Database Dashboard")
    st.markdown("**Authorized Access - Executive Analytics Portal**")
    
    # Add logout button
    if st.button("🚪 Logout", key="logout_btn"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.markdown("---")
    
    # Load analyzer
    analyzer = DashboardAnalyzer()
    
    if analyzer.df.empty:
        st.error("No data available. Please check your master database file.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Extract unique categories from the data
    all_categories = set()
    for _, contact in analyzer.df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip()
            if cat:
                all_categories.add(cat.title())
    
    # Machine Category filter (NEW!)
    category_options = ['All Categories'] + sorted(list(all_categories))
    selected_category = st.sidebar.selectbox("🏗️ Equipment Category", category_options)
    
    # Quick search for specific equipment
    st.sidebar.markdown("---")
    search_term = st.sidebar.text_input("🔍 Search Equipment/Company", placeholder="e.g., CAT, John Deere, Excavator")
    
    # Priority filter
    priority_options = ['All'] + list(analyzer.df['priority_level'].unique())
    selected_priority = st.sidebar.selectbox("Priority Level", priority_options)
    
    # State filter
    state_options = ['All'] + sorted(analyzer.df['state'].unique())
    selected_state = st.sidebar.selectbox("State", state_options)
    
    # Listing count filter
    min_listings = st.sidebar.slider("Minimum Listings", 0, int(analyzer.df['total_listings'].max()), 0)
    
    # Apply filters
    filtered_df = analyzer.df.copy()
    
    # Category filter (NEW!)
    if selected_category != 'All Categories':
        # Filter contacts that have this category in their categories string
        filtered_df = filtered_df[filtered_df['categories'].str.contains(selected_category.lower(), case=False, na=False)]
    
    # Search filter (NEW!)
    if search_term:
        search_mask = (
            filtered_df['seller_company'].str.contains(search_term, case=False, na=False) |
            filtered_df['categories'].str.contains(search_term, case=False, na=False) |
            filtered_df['primary_location'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]
    
    if selected_priority != 'All':
        filtered_df = filtered_df[filtered_df['priority_level'] == selected_priority]
    
    if selected_state != 'All':
        filtered_df = filtered_df[filtered_df['state'] == selected_state]
    
    filtered_df = filtered_df[filtered_df['total_listings'] >= min_listings]
    
    # Main dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Contacts", f"{len(filtered_df):,}")
    
    with col2:
        high_value_count = len(filtered_df[filtered_df['priority_level'].isin(['Premium', 'High'])])
        st.metric("High-Value Contacts", f"{high_value_count:,}")
    
    with col3:
        total_listings = filtered_df['total_listings'].sum()
        st.metric("Total Listings", f"{total_listings:,}")
    
    with col4:
        avg_listings = filtered_df['total_listings'].mean()
        st.metric("Avg Listings/Contact", f"{avg_listings:.1f}")
    
    # Equipment Category Analysis
    st.subheader("🏗️ Equipment Category Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    
    # Extract equipment categories from sources
    category_counts = {}
    for _, contact in filtered_df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip()
            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Display top categories
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    with col1:
        if sorted_categories:
            st.metric("Primary Category", sorted_categories[0][0].title(), f"{sorted_categories[0][1]:,} contacts")
    
    with col2:
        if len(sorted_categories) > 1:
            st.metric("Secondary Category", sorted_categories[1][0].title(), f"{sorted_categories[1][1]:,} contacts")
    
    with col3:
        excavator_count = category_counts.get('construction', 0)  # Legacy category
        st.metric("Construction Equipment", f"{excavator_count:,}")
    
    with col4:
        multi_category = len([c for c in filtered_df['categories'] if ',' in str(c)])
        st.metric("Multi-Category Dealers", f"{multi_category:,}")
    
    # Category-Specific Insights (NEW!)
    if selected_category != 'All Categories':
        st.markdown("---")
        st.subheader(f"🎯 {selected_category} Market Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_listings_category = filtered_df['total_listings'].mean()
            st.metric("Avg Listings per Dealer", f"{avg_listings_category:.1f}")
        
        with col2:
            top_dealer = filtered_df.nlargest(1, 'total_listings')
            if not top_dealer.empty:
                st.metric("Top Dealer", top_dealer.iloc[0]['seller_company'][:20] + "...", f"{top_dealer.iloc[0]['total_listings']} listings")
        
        with col3:
            premium_in_category = len(filtered_df[filtered_df['priority_level'] == 'Premium'])
            st.metric("Premium Dealers", f"{premium_in_category}")
        
        with col4:
            states_with_category = filtered_df['state'].nunique()
            st.metric("States Covered", f"{states_with_category}")
        
        # Category insights
        st.info(f"💡 **{selected_category} Insights:** {len(filtered_df):,} dealers found with avg {avg_listings_category:.1f} listings each. "
                f"Top markets: {', '.join(filtered_df['state'].value_counts().head(3).index.tolist())}")
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Priority Distribution")
        priority_counts = filtered_df['priority_level'].value_counts()
        fig_priority = px.pie(
            values=priority_counts.values,
            names=priority_counts.index,
            color_discrete_map={
                'Premium': '#ff6b6b',
                'High': '#ffa726',
                'Medium': '#42a5f5',
                'Low': '#66bb6a',
                'Minimal': '#bdbdbd'
            }
        )
        st.plotly_chart(fig_priority, use_container_width=True)
    
    with col2:
        st.subheader("🏗️ Equipment Categories")
        if category_counts:
            # Create category chart
            cat_df = pd.DataFrame(list(category_counts.items()), columns=['Category', 'Count'])
            cat_df = cat_df.sort_values('Count', ascending=True).tail(8)  # Top 8 categories
            
            fig_cat = px.bar(
                cat_df,
                x='Count',
                y='Category',
                orientation='h',
                labels={'Count': 'Number of Contacts', 'Category': 'Equipment Type'},
                color='Count',
                color_continuous_scale='viridis'
            )
            fig_cat.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No category data available")
    
    # Geographic Distribution (moved to next row)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🗺️ Geographic Distribution")
        state_counts = filtered_df['state'].value_counts().head(10)
        fig_geo = px.bar(
            x=state_counts.values,
            y=state_counts.index,
            orientation='h',
            labels={'x': 'Number of Contacts', 'y': 'State'}
        )
        fig_geo.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_geo, use_container_width=True)
    
    # Charts row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Listing Volume Distribution")
        # Create bins for listing counts
        bins = [0, 1, 5, 10, 20, 50, float('inf')]
        labels = ['0', '1-4', '5-9', '10-19', '20-49', '50+']
        filtered_df['listing_range'] = pd.cut(filtered_df['total_listings'], bins=bins, labels=labels, include_lowest=True)
        
        range_counts = filtered_df['listing_range'].value_counts().reindex(labels)
        fig_volume = px.bar(
            x=labels,
            y=range_counts.values,
            labels={'x': 'Listing Count Range', 'y': 'Number of Contacts'}
        )
        st.plotly_chart(fig_volume, use_container_width=True)
    
    with col2:
        st.subheader("🏆 Top Companies by Listings")
        top_companies = filtered_df.nlargest(10, 'total_listings')[['seller_company', 'total_listings', 'priority_level']]
        
        fig_companies = px.bar(
            top_companies,
            x='total_listings',
            y='seller_company',
            color='priority_level',
            orientation='h',
            color_discrete_map={
                'Premium': '#ff6b6b',
                'High': '#ffa726',
                'Medium': '#42a5f5',
                'Low': '#66bb6a',
                'Minimal': '#bdbdbd'
            }
        )
        fig_companies.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_companies, use_container_width=True)
    
    # High-value contacts table
    st.subheader("💎 High-Value Contacts")
    
    high_value_df = filtered_df[filtered_df['priority_level'].isin(['Premium', 'High'])].sort_values('priority_score', ascending=False)
    
    if len(high_value_df) > 0:
        # Format the display
        display_df = high_value_df[['seller_company', 'primary_phone', 'primary_location', 'total_listings', 'priority_level', 'priority_score']].copy()
        display_df.columns = ['Company', 'Phone', 'Location', 'Listings', 'Priority', 'Score']
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download High-Value Contacts CSV",
            data=csv,
            file_name=f"high_value_contacts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No high-value contacts match your current filters.")
    
    # Market insights
    st.subheader("💡 Market Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Top Performing States**")
        top_states = filtered_df.groupby('state').agg({
            'total_listings': 'sum',
            'contact_id': 'count'
        }).sort_values('total_listings', ascending=False).head(5)
        
        for state, row in top_states.iterrows():
            avg_listings = row['total_listings'] / row['contact_id']
            st.write(f"• **{state}**: {row['contact_id']} contacts, {avg_listings:.1f} avg listings")
    
    with col2:
        st.write("**Equipment Dealer Networks**")
        dealer_keywords = ['wheeler', 'holt cat', 'empire', 'ring power', 'altorfer']
        
        for keyword in dealer_keywords:
            matching = filtered_df[filtered_df['seller_company'].str.contains(keyword, case=False, na=False)]
            if len(matching) > 0:
                total_listings = matching['total_listings'].sum()
                st.write(f"• **{keyword.title()}**: {len(matching)} locations, {total_listings} listings")
    
    with col3:
        st.write("**Data Quality Metrics**")
        total_contacts = len(filtered_df)
        with_phone = len(filtered_df[filtered_df['primary_phone'] != ''])
        with_email = len(filtered_df[filtered_df['email'] != ''])
        complete_location = len(filtered_df[filtered_df['primary_location'].str.contains(',', na=False)])
        
        st.write(f"• **Phone Coverage**: {with_phone/total_contacts*100:.1f}%")
        st.write(f"• **Email Coverage**: {with_email/total_contacts*100:.1f}%")
        st.write(f"• **Complete Locations**: {complete_location/total_contacts*100:.1f}%")

if __name__ == "__main__":
    main()

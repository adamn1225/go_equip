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

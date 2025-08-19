#!/usr/bin/env python3
"""
Interactive Contact Database Dashboard
Visual analytics and insights for equipment seller database
Enhanced with Heavy Haulers Equipment Logistics sales intelligence
"""

import json
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter
import re
from datetime import datetime
import openai

# Configure Streamlit page
st.set_page_config(
    page_title="Equipment Seller Database Dashboard",
    page_icon="🏗️",
    layout="wide"
)

# Authentication function
def check_password():
    """Simple password authentication for executive access"""
    def password_entered():
        # Check if password key exists before accessing it
        if "password" in st.session_state and st.session_state["password"] == "ContactAnalytics2025!":
            st.session_state["password_correct"] = True
            # Only delete if it exists
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("# Contact Analytics Dashboard")
        st.markdown("**Executive Access Required**")
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.info("Contact your system administrator for access credentials.")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("# Contact Analytics Dashboard") 
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
    
    # Dashboard Mode Selector
    st.markdown("# Equipment Seller Database Dashboard")
    st.markdown("**Authorized Access - Analytics Portal**")
    
    # Creative Mode Selection UI
    st.markdown("### Choose Your Analytics Experience")
    
    # Add custom CSS for hover effects
    st.markdown("""
    <style>
    .dashboard-card {
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .dashboard-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    
    .general-card {
        border: 2px solid #1f77b4;
        background: #051117;
    }
    
    .heavy-card {
        border: 2px solid #ff6b35;
        background: linear-gradient(135deg, #fff3e0 0%, #ffcc02 100%);
    }
    
    .card-title {
        margin: 0 0 15px 0;
        font-weight: bold;
    }
    
    .card-description {
        margin: 10px 0 15px 0;
        line-height: 1.4;
    }
    
    .card-features {
        font-size: 14px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create two attractive columns for mode selection
    col1, col2 = st.columns(2, gap="large")
    
    # Enhanced CSS for beautiful blue buttons (blue-500 = #3b82f6)
    st.markdown("""
    <style>
    /* Override Streamlit's default button styles */
    .stButton > button {
        background: #071014 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1.1em !important;
        padding: 0.75em 1.5em !important;
        margin-top: 15px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3) !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #184e66 0%, #071014 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3) !important;
    }
    
    /* Style for selected state */
    .stButton > button[data-baseweb="button"][kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.5) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with col1:
        # General Analytics Card
        with st.container():
            st.markdown("""
            <div class="dashboard-card general-card">
                <h2 style="color: #dce0e6;" class="card-title">General Insights/Analytics</h2>
                <p style="color: #f0f2f5;" class="card-description">
                    Comprehensive database insights, contact analysis, 
                    and business intelligence across all equipment categories
                </p>
                <div style="color: #f0f2f5;" class="card-features">
                    - Contact Database Overview<br>
                    - Geographic Distribution<br>
                    - Category Analysis<br>
                    - Source Performance
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            general_selected = st.button(
                "Launch General Analytics", 
                key="general_btn",
                use_container_width=True,
                type="primary" if st.session_state.get('dashboard_mode') == 'general' else "secondary"
            )
    
    with col2:
        # Heavy Haulers Card  
        with st.container():
            st.markdown("""
            <div class="dashboard-card general-card">
                <h2 style="color: #dce0e6;" class="card-title">AI Insights/Analytics</h2>
                <p style="color: #f0f2f5;" class="card-description">
                    Advanced sales intelligence focused on high-value 
                    equipment dealers with AI-powered insights
                </p>
                <div style="color: #f0f2f5;" class="card-features">
                    - Business Potential Scoring<br>
                    - AI-Powered Company Analysis<br>
                    - Priority Lead Identification<br>
                    - Geographic Heat Mapping
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            heavy_selected = st.button(
                "Launch Heavy Haulers Intel", 
                key="heavy_btn",
                use_container_width=True,
                type="primary" if st.session_state.get('dashboard_mode') == 'heavy' else "secondary"
            )
    
    # Handle mode selection
    if general_selected:
        st.session_state['dashboard_mode'] = 'general'
    elif heavy_selected:
        st.session_state['dashboard_mode'] = 'heavy'
    
    # Set default if no selection
    if 'dashboard_mode' not in st.session_state:
        st.session_state['dashboard_mode'] = 'general'
    
    dashboard_mode = st.session_state['dashboard_mode']
    
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
    
    # Route to appropriate dashboard
    if dashboard_mode == "heavy":
        heavy_haulers_dashboard(analyzer)
    else:
        general_analytics_dashboard(analyzer)

def general_analytics_dashboard(analyzer):
    """Original general analytics dashboard with dynamic category detection"""
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Extract unique categories from the data with statistics
    all_categories = {}
    category_stats = {}
    
    for _, contact in analyzer.df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip().lower()
            if cat and cat != '':
                # Clean category name for display
                clean_cat = cat.replace('_', ' ').title()
                if clean_cat not in all_categories:
                    all_categories[clean_cat] = cat
                    category_stats[clean_cat] = {
                        'count': 0,
                        'total_listings': 0,
                        'states': set()
                    }
                
                category_stats[clean_cat]['count'] += 1
                category_stats[clean_cat]['total_listings'] += contact.get('total_listings', 0)
                if contact.get('state') and contact.get('state') != 'Unknown':
                    category_stats[clean_cat]['states'].add(contact.get('state'))
    
    # Sort categories by contact count (most popular first)
    sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    # Machine Category filter with dynamic options
    category_options = ['All Categories'] + [cat[0] for cat in sorted_categories]
    selected_category = st.sidebar.selectbox("Equipment Category", category_options)
    
    # Show category insights in sidebar
    if selected_category != 'All Categories' and selected_category in category_stats:
        stats = category_stats[selected_category]
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 📊 {selected_category} Overview")
        st.sidebar.metric("Dealers", f"{stats['count']:,}")
        st.sidebar.metric("Total Listings", f"{stats['total_listings']:,}")
        st.sidebar.metric("States", f"{len(stats['states'])}")
        
        if stats['count'] > 0:
            avg_listings = stats['total_listings'] / stats['count']
            st.sidebar.metric("Avg Listings/Dealer", f"{avg_listings:.1f}")
    
    # Quick search for specific equipment
    st.sidebar.markdown("---")
    search_term = st.sidebar.text_input("Search Equipment/Company", placeholder="e.g., CAT, John Deere, Excavator")
    
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
    
    # Use native Streamlit components for better compatibility
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Priority Distribution")
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
        st.subheader("Equipment Categories")
        # Extract equipment categories from sources for chart
        category_counts = {}
        for _, contact in filtered_df.iterrows():
            categories = contact.get('categories', 'construction').split(',')
            for cat in categories:
                cat = cat.strip()
                if cat:
                    category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if category_counts:
            # Create category chart - show ALL categories
            cat_df = pd.DataFrame(list(category_counts.items()), columns=['Category', 'Count'])
            cat_df = cat_df.sort_values('Count', ascending=True)  # Show ALL categories
            
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
                showlegend=False,
                height=max(400, len(cat_df) * 50)  # Adjust height based on number of categories
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
        st.subheader("Listing Volume Distribution")
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
        st.subheader("Top Companies by Listings")
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
    st.subheader("High-Value Contacts")
    
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

def heavy_haulers_dashboard(analyzer):
    """Heavy Haulers Equipment Logistics - Sales Intelligence Dashboard"""
    
    # Custom CSS for Heavy Haulers branding
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #2a5298;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .opportunity-high { border-left-color: #28a745; }
        .opportunity-medium { border-left-color: #ffc107; }
        .opportunity-low { border-left-color: #dc3545; }
        .stButton > button {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🚛 Heavy Haulers Equipment Logistics</h1>
        <p style="color: #e8f4fd; margin: 0; font-size: 1.2em;">Sales Intelligence Dashboard - Equipment Dealer Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Process dealer data for Heavy Haulers
    def process_dealer_data_heavy_haulers():
        records = []
        for _, row in analyzer.df.iterrows():
            # Skip contacts with "Unknown" names for better data quality
            if row['seller_company'] == 'Unknown' or str(row['seller_company']).strip() == '':
                continue
                
            # Extract equipment categories from the existing categories field
            equipment_types = []
            if pd.notna(row['categories']):
                categories = str(row['categories']).lower().split(',')
                for category in categories:
                    category = category.strip()
                    if 'excavator' in category:
                        equipment_types.append('Excavator')
                    elif 'crane' in category:
                        equipment_types.append('Crane')
                    elif 'dozer' in category or 'bulldozer' in category:
                        equipment_types.append('Dozer')
                    elif category:
                        equipment_types.append(category.title())
            
            # Remove duplicates and create string
            equipment_types = list(set(equipment_types))
            equipment_str = ', '.join(equipment_types) if equipment_types else 'General'
            
            records.append({
                'contact_id': row['contact_id'],
                'name': row['seller_company'],
                'phone': row['primary_phone'],
                'location': row['primary_location'],
                'state': row['state'],
                'website': row.get('website', ''),
                'equipment_types': equipment_str,
                'num_equipment_types': len(equipment_types),
                'num_sources': row.get('num_sources', 1),
                'total_listings': row['total_listings']
            })
        
        return pd.DataFrame(records)
    
    df = process_dealer_data_heavy_haulers()
    
    if df.empty:
        st.error("No Heavy Haulers data available.")
        return
        
    # Sidebar filters
    st.sidebar.header("🎯 Target Market Filters")
    
    # Equipment type filter
    equipment_options = ['All'] + sorted(df['equipment_types'].str.split(', ').explode().unique().tolist())
    selected_equipment = st.sidebar.selectbox("Equipment Type", equipment_options, key="hh_equipment")
    
    # State filter
    state_options = ['All'] + sorted([s for s in df['state'].unique() if s])
    selected_state = st.sidebar.selectbox("State", state_options, key="hh_state")
    
    # Filter data
    filtered_df = df.copy()
    if selected_equipment != 'All':
        filtered_df = filtered_df[filtered_df['equipment_types'].str.contains(selected_equipment, na=False)]
    if selected_state != 'All':
        filtered_df = filtered_df[filtered_df['state'] == selected_state]
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Market Overview", 
        "🎯 Sales Targets", 
        "📍 Geographic Analysis", 
        "🤖 AI Insights", 
        "📋 Contact Management"
    ])
    
    with tab1:
        st.header("Market Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #2a5298; margin: 0;">Total Dealers</h3>
                <h2 style="color: #1e3c72; margin: 0;">{:,}</h2>
                <p style="color: #6c757d; margin: 0;">Potential Customers</p>
            </div>
            """.format(len(filtered_df)), unsafe_allow_html=True)
        
        with col2:
            avg_equipment = filtered_df['num_equipment_types'].mean()
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #2a5298; margin: 0;">Avg Equipment Types</h3>
                <h2 style="color: #1e3c72; margin: 0;">{:.1f}</h2>
                <p style="color: #6c757d; margin: 0;">Per Dealer</p>
            </div>
            """.format(avg_equipment), unsafe_allow_html=True)
        
        with col3:
            states_count = len(filtered_df['state'].unique())
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #2a5298; margin: 0;">Geographic Reach</h3>
                <h2 style="color: #1e3c72; margin: 0;">{}</h2>
                <p style="color: #6c757d; margin: 0;">States Covered</p>
            </div>
            """.format(states_count), unsafe_allow_html=True)
        
        with col4:
            has_phone = (filtered_df['phone'] != '').sum()
            phone_rate = (has_phone / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #2a5298; margin: 0;">Contact Rate</h3>
                <h2 style="color: #1e3c72; margin: 0;">{:.0f}%</h2>
                <p style="color: #6c757d; margin: 0;">Have Phone Numbers</p>
            </div>
            """.format(phone_rate), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Equipment Type Distribution")
            equipment_counts = Counter()
            for equipment_list in filtered_df['equipment_types']:
                if pd.notna(equipment_list):
                    for equipment in str(equipment_list).split(', '):
                        equipment_counts[equipment.strip()] += 1
            
            if equipment_counts:
                equipment_df = pd.DataFrame(list(equipment_counts.items()), 
                                         columns=['Equipment', 'Count'])
                fig = px.pie(equipment_df, values='Count', names='Equipment', 
                            title="Market Share by Equipment Type")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True, key="hh_equipment_pie_chart")
        
        with col2:
            st.subheader("Top States by Dealer Count")
            state_counts = filtered_df['state'].value_counts().head(10)
            if not state_counts.empty:
                fig = px.bar(x=state_counts.values, y=state_counts.index, 
                            orientation='h', title="Geographic Distribution")
                fig.update_layout(yaxis_title="State", xaxis_title="Dealer Count")
                st.plotly_chart(fig, use_container_width=True, key="hh_states_bar_chart")
    
    with tab2:
        st.header("🎯 Priority Sales Targets")
        st.markdown("**Dealers ranked by business potential for Heavy Haulers**")
        
        # Priority scoring explanation
        with st.expander("📊 Priority Scoring System", expanded=False):
            st.markdown("""
            **How we calculate Business Potential Score:**
            
            • **Equipment Types** (+20 per type): More variety = more transportation needs
            • **Multiple Sources** (+10 per source, max 50): Established dealers with multiple listings  
            • **Contact Info** (+25): Phone number available for direct outreach
            • **Professional Presence** (+15): Has website - more established business
            • **Equipment Bonuses**:
              - 🏗️ Cranes: +20 (high-value specialty transport)
              - 🚜 Excavators: +15 (consistent volume opportunities)  
              - 🚧 Dozers: +10 (regular transport needs)
            
            **Priority Ranges:**
            • 🔥 **HIGH (80-200+ points)**: Premium targets - call first!
            • ⚡ **MEDIUM (50-80 points)**: Good prospects - solid opportunities
            • 📋 **LOW (0-50 points)**: Future follow-up - nurture relationships
            """)
        
        # Calculate business potential scores
        def calculate_business_potential(row):
            score = 0
            
            # More equipment types = higher potential
            score += row['num_equipment_types'] * 20
            
            # Multiple sources = more established business
            score += min(row['num_sources'], 5) * 10
            
            # Has phone number = easier to reach
            if row['phone']:
                score += 25
            
            # Has website = more professional operation
            if row['website']:
                score += 15
            
            # High-demand equipment bonuses
            equipment_list = str(row['equipment_types']).lower()
            if 'excavator' in equipment_list:
                score += 15
            if 'crane' in equipment_list:
                score += 20  # Cranes are high-value for logistics
            if 'dozer' in equipment_list:
                score += 10
            
            return score
        
        filtered_df['business_potential'] = filtered_df.apply(calculate_business_potential, axis=1)
        filtered_df['priority_level'] = pd.cut(filtered_df['business_potential'], 
                                             bins=[0, 50, 80, 200], 
                                             labels=['Low', 'Medium', 'High'])
        
        # Priority level summary
        priority_counts = filtered_df['priority_level'].value_counts()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="metric-card opportunity-high">
                <h3 style="color: #1e5631; font-weight: bold;">🔥 High Priority</h3>
                <h2 style="color: #1e3c72; font-size: 2.5rem;">{}</h2>
                <p style="color: #495057; font-weight: 500;">Premium Targets</p>
            </div>
            """.format(priority_counts.get('High', 0)), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card opportunity-medium">
                <h3 style="color: #b8860b; font-weight: bold;">⚡ Medium Priority</h3>
                <h2 style="color: #1e3c72; font-size: 2.5rem;">{}</h2>
                <p style="color: #495057; font-weight: 500;">Good Prospects</p>
            </div>
            """.format(priority_counts.get('Medium', 0)), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card opportunity-low">
                <h3 style="color: #c53030; font-weight: bold;">📋 Low Priority</h3>
                <h2 style="color: #1e3c72; font-size: 2.5rem;">{}</h2>
                <p style="color: #495057; font-weight: 500;">Future Follow-up</p>
            </div>
            """.format(priority_counts.get('Low', 0)), unsafe_allow_html=True)
        
        # Top prospects table
        st.subheader("🎯 Top Sales Prospects")
        top_prospects = filtered_df.nlargest(20, 'business_potential')[
            ['name', 'location', 'phone', 'equipment_types', 'business_potential', 'priority_level']
        ].copy()
        
        # Add action buttons and format for display
        top_prospects['Score'] = top_prospects['business_potential'].round(0).astype(int)
        
        # Display with color coding for priority levels
        for idx, row in top_prospects.iterrows():
            priority = row['priority_level']
            score = row['Score']
            
            # Color coding based on priority with better contrast
            if priority == 'High':
                priority_color = "🔥 **HIGH PRIORITY**"
                card_color = "#1e5631"  # Dark green
                text_color = "#ffffff"   # White text
            elif priority == 'Medium':
                priority_color = "⚡ **MEDIUM PRIORITY**"
                card_color = "#b8860b"   # Dark gold
                text_color = "#ffffff"   # White text
            else:
                priority_color = "📋 **LOW PRIORITY**"
                card_color = "#2c3e50"   # Dark blue-gray
                text_color = "#ffffff"   # White text
            
            with st.container():
                st.markdown(f"""
                <div style="background-color: {card_color}; color: {text_color}; padding: 15px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #ffffff;">
                    <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 8px;">
                        {row['name']} | {priority_color} | Score: {score}
                    </div>
                    <div style="margin: 4px 0;">📍 <strong>Location:</strong> {row['location']}</div>
                    <div style="margin: 4px 0;">📞 <strong>Phone:</strong> {row['phone']}</div>
                    <div style="margin: 4px 0;">🚛 <strong>Equipment:</strong> {row['equipment_types']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Export functionality
        st.subheader("📥 Export Sales Lists")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export High Priority List", key="hh_export_high"):
                high_priority = filtered_df[filtered_df['priority_level'] == 'High']
                csv = high_priority[['name', 'phone', 'location', 'equipment_types', 'website']].to_csv(index=False)
                st.download_button("Download CSV", csv, "heavy_haulers_high_priority.csv", "text/csv", key="hh_download_high")
        
        with col2:
            if st.button("Export All Prospects", key="hh_export_all"):
                csv = filtered_df[['name', 'phone', 'location', 'equipment_types', 'business_potential']].to_csv(index=False)
                st.download_button("Download CSV", csv, "heavy_haulers_all_prospects.csv", "text/csv", key="hh_download_all")
    
    with tab3:
        st.header("📍 Geographic Market Analysis")
        st.markdown("**Identify underserved markets and expansion opportunities**")
        
        # State analysis with basic geographic distribution
        state_analysis = filtered_df.groupby('state').agg({
            'contact_id': 'count',
            'num_equipment_types': 'mean',
            'business_potential': 'mean'
        }).round(2)
        state_analysis.columns = ['Dealer_Count', 'Avg_Equipment_Types', 'Avg_Business_Potential']
        state_analysis = state_analysis.sort_values('Dealer_Count', ascending=False).reset_index()
        
        # Geographic distribution bar chart
        st.subheader("📊 Dealer Distribution by State")
        if not state_analysis.empty:
            top_15_states = state_analysis.head(15)
            fig = px.bar(
                top_15_states,
                x='Dealer_Count',
                y='state',
                orientation='h',
                title="Top 15 States by Dealer Count",
                labels={'Dealer_Count': 'Number of Equipment Dealers', 'state': 'State'},
                color='Avg_Business_Potential',
                color_continuous_scale='RdYlBu_r'
            )
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=500
            )
            st.plotly_chart(fig, use_container_width=True, key="hh_geographic_chart")
        
        # State abbreviation mapping for choropleth
        state_abbr_map = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
            'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
            'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
            'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
            'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
            'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
            'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
            'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
        }
        
        # US Business Potential Heatmap
        st.subheader("🗺️ US Business Potential Heatmap")
        if not state_analysis.empty:
            # Add state abbreviations for choropleth
            state_analysis_valid = state_analysis[state_analysis['state'].isin(state_abbr_map.keys())].copy()
            if not state_analysis_valid.empty:
                state_analysis_valid['state_code'] = state_analysis_valid['state'].map(state_abbr_map)
                
                # Create choropleth map
                fig_map = go.Figure(data=go.Choropleth(
                    locations=state_analysis_valid['state_code'],
                    z=state_analysis_valid['Avg_Business_Potential'],
                    locationmode='USA-states',
                    colorscale='RdYlBu_r',
                    colorbar_title="Average Business Potential Score",
                    text=state_analysis_valid['state'],
                    hovertemplate='<b>%{text}</b><br>Dealers: %{customdata[0]}<br>Avg Business Potential: %{z:.1f}<br>Avg Equipment Types: %{customdata[1]:.1f}<extra></extra>',
                    customdata=state_analysis_valid[['Dealer_Count', 'Avg_Equipment_Types']].values
                ))
                
                fig_map.update_layout(
                    title_text="Heavy Haulers Business Potential by State",
                    geo_scope='usa',
                    height=500,
                    title_x=0.5
                )
                
                st.plotly_chart(fig_map, use_container_width=True, key="hh_choropleth_map")
    
    with tab4:
        st.header("🤖 AI-Powered Business Insights")
        st.markdown("**Get intelligent analysis of your equipment dealer market**")
        
        # OpenAI configuration
        shared_api_key = os.getenv("OPENAI_API_KEY", "")
        
        if shared_api_key and shared_api_key != "your_openai_api_key_here":
            # Shared API key is configured
            st.success("✅ Team OpenAI API key configured - AI features ready!")
            openai_api_key = shared_api_key
        else:
            # No shared key, allow individual key input
            st.info("💡 Enter your OpenAI API key to enable AI-powered insights")
            openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                         value="", key="hh_openai_key",
                                         help="Get your API key from https://platform.openai.com/api-keys")
        
        # Calculate business potential scores for filtering (always available)
        def calculate_business_potential(row):
            score = 0
            
            # More equipment types = higher potential
            score += row['num_equipment_types'] * 20
            
            # Multiple sources = more established business
            score += min(row['num_sources'], 5) * 10
            
            # Has phone number = easier to reach
            if row['phone']:
                score += 25
            
            # Has website = more professional operation
            if row['website']:
                score += 15
            
            # High-demand equipment bonuses
            equipment_list = str(row['equipment_types']).lower()
            if 'excavator' in equipment_list:
                score += 15
            if 'crane' in equipment_list:
                score += 20  # Cranes are high-value for logistics
            if 'dozer' in equipment_list:
                score += 10
            
            return score
        
        # Apply business potential scoring (always available)
        filtered_df['business_potential'] = filtered_df.apply(calculate_business_potential, axis=1)
        filtered_df['priority_level'] = pd.cut(filtered_df['business_potential'], 
                                             bins=[0, 50, 80, 200], 
                                             labels=['Low', 'Medium', 'High'])
        
        # Company Search Section - Always visible
        st.subheader("🔍 Individual Company Analysis")
        st.markdown("**Select any company for detailed analysis and AI-powered insights**")
        
        # Enhanced company search - include ALL dealers
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Search by company name
            company_search = st.text_input("🔍 Search for company", 
                                          placeholder="Type company name to search...",
                                          help="Start typing to filter companies",
                                          key="hh_company_search")
        
        with col2:
            # Filter by priority level
            priority_filter = st.selectbox("Priority Level", 
                                          options=['All', 'High', 'Medium', 'Low'],
                                          help="Filter companies by priority",
                                          key="hh_priority_filter")
        
        # Filter companies based on search and priority
        searchable_df = filtered_df.copy()
        
        # Apply priority filter
        if priority_filter != 'All':
            searchable_df = searchable_df[searchable_df['priority_level'] == priority_filter]
        
        # Apply company name search
        if company_search:
            searchable_df = searchable_df[searchable_df['name'].str.contains(company_search, case=False, na=False)]
        
        # Company selection dropdown
        if not searchable_df.empty:
            # Sort by business potential score (highest first)
            searchable_df = searchable_df.sort_values('business_potential', ascending=False)
            
            # Create display options with score and location
            company_options = []
            for _, row in searchable_df.iterrows():
                display_name = f"{row['name']} (Score: {row['business_potential']:.0f}, {row['location']})"
                company_options.append(display_name)
            
            selected_company_display = st.selectbox(
                f"Select company for analysis ({len(company_options)} matches)",
                options=company_options,
                help="Companies sorted by business potential score",
                key="hh_company_select"
            )
            
            # Show company details (always available)
            if selected_company_display:
                # Extract actual company name from display
                company_name = selected_company_display.split(" (Score:")[0]
                selected_row = searchable_df[searchable_df['name'] == company_name].iloc[0]
                
                # Display company information
                st.subheader(f"📊 Company Profile: {selected_row['name']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Business Potential Score", f"{selected_row['business_potential']:.0f}")
                    st.metric("Priority Level", selected_row['priority_level'])
                
                with col2:
                    st.metric("Equipment Types", selected_row['num_equipment_types'])
                    st.metric("Data Sources", selected_row['num_sources'])
                
                with col3:
                    st.metric("Has Phone", "✅" if selected_row['phone'] else "❌")
                    st.metric("Has Website", "✅" if selected_row['website'] else "❌")
                
                # Company details
                st.write(f"**Location:** {selected_row['location']}")
                if selected_row['phone']:
                    st.write(f"**Phone:** {selected_row['phone']}")
                if selected_row['website']:
                    st.write(f"**Website:** {selected_row['website']}")
                st.write(f"**Equipment Types:** {selected_row['equipment_types']}")
                
                # AI Analysis Section (requires API key)
                st.subheader("🤖 AI-Powered Analysis")
                
                if openai_api_key:
                    if st.button("🤖 Generate AI Analysis", key="hh_company_ai_analysis"):
                        # Extract actual company name from display
                        selected_company = selected_company_display.split(" (Score:")[0]
                        dealer_info = searchable_df[searchable_df['name'] == selected_company].iloc[0]
                        
                        dealer_summary = f"""
                        Company: {dealer_info['name']}
                        Location: {dealer_info['location']}
                        State: {dealer_info['state']}
                        Equipment Types: {dealer_info['equipment_types']}
                        Business Potential Score: {dealer_info['business_potential']:.0f} out of 200
                        Priority Level: {dealer_info['priority_level']}
                        Phone Available: {'Yes' if dealer_info['phone'] else 'No'}
                        Website Available: {'Yes' if dealer_info['website'] else 'No'}
                        Number of Equipment Categories: {dealer_info['num_equipment_types']}
                        Data Sources: {dealer_info['num_sources']}
                        Total Listings: {dealer_info['total_listings']}
                        """
                        
                        with st.spinner(f"Analyzing {selected_company}..."):
                            try:
                                import openai
                                client = openai.OpenAI(api_key=openai_api_key)
                                response = client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "You are a sales strategist for Heavy Haulers Equipment Logistics, specializing in cold outreach to equipment dealers. Create actionable sales strategies with specific talking points and approach recommendations."},
                                        {"role": "user", "content": f"Create a comprehensive cold outreach strategy for this equipment dealer. Include: 1) Why they need Heavy Haulers services, 2) Specific talking points based on their equipment types, 3) Best approach method, 4) Potential objections and responses, 5) Follow-up strategy. Company details: {dealer_summary}"}
                                    ],
                                    max_tokens=600,
                                    temperature=0.7
                                )
                                
                                st.success(f"✅ AI Analysis Complete for {selected_company}")
                                
                                # Display results in an attractive format
                                st.markdown("---")
                                st.markdown(f"### 🎯 Sales Strategy: **{selected_company}**")
                                
                                # Company quick facts
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Priority", dealer_info['priority_level'])
                                with col2:
                                    st.metric("Score", f"{dealer_info['business_potential']:.0f}/200")
                                with col3:
                                    st.metric("Equipment Types", dealer_info['num_equipment_types'])
                                with col4:
                                    st.metric("Location", dealer_info['state'])
                                
                                st.markdown("### 🤖 AI Recommendations")
                                st.write(response.choices[0].message.content)
                                
                                # Contact info section
                                st.markdown("### 📞 Contact Information")
                                contact_col1, contact_col2 = st.columns(2)
                                with contact_col1:
                                    if dealer_info['phone']:
                                        st.markdown(f"**Phone:** {dealer_info['phone']}")
                                    else:
                                        st.markdown("**Phone:** Not available")
                                
                                with contact_col2:
                                    if dealer_info['website']:
                                        st.markdown(f"**Website:** {dealer_info['website']}")
                                    else:
                                        st.markdown("**Website:** Not available")
                                
                                st.markdown(f"**Full Address:** {dealer_info['location']}")
                                
                            except Exception as e:
                                st.error(f"❌ API Error: {str(e)}")
                                st.info("💡 Tip: Make sure your OpenAI API key is valid and has sufficient credits.")
                else:
                    st.warning("🔑 OpenAI API key required for AI-powered analysis")
                    st.info("Enter your OpenAI API key above to unlock AI-powered outreach strategies and insights.")
                    st.markdown("**Without API key, you can still:**")
                    st.markdown("- Browse and search all companies")
                    st.markdown("- View business potential scores")
                    st.markdown("- Access contact information")
                    st.markdown("- Use pre-built insights below")
            
            else:
                st.info(f"No companies found matching your search criteria. Try adjusting your filters.")
            
            # Market Analysis Section
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎯 Generate Cold Outreach Strategy", key="hh_ai_strategy"):
                    # Generate AI insights for Heavy Haulers
                    st.info("AI analysis would be generated here using the OpenAI API...")
            
            with col2:
                if st.button("📊 Market Analysis Report", key="hh_ai_report"):
                    st.info("Market analysis report would be generated here...")
        
        # Pre-built insights (no API usage)
        st.subheader("📊 Quick Insights (No API Usage)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Cold Outreach Recommendations")
            
            crane_dealers = len(filtered_df[filtered_df['equipment_types'].str.contains('Crane', na=False)])
            excavator_dealers = len(filtered_df[filtered_df['equipment_types'].str.contains('Excavator', na=False)])
            
            recommendations = f"""
            **Priority Equipment Types for Heavy Haulers:**
            
            🏗️ **Crane Dealers ({crane_dealers})**: Premium logistics needs
            - High-value equipment requiring specialized transport
            - Often need permits and route planning
            - Excellent upsell opportunities for white-glove service
            
            🚜 **Excavator Dealers ({excavator_dealers})**: Volume opportunities  
            - Consistent transportation needs
            - Multiple units per shipment common
            - Good for building recurring relationships
            
            **Outreach Tips:**
            - Lead with cost savings and reliability
            - Mention permit handling and route optimization
            - Offer free shipping quotes as conversation starter
            """
            
            st.markdown(recommendations)
        
        with col2:
            st.markdown("### 📍 Geographic Strategy")
            
            top_3_states = state_analysis.head(3)
            geographic_strategy = f"""
            **Top Target States:**
            
            """
            
            for idx, row in top_3_states.iterrows():
                geographic_strategy += f"""
            **{row['state']}**: {row['Dealer_Count']} dealers
            - Avg {row['Avg_Equipment_Types']:.1f} equipment types per dealer
            - Business potential score: {row['Avg_Business_Potential']:.1f}
            
            """
            
            geographic_strategy += """
            **Expansion Opportunities:**
            - States with <10 dealers but high equipment diversity
            - Markets near major shipping routes
            - Areas with growing construction activity
            """
            
            st.markdown(geographic_strategy)
    
    with tab5:
        st.header("📋 Contact Management")
        st.markdown("**Manage and export your sales prospect database**")
        
        # Search and filter
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 Search dealers", placeholder="Company name, location, or equipment type", key="hh_search")
        with col2:
            show_only_priority = st.checkbox("Show only high priority prospects", key="hh_priority_checkbox")
        
        # Apply filters
        display_df = filtered_df.copy()
        if search_term:
            mask = (
                display_df['name'].str.contains(search_term, case=False, na=False) |
                display_df['location'].str.contains(search_term, case=False, na=False) |
                display_df['equipment_types'].str.contains(search_term, case=False, na=False)
            )
            display_df = display_df[mask]
        
        if show_only_priority:
            display_df = display_df[display_df['priority_level'] == 'High']
        
        # Contact table
        st.subheader(f"📞 Contact Database ({len(display_df)} dealers)")
        
        contact_display = display_df[[
            'name', 'phone', 'location', 'equipment_types', 
            'business_potential', 'priority_level', 'website'
        ]].copy()
        
        # Display contacts
        st.dataframe(
            contact_display,
            use_container_width=True,
            height=400
        )
        
        # Bulk actions
        st.subheader("📤 Export Options")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 Export Current View", key="hh_export_current"):
                csv = display_df[['name', 'phone', 'location', 'equipment_types', 'business_potential']].to_csv(index=False)
                st.download_button("Download", csv, f"heavy_haulers_filtered_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="hh_download_current")
        
        with col2:
            if st.button("📞 Phone List Only", key="hh_phone_only"):
                phone_df = display_df[display_df['phone'] != ''][['name', 'phone', 'location']]
                csv = phone_df.to_csv(index=False)
                st.download_button("Download", csv, f"heavy_haulers_phones_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="hh_download_phones")

if __name__ == "__main__":
    main()

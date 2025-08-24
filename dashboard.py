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
import subprocess
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter
import re
from datetime import datetime
import openai

# Import CRM features
try:
    from crm_features import (
        CRMManager, render_sales_rep_selector, render_territory_assignment,
        render_call_campaign_manager, render_email_integration,
        render_contact_timeline, add_crm_navigation
    )
    CRM_ENABLED = True
except ImportError:
    CRM_ENABLED = False
    print("CRM features not available - install sendgrid: pip install sendgrid")

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
    def __init__(self):
        """Initialize D1-powered dashboard analyzer"""
        self.database_name = "equipment-contacts"
        self.load_data()
    
    def get_cloudflare_credentials(self):
        """Get Cloudflare credentials from secrets or environment variables"""
        try:
            # Try Streamlit secrets first (local development or Streamlit Cloud secrets)
            if hasattr(st, 'secrets') and 'cloudflare' in st.secrets:
                return {
                    'api_token': st.secrets["cloudflare"]["api_token"],
                    'account_id': st.secrets["cloudflare"]["account_id"],
                    'database_id': st.secrets["cloudflare"]["database_id"]
                }
        except:
            pass
        
        # Fallback to environment variables (Streamlit Cloud env vars or system env)
        try:
            return {
                'api_token': os.environ['CLOUDFLARE_API_TOKEN'],
                'account_id': os.environ['CLOUDFLARE_ACCOUNT_ID'], 
                'database_id': os.environ['CLOUDFLARE_DATABASE_ID']
            }
        except KeyError as e:
            st.error(f"Missing Cloudflare credential: {e}")
            st.error("Please configure credentials in Streamlit secrets or environment variables")
            return None

    def execute_d1_query(self, sql_query):
        """Execute a query on D1 database using wrangler CLI or HTTP API fallback"""
        # Get credentials
        creds = self.get_cloudflare_credentials()
        if not creds:
            return []
        
        # Try wrangler CLI first (for development)
        try:
            cmd = ["wrangler", "d1", "execute", self.database_name, "--remote", "--command", sql_query, "--json"]
            
            env = os.environ.copy()
            env['CLOUDFLARE_API_TOKEN'] = creds['api_token']
            env['CLOUDFLARE_ACCOUNT_ID'] = creds['account_id']
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                    if isinstance(data, list) and len(data) > 0 and 'results' in data[0]:
                        return data[0]['results']
                    return []
                except json.JSONDecodeError as e:
                    st.error(f"JSON parsing error: {e}")
                    return []
            else:
                raise Exception("Wrangler failed, trying HTTP API")
                
        except Exception as e:
            # Fallback to HTTP API (for production)
            return self.execute_d1_query_http(sql_query)
    
    def execute_d1_query_http(self, sql_query):
        """Execute D1 query using HTTP API (production fallback)"""
        try:
            import requests
            
            # Get credentials 
            creds = self.get_cloudflare_credentials()
            if not creds:
                return []
            
            url = f"https://api.cloudflare.com/client/v4/accounts/{creds['account_id']}/d1/database/{creds['database_id']}/query"
            
            headers = {
                'Authorization': f'Bearer {creds["api_token"]}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'sql': sql_query
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('result'):
                    return data['result'][0]['results']
                else:
                    st.error(f"D1 API error: {data}")
                    return []
            else:
                st.error(f"HTTP error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            st.error(f"Error executing D1 HTTP query: {e}")
            return []
    
    def load_data(self):
        """Load and process contact data from D1 database - USING UNIQUE PHONES"""
        try:
            # Check if unique_phones table exists first
            check_table_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='unique_phones'
            """
            
            table_check = self.execute_d1_query(check_table_query)
            
            if not table_check:
                st.warning("⚠️ Unique phones table not found. Please run: `python d1_dialer_setup.py populate`")
                self.df = pd.DataFrame()
                return
            
            # Use UNIQUE PHONES instead of raw contacts to avoid duplicates
            # This reduces data from ~45K to ~11K unique contacts
            sql_query = """
            SELECT 
                up.phone_number as primary_phone,
                up.company_name as seller_company,
                up.location as primary_location,
                up.equipment_category as categories,
                up.total_listings,
                up.priority_score,
                up.first_seen_date,
                up.last_updated,
                up.call_status,
                up.call_attempts,
                up.sales_notes,
                -- Extract state from location
                CASE 
                    WHEN up.location LIKE '%, %' 
                    THEN TRIM(SUBSTR(up.location, INSTR(up.location, ',') + 1))
                    ELSE 'Unknown'
                END as state,
                -- Priority level from score
                CASE 
                    WHEN up.priority_score >= 90 THEN 'Premium'
                    WHEN up.priority_score >= 75 THEN 'High'
                    WHEN up.priority_score >= 60 THEN 'Medium'
                    WHEN up.priority_score >= 50 THEN 'Standard'
                    ELSE 'Low'
                END as priority_level
            FROM unique_phones up
            ORDER BY up.priority_score DESC, up.total_listings DESC
            """
            
            results = self.execute_d1_query(sql_query)
            
            if not results:
                st.error("❌ Failed to load unique phone data from D1 database")
                self.df = pd.DataFrame()
                return
            
            st.success(f"✅ Loaded {len(results):,} UNIQUE contacts (75% duplicate reduction!)")
            
            # Process results into DataFrame - using UNIQUE PHONE data structure
            records = []
            
            for row in results:
                # Map unique_phones fields to dashboard format
                record = {
                    'contact_id': f"UP_{row['primary_phone']}",  # Create synthetic ID
                    'seller_company': row['seller_company'] or 'Unknown',
                    'primary_phone': row['primary_phone'] or '',
                    'email': '',  # Not available in unique_phones table
                    'primary_location': row['primary_location'] or '',
                    'city': row['primary_location'].split(',')[0].strip() if row['primary_location'] and ',' in row['primary_location'] else row['primary_location'] or '',
                    'state': row['state'] or 'Unknown',
                    'total_listings': row['total_listings'] or 1,
                    'first_contact_date': row['first_seen_date'],
                    'categories': row['categories'] or 'general',
                    'priority_score': row['priority_score'] or 50,
                    'priority_level': row['priority_level'] or 'Standard',
                    # Simplified equipment data for now
                    'equipment_makes': [],
                    'equipment_models': [],
                    'equipment_years': [],
                    'listing_prices': [],
                    'has_equipment_data': bool(row['categories']),
                    'has_pricing_data': False,
                    'unique_makes': 0,
                    'unique_models': 0,
                    'price_range': 'No Pricing',
                    'num_sources': 1,
                    'call_status': row['call_status'] or 'Not Called',
                    'call_attempts': row['call_attempts'] or 0,
                    'sales_notes': row['sales_notes'] or ''
                }
                
                records.append(record)
            
            self.df = pd.DataFrame(records)
            
            # Create mock master_log for compatibility with existing features
            unique_categories = []
            if not self.df.empty:
                for categories_str in self.df['categories'].dropna():
                    if categories_str and categories_str != 'general':
                        unique_categories.extend(categories_str.split(','))
                        
            unique_categories = [cat.strip() for cat in unique_categories if cat.strip()]
            
            self.master_log = {
                'metadata': {
                    'categories': list(set(unique_categories)) if unique_categories else ['general']
                },
                'contacts': {record['contact_id']: record for record in records}
            }
            
            st.success(f"✅ Successfully processed {len(records):,} UNIQUE contacts from D1 database!")
            
        except Exception as e:
            st.error(f"❌ Error loading unique phone data from D1: {str(e)}")
            self.df = pd.DataFrame()
            self.master_log = {'metadata': {'categories': []}, 'contacts': {}}
    
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
            
        # Equipment data bonus (NEW!)
        if record.get('has_equipment_data', False):
            score += 15
            
        # Pricing data bonus (NEW!)
        if record.get('has_pricing_data', False):
            score += 10
        
        return score
    
    def _calculate_price_range(self, prices):
        """Calculate price range category from price list"""
        if not prices:
            return "No Pricing"
        
        # Extract numeric values from price strings
        numeric_prices = []
        for price in prices:
            try:
                # Remove $ and commas, convert to float
                clean_price = float(str(price).replace('$', '').replace(',', ''))
                numeric_prices.append(clean_price)
            except (ValueError, AttributeError):
                continue
        
        if not numeric_prices:
            return "No Pricing"
        
        max_price = max(numeric_prices)
        
        if max_price < 50000:
            return "Under $50K"
        elif max_price < 100000:
            return "$50K - $100K"
        elif max_price < 250000:
            return "$100K - $250K"
        elif max_price < 500000:
            return "$250K - $500K"
        else:
            return "$500K+"
    
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
    
    # CRM Mode Selection (if available)
    if CRM_ENABLED:
        rep_id, rep_name = render_sales_rep_selector()
        st.session_state['rep_name'] = rep_name
        crm_mode = add_crm_navigation()
        
        # Handle CRM modes
        if crm_mode == "Territory Management":
            analyzer = DashboardAnalyzer()
            render_territory_assignment(analyzer.df)
            return
        elif crm_mode == "Call Campaign":
            analyzer = DashboardAnalyzer()
            render_call_campaign_manager(analyzer.df)
            return
        elif crm_mode == "Email Marketing":
            render_email_integration()
            return
        elif crm_mode == "Analytics":
            # Fall through to regular dashboard with CRM metrics
            pass
    
    # Dashboard Mode Selector
    st.markdown("# Equipment Seller Database Dashboard")
    if CRM_ENABLED:
        st.markdown(f"**Authorized Access - Analytics Portal** | Logged in as: {st.session_state.get('rep_name', 'Admin')}")
    else:
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
    
    # Show all categories from database metadata
    categories_in_db = analyzer.master_log.get('metadata', {}).get('categories', [])
    if categories_in_db:
        with st.expander('📚 All Categories in Database', expanded=False):
            st.markdown(', '.join(sorted(categories_in_db)))
    
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
    
    # Equipment Data Filters (NEW!)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Equipment Filters")
    
    # Equipment data availability filter
    equipment_data_options = ['All Contacts', 'With Equipment Data', 'Without Equipment Data']
    equipment_data_filter = st.sidebar.selectbox("Equipment Data", equipment_data_options)
    
    # Price data filter
    pricing_options = ['All Contacts', 'With Pricing', 'Without Pricing']
    pricing_filter = st.sidebar.selectbox("Pricing Data", pricing_options)
    
    # Price range filter (only show if there are contacts with pricing)
    if analyzer.df['has_pricing_data'].any():
        price_ranges = sorted(analyzer.df[analyzer.df['has_pricing_data']]['price_range'].unique())
        if price_ranges:
            price_range_options = ['All Price Ranges'] + price_ranges
            selected_price_range = st.sidebar.selectbox("Price Range", price_range_options)
        else:
            selected_price_range = 'All Price Ranges'
    else:
        selected_price_range = 'All Price Ranges'
    
    # Equipment make filter (only show if there are contacts with makes)
    if analyzer.df['equipment_makes'].apply(len).sum() > 0:
        all_makes = []
        for makes_list in analyzer.df['equipment_makes']:
            all_makes.extend(makes_list)
        unique_makes = sorted(set(all_makes))
        if unique_makes:
            make_options = ['All Makes'] + unique_makes
            selected_make = st.sidebar.selectbox("Equipment Make", make_options)
        else:
            selected_make = 'All Makes'
    else:
        selected_make = 'All Makes'
    
    # Standard filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Standard Filters")
    
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
        # Also search in equipment makes and models
        equipment_mask = filtered_df.apply(lambda row: 
            any(search_term.lower() in str(make).lower() for make in row.get('equipment_makes', [])) or
            any(search_term.lower() in str(model).lower() for model in row.get('equipment_models', [])), axis=1)
        filtered_df = filtered_df[search_mask | equipment_mask]
    
    # Equipment data filters (NEW!)
    if equipment_data_filter == 'With Equipment Data':
        filtered_df = filtered_df[filtered_df['has_equipment_data'] == True]
    elif equipment_data_filter == 'Without Equipment Data':
        filtered_df = filtered_df[filtered_df['has_equipment_data'] == False]
    
    if pricing_filter == 'With Pricing':
        filtered_df = filtered_df[filtered_df['has_pricing_data'] == True]
    elif pricing_filter == 'Without Pricing':
        filtered_df = filtered_df[filtered_df['has_pricing_data'] == False]
    
    if selected_price_range != 'All Price Ranges':
        filtered_df = filtered_df[filtered_df['price_range'] == selected_price_range]
    
    if selected_make != 'All Makes':
        make_mask = filtered_df.apply(lambda row: selected_make in row.get('equipment_makes', []), axis=1)
        filtered_df = filtered_df[make_mask]
    
    # Standard filters
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
        st.metric("High-Value Contacts", f"{high_value_count:,}", 
                 help="Dealers with highest business potential - call these first!")
    
    with col3:
        equipment_data_count = len(filtered_df[filtered_df['has_equipment_data'] == True])
        st.metric("With Equipment Data", f"{equipment_data_count:,}",
                 help="Contacts with year, make, model information")
    
    with col4:
        pricing_data_count = len(filtered_df[filtered_df['has_pricing_data'] == True])
        st.metric("With Pricing Data", f"{pricing_data_count:,}",
                 help="Contacts with listing price information")
    
    # CSV Download Section - ENHANCED FOR VISIBILITY
    st.markdown("---")
    st.markdown("## 📥 **DOWNLOAD FULL CONTACT LIST**")
    st.markdown("### Export ALL contacts matching your current filters (not just high-value ones)")
    
    # Show current filter summary
    filter_summary = []
    if selected_category != 'All Categories':
        filter_summary.append(f"**Category:** {selected_category}")
    if selected_state != 'All':
        filter_summary.append(f"**State:** {selected_state}")
    if selected_priority != 'All':
        filter_summary.append(f"**Priority:** {selected_priority}")
    if selected_make != 'All Makes':
        filter_summary.append(f"**Equipment Make:** {selected_make}")
    if equipment_data_filter != 'All Contacts':
        filter_summary.append(f"**Equipment Data:** {equipment_data_filter}")
    if pricing_filter != 'All Contacts':
        filter_summary.append(f"**Pricing:** {pricing_filter}")
    
    if filter_summary:
        st.markdown("**Current Filters Applied:**")
        st.markdown(" | ".join(filter_summary))
    else:
        st.markdown("**No filters applied - showing all contacts**")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if len(filtered_df) > 0:
            st.success(f"✅ Ready to download **{len(filtered_df):,} contacts**")
            st.markdown("**Example:** If you selected 'Excavator' category, this downloads ALL excavator dealers, not just high-priority ones.")
        else:
            st.warning("⚠️ No contacts match your current filters")
        
        # Create comprehensive CSV data
        if len(filtered_df) > 0:
            # Prepare detailed export data
            export_records = []
            for _, row in filtered_df.iterrows():
                # Basic contact info
                record = {
                    'Company': row['seller_company'],
                    'Phone': row['primary_phone'],
                    'Location': row['primary_location'], 
                    'State': row['state'],
                    'Email': row.get('email', ''),
                    'Categories': row['categories'],
                    'Total_Listings': row['total_listings'],
                    'Priority_Level': row['priority_level'],
                    'Priority_Score': row['priority_score'],
                    'First_Contact_Date': row.get('first_contact_date', ''),
                    'Last_Updated': row.get('last_updated', ''),
                    'Number_of_Sources': row.get('num_sources', 1)
                }
                
                # Equipment data (flatten arrays for CSV)
                equipment_makes = ', '.join(row.get('equipment_makes', []))
                equipment_models = ', '.join(row.get('equipment_models', []))
                equipment_years = ', '.join(row.get('equipment_years', []))
                listing_prices = ', '.join(row.get('listing_prices', []))
                
                record.update({
                    'Equipment_Makes': equipment_makes,
                    'Equipment_Models': equipment_models, 
                    'Equipment_Years': equipment_years,
                    'Listing_Prices': listing_prices,
                    'Price_Range': row.get('price_range', 'No Pricing'),
                    'Has_Equipment_Data': '✅' if row.get('has_equipment_data', False) else '❌',
                    'Has_Pricing_Data': '✅' if row.get('has_pricing_data', False) else '❌'
                })
                
                export_records.append(record)
            
            export_df = pd.DataFrame(export_records)
            csv_data = export_df.to_csv(index=False)
            
            # Generate filename based on current filters
            filename_parts = []
            if selected_category != 'All Categories':
                filename_parts.append(f"category-{selected_category.replace(' ', '-').replace('/', '-')}")
            if selected_state != 'All':
                filename_parts.append(f"state-{selected_state.replace(' ', '-')}")
            if selected_priority != 'All':
                filename_parts.append(f"priority-{selected_priority.lower()}")
            if selected_make != 'All Makes':
                filename_parts.append(f"make-{selected_make.replace(' ', '-')}")
            
            if filename_parts:
                filename = f"contacts_{'_'.join(filename_parts)}_{datetime.now().strftime('%Y%m%d')}.csv"
            else:
                filename = f"all_contacts_{datetime.now().strftime('%Y%m%d')}.csv"
            
        else:
            csv_data = "No data to export"
            filename = "no_data.csv"
    
    with col2:
        if len(filtered_df) > 0:
            # Make the button much more prominent
            st.markdown("### 🔥 **DOWNLOAD NOW**")
            st.download_button(
                label=f"📊 GET ALL {len(filtered_df):,} CONTACTS",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help=f"Downloads ALL {len(filtered_df):,} contacts matching your filters",
                use_container_width=True,
                type="primary"
            )
            st.markdown(f"**File:** `{filename}`")
        else:
            st.error("❌ No contacts match your filters")
            st.markdown("Try adjusting your filter settings above.")
    
    with col3:
        if len(filtered_df) > 0:
            # Quick stats about the export
            st.metric("Export Size", f"{len(filtered_df):,} rows")
            st.metric("File Size", f"{len(csv_data)//1024:.0f} KB")
        else:
            st.metric("Export Size", "0 rows")
    
    # Quick Category Downloads Section
    st.markdown("---")
    st.markdown("### 🏗️ **Quick Category Downloads**")
    st.markdown("**One-click downloads for popular equipment categories:**")
    
    # Get category counts for quick download buttons
    category_counts = {}
    for _, contact in analyzer.df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip().lower()
            if cat and cat != '' and cat != 'construction':
                if cat not in category_counts:
                    category_counts[cat] = 0
                category_counts[cat] += 1
    
    # Sort by count and show top categories
    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    
    if sorted_cats:
        st.markdown("**Available Categories:**")
        cols = st.columns(3)
        for i, (cat, count) in enumerate(sorted_cats):
            with cols[i % 3]:
                # Create download data for this specific category
                cat_filter_df = analyzer.df[analyzer.df['categories'].str.contains(cat, case=False, na=False)]
                
                if len(cat_filter_df) > 0:
                    # Create CSV for this category
                    cat_export_records = []
                    for _, row in cat_filter_df.iterrows():
                        record = {
                            'Company': row['seller_company'],
                            'Phone': row['primary_phone'],
                            'Location': row['primary_location'],
                            'State': row['state'],
                            'Email': row.get('email', ''),
                            'Categories': row['categories'],
                            'Total_Listings': row['total_listings'],
                            'Priority_Level': row['priority_level'],
                            'Equipment_Makes': ', '.join(row.get('equipment_makes', [])),
                            'Equipment_Models': ', '.join(row.get('equipment_models', [])),
                            'Listing_Prices': ', '.join(row.get('listing_prices', []))
                        }
                        cat_export_records.append(record)
                    
                    cat_csv = pd.DataFrame(cat_export_records).to_csv(index=False)
                    cat_filename = f"{cat}_contacts_{datetime.now().strftime('%Y%m%d')}.csv"
                    
                    st.download_button(
                        label=f"📥 {cat.title()}\n({count:,} contacts)",
                        data=cat_csv,
                        file_name=cat_filename,
                        mime="text/csv",
                        help=f"Download all {count:,} {cat} dealers",
                        use_container_width=True,
                        key=f"quick_download_{cat}"
                    )
    else:
        st.info("No category data available for quick downloads")
    
    # Use native Streamlit components for better compatibility
    
    # Equipment Analytics Row (NEW!)
    st.markdown("---")
    st.subheader("🔧 Equipment Intelligence")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Top Equipment Makes**")
        if filtered_df['equipment_makes'].apply(len).sum() > 0:
            all_makes = []
            for makes_list in filtered_df['equipment_makes']:
                all_makes.extend(makes_list)
            make_counts = pd.Series(all_makes).value_counts().head(10)
            fig_makes = px.bar(
                x=make_counts.values,
                y=make_counts.index,
                orientation='h',
                labels={'x': 'Number of Contacts', 'y': 'Equipment Make'}
            )
            fig_makes.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig_makes, use_container_width=True)
        else:
            st.info("No equipment make data available in current selection.")
    
    with col2:
        st.markdown("**Price Range Distribution**")
        if filtered_df['has_pricing_data'].any():
            price_range_counts = filtered_df[filtered_df['has_pricing_data']]['price_range'].value_counts()
            fig_prices = px.pie(
                values=price_range_counts.values,
                names=price_range_counts.index,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_prices, use_container_width=True)
        else:
            st.info("No pricing data available in current selection.")
    
    with col3:
        st.markdown("**Equipment Data Coverage**")
        data_coverage = {
            'With Equipment Data': len(filtered_df[filtered_df['has_equipment_data'] == True]),
            'Without Equipment Data': len(filtered_df[filtered_df['has_equipment_data'] == False]),
            'With Pricing Data': len(filtered_df[filtered_df['has_pricing_data'] == True]),
            'Without Pricing Data': len(filtered_df[filtered_df['has_pricing_data'] == False])
        }
        
        # Create a simple bar chart for data coverage
        coverage_df = pd.DataFrame(list(data_coverage.items()), columns=['Category', 'Count'])
        fig_coverage = px.bar(
            coverage_df,
            x='Count',
            y='Category',
            orientation='h',
            color='Category',
            color_discrete_sequence=['#2E8B57', '#DC143C', '#1E90FF', '#FF6347']
        )
        fig_coverage.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_coverage, use_container_width=True)
    
    # Traditional Charts Row
    st.markdown("---")
    st.subheader("📊 Traditional Analytics")
    
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
    st.subheader("🎯 High-Value Contacts with Equipment Intelligence")
    
    high_value_df = filtered_df[filtered_df['priority_level'].isin(['Premium', 'High'])].sort_values('priority_score', ascending=False)
    
    if len(high_value_df) > 0:
        # Create enhanced display with equipment info
        display_records = []
        for _, row in high_value_df.iterrows():
            # Summarize equipment data
            makes_summary = ', '.join(row['equipment_makes'][:3]) if row['equipment_makes'] else 'N/A'
            if len(row['equipment_makes']) > 3:
                makes_summary += f" (+{len(row['equipment_makes'])-3} more)"
            
            years_summary = 'N/A'
            if row['equipment_years']:
                unique_years = sorted(set(row['equipment_years']))
                if len(unique_years) <= 3:
                    years_summary = ', '.join(unique_years)
                else:
                    years_summary = f"{unique_years[0]}-{unique_years[-1]} ({len(unique_years)} years)"
            
            price_summary = row['price_range'] if row['has_pricing_data'] else 'No Pricing'
            
            display_records.append({
                'Company': row['seller_company'],
                'Phone': row['primary_phone'],
                'Location': row['primary_location'],
                'Listings': row['total_listings'],
                'Priority': row['priority_level'],
                'Score': row['priority_score'],
                'Top Makes': makes_summary,
                'Years': years_summary,
                'Price Range': price_summary,
                'Equipment Data': '✅' if row['has_equipment_data'] else '❌',
                'Pricing Data': '✅' if row['has_pricing_data'] else '❌'
            })
        
        display_df = pd.DataFrame(display_records)
        
        # Show equipment data toggle
        show_equipment = st.checkbox("Show Equipment Details", value=True)
        
        if show_equipment:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            # Show basic view
            basic_df = display_df[['Company', 'Phone', 'Location', 'Listings', 'Priority', 'Score']]
            st.dataframe(
                basic_df,
                use_container_width=True,
                hide_index=True
            )
        
        # Download button with equipment data
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download High-Value Contacts with Equipment Data",
            data=csv,
            file_name=f"high_value_contacts_equipment_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        # Equipment insights for high-value contacts
        col1, col2 = st.columns(2)
        with col1:
            equipment_coverage = len([r for r in display_records if r['Equipment Data'] == '✅'])
            st.metric("Equipment Data Coverage", f"{equipment_coverage}/{len(display_records)}", 
                     f"{equipment_coverage/len(display_records)*100:.1f}%")
        with col2:
            pricing_coverage = len([r for r in display_records if r['Pricing Data'] == '✅'])
            st.metric("Pricing Data Coverage", f"{pricing_coverage}/{len(display_records)}", 
                     f"{pricing_coverage/len(display_records)*100:.1f}%")
        
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
        
        # Heavy Haulers CSV Download Section
        st.subheader("📥 Export Sales Prospects")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("**Download current filtered prospects for your sales team**")
            
            if len(filtered_df) > 0:
                # Create Heavy Haulers specific export
                hh_export_records = []
                for _, row in filtered_df.iterrows():
                    record = {
                        'Dealer_Name': row['name'],
                        'Contact_Phone': row['phone'],
                        'Location': row['location'],
                        'State': row['state'],
                        'Equipment_Specialization': row['equipment_types'],
                        'Number_Equipment_Types': row['num_equipment_types'],
                        'Total_Listings': row['total_listings'],
                        'Data_Sources': row['num_sources'],
                        'Business_Opportunity': 'High' if row['total_listings'] > 20 else 'Medium' if row['total_listings'] > 5 else 'Low',
                        'Contact_ID': row['contact_id']
                    }
                    hh_export_records.append(record)
                
                hh_export_df = pd.DataFrame(hh_export_records)
                hh_csv_data = hh_export_df.to_csv(index=False)
                
                # Generate Heavy Haulers specific filename
                hh_filename_parts = ["heavy_haulers_prospects"]
                if selected_equipment != 'All':
                    hh_filename_parts.append(f"equipment-{selected_equipment.replace(' ', '-')}")
                if selected_state != 'All':
                    hh_filename_parts.append(f"state-{selected_state.replace(' ', '-')}")
                
                hh_filename = f"{'_'.join(hh_filename_parts)}_{datetime.now().strftime('%Y%m%d')}.csv"
            else:
                hh_csv_data = "No data to export"
                hh_filename = "no_prospects.csv"
        
        with col2:
            if len(filtered_df) > 0:
                st.download_button(
                    label="🚛 Download Prospects",
                    data=hh_csv_data,
                    file_name=hh_filename,
                    mime="text/csv",
                    help=f"Download {len(filtered_df):,} dealer prospects for Heavy Haulers sales team",
                    use_container_width=True
                )
            else:
                st.info("No prospects to download")
        
        with col3:
            if len(filtered_df) > 0:
                st.metric("Prospect Count", f"{len(filtered_df):,}")
                high_opportunity = len(filtered_df[filtered_df['total_listings'] > 20])
                st.metric("High Opportunity", f"{high_opportunity}")
            else:
                st.metric("Prospect Count", "0")
        
        st.markdown("---")
        
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

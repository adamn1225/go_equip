#!/usr/bin/env python3
"""
AI-Enhanced Equipment Dashboard
Integrates OpenAI for intelligent insights and CAPTCHA solver status
"""

import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter
import re
from datetime import datetime
import os
import requests

# Check for AI capabilities
try:
    import openai
    OPENAI_AVAILABLE = True
    # Set OpenAI API key if available
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        openai.api_key = openai_key
except ImportError:
    OPENAI_AVAILABLE = False

# Authentication function (same as before)
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

def check_captcha_solver_status():
    """Check if CAPTCHA solver is running"""
    try:
        response = requests.get("http://localhost:5000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                'online': True,
                'status': data.get('status', 'unknown'),
                'api_configured': data.get('api_keys_configured', {}).get('2captcha', False)
            }
    except:
        pass
    
    return {'online': False, 'status': 'offline', 'api_configured': False}

def get_ai_insights(data_summary):
    """Generate AI insights using OpenAI"""
    if not OPENAI_AVAILABLE or not openai.api_key:
        return None
    
    try:
        prompt = f"""
        Analyze this equipment dealer database and provide 3 key business insights:
        
        Data Summary:
        - Total Contacts: {data_summary.get('total_contacts', 0):,}
        - Categories: {', '.join(data_summary.get('categories', []))}
        - Top States: {', '.join(data_summary.get('top_states', []))}
        - High-Value Contacts: {data_summary.get('high_value_count', 0)}
        - Average Listings per Contact: {data_summary.get('avg_listings', 0):.1f}
        
        Provide insights as 3 bullet points, each focusing on:
        1. Market opportunity
        2. Geographic concentration 
        3. Strategic recommendation
        
        Keep each point under 25 words and actionable for equipment sales.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"AI insights temporarily unavailable: {str(e)}"

# Your existing DashboardAnalyzer class remains the same
class DashboardAnalyzer:
    def __init__(self, master_log_file="master_contact_database.json"):
        self.master_log_file = master_log_file
        self.load_data()
    
    def load_data(self):
        """Load and process contact data"""
        try:
            with open(self.master_log_file, 'r', encoding='utf-8') as f:
                self.master_log = json.load(f)
            
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
                
                location = contact['primary_location']
                if location:
                    match = re.search(r',\s*([A-Za-z\s]+)$', location)
                    record['state'] = match.group(1).strip() if match else 'Unknown'
                else:
                    record['state'] = 'Unknown'
                
                categories = []
                for source in contact.get('sources', []):
                    category = source.get('category', '').strip()
                    if category and category not in categories:
                        categories.append(category)
                record['categories'] = ', '.join(categories) if categories else 'construction'
                
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
        
        company = str(record['seller_company']).lower()
        
        major_brands = ['wheeler machinery', 'holt cat', 'caterpillar', 'john deere', 'komatsu', 
                       'empire southwest', 'ring power', 'altorfer', 'fabick cat']
        if any(brand in company for brand in major_brands):
            score += 25
        
        if any(word in company for word in ['equipment', 'machinery', 'rental']):
            score += 15
        
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
    if not check_password():
        return
    
    st.set_page_config(
        page_title="AI-Enhanced Equipment Intelligence",
        page_icon="🤖",
        layout="wide"
    )
    
    # Header with AI status
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("🤖 AI-Enhanced Equipment Intelligence Dashboard")
        st.markdown("**Executive Analytics Portal with AI Insights**")
    
    with col2:
        # CAPTCHA Solver Status
        captcha_status = check_captcha_solver_status()
        if captcha_status['online']:
            st.success("🔓 CAPTCHA Solver: Online")
            if captcha_status['api_configured']:
                st.info("✅ 2captcha API: Ready")
            else:
                st.warning("⚠️ API Key Missing")
        else:
            st.error("❌ CAPTCHA Solver: Offline")
    
    with col3:
        # AI Status
        if OPENAI_AVAILABLE and openai.api_key:
            st.success("🧠 AI Insights: Enabled")
        else:
            st.info("🧠 AI Insights: Disabled")
    
    if st.button("🚪 Logout", key="logout_btn"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.markdown("---")
    
    # Load analyzer
    analyzer = DashboardAnalyzer()
    
    if analyzer.df.empty:
        st.error("No data available. Please check your master database file.")
        return
    
    # Sidebar filters (same as before)
    st.sidebar.header("🔍 Filters")
    
    all_categories = set()
    for _, contact in analyzer.df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip()
            if cat:
                all_categories.add(cat.title())
    
    category_options = ['All Categories'] + sorted(list(all_categories))
    selected_category = st.sidebar.selectbox("🏗️ Equipment Category", category_options)
    
    st.sidebar.markdown("---")
    search_term = st.sidebar.text_input("🔍 Search Equipment/Company", placeholder="e.g., CAT, John Deere, Excavator")
    
    priority_options = ['All'] + list(analyzer.df['priority_level'].unique())
    selected_priority = st.sidebar.selectbox("Priority Level", priority_options)
    
    state_options = ['All'] + sorted(analyzer.df['state'].unique())
    selected_state = st.sidebar.selectbox("State", state_options)
    
    min_listings = st.sidebar.slider("Minimum Listings", 0, int(analyzer.df['total_listings'].max()), 0)
    
    # Apply filters (same logic as before)
    filtered_df = analyzer.df.copy()
    
    if selected_category != 'All Categories':
        filtered_df = filtered_df[filtered_df['categories'].str.contains(selected_category.lower(), case=False, na=False)]
    
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
    
    # AI Insights Section (NEW!)
    if OPENAI_AVAILABLE and openai.api_key:
        st.subheader("🧠 AI-Generated Market Insights")
        
        with st.expander("📊 Generate AI Analysis", expanded=False):
            if st.button("🚀 Analyze Market with AI"):
                with st.spinner("AI analyzing your equipment market data..."):
                    # Prepare data summary for AI
                    data_summary = {
                        'total_contacts': len(filtered_df),
                        'categories': sorted(list(all_categories))[:5],  # Top 5 categories
                        'top_states': filtered_df['state'].value_counts().head(3).index.tolist(),
                        'high_value_count': len(filtered_df[filtered_df['priority_level'].isin(['Premium', 'High'])]),
                        'avg_listings': filtered_df['total_listings'].mean()
                    }
                    
                    insights = get_ai_insights(data_summary)
                    
                    if insights:
                        st.success("🎯 AI Market Analysis Complete!")
                        st.markdown("### Strategic Recommendations:")
                        st.markdown(insights)
                    else:
                        st.error("AI analysis temporarily unavailable")
    
    # Main dashboard metrics (same as before)
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
    
    # System Status Dashboard (NEW!)
    st.subheader("🔧 System Status & AI Capabilities")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if captcha_status['online']:
            st.success("🤖 CAPTCHA Solver\nOperational")
        else:
            st.error("🤖 CAPTCHA Solver\nOffline")
            st.info("Run: `./start_captcha_solver_lite.sh`")
    
    with col2:
        if OPENAI_AVAILABLE and openai.api_key:
            st.success("🧠 AI Insights\nEnabled")
        else:
            st.info("🧠 AI Insights\nNot Configured")
    
    with col3:
        categories_count = len(all_categories)
        st.metric("Equipment Types", f"{categories_count}")
    
    with col4:
        data_freshness = datetime.now().strftime("%Y-%m-%d")
        st.metric("Last Updated", data_freshness)
    
    # Rest of your existing dashboard code continues here...
    # (Equipment Category Analysis, Charts, etc. - same as your original dashboard.py)
    
    # Equipment Category Analysis
    st.subheader("🏗️ Equipment Category Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    
    category_counts = {}
    for _, contact in filtered_df.iterrows():
        categories = contact.get('categories', 'construction').split(',')
        for cat in categories:
            cat = cat.strip()
            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1
    
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    with col1:
        if sorted_categories:
            st.metric("Primary Category", sorted_categories[0][0].title(), f"{sorted_categories[0][1]:,} contacts")
    
    with col2:
        if len(sorted_categories) > 1:
            st.metric("Secondary Category", sorted_categories[1][0].title(), f"{sorted_categories[1][1]:,} contacts")
    
    with col3:
        excavator_count = category_counts.get('construction', 0)
        st.metric("Construction Equipment", f"{excavator_count:,}")
    
    with col4:
        multi_category = len([c for c in filtered_df['categories'] if ',' in str(c)])
        st.metric("Multi-Category Dealers", f"{multi_category:,}")
    
    # Charts (same as your existing dashboard)
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
            cat_df = pd.DataFrame(list(category_counts.items()), columns=['Category', 'Count'])
            cat_df = cat_df.sort_values('Count', ascending=True).tail(8)
            
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
    
    # High-value contacts table (same as before)
    st.subheader("💎 High-Value Contacts")
    
    high_value_df = filtered_df[filtered_df['priority_level'].isin(['Premium', 'High'])].sort_values('priority_score', ascending=False)
    
    if len(high_value_df) > 0:
        display_df = high_value_df[['seller_company', 'primary_phone', 'primary_location', 'total_listings', 'priority_level', 'priority_score']].copy()
        display_df.columns = ['Company', 'Phone', 'Location', 'Listings', 'Priority', 'Score']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download High-Value Contacts CSV",
            data=csv,
            file_name=f"high_value_contacts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No high-value contacts match your current filters.")

if __name__ == "__main__":
    main()

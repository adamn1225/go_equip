#!/usr/bin/env python3
"""
Enhanced Heavy Haulers Equipment Logistics Dashboard
D1 Integration with Unique Phone Numbers and Advanced CRM

Features:
- D1 database integration with real-time data
- Unique phone numbers for multi-line dialer
- Territory-based lead management
- Advanced sales analytics and AI insights
- Call tracking and email collection
"""

import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
import numpy as np
from collections import Counter, defaultdict

# Load environment variables
load_dotenv()

# Import D1 integration
from d1_integration import D1ScraperIntegration

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
    st.warning("📋 CRM features require additional packages: pip install sendgrid")

# Configure page
st.set_page_config(
    page_title="Heavy Haulers - Enhanced Sales Intelligence",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for Heavy Haulers with dialer integration
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    .dialer-dashboard {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: white;
    }
    .crm-section {
        background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: white;
    }
    .analytics-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #2a5298;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .priority-very-high { border-left-color: #28a745; background: linear-gradient(135deg, #d4edda, #c3e6cb); }
    .priority-high { border-left-color: #17a2b8; background: linear-gradient(135deg, #d1ecf1, #bee5eb); }
    .priority-medium { border-left-color: #ffc107; background: linear-gradient(135deg, #fff3cd, #ffeaa7); }
    .priority-standard { border-left-color: #6c757d; background: linear-gradient(135deg, #f8f9fa, #e9ecef); }
    .metric-highlight {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin: 0.5rem 0;
    }
    .dialer-number {
        font-family: 'Courier New', monospace;
        font-weight: bold;
        color: #1e3c72;
    }
</style>
""", unsafe_allow_html=True)

def get_d1_connection():
    """Get D1 database connection"""
    if not all([os.getenv('CLOUDFLARE_ACCOUNT_ID'), 
                os.getenv('D1_DATABASE_ID'), 
                os.getenv('CLOUDFLARE_API_TOKEN')]):
        return None
    
    return D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_dialer_analytics():
    """Load comprehensive dialer analytics from D1"""
    d1 = get_d1_connection()
    if not d1:
        return None
    
    try:
        # Get dialer data with enhanced analytics
        result = d1.execute_query("""
            SELECT 
                up.phone_number,
                up.company_name,
                up.location,
                up.equipment_category,
                up.total_listings,
                up.priority_score,
                up.call_status,
                up.call_attempts,
                up.last_call_date,
                up.call_result,
                up.sales_notes,
                up.created_at,
                up.updated_at,
                -- Extract state from location
                CASE 
                    WHEN up.location LIKE '%, %' 
                    THEN TRIM(SUBSTR(up.location, INSTR(up.location, ',') + 1))
                    ELSE 'Unknown'
                END as state,
                -- Priority level categorization
                CASE 
                    WHEN up.priority_score >= 90 THEN 'Very High'
                    WHEN up.priority_score >= 75 THEN 'High'
                    WHEN up.priority_score >= 60 THEN 'Medium'
                    ELSE 'Standard'
                END as priority_level
            FROM unique_phones up
            ORDER BY up.priority_score DESC, up.total_listings DESC
        """)
        
        if result and result.get('success') and result.get('result'):
            result_data = result['result']
            if isinstance(result_data, list) and len(result_data) > 0:
                if 'results' in result_data[0]:
                    return pd.DataFrame(result_data[0]['results'])
                else:
                    return pd.DataFrame(result_data)
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Error loading dialer analytics: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_database_statistics():
    """Get comprehensive database statistics"""
    d1 = get_d1_connection()
    if not d1:
        return {}
    
    stats = {}
    
    try:
        # Total contacts
        result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
        if result and result.get('success') and result.get('result'):
            result_data = result['result'][0]['results'][0] if 'results' in result['result'][0] else result['result'][0]
            stats['total_contacts'] = result_data['total']
        
        # Unique phones
        result = d1.execute_query("SELECT COUNT(*) as total FROM unique_phones")
        if result and result.get('success') and result.get('result'):
            result_data = result['result'][0]['results'][0] if 'results' in result['result'][0] else result['result'][0]
            stats['unique_phones'] = result_data['total']
        
        # High priority leads
        result = d1.execute_query("SELECT COUNT(*) as total FROM unique_phones WHERE priority_score >= 75")
        if result and result.get('success') and result.get('result'):
            result_data = result['result'][0]['results'][0] if 'results' in result['result'][0] else result['result'][0]
            stats['high_priority'] = result_data['total']
        
        # Not called yet
        result = d1.execute_query("SELECT COUNT(*) as total FROM unique_phones WHERE call_status = 'not_called'")
        if result and result.get('success') and result.get('result'):
            result_data = result['result'][0]['results'][0] if 'results' in result['result'][0] else result['result'][0]
            stats['not_called'] = result_data['total']
        
        # Equipment categories
        result = d1.execute_query("""
            SELECT equipment_category, COUNT(*) as count 
            FROM unique_phones 
            GROUP BY equipment_category 
            ORDER BY count DESC 
            LIMIT 10
        """)
        if result and result.get('success') and result.get('result'):
            result_data = result['result'][0]['results'] if 'results' in result['result'][0] else result['result']
            stats['top_categories'] = result_data
        
        return stats
        
    except Exception as e:
        st.error(f"❌ Error loading statistics: {e}")
        return {}

def render_enhanced_header():
    """Enhanced Heavy Haulers header with D1 status"""
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">🚛 Heavy Haulers Equipment Logistics</h1>
        <h2 style="color: #e8f4fd; margin: 0.5rem 0; font-size: 1.5rem;">Enhanced Sales Intelligence Dashboard</h2>
        <p style="color: #b8d4f0; margin: 0; font-size: 1.1em;">
            D1 Database • Unique Phone System • Multi-Line Dialer Ready • Advanced CRM
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_dialer_command_center():
    """Render the main dialer command center"""
    st.markdown("""
    <div class="dialer-dashboard">
        <h2 style="margin: 0 0 1rem 0;">📞 Multi-Line Dialer Command Center</h2>
        <p style="margin: 0;">Real-time dialer analytics and lead management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load dialer data
    dialer_df = load_dialer_analytics()
    stats = get_database_statistics()
    
    if dialer_df is None or dialer_df.empty:
        st.error("❌ No dialer data available. Run: `python d1_dialer_setup.py populate`")
        return
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown('<div class="analytics-card priority-very-high">', unsafe_allow_html=True)
        st.markdown('<div class="metric-highlight">📋</div>', unsafe_allow_html=True)
        st.metric("Total Database", f"{stats.get('total_contacts', 0):,}", help="All contacts in database")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="analytics-card priority-high">', unsafe_allow_html=True)
        st.markdown('<div class="metric-highlight">📞</div>', unsafe_allow_html=True)
        unique_count = stats.get('unique_phones', 0)
        duplicate_reduction = ((stats.get('total_contacts', 1) - unique_count) / stats.get('total_contacts', 1) * 100) if stats.get('total_contacts', 0) > 0 else 0
        st.metric("Unique Numbers", f"{unique_count:,}", f"-{duplicate_reduction:.0f}% duplicates")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="analytics-card priority-medium">', unsafe_allow_html=True)
        st.markdown('<div class="metric-highlight">🎯</div>', unsafe_allow_html=True)
        st.metric("High Priority", f"{stats.get('high_priority', 0):,}", help="5+ equipment listings")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="analytics-card priority-standard">', unsafe_allow_html=True)
        st.markdown('<div class="metric-highlight">📲</div>', unsafe_allow_html=True)
        st.metric("Ready to Call", f"{stats.get('not_called', 0):,}", help="Not yet contacted")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        called_count = len(dialer_df[dialer_df['call_status'] != 'not_called'])
        conversion_rate = (called_count / len(dialer_df) * 100) if len(dialer_df) > 0 else 0
        st.markdown('<div class="analytics-card priority-high">', unsafe_allow_html=True)
        st.markdown('<div class="metric-highlight">📈</div>', unsafe_allow_html=True)
        st.metric("Contact Rate", f"{conversion_rate:.1f}%", f"{called_count:,} contacted")
        st.markdown('</div>', unsafe_allow_html=True)

def render_priority_breakdown():
    """Render priority-based lead breakdown"""
    st.markdown("### 🎯 Priority Lead Analysis")
    
    dialer_df = load_dialer_analytics()
    if dialer_df.empty:
        return
    
    # Priority analysis
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 Priority Distribution")
        priority_counts = dialer_df['priority_level'].value_counts()
        
        # Create enhanced priority chart
        colors = {'Very High': '#28a745', 'High': '#17a2b8', 'Medium': '#ffc107', 'Standard': '#6c757d'}
        fig_priority = px.pie(
            values=priority_counts.values,
            names=priority_counts.index,
            title="Lead Priority Breakdown",
            color=priority_counts.index,
            color_discrete_map=colors
        )
        fig_priority.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_priority, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 Equipment Categories")
        top_categories = dialer_df['equipment_category'].value_counts().head(8)
        
        fig_categories = px.bar(
            x=top_categories.values,
            y=top_categories.index,
            orientation='h',
            title="Top Equipment Categories",
            color=top_categories.values,
            color_continuous_scale="viridis"
        )
        fig_categories.update_layout(showlegend=False)
        st.plotly_chart(fig_categories, use_container_width=True)
    
    with col3:
        st.markdown("#### 🗺️ Geographic Distribution")
        state_counts = dialer_df['state'].value_counts().head(10)
        
        fig_states = px.bar(
            x=state_counts.index,
            y=state_counts.values,
            title="Top States by Lead Count",
            color=state_counts.values,
            color_continuous_scale="blues"
        )
        fig_states.update_layout(showlegend=False, xaxis_tickangle=45)
        st.plotly_chart(fig_states, use_container_width=True)

def render_dialer_export_center():
    """Render export options for dialer lists"""
    st.markdown("### 📤 Dialer Export Center")
    
    dialer_df = load_dialer_analytics()
    if dialer_df.empty:
        return
    
    export_col1, export_col2, export_col3, export_col4 = st.columns(4)
    
    with export_col1:
        st.markdown("#### 🔥 Very High Priority")
        very_high_df = dialer_df[dialer_df['priority_level'] == 'Very High']
        st.metric("Count", f"{len(very_high_df):,}")
        
        if len(very_high_df) > 0:
            csv_data = very_high_df.to_csv(index=False)
            st.download_button(
                label="📞 Download VIP List",
                data=csv_data,
                file_name=f"very_high_priority_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary"
            )
    
    with export_col2:
        st.markdown("#### ⭐ High Priority")
        high_df = dialer_df[dialer_df['priority_level'] == 'High']
        st.metric("Count", f"{len(high_df):,}")
        
        if len(high_df) > 0:
            csv_data = high_df.to_csv(index=False)
            st.download_button(
                label="📞 Download High Priority",
                data=csv_data,
                file_name=f"high_priority_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with export_col3:
        st.markdown("#### 📲 Not Called Yet")
        not_called_df = dialer_df[dialer_df['call_status'] == 'not_called']
        st.metric("Count", f"{len(not_called_df):,}")
        
        if len(not_called_df) > 0:
            csv_data = not_called_df.to_csv(index=False)
            st.download_button(
                label="📞 Download Fresh Leads",
                data=csv_data,
                file_name=f"not_called_leads_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with export_col4:
        st.markdown("#### 🎯 Custom Filter")
        category_options = ['All'] + list(dialer_df['equipment_category'].unique())
        selected_category = st.selectbox("Equipment Type:", category_options)
        
        if selected_category != 'All':
            filtered_df = dialer_df[dialer_df['equipment_category'] == selected_category]
        else:
            filtered_df = dialer_df
            
        st.metric("Count", f"{len(filtered_df):,}")
        
        if len(filtered_df) > 0:
            csv_data = filtered_df.to_csv(index=False)
            st.download_button(
                label="📞 Download Filtered",
                data=csv_data,
                file_name=f"{selected_category.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

def render_live_dialer_preview():
    """Render live preview of dialer-ready numbers"""
    st.markdown("### 📋 Live Dialer Preview")
    
    dialer_df = load_dialer_analytics()
    if dialer_df.empty:
        return
    
    # Filter options
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        priority_filter = st.selectbox(
            "Priority Filter:",
            ['All', 'Very High', 'High', 'Medium', 'Standard']
        )
    
    with filter_col2:
        status_filter = st.selectbox(
            "Call Status:",
            ['All'] + list(dialer_df['call_status'].unique())
        )
    
    with filter_col3:
        limit = st.slider("Preview Limit:", 5, 100, 20)
    
    # Apply filters
    preview_df = dialer_df.copy()
    
    if priority_filter != 'All':
        preview_df = preview_df[preview_df['priority_level'] == priority_filter]
    
    if status_filter != 'All':
        preview_df = preview_df[preview_df['call_status'] == status_filter]
    
    # Sort and limit
    preview_df = preview_df.head(limit)
    
    if preview_df.empty:
        st.info("No records match the current filters.")
        return
    
    # Enhanced display format
    st.markdown(f"**Showing {len(preview_df)} leads:**")
    
    # Custom formatting for dialer display
    display_df = preview_df.copy()
    display_df['phone_display'] = display_df['phone_number'].apply(lambda x: f"📞 {x}")
    display_df['priority_display'] = display_df.apply(
        lambda row: f"{'🔥' if row['priority_level'] == 'Very High' else '⭐' if row['priority_level'] == 'High' else '📊' if row['priority_level'] == 'Medium' else '📋'} {row['priority_level']} ({row['priority_score']})",
        axis=1
    )
    
    # Show formatted table
    st.dataframe(
        display_df[['company_name', 'phone_display', 'location', 'equipment_category', 'priority_display', 'total_listings', 'call_status']],
        use_container_width=True,
        column_config={
            'company_name': 'Company',
            'phone_display': 'Phone Number',
            'location': 'Location',
            'equipment_category': 'Equipment',
            'priority_display': 'Priority',
            'total_listings': 'Listings',
            'call_status': 'Status'
        },
        hide_index=True
    )

def render_crm_sales_dashboard():
    """Render CRM and sales management dashboard"""
    if not CRM_ENABLED:
        st.markdown("""
        <div class="crm-section">
            <h2 style="margin: 0 0 1rem 0;">🎯 CRM System</h2>
            <p style="margin: 0;">CRM features require additional packages: pip install sendgrid</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("""
    <div class="crm-section">
        <h2 style="margin: 0 0 1rem 0;">🎯 Advanced CRM & Sales Management</h2>
        <p style="margin: 0;">Territory management, call tracking, and email integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sales rep selector
    current_rep, rep_name = render_sales_rep_selector()
    
    # Load dialer data for CRM
    dialer_df = load_dialer_analytics()
    
    if dialer_df.empty:
        st.warning("No data available for CRM features")
        return
    
    # CRM navigation
    crm_mode = st.sidebar.radio(
        "CRM Mode:",
        ["📊 Overview", "🗺️ Territory", "📞 Call Campaign", "📧 Email Marketing", "📈 Analytics"]
    )
    
    if crm_mode == "🗺️ Territory":
        render_territory_assignment(dialer_df)
    elif crm_mode == "📞 Call Campaign":
        render_call_campaign_manager(dialer_df)
    elif crm_mode == "📧 Email Marketing":
        render_email_integration()
    elif crm_mode == "📈 Analytics":
        render_crm_performance_analytics(current_rep)
    else:
        render_crm_overview(dialer_df, current_rep)

def render_crm_overview(dialer_df, current_rep):
    """Render CRM overview dashboard"""
    st.markdown("#### 📊 Sales Performance Overview")
    
    crm = CRMManager()
    assignments = crm.load_assignments()
    activities = crm.load_activities()
    
    # Get metrics for current rep
    my_leads = [int(lead_id) for lead_id, rep in assignments.items() if rep == current_rep]
    my_activities = {k: v for k, v in activities.items() if v.get('rep') == current_rep}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Assigned Leads", len(my_leads))
    
    with col2:
        calls_today = sum(1 for activity in my_activities.values() 
                         if activity.get('last_updated', '').startswith(datetime.now().date().isoformat()))
        st.metric("📞 Calls Today", calls_today)
    
    with col3:
        interested = sum(1 for activity in my_activities.values() 
                        if 'Interested' in activity.get('status', ''))
        st.metric("🎯 Interested Leads", interested)
    
    with col4:
        emails = sum(1 for activity in my_activities.values() 
                    if activity.get('email') and activity['email'].strip())
        st.metric("📧 Emails Collected", emails)

def render_crm_performance_analytics(current_rep):
    """Render detailed CRM performance analytics"""
    st.markdown("#### 📈 Detailed Performance Analytics")
    
    crm = CRMManager()
    activities = crm.load_activities()
    
    # Filter for current rep
    rep_activities = {k: v for k, v in activities.items() if v.get('rep') == current_rep}
    
    if not rep_activities:
        st.info("Start making calls to see detailed analytics!")
        return
    
    # Performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Daily activity
        daily_activity = defaultdict(int)
        for activity in rep_activities.values():
            date = activity.get('last_updated', '')[:10]
            if date:
                daily_activity[date] += 1
        
        if daily_activity:
            fig_daily = px.line(
                x=list(daily_activity.keys()),
                y=list(daily_activity.values()),
                title="Daily Call Activity Trend"
            )
            st.plotly_chart(fig_daily, use_container_width=True)
    
    with col2:
        # Call outcomes
        outcomes = [activity.get('status', 'Unknown') for activity in rep_activities.values()]
        outcome_counts = Counter(outcomes)
        
        fig_outcomes = px.pie(
            values=list(outcome_counts.values()),
            names=list(outcome_counts.keys()),
            title="Call Outcome Distribution"
        )
        st.plotly_chart(fig_outcomes, use_container_width=True)

def main():
    """Main Heavy Haulers dashboard application"""
    
    # Enhanced header
    render_enhanced_header()
    
    # Check D1 connection
    d1 = get_d1_connection()
    if not d1:
        st.error("❌ D1 database connection required. Please check your .env configuration.")
        st.info("Required: CLOUDFLARE_ACCOUNT_ID, D1_DATABASE_ID, CLOUDFLARE_API_TOKEN")
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("🚛 Heavy Haulers Navigation")
    st.sidebar.markdown("---")
    
    main_mode = st.sidebar.selectbox(
        "Dashboard Mode:",
        [
            "📞 Dialer Command Center",
            "🎯 CRM & Sales Management", 
            "📊 Analytics & Insights",
            "⚙️ System Administration"
        ]
    )
    
    # Render selected mode
    if main_mode == "📞 Dialer Command Center":
        render_dialer_command_center()
        st.markdown("---")
        render_priority_breakdown()
        st.markdown("---")
        render_dialer_export_center()
        st.markdown("---")
        render_live_dialer_preview()
        
    elif main_mode == "🎯 CRM & Sales Management":
        render_crm_sales_dashboard()
        
    elif main_mode == "📊 Analytics & Insights":
        render_advanced_analytics()
        
    elif main_mode == "⚙️ System Administration":
        render_system_administration()
    
    # Footer with system info
    st.markdown("---")
    stats = get_database_statistics()
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; margin-top: 2rem;">
        <p style="margin: 0; color: #495057; font-weight: bold;">Heavy Haulers Equipment Logistics - Enhanced Sales Intelligence</p>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">
            Database: {stats.get('total_contacts', 0):,} contacts • 
            Unique Numbers: {stats.get('unique_phones', 0):,} • 
            High Priority: {stats.get('high_priority', 0):,} • 
            Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_advanced_analytics():
    """Render advanced analytics and insights"""
    st.markdown("## 📊 Advanced Analytics & Market Insights")
    
    dialer_df = load_dialer_analytics()
    if dialer_df.empty:
        st.warning("No data available for analytics")
        return
    
    # Market analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏗️ Equipment Market Analysis")
        category_analysis = dialer_df.groupby('equipment_category').agg({
            'total_listings': 'sum',
            'priority_score': 'mean',
            'company_name': 'count'
        }).round(1)
        
        st.dataframe(category_analysis, use_container_width=True)
    
    with col2:
        st.markdown("### 🗺️ Geographic Market Distribution")
        state_analysis = dialer_df.groupby('state').agg({
            'company_name': 'count',
            'total_listings': 'sum',
            'priority_score': 'mean'
        }).sort_values('company_name', ascending=False).head(15)
        
        st.dataframe(state_analysis, use_container_width=True)

def render_system_administration():
    """Render system administration tools"""
    st.markdown("## ⚙️ System Administration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔄 Data Management")
        
        if st.button("🔄 Refresh Cache"):
            st.cache_data.clear()
            st.success("✅ Cache cleared!")
        
        if st.button("📊 Update Statistics"):
            # Clear cache to force refresh
            get_database_statistics.clear()
            st.success("✅ Statistics refreshed!")
    
    with col2:
        st.markdown("### 📞 Dialer Management")
        
        if st.button("🔄 Refresh Dialer Data"):
            st.info("💡 Run: `python d1_dialer_setup.py populate`")
        
        if st.button("📋 Export Full Database"):
            dialer_df = load_dialer_analytics()
            if not dialer_df.empty:
                csv_data = dialer_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Complete Database",
                    data=csv_data,
                    file_name=f"complete_dialer_database_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
    
    with col3:
        st.markdown("### 🔧 System Status")
        
        # Database connection test
        d1 = get_d1_connection()
        if d1:
            try:
                result = d1.execute_query("SELECT 1 as test")
                if result and result.get('success'):
                    st.success("✅ D1 Database Online")
                else:
                    st.error("❌ D1 Database Error")
            except Exception as e:
                st.error(f"❌ Connection Error: {e}")
        
        # Show environment status
        required_env = ['CLOUDFLARE_ACCOUNT_ID', 'D1_DATABASE_ID', 'CLOUDFLARE_API_TOKEN']
        missing_env = [env for env in required_env if not os.getenv(env)]
        
        if missing_env:
            st.error(f"❌ Missing: {', '.join(missing_env)}")
        else:
            st.success("✅ Environment Configured")

if __name__ == "__main__":
    main()

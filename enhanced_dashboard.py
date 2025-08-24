#!/usr/bin/env python3
"""
Enhanced Contact Database Dashboard - D1 Integration
Now with unique phone numbers dialer system and advanced CRM features

Features:
- D1 database integration with unique phones table
- Multi-line dialer support with deduplicated numbers
- Advanced CRM with territory management
- Real-time sales analytics and lead tracking
"""

import json
import os
import pandas as pd
import streamlit as st
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter

# Load environment variables
load_dotenv()

# Import D1 integration
from d1_integration import D1ScraperIntegration

# Import CRM features
try:
    from crm_features import (
        CRMManager, render_sales_rep_selector, render_territory_assignment,
        render_call_campaign_manager, render_email_integration,
        render_contact_timeline, add_crm_navigation, render_fixed_research_panel
    )
    CRM_ENABLED = True
except ImportError:
    CRM_ENABLED = False
    st.warning("📋 CRM features not available - install dependencies: pip install sendgrid")

# Configure Streamlit page
st.set_page_config(
    page_title="Enhanced Equipment Seller Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .dialer-metrics {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .database-status {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .priority-high { border-left-color: #28a745; }
    .priority-medium { border-left-color: #ffc107; }
    .priority-low { border-left-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

def get_d1_connection():
    """Get D1 database connection"""
    if not all([os.getenv('CLOUDFLARE_ACCOUNT_ID'), 
                os.getenv('D1_DATABASE_ID'), 
                os.getenv('CLOUDFLARE_API_TOKEN')]):
        st.error("❌ Missing D1 credentials in .env file")
        return None
    
    return D1ScraperIntegration(
        os.getenv('CLOUDFLARE_ACCOUNT_ID'),
        os.getenv('D1_DATABASE_ID'),
        os.getenv('CLOUDFLARE_API_TOKEN')
    )

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_d1_contacts_data():
    """Load contacts data from D1 database"""
    d1 = get_d1_connection()
    if not d1:
        return pd.DataFrame()
    
    try:
        # Get all contacts with source information
        result = d1.execute_query("""
            SELECT 
                c.id,
                c.seller_company,
                c.primary_phone,
                c.primary_location,
                c.email,
                c.website,
                c.total_listings,
                c.priority_score,
                c.priority_level,
                c.city,
                c.state,
                c.country,
                c.last_updated,
                cs.category as equipment_category,
                cs.site as source_site,
                cs.listing_count
            FROM contacts c
            LEFT JOIN contact_sources cs ON c.id = cs.contact_id
            ORDER BY c.priority_score DESC, c.total_listings DESC
        """)
        
        if result and result.get('success') and result.get('result'):
            # Handle nested D1 result structure
            result_data = result['result']
            if isinstance(result_data, list) and len(result_data) > 0:
                if 'results' in result_data[0]:
                    contacts = result_data[0]['results']
                else:
                    contacts = result_data
                    
                return pd.DataFrame(contacts)
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Error loading D1 data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_d1_dialer_data():
    """Load unique phone numbers from dialer table"""
    d1 = get_d1_connection()
    if not d1:
        return pd.DataFrame()
    
    try:
        result = d1.execute_query("""
            SELECT 
                phone_number,
                company_name,
                location,
                equipment_category,
                total_listings,
                priority_score,
                call_status,
                call_attempts,
                last_call_date,
                call_result,
                sales_notes,
                created_at
            FROM unique_phones
            ORDER BY priority_score DESC, total_listings DESC
        """)
        
        if result and result.get('success') and result.get('result'):
            result_data = result['result']
            if isinstance(result_data, list) and len(result_data) > 0:
                if 'results' in result_data[0]:
                    phones = result_data[0]['results']
                else:
                    phones = result_data
                    
                return pd.DataFrame(phones)
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"❌ Error loading dialer data: {e}")
        return pd.DataFrame()

def render_enhanced_header():
    """Render enhanced header with D1 status"""
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🏗️ Enhanced Equipment Seller Dashboard</h1>
        <p style="color: #e8f4fd; margin: 0; font-size: 1.2em;">
            D1 Database • Unique Phone System • Advanced CRM
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_database_overview():
    """Render database status and overview"""
    st.markdown("## 📊 Database Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Load data
    contacts_df = load_d1_contacts_data()
    dialer_df = load_d1_dialer_data()
    
    with col1:
        st.markdown('<div class="database-status">', unsafe_allow_html=True)
        st.metric(
            label="📋 Total Contacts",
            value=f"{len(contacts_df):,}" if not contacts_df.empty else "0",
            help="All contacts in D1 database"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="dialer-metrics">', unsafe_allow_html=True)
        st.metric(
            label="📞 Unique Phone Numbers",
            value=f"{len(dialer_df):,}" if not dialer_df.empty else "0",
            help="Deduplicated numbers for dialer"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        if not dialer_df.empty:
            high_priority = len(dialer_df[dialer_df['priority_score'] >= 75])
            st.metric(
                label="🎯 High Priority Leads",
                value=f"{high_priority:,}",
                help="Companies with 5+ listings"
            )
        else:
            st.metric("🎯 High Priority Leads", "0")
    
    with col4:
        if not dialer_df.empty:
            not_called = len(dialer_df[dialer_df['call_status'] == 'not_called'])
            st.metric(
                label="📲 Ready to Call",
                value=f"{not_called:,}",
                help="Numbers not yet contacted"
            )
        else:
            st.metric("📲 Ready to Call", "0")

def render_dialer_dashboard():
    """Render dialer-specific dashboard"""
    st.markdown("## 📞 Multi-Line Dialer Dashboard")
    
    dialer_df = load_d1_dialer_data()
    
    if dialer_df.empty:
        st.warning("📞 No dialer data available. Run: `python d1_dialer_setup.py populate`")
        return
    
    # Dialer metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 Call Status Distribution")
        status_counts = dialer_df['call_status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Call Status Breakdown"
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        st.markdown("### 🎯 Priority Score Distribution")
        priority_bins = pd.cut(dialer_df['priority_score'], 
                              bins=[0, 59, 74, 89, 100],
                              labels=['Standard', 'Medium', 'High', 'Very High'])
        priority_counts = priority_bins.value_counts()
        
        fig_priority = px.bar(
            x=priority_counts.index,
            y=priority_counts.values,
            title="Priority Distribution",
            color=priority_counts.values,
            color_continuous_scale="viridis"
        )
        st.plotly_chart(fig_priority, use_container_width=True)
    
    with col3:
        st.markdown("### 📈 Top Equipment Categories")
        category_counts = dialer_df['equipment_category'].value_counts().head(8)
        fig_categories = px.bar(
            x=category_counts.values,
            y=category_counts.index,
            orientation='h',
            title="Top Equipment Categories"
        )
        st.plotly_chart(fig_categories, use_container_width=True)
    
    # Export dialer lists
    st.markdown("---")
    st.markdown("### 📤 Export Dialer Lists")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        if st.button("📞 Export High Priority List", type="primary"):
            high_priority_df = dialer_df[dialer_df['priority_score'] >= 75]
            csv_data = high_priority_df.to_csv(index=False)
            st.download_button(
                label="Download High Priority CSV",
                data=csv_data,
                file_name=f"high_priority_dialer_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.success(f"✅ {len(high_priority_df)} high priority numbers ready for export!")
    
    with export_col2:
        if st.button("📋 Export Not Called List"):
            not_called_df = dialer_df[dialer_df['call_status'] == 'not_called']
            csv_data = not_called_df.to_csv(index=False)
            st.download_button(
                label="Download Not Called CSV",
                data=csv_data,
                file_name=f"not_called_dialer_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.success(f"✅ {len(not_called_df)} new numbers ready for export!")
    
    with export_col3:
        if st.button("🎯 Export Category Focused"):
            category = st.selectbox("Select Category:", dialer_df['equipment_category'].unique())
            category_df = dialer_df[dialer_df['equipment_category'] == category]
            csv_data = category_df.to_csv(index=False)
            st.download_button(
                label=f"Download {category} CSV",
                data=csv_data,
                file_name=f"{category.replace(' ', '_')}_dialer_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.success(f"✅ {len(category_df)} {category} numbers ready!")

def render_crm_integration():
    """Render CRM features if available"""
    if not CRM_ENABLED:
        st.markdown("## 📋 CRM Features")
        st.warning("CRM features not available. Install dependencies: `pip install sendgrid`")
        return
    
    st.markdown("## 🎯 Advanced CRM System")
    
    # Sales rep selector
    current_rep, rep_name = render_sales_rep_selector()
    
    # Load D1 data for CRM
    contacts_df = load_d1_contacts_data()
    dialer_df = load_d1_dialer_data()
    
    if contacts_df.empty and dialer_df.empty:
        st.warning("No contact data available for CRM features")
        return
    
    # Use dialer data primarily (unique numbers)
    crm_df = dialer_df if not dialer_df.empty else contacts_df
    
    # CRM mode selection
    crm_mode = add_crm_navigation()
    
    if crm_mode == "Territory Management":
        render_territory_assignment(crm_df)
    elif crm_mode == "Call Campaign":
        render_call_campaign_manager(crm_df)
    elif crm_mode == "Email Marketing":
        render_email_integration()
    elif crm_mode == "Analytics":
        render_crm_analytics(crm_df, current_rep)
    else:
        render_crm_dashboard_overview(crm_df, current_rep)

def render_crm_dashboard_overview(df, current_rep):
    """Render CRM dashboard overview"""
    st.markdown("### 📊 CRM Dashboard Overview")
    
    crm = CRMManager()
    assignments = crm.load_assignments()
    activities = crm.load_activities()
    
    # Get assigned leads for current rep
    my_leads = [int(lead_id) for lead_id, rep in assignments.items() if rep == current_rep]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Assigned Leads", len(my_leads))
    
    with col2:
        called_today = sum(1 for activity in activities.values() 
                          if activity.get('rep') == current_rep and 
                             activity.get('last_updated', '').startswith(datetime.now().date().isoformat()))
        st.metric("📞 Calls Made Today", called_today)
    
    with col3:
        interested_leads = sum(1 for activity in activities.values()
                              if activity.get('rep') == current_rep and
                                 'Interested' in activity.get('status', ''))
        st.metric("🎯 Interested Leads", interested_leads)
    
    with col4:
        emails_collected = sum(1 for activity in activities.values()
                              if activity.get('rep') == current_rep and
                                 activity.get('email') and activity['email'].strip())
        st.metric("📧 Emails Collected", emails_collected)

def render_crm_analytics(df, current_rep):
    """Render CRM analytics and performance metrics"""
    st.markdown("### 📈 Sales Performance Analytics")
    
    crm = CRMManager()
    activities = crm.load_activities()
    
    # Filter activities for current rep
    rep_activities = {k: v for k, v in activities.items() 
                     if v.get('rep') == current_rep}
    
    if not rep_activities:
        st.info("No activity data yet. Start making calls to see analytics!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Call results over time
        st.markdown("#### 📞 Daily Call Activity")
        daily_calls = defaultdict(int)
        for activity in rep_activities.values():
            date = activity.get('last_updated', '')[:10]  # Get date part
            if date:
                daily_calls[date] += 1
        
        if daily_calls:
            dates = list(daily_calls.keys())
            counts = list(daily_calls.values())
            
            fig_daily = px.line(
                x=dates, y=counts,
                title="Daily Call Volume",
                labels={'x': 'Date', 'y': 'Calls Made'}
            )
            st.plotly_chart(fig_daily, use_container_width=True)
    
    with col2:
        # Call outcomes
        st.markdown("#### 🎯 Call Outcomes")
        outcomes = [activity.get('status', 'Unknown') 
                   for activity in rep_activities.values()]
        outcome_counts = Counter(outcomes)
        
        if outcome_counts:
            fig_outcomes = px.pie(
                values=list(outcome_counts.values()),
                names=list(outcome_counts.keys()),
                title="Call Results Distribution"
            )
            st.plotly_chart(fig_outcomes, use_container_width=True)

def render_system_tools():
    """Render system maintenance and diagnostic tools"""
    st.markdown("## ⚙️ System Tools")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔄 Data Management")
        
        if st.button("🔄 Refresh D1 Cache", type="secondary"):
            st.cache_data.clear()
            st.success("✅ Cache cleared! Data will refresh on next load.")
        
        if st.button("📊 Update Dialer Data"):
            with st.spinner("Updating dialer data..."):
                # This would trigger the dialer setup populate command
                st.info("💡 Run in terminal: `python d1_dialer_setup.py populate`")
    
    with col2:
        st.markdown("### 📈 Database Status")
        
        d1 = get_d1_connection()
        if d1:
            try:
                # Check database connection
                result = d1.execute_query("SELECT COUNT(*) as total FROM contacts")
                if result and result.get('success'):
                    st.success("✅ D1 Database Connected")
                else:
                    st.error("❌ D1 Database Error")
            except Exception as e:
                st.error(f"❌ Connection Error: {e}")
        else:
            st.error("❌ D1 Credentials Missing")
    
    with col3:
        st.markdown("### 🛠️ Quick Actions")
        
        if st.button("📞 Export Latest Dialer List"):
            dialer_df = load_d1_dialer_data()
            if not dialer_df.empty:
                csv_data = dialer_df.to_csv(index=False)
                st.download_button(
                    label="Download Current Dialer List",
                    data=csv_data,
                    file_name=f"current_dialer_list_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No dialer data available")

def main():
    """Main dashboard application"""
    # Enhanced header
    render_enhanced_header()
    
    # Check D1 connection
    if not get_d1_connection():
        st.error("❌ Cannot connect to D1 database. Please check your .env configuration.")
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("🏗️ Dashboard Navigation")
    
    page_mode = st.sidebar.selectbox(
        "Select View:",
        ["📊 Database Overview", "📞 Dialer Dashboard", "🎯 CRM System", "⚙️ System Tools"]
    )
    
    # Render selected page
    if page_mode == "📊 Database Overview":
        render_database_overview()
        
        # Quick data preview
        st.markdown("---")
        st.markdown("### 📋 Recent Contacts Preview")
        contacts_df = load_d1_contacts_data()
        if not contacts_df.empty:
            st.dataframe(contacts_df.head(10), use_container_width=True)
        
    elif page_mode == "📞 Dialer Dashboard":
        render_dialer_dashboard()
        
    elif page_mode == "🎯 CRM System":
        render_crm_integration()
        
    elif page_mode == "⚙️ System Tools":
        render_system_tools()
    
    # Fixed research panel (if active)
    if CRM_ENABLED:
        render_fixed_research_panel()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: #666;">
        <p>Enhanced Equipment Seller Dashboard • D1 Integration • Unique Phone System</p>
        <p>Last Updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()

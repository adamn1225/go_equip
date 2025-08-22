#!/usr/bin/env python3
"""
D1-Powered Dashboard
Uses Cloudflare D1 database instead of JSON files for better performance
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import json
import os
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="Equipment Seller Database Dashboard (D1)",
    page_icon="🏗️",
    layout="wide"
)

class D1DashboardManager:
    def __init__(self):
        self.database_name = "equipment-contacts"
    
    def execute_d1_query(self, sql_query):
        """Execute a query on D1 database using wrangler CLI"""
        try:
            # Use wrangler CLI to query D1 (remote database with your credentials)
            cmd = ["wrangler", "d1", "execute", self.database_name, "--remote", "--command", sql_query, "--json"]
            
            # Set environment variables for authentication
            env = os.environ.copy()
            env['CLOUDFLARE_API_TOKEN'] = 'nAHcEEszR31BJuiCrSyEIK8rOEtYmBtpk_eA7u_9'
            env['CLOUDFLARE_ACCOUNT_ID'] = 'c0ae0f2da2cc0cf49cc5a01d3f24b30e'
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                # Parse the JSON output
                output_lines = result.stdout.strip().split('\n')
                # Find the JSON result (skip wrangler headers)
                for line in output_lines:
                    if line.startswith('[') or line.startswith('{'):
                        return json.loads(line)
                return []
            else:
                st.error(f"D1 Query failed: {result.stderr}")
                return []
        except Exception as e:
            st.error(f"Error executing D1 query: {e}")
            return []
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_contact_summary(_self):
        """Get contact summary data"""
        query = """
        SELECT 
            id, seller_company, primary_phone, primary_location, state,
            total_listings, priority_level, categories, category_count,
            unique_makes, equipment_records
        FROM contact_summary 
        ORDER BY total_listings DESC
        """
        return _self.execute_d1_query(query)
    
    @st.cache_data(ttl=300)
    def get_category_stats(_self):
        """Get category statistics"""
        query = """
        SELECT 
            category,
            COUNT(DISTINCT contact_id) as contact_count,
            SUM(listing_count) as total_listings
        FROM contact_sources 
        GROUP BY category 
        ORDER BY contact_count DESC
        """
        return _self.execute_d1_query(query)
    
    @st.cache_data(ttl=300)
    def get_state_stats(_self):
        """Get state distribution"""
        query = """
        SELECT 
            state,
            COUNT(*) as contact_count,
            SUM(total_listings) as total_listings
        FROM contacts 
        WHERE state != 'Unknown'
        GROUP BY state 
        ORDER BY contact_count DESC
        LIMIT 15
        """
        return _self.execute_d1_query(query)
    
    @st.cache_data(ttl=300)
    def get_equipment_makes(_self):
        """Get top equipment makes"""
        query = """
        SELECT 
            equipment_make,
            COUNT(*) as count,
            COUNT(DISTINCT contact_id) as unique_contacts
        FROM equipment_data 
        WHERE equipment_make != ''
        GROUP BY equipment_make 
        ORDER BY count DESC 
        LIMIT 10
        """
        return _self.execute_d1_query(query)
    
    @st.cache_data(ttl=300)
    def get_dashboard_totals(_self):
        """Get overall dashboard statistics"""
        queries = {
            'total_contacts': 'SELECT COUNT(*) as count FROM contacts',
            'total_categories': 'SELECT COUNT(DISTINCT category) as count FROM contact_sources',
            'total_listings': 'SELECT SUM(total_listings) as count FROM contacts',
            'premium_contacts': "SELECT COUNT(*) as count FROM contacts WHERE priority_level = 'premium'"
        }
        
        results = {}
        for key, query in queries.items():
            result = _self.execute_d1_query(query)
            if result and len(result) > 0:
                results[key] = result[0].get('count', 0)
            else:
                results[key] = 0
        
        return results

# Authentication (keeping your existing auth)
def check_password():
    """Simple password authentication for executive access"""
    def password_entered():
        if "password" in st.session_state and st.session_state["password"] == "ContactAnalytics2025!":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("# Contact Analytics Dashboard (D1 Powered)")
        st.markdown("**Executive Access Required**")
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.info("Contact your system administrator for access credentials.")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("# Contact Analytics Dashboard (D1 Powered)")
        st.text_input("Enter Password:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password")
        return False
    else:
        return True

def main():
    # Check authentication first
    if not check_password():
        return
    
    st.markdown("# 🏗️ Equipment Seller Database Dashboard")
    st.markdown("### **Powered by Cloudflare D1** - Lightning fast global database")
    
    # Add logout button
    if st.button("🚪 Logout", key="logout_btn"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.markdown("---")
    
    # Initialize D1 manager
    d1_manager = D1DashboardManager()
    
    # Get dashboard totals
    with st.spinner("Loading dashboard data from D1..."):
        totals = d1_manager.get_dashboard_totals()
    
    # Main dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📞 Total Contacts",
            value=f"{totals['total_contacts']:,}",
            delta="From D1 Database"
        )
    
    with col2:
        st.metric(
            label="🏷️ Equipment Categories", 
            value=f"{totals['total_categories']:,}",
            delta="Active Categories"
        )
    
    with col3:
        st.metric(
            label="📋 Total Listings",
            value=f"{totals['total_listings']:,}",
            delta="All Sources"
        )
    
    with col4:
        st.metric(
            label="⭐ Premium Contacts",
            value=f"{totals['premium_contacts']:,}",
            delta="High Value Targets"
        )
    
    # Charts section
    st.markdown("## 📊 Analytics Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Top Equipment Categories")
        category_data = d1_manager.get_category_stats()
        
        if category_data:
            df_categories = pd.DataFrame(category_data)
            fig = px.bar(
                df_categories.head(10), 
                x='contact_count', 
                y='category',
                title="Contact Count by Equipment Category",
                orientation='h'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")
    
    with col2:
        st.subheader("🗺️ Geographic Distribution")
        state_data = d1_manager.get_state_stats()
        
        if state_data:
            df_states = pd.DataFrame(state_data)
            fig = px.pie(
                df_states.head(10), 
                values='contact_count', 
                names='state',
                title="Contacts by State"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No state data available")
    
    # Equipment makes chart
    st.subheader("🏭 Top Equipment Manufacturers")
    makes_data = d1_manager.get_equipment_makes()
    
    if makes_data:
        df_makes = pd.DataFrame(makes_data)
        fig = px.bar(
            df_makes, 
            x='equipment_make', 
            y='count',
            title="Equipment Count by Manufacturer",
            text='unique_contacts'
        )
        fig.update_traces(texttemplate='%{text} contacts', textposition='outside')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equipment manufacturer data available")
    
    # Recent contacts table
    st.subheader("📋 Contact Database Overview")
    contact_data = d1_manager.get_contact_summary()
    
    if contact_data:
        df_contacts = pd.DataFrame(contact_data)
        
        # Display top 20 contacts
        display_df = df_contacts.head(20)[[
            'seller_company', 'primary_phone', 'primary_location', 
            'categories', 'total_listings', 'priority_level'
        ]]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Download section
        st.markdown("### 📥 Export Data")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            csv = df_contacts.to_csv(index=False)
            st.download_button(
                label="📊 Download All Contacts CSV",
                data=csv,
                file_name=f"d1_contacts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.info(f"Total records: {len(df_contacts):,}")
        
        with col3:
            if st.button("🔄 Refresh Data"):
                st.cache_data.clear()
                st.rerun()
    
    else:
        st.info("No contact data found in D1 database")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d;">
        <p>🚀 <strong>Powered by Cloudflare D1</strong> - Global serverless database</p>
        <p>⚡ Lightning-fast queries from the edge</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

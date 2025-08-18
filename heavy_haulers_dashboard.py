#!/usr/bin/env python3
"""
Heavy Haulers Equipment Logistics - Sales Intelligence Dashboard
AI-powered analytics for cold outreach and business development
"""

import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import openai
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import re
import numpy as np
from collections import Counter, defaultdict

# Configure page
st.set_page_config(
    page_title="Heavy Haulers - Sales Intelligence Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Load data
@st.cache_data
def load_master_database():
    """Load the master contact database"""
    try:
        with open('master_contact_database.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Master contact database not found. Please ensure master_contact_database.json exists.")
        return None

@st.cache_data
def process_dealer_data(master_log):
    """Process dealer data for Heavy Haulers analytics"""
    if not master_log:
        return pd.DataFrame()
    
    records = []
    for contact_id, contact in master_log['contacts'].items():
        # Extract all information using correct field names
        name = contact.get('seller_company', 'Unknown')
        phone = contact.get('primary_phone', '')
        location = contact.get('primary_location', '')
        website = contact.get('website', '')
        
        # Skip contacts with "Unknown" names for better data quality
        if name == 'Unknown' or name.strip() == '':
            continue
            
        # Extract state from location
        state = 'Unknown'
        if location:
            match = re.search(r',\s*([A-Za-z\s]+)$', location)
            state = match.group(1).strip() if match else 'Unknown'
            
        # Extract equipment categories from sources
        equipment_types = []
        sources = contact.get('sources', [])
        
        for source in sources:
            # Extract category from source
            category = source.get('category', '').strip().lower()
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
            'contact_id': contact_id,
            'name': name,
            'phone': phone,
            'location': location,
            'state': state,
            'website': website,
            'equipment_types': equipment_str,
            'num_equipment_types': len(equipment_types),
            'num_sources': len(sources),
            'total_listings': contact.get('total_listings', 1)
        })
    
    return pd.DataFrame(records)

# Load and process data
master_log = load_master_database()
if master_log:
    df = process_dealer_data(master_log)
    
    if not df.empty:
        # Sidebar filters
        st.sidebar.header("🎯 Target Market Filters")
        
        # Equipment type filter
        equipment_options = ['All'] + sorted(df['equipment_types'].str.split(', ').explode().unique().tolist())
        selected_equipment = st.sidebar.selectbox("Equipment Type", equipment_options)
        
        # State filter
        state_options = ['All'] + sorted([s for s in df['state'].unique() if s])
        selected_state = st.sidebar.selectbox("State", state_options)
        
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
                        for equipment in equipment_list.split(', '):
                            equipment_counts[equipment] += 1
                
                if equipment_counts:
                    equipment_df = pd.DataFrame(list(equipment_counts.items()), 
                                             columns=['Equipment', 'Count'])
                    fig = px.pie(equipment_df, values='Count', names='Equipment', 
                                title="Market Share by Equipment Type")
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, key="equipment_pie_chart")
            
            with col2:
                st.subheader("Top States by Dealer Count")
                state_counts = filtered_df['state'].value_counts().head(10)
                if not state_counts.empty:
                    fig = px.bar(x=state_counts.values, y=state_counts.index, 
                                orientation='h', title="Geographic Distribution")
                    fig.update_layout(yaxis_title="State", xaxis_title="Dealer Count")
                    st.plotly_chart(fig, use_container_width=True, key="states_bar_chart")
        
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
            top_prospects['Action'] = '📞 Call Now'
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
            
            # Also show the traditional table view
            st.subheader("📋 Complete Prospect List")
            display_prospects = top_prospects[['name', 'location', 'phone', 'equipment_types', 'Score', 'priority_level']].copy()
            st.dataframe(display_prospects, use_container_width=True)
            
            # Export functionality
            st.subheader("📥 Export Sales Lists")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Export High Priority List"):
                    high_priority = filtered_df[filtered_df['priority_level'] == 'High']
                    csv = high_priority[['name', 'phone', 'location', 'equipment_types', 'website']].to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_high_priority.csv", "text/csv")
            
            with col2:
                if st.button("Export All Prospects"):
                    csv = filtered_df[['name', 'phone', 'location', 'equipment_types', 'business_potential']].to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_all_prospects.csv", "text/csv")
            
            with col3:
                if st.button("Export by State"):
                    if selected_state != 'All':
                        state_data = filtered_df[filtered_df['state'] == selected_state]
                        csv = state_data[['name', 'phone', 'location', 'equipment_types']].to_csv(index=False)
                        st.download_button("Download CSV", csv, f"heavy_haulers_{selected_state.lower()}.csv", "text/csv")
        
        with tab3:
            st.header("📍 Geographic Market Analysis")
            st.markdown("**Identify underserved markets and expansion opportunities**")
            
            # State name to abbreviation mapping for choropleth map
            state_abbr_map = {
                'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
                'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
                'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
                'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
                'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
                'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH',
                'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
                'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
                'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
                'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
                'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
            }
            
            # State analysis
            state_analysis = filtered_df.groupby('state').agg({
                'contact_id': 'count',
                'num_equipment_types': 'mean',
                'business_potential': 'mean'
            }).round(2)
            state_analysis.columns = ['Dealer_Count', 'Avg_Equipment_Types', 'Avg_Business_Potential']
            state_analysis = state_analysis.sort_values('Dealer_Count', ascending=False).reset_index()
            
            # Add state abbreviations for choropleth map
            state_analysis['state_abbr'] = state_analysis['state'].map(state_abbr_map)
            # Filter out states that don't have abbreviations (like 'Unknown' or invalid states)
            state_analysis_valid = state_analysis[state_analysis['state_abbr'].notna()].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Market Density by State")
                if not state_analysis_valid.empty:
                    fig = px.choropleth(
                        state_analysis_valid, 
                        locations='state_abbr',
                        color='Dealer_Count',
                        hover_name='state',
                        hover_data={'Dealer_Count': True, 'Avg_Business_Potential': ':.1f', 'state_abbr': False},
                        locationmode='USA-states',
                        title="Heavy Haulers Market Penetration by State",
                        color_continuous_scale="Blues",
                        labels={'Dealer_Count': 'Number of Dealers', 'Avg_Business_Potential': 'Avg Business Potential'}
                    )
                    fig.update_layout(
                        geo_scope="usa",
                        height=500,
                        title_font_size=14
                    )
                    st.plotly_chart(fig, use_container_width=True, key="choropleth_heat_map")
                else:
                    st.info("No valid state data available for heat map visualization.")
            
            with col2:
                st.subheader("Business Potential vs Market Size")
                if not state_analysis_valid.empty:
                    fig = px.scatter(
                        state_analysis_valid, 
                        x='Dealer_Count', 
                        y='Avg_Business_Potential',
                        size='Avg_Equipment_Types',
                        hover_name='state',
                        title="Market Opportunity Analysis",
                        labels={
                            'Dealer_Count': 'Number of Dealers',
                            'Avg_Business_Potential': 'Average Business Potential Score',
                            'Avg_Equipment_Types': 'Avg Equipment Types'
                        }
                    )
                    fig.update_traces(marker=dict(opacity=0.7))
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True, key="scatter_plot_business_potential")
                else:
                    st.info("No valid state data available for scatter plot visualization.")
            
            # Underserved markets
            st.subheader("🎯 Market Intelligence")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Top Target States")
                if not state_analysis_valid.empty:
                    top_states = state_analysis_valid.head(10)[['state', 'Dealer_Count', 'Avg_Business_Potential', 'Avg_Equipment_Types']]
                    top_states.columns = ['State', 'Dealers', 'Avg Score', 'Avg Equipment Types']
                    st.dataframe(
                        top_states,
                        use_container_width=True,
                        hide_index=True
                    )
                
            with col2:
                st.markdown("### 🎯 Underserved Opportunities")
                # Define underserved as low dealer count but high potential
                if not state_analysis_valid.empty:
                    median_dealers = state_analysis_valid['Dealer_Count'].median()
                    median_potential = state_analysis_valid['Avg_Business_Potential'].median()
                    
                    underserved = state_analysis_valid[
                        (state_analysis_valid['Dealer_Count'] < median_dealers) &
                        (state_analysis_valid['Avg_Business_Potential'] > median_potential)
                    ].head(5)
                    
                    if not underserved.empty:
                        st.markdown("**States with high potential but fewer competitors:**")
                        for _, row in underserved.iterrows():
                            st.markdown(f"• **{row['state']}**: {int(row['Dealer_Count'])} dealers, {row['Avg_Business_Potential']:.1f} avg score")
                    else:
                        st.info("No clearly underserved markets identified. Consider expanding in top states.")
            
            # Geographic distribution bar chart as backup
            st.subheader("📊 Dealer Distribution by State")
            if not state_analysis_valid.empty:
                top_15_states = state_analysis_valid.head(15)
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
                st.plotly_chart(fig, use_container_width=True, key="fallback_distribution_chart")
        
        with tab4:
            st.header("🤖 AI-Powered Business Insights")
            st.markdown("**Get intelligent analysis of your equipment dealer market**")
            
            # OpenAI configuration
            openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                         value=os.getenv("OPENAI_API_KEY", ""))
            
            if openai_api_key:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Market Analysis")
                    if st.button("🔍 Generate Market Report", key="market_report"):
                        with st.spinner("Analyzing market data..."):
                            # Prepare market summary
                            total_dealers = len(filtered_df)
                            top_states = state_analysis.head(5)['state'].tolist()
                            equipment_dist = Counter()
                            for eq_list in filtered_df['equipment_types']:
                                if pd.notna(eq_list):
                                    for eq in eq_list.split(', '):
                                        equipment_dist[eq] += 1
                            
                            market_summary = f"""
                            Heavy Haulers Equipment Logistics - Market Analysis:
                            
                            Total Dealers: {total_dealers:,}
                            Top 5 States: {', '.join(top_states)}
                            Equipment Distribution: {dict(equipment_dist.most_common(5))}
                            Average Business Potential: {filtered_df['business_potential'].mean():.1f}
                            High Priority Targets: {len(filtered_df[filtered_df['priority_level'] == 'High'])}
                            """
                            
                            try:
                                client = openai.OpenAI(api_key=openai_api_key)
                                response = client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "You are a business analyst specializing in equipment logistics and heavy hauling services. Provide actionable insights for sales and marketing teams."},
                                        {"role": "user", "content": f"Analyze this equipment dealer market data and provide strategic insights for Heavy Haulers Equipment Logistics company's sales team: {market_summary}"}
                                    ],
                                    max_tokens=500
                                )
                                
                                st.success("Market Analysis Complete!")
                                st.markdown("### 📈 Strategic Insights")
                                st.write(response.choices[0].message.content)
                                
                            except Exception as e:
                                st.error(f"API Error: {str(e)}")
                
                with col2:
                    st.subheader("💼 Individual Dealer Analysis")
                    
                    # Select a high-priority dealer for detailed analysis
                    high_priority_dealers = filtered_df[filtered_df['priority_level'] == 'High']
                    if not high_priority_dealers.empty:
                        selected_dealer = st.selectbox(
                            "Select dealer for AI analysis",
                            options=high_priority_dealers['name'].tolist()
                        )
                        
                        if st.button("🔍 Analyze Selected Dealer", key="dealer_analysis"):
                            dealer_info = high_priority_dealers[high_priority_dealers['name'] == selected_dealer].iloc[0]
                            
                            dealer_summary = f"""
                            Dealer: {dealer_info['name']}
                            Location: {dealer_info['location']}
                            Equipment Types: {dealer_info['equipment_types']}
                            Business Potential Score: {dealer_info['business_potential']}
                            Has Phone: {'Yes' if dealer_info['phone'] else 'No'}
                            Has Website: {'Yes' if dealer_info['website'] else 'No'}
                            Number of Sources: {dealer_info['num_sources']}
                            """
                            
                            with st.spinner("Analyzing dealer profile..."):
                                try:
                                    client = openai.OpenAI(api_key=openai_api_key)
                                    response = client.chat.completions.create(
                                        model="gpt-3.5-turbo",
                                        messages=[
                                            {"role": "system", "content": "You are a sales strategist for Heavy Haulers Equipment Logistics. Provide specific outreach recommendations and talking points for approaching equipment dealers."},
                                            {"role": "user", "content": f"Create a cold outreach strategy for this equipment dealer. Include talking points about how Heavy Haulers can help with their equipment transportation needs: {dealer_summary}"}
                                        ],
                                        max_tokens=400
                                    )
                                    
                                    st.success(f"Analysis for {selected_dealer}")
                                    st.markdown("### 🎯 Outreach Strategy")
                                    st.write(response.choices[0].message.content)
                                    
                                except Exception as e:
                                    st.error(f"API Error: {str(e)}")
            
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
                - Avg business potential: {row['Avg_Business_Potential']:.0f}
                - Focus on multi-equipment dealers
                
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
                search_term = st.text_input("🔍 Search dealers", placeholder="Company name, location, or equipment type")
            with col2:
                show_only_priority = st.checkbox("Show only high priority prospects")
            
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
            
            # Contact table with action buttons
            st.subheader(f"📞 Contact Database ({len(display_df)} dealers)")
            
            # Add call status tracking (simulated)
            if 'call_status' not in st.session_state:
                st.session_state.call_status = {}
            
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
                if st.button("📋 Export Current View"):
                    csv = display_df[['name', 'phone', 'location', 'equipment_types', 'website']].to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_contacts.csv", "text/csv")
            
            with col2:
                if st.button("📞 Phone List Only"):
                    phone_contacts = display_df[display_df['phone'] != '']
                    csv = phone_contacts[['name', 'phone', 'location']].to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_phone_list.csv", "text/csv")
            
            with col3:
                if st.button("🏆 High Priority Only"):
                    high_priority = display_df[display_df['priority_level'] == 'High']
                    csv = high_priority[['name', 'phone', 'location', 'equipment_types']].to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_priority_targets.csv", "text/csv")
            
            with col4:
                if st.button("📧 Email Format"):
                    # Format for email marketing tools
                    email_format = display_df[['name', 'location', 'equipment_types']].copy()
                    email_format['subject_line'] = "Heavy Equipment Transportation Solutions for " + email_format['name']
                    csv = email_format.to_csv(index=False)
                    st.download_button("Download CSV", csv, "heavy_haulers_email_campaign.csv", "text/csv")
    
    else:
        st.error("No data available to display.")
else:
    st.error("Unable to load master contact database.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d;">
    <p>🚛 <strong>Heavy Haulers Equipment Logistics</strong> - Sales Intelligence Dashboard</p>
    <p>Powered by AI-driven market analysis for strategic business development</p>
</div>
""", unsafe_allow_html=True)
